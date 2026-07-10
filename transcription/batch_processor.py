"""Batch processor for transcribing multiple audio files."""
import os
import time
import hashlib
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Callable, Optional, List
from utilities.file_utils import FileUtils
from utilities.format_utils import FormatUtils
from utilities.date_parser import DateParser
from utilities.audio_utils import AudioUtils
from config.constants import STATUS_SKIPPED, BYTES_PER_MB
from config.environment import WAVE_AVAILABLE, MUTAGEN_AVAILABLE

if WAVE_AVAILABLE:
    import wave

try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


class BatchProcessor:
    """Handles batch processing of multiple audio files."""
    
    def __init__(self, transcriber, model_manager):
        """Initialize batch processor.
        
        Args:
            transcriber: Transcriber instance.
            model_manager: ModelManager instance.
        """
        self.transcriber = transcriber
        self.model_manager = model_manager
        self.cancel_requested = False
        
        # Statistics
        self.total_files = 0
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.transcribed_files = 0
        self.processing_times = []
        self.word_counts = []
        self.audio_durations = []
        self.file_sizes_mb = []
        self.total_words = 0
        self.file_words_per_second = []
        self.last_file_metrics = None
        self.scan_plan = []
        self.estimated_total_audio_seconds = 0
        self.estimated_remaining_audio_seconds = 0
        self.estimated_total_words = 0
        self.estimated_remaining_words = 0
        self.estimated_total_files_to_transcribe = 0
        self.estimated_files_remaining_to_transcribe = 0
        self.actual_word_source_files = 0
        self.estimated_word_source_files = 0
        self.pre_scan_summary = {}
        self.start_time = None
        self.failed_files_with_reasons = {}  # Dict of filename -> reason for failure
        self.completed_transcribe_files = 0
        self.completed_transcribe_audio_seconds = 0.0
        self.completed_transcribe_processing_seconds = 0.0
        self.file_speed_ratios = []
        self.current_file_path = None
        self.current_file_step = "idle"
        self.current_file_started_at = None
        self.current_file_audio_duration_seconds = 0.0

    def _set_current_file_state(self, audio_file=None, step=None, start_now=False, audio_duration_seconds=None):
        """Track current-file status for live UI metrics."""
        if audio_file is not None:
            self.current_file_path = audio_file
        if step is not None:
            self.current_file_step = step
        if start_now:
            self.current_file_started_at = time.time()
        if audio_duration_seconds is not None:
            self.current_file_audio_duration_seconds = max(0.0, float(audio_duration_seconds or 0.0))

    def _quick_content_fingerprint(self, file_path, chunk_size=128 * 1024):
        """Create a fast fingerprint from file size + first/last chunk."""
        file_size = os.path.getsize(file_path)
        hasher = hashlib.sha1()

        with open(file_path, 'rb') as f:
            if file_size <= (2 * chunk_size):
                hasher.update(f.read())
            else:
                first_chunk = f.read(chunk_size)
                f.seek(max(file_size - chunk_size, 0), os.SEEK_SET)
                last_chunk = f.read(chunk_size)
                hasher.update(first_chunk)
                hasher.update(last_chunk)

        return f"{file_size}:{hasher.hexdigest()}"

    def _full_file_hash(self, file_path, chunk_size=1024 * 1024):
        """Compute full-file hash for precise duplicate verification."""
        hasher = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def _probe_audio_duration_seconds(self, audio_file):
        """Probe duration quickly from metadata/header without full decode."""
        file_ext = os.path.splitext(audio_file)[1].lower()

        if MutagenFile is not None and MUTAGEN_AVAILABLE:
            try:
                audio_obj = MutagenFile(audio_file)
                if audio_obj is not None and getattr(audio_obj, 'info', None):
                    length = float(getattr(audio_obj.info, 'length', 0.0) or 0.0)
                    if length > 0:
                        return length
            except Exception:
                pass

        if file_ext == '.wav' and WAVE_AVAILABLE:
            try:
                with wave.open(audio_file, 'rb') as wav_file:
                    frame_rate = wav_file.getframerate()
                    total_frames = wav_file.getnframes()
                    if frame_rate and frame_rate > 0:
                        return float(total_frames / frame_rate)
            except Exception:
                pass

        return 0.0

    def _build_output_file_path(self, audio_file, input_folder, output_folder, options):
        """Build output transcript path for a given audio file."""
        if options.get('preserve_structure', False):
            rel_path = FileUtils.get_relative_path(audio_file, input_folder)
            return os.path.join(output_folder, os.path.splitext(rel_path)[0] + '.txt')

        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        return os.path.join(output_folder, base_name + '.txt')

    def _write_text_atomic(self, output_file, text):
        """Write text atomically to avoid partial output files on interruption."""
        FileUtils.ensure_directory(output_file)
        target_dir = os.path.dirname(os.path.abspath(output_file))
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=target_dir or None,
                delete=False,
                newline='\n'
            ) as temp_file:
                temp_path = temp_file.name
                temp_file.write(text)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, output_file)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _count_words_in_existing_transcript(self, transcript_file):
        """Count words in an existing transcript file, if readable."""
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                return FormatUtils.count_words(f.read())
        except Exception:
            return None

    def pre_scan_batch(self, input_folder, output_folder, options, log_callback=None):
        """Pre-scan batch files for skip status and ETA-related estimates."""
        audio_files = FileUtils.get_audio_files(input_folder, options.get('recursive', False))
        estimated_wpm = options.get('estimated_wpm', 150)
        estimated_words_per_mb = options.get('estimated_words_per_mb', 1200)
        estimated_seconds_per_mb = options.get('estimated_seconds_per_mb', 64)
        skip_duplicates = options.get('skip_duplicates', True)
        report_duplicates = options.get('report_duplicates', False)
        duplicate_scan_enabled = bool(skip_duplicates or report_duplicates)

        try:
            min_duplicate_size_mb = max(0.0, float(options.get('duplicate_min_size_mb', 0.5)))
        except (TypeError, ValueError):
            min_duplicate_size_mb = 0.5
        min_duplicate_size_bytes = int(min_duplicate_size_mb * BYTES_PER_MB)

        try:
            max_duplicate_group_files = max(2, int(options.get('duplicate_max_group_files', 200)))
        except (TypeError, ValueError):
            max_duplicate_group_files = 200

        if log_callback:
            log_callback(f"🔎 Pre-scan started for {len(audio_files)} file(s)")

        # Build output-path map early to detect collisions before processing.
        output_to_audio_files = defaultdict(list)
        normalized_to_output = {}
        for audio_file in audio_files:
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            norm_output = os.path.normcase(os.path.abspath(output_file))
            output_to_audio_files[norm_output].append(audio_file)
            if norm_output not in normalized_to_output:
                normalized_to_output[norm_output] = os.path.abspath(output_file)

        output_collisions = []
        for norm_output, sources in output_to_audio_files.items():
            if len(sources) > 1:
                output_collisions.append({
                    'output_file': normalized_to_output.get(norm_output, norm_output),
                    'audio_files': sorted(sources)
                })

        # Fast duplicate-content scan: size -> quick fingerprint -> full hash for ties.
        # Heuristics:
        # - Skip duplicate scan entirely unless it is needed.
        # - Ignore very small files where hashing overhead rarely pays off.
        # - Skip abnormally large same-size groups to keep pre-scan bounded.
        duplicate_groups = []
        duplicate_skip_set = set()
        skipped_large_duplicate_groups = 0
        if duplicate_scan_enabled:
            files_by_size = defaultdict(list)
            for audio_file in audio_files:
                try:
                    file_size = os.path.getsize(audio_file)
                    if file_size < min_duplicate_size_bytes:
                        continue
                    files_by_size[file_size].append(audio_file)
                except Exception:
                    continue

            candidate_groups = [group for group in files_by_size.values() if len(group) > 1]
            for size_group in candidate_groups:
                if len(size_group) > max_duplicate_group_files:
                    skipped_large_duplicate_groups += 1
                    continue

                quick_groups = defaultdict(list)
                for audio_file in size_group:
                    try:
                        quick_fp = self._quick_content_fingerprint(audio_file)
                        quick_groups[quick_fp].append(audio_file)
                    except Exception:
                        continue

                for quick_group in quick_groups.values():
                    if len(quick_group) <= 1:
                        continue

                    hash_groups = defaultdict(list)
                    for audio_file in quick_group:
                        try:
                            full_hash = self._full_file_hash(audio_file)
                            hash_groups[full_hash].append(audio_file)
                        except Exception:
                            continue

                    for exact_group in hash_groups.values():
                        if len(exact_group) <= 1:
                            continue
                        sorted_group = sorted(exact_group)
                        duplicate_groups.append({'audio_files': sorted_group})
                        if skip_duplicates:
                            duplicate_skip_set.update(sorted_group[1:])

            if log_callback and skipped_large_duplicate_groups > 0:
                log_callback(
                    f"⚠️ Duplicate scan skipped {skipped_large_duplicate_groups} large same-size group(s) "
                    f"(limit={max_duplicate_group_files}, min_size={min_duplicate_size_mb:.2f}MB)"
                )

        files = []
        estimated_total_audio_seconds = 0.0
        estimated_total_words = 0
        estimated_files_to_transcribe = 0

        file_sizes_mb = {}
        duration_by_file = {}
        for audio_file in audio_files:
            try:
                file_sizes_mb[audio_file] = os.path.getsize(audio_file) / BYTES_PER_MB
            except Exception:
                file_sizes_mb[audio_file] = 0.0

        # Probe durations concurrently to keep pre-scan fast on large batches.
        max_workers = min(8, max(1, os.cpu_count() or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self._probe_audio_duration_seconds, audio_file): audio_file for audio_file in audio_files}
            for future in as_completed(future_map):
                audio_file = future_map[future]
                duration = 0.0
                try:
                    duration = float(future.result() or 0.0)
                except Exception:
                    duration = 0.0

                if duration <= 0:
                    duration = float(file_sizes_mb.get(audio_file, 0.0) * estimated_seconds_per_mb)
                duration_by_file[audio_file] = duration

        for audio_file in audio_files:
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            skip_existing = options.get('skip_existing', True) and os.path.exists(output_file)
            skip_duplicate = audio_file in duplicate_skip_set
            will_skip = skip_existing or skip_duplicate

            file_size_mb = file_sizes_mb.get(audio_file, 0.0)
            duration_seconds = duration_by_file.get(audio_file, 0.0)
            if duration_seconds > 0:
                estimated_words = int((duration_seconds / 60.0) * estimated_wpm)
            else:
                estimated_words = int(file_size_mb * estimated_words_per_mb)

            skip_reason = None
            if skip_existing:
                skip_reason = 'existing_transcript'
            elif skip_duplicate:
                skip_reason = 'duplicate_content'

            files.append({
                'audio_file': audio_file,
                'output_file': output_file,
                'will_skip': will_skip,
                'will_skip_existing': skip_existing,
                'will_skip_duplicate': skip_duplicate,
                'skip_reason': skip_reason,
                'file_size_mb': file_size_mb,
                'estimated_duration_seconds': duration_seconds,
                'estimated_words': estimated_words,
                'existing_transcript_words': None
            })

            if not will_skip:
                estimated_files_to_transcribe += 1
                estimated_total_audio_seconds += duration_seconds
                estimated_total_words += estimated_words

        pre_scan_data = {
            'files': files,
            'total_files': len(files),
            'estimated_total_audio_seconds': estimated_total_audio_seconds,
            'estimated_total_words': estimated_total_words,
            'estimated_total_files_to_transcribe': estimated_files_to_transcribe,
            'estimated_total_files_to_skip': len(files) - estimated_files_to_transcribe,
            'existing_transcript_skips': sum(1 for f in files if f.get('will_skip_existing')),
            'duplicate_content_skips': sum(1 for f in files if f.get('will_skip_duplicate')),
            'duplicate_content_groups': duplicate_groups,
            'output_path_collisions': output_collisions,
            'cache_used': False,
            'cache_cached_at': None
        }

        self.pre_scan_summary = {
            'existing_transcript_skips': pre_scan_data['existing_transcript_skips'],
            'duplicate_content_skips': pre_scan_data['duplicate_content_skips'],
            'duplicate_content_groups': pre_scan_data['duplicate_content_groups'],
            'output_path_collisions': pre_scan_data['output_path_collisions']
        }

        if log_callback:
            if pre_scan_data['duplicate_content_groups']:
                log_callback(
                    f"🧬 Duplicate-content groups found: {len(pre_scan_data['duplicate_content_groups'])} "
                    f"({pre_scan_data['duplicate_content_skips']} file(s) marked to skip)"
                )
            if pre_scan_data['output_path_collisions']:
                log_callback(
                    f"⚠️ Output filename collisions: {len(pre_scan_data['output_path_collisions'])}"
                )

            log_callback(
                "📈 Pre-scan complete: "
                f"{pre_scan_data['estimated_total_files_to_transcribe']} to transcribe, "
                f"{pre_scan_data['estimated_total_files_to_skip']} skipped, "
                f"~{FormatUtils.format_time(pre_scan_data['estimated_total_audio_seconds'])} audio"
            )

        return pre_scan_data
    
    def process_batch(self, input_folder, output_folder, options, progress_callback=None, log_callback=None, pre_scan_data=None):
        """Process a batch of audio files.
        
        Args:
            input_folder: Input folder path.
            output_folder: Output folder path.
            options: Dictionary of processing options (detect_date, chars_per_line, skip_existing, 
                    preserve_structure, recursive, create_summary, engine, timestamps_enabled, 
                    timestamp_format, timestamp_interval).
            progress_callback: Optional callback for progress updates (file_num, total, current_file).
            log_callback: Optional callback for log messages.
            
        Returns:
            Dictionary with statistics (total, successful, failed, total_time).
        """
        # Reset statistics
        self.cancel_requested = False
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.transcribed_files = 0
        self.processing_times = []
        self.word_counts = []
        self.audio_durations = []
        self.file_sizes_mb = []
        self.total_words = 0
        self.file_words_per_second = []
        self.last_file_metrics = None
        self.failed_files_with_reasons = {}
        self.start_time = time.time()
        self.scan_plan = []
        self.estimated_total_audio_seconds = 0
        self.estimated_remaining_audio_seconds = 0
        self.estimated_total_words = 0
        self.estimated_remaining_words = 0
        self.estimated_total_files_to_transcribe = 0
        self.estimated_files_remaining_to_transcribe = 0
        self.actual_word_source_files = 0
        self.estimated_word_source_files = 0
        self.pre_scan_summary = {}
        self.completed_transcribe_files = 0
        self.completed_transcribe_audio_seconds = 0.0
        self.completed_transcribe_processing_seconds = 0.0
        self.file_speed_ratios = []
        self.current_file_path = None
        self.current_file_step = "idle"
        self.current_file_started_at = None
        self.current_file_audio_duration_seconds = 0.0
        
        # Use pre-scan data if provided; otherwise compute it now.
        if pre_scan_data is None:
            pre_scan_data = self.pre_scan_batch(input_folder, output_folder, options, log_callback)

        self.scan_plan = pre_scan_data.get('files', [])
        self.total_files = pre_scan_data.get('total_files', len(self.scan_plan))
        self.estimated_total_audio_seconds = pre_scan_data.get('estimated_total_audio_seconds', 0)
        self.estimated_remaining_audio_seconds = self.estimated_total_audio_seconds
        self.estimated_total_words = pre_scan_data.get('estimated_total_words', 0)
        self.estimated_remaining_words = self.estimated_total_words
        self.estimated_total_files_to_transcribe = pre_scan_data.get('estimated_total_files_to_transcribe', 0)
        self.estimated_files_remaining_to_transcribe = self.estimated_total_files_to_transcribe
        self.pre_scan_summary = {
            'existing_transcript_skips': pre_scan_data.get('existing_transcript_skips', 0),
            'duplicate_content_skips': pre_scan_data.get('duplicate_content_skips', 0),
            'duplicate_content_groups': pre_scan_data.get('duplicate_content_groups', []),
            'output_path_collisions': pre_scan_data.get('output_path_collisions', [])
        }
        
        if log_callback:
            log_callback(f"Found {self.total_files} audio files to process")
        
        # Process each file
        for i, file_plan in enumerate(self.scan_plan):
            if self.cancel_requested:
                if log_callback:
                    log_callback("Processing cancelled by user")
                break

            audio_file = file_plan['audio_file']
            self._set_current_file_state(
                audio_file=audio_file,
                step='queued',
                audio_duration_seconds=file_plan.get('estimated_duration_seconds', 0)
            )

            if progress_callback:
                progress_callback(i, self.total_files, audio_file)
            
            # Process the file
            result = self._process_single_file(
                audio_file, input_folder, output_folder, options, log_callback,
                file_plan=file_plan, display_index=i + 1
            )

            status = result.get('status')
            self.last_file_metrics = {
                'file_name': os.path.basename(audio_file),
                'status': status,
                'words': result.get('words', 0),
                'process_time': result.get('process_time', 0),
                'words_per_second': result.get('words_per_second'),
                'duration': result.get('duration', file_plan.get('estimated_duration_seconds', 0) if file_plan else 0),
                'file_size_mb': file_plan.get('file_size_mb'),
                'estimated_duration_seconds': file_plan.get('estimated_duration_seconds'),
                'estimated_words': file_plan.get('estimated_words'),
                'batch_index': i + 1,
                'batch_total': self.total_files,
                'processed_files': self.processed_files,
                'successful_files': self.successful_files,
                'failed_files': self.failed_files,
                'skipped_files': self.skipped_files,
                'total_words': self.total_words
            }
            
            if status in ('success', 'skipped'):
                self.successful_files += 1
            else:
                self.failed_files += 1

            # Consume remaining estimated work for non-skipped files once completed.
            if not file_plan.get('will_skip', False):
                self.completed_transcribe_files += 1
                completed_duration = float(result.get('duration', 0) or 0)
                if completed_duration <= 0:
                    completed_duration = float(file_plan.get('estimated_duration_seconds', 0) or 0)
                self.completed_transcribe_audio_seconds += max(0.0, completed_duration)

                result_process_time = float(result.get('process_time', 0) or 0)
                if result_process_time > 0:
                    self.completed_transcribe_processing_seconds += result_process_time

                self.estimated_remaining_audio_seconds = max(
                    0,
                    self.estimated_remaining_audio_seconds - file_plan.get('estimated_duration_seconds', 0)
                )
                self.estimated_remaining_words = max(
                    0,
                    self.estimated_remaining_words - file_plan.get('estimated_words', 0)
                )
                self.estimated_files_remaining_to_transcribe = max(
                    0,
                    self.estimated_files_remaining_to_transcribe - 1
                )

            self._set_current_file_state(step=status)

            self.processed_files = i + 1

            if progress_callback:
                progress_callback(self.processed_files, self.total_files, audio_file)
        
        total_time = time.time() - self.start_time
        self._set_current_file_state(step='done')
        
        # Create summary if requested
        if options.get('create_summary', True) and not self.cancel_requested:
            self._create_summary(output_folder, total_time, log_callback)
        
        return {
            'total': self.total_files,
            'successful': self.successful_files,
            'failed': self.failed_files,
            'skipped': self.skipped_files,
            'transcribed': self.transcribed_files,
            'total_words': self.total_words,
            'estimated_total_audio_seconds': self.estimated_total_audio_seconds,
            'estimated_total_words': self.estimated_total_words,
            'estimated_total_files_to_transcribe': self.estimated_total_files_to_transcribe,
            'total_time': total_time
        }
    
    def _process_single_file(self, audio_file, input_folder, output_folder, options, log_callback,
                             file_plan=None, display_index=None):
        """Process a single audio file.
        
        Args:
            audio_file: Audio file path.
            input_folder: Input folder path.
            output_folder: Output folder path.
            options: Processing options dictionary.
            log_callback: Optional callback for log messages.
            
        Returns:
            True if successful, False otherwise.
        """
        file_name = os.path.basename(audio_file)

        if display_index is None:
            display_index = self.processed_files
        
        if log_callback:
            log_callback(f"[{display_index}/{self.total_files}] Processing: {file_name}")
        
        start_time = time.time()
        self._set_current_file_state(audio_file=audio_file, step='preparing', start_now=True)
        
        try:
            # Determine output path
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            
            # Skip if exists
            if options.get('skip_existing', True) and os.path.exists(output_file):
                self._set_current_file_state(step='skipped')
                if log_callback:
                    log_callback(f"{STATUS_SKIPPED} Skipped (already exists): {os.path.basename(output_file)}")
                self.skipped_files += 1

                return {
                    'status': 'skipped',
                    'words': 0,
                    'process_time': 0,
                    'words_per_second': None,
                    'duration': file_plan.get('estimated_duration_seconds', 0) if file_plan is not None else 0
                }

            # Skip known duplicate-content files from pre-scan.
            if file_plan is not None and file_plan.get('will_skip_duplicate', False):
                self._set_current_file_state(step='skipped')
                if log_callback:
                    log_callback(f"{STATUS_SKIPPED} Skipped duplicate content: {file_name}")
                self.skipped_files += 1
                est_duration = float(file_plan.get('estimated_duration_seconds', 0) or 0)

                return {
                    'status': 'skipped',
                    'words': 0,
                    'process_time': 0,
                    'words_per_second': None,
                    'duration': est_duration
                }
            
            # Get file size once and reuse to avoid repeated filesystem calls.
            file_size_bytes = os.path.getsize(audio_file)
            file_size = file_size_bytes / BYTES_PER_MB  # MB
            
            # Transcribe (with or without diarization)
            FileUtils.ensure_directory(output_file)
            self._set_current_file_state(step='transcribing')
            
            # Check if diarization is enabled
            if options.get('diarization_enabled', False) and options.get('diarizer'):
                # Transcribe with speaker diarization
                diarizer = options['diarizer']
                num_speakers = options.get('num_speakers')
                result = self.transcriber.transcribe_with_diarization(
                    audio_file, 
                    options.get('engine', 'auto_gpu'),
                    diarizer,
                    num_speakers,
                    options
                )
            else:
                # Regular transcription without diarization
                result = self.transcriber.transcribe_with_metadata(
                    audio_file, 
                    options.get('engine', 'auto_gpu'), 
                    options
                )
            
            # Extract results
            text, language, duration, avg_confidence, audio_metadata = FormatUtils.extract_transcription_results(result)
            
            # Format text if requested
            chars_per_line = options.get('chars_per_line', 80)
            self._set_current_file_state(step='formatting', audio_duration_seconds=duration if duration and duration > 0 else self.current_file_audio_duration_seconds)
            if chars_per_line > 0:
                formatted_text = FormatUtils.format_text_with_line_breaks(text, chars_per_line)
            else:
                formatted_text = text
            
            # Detect date if requested
            detected_date = None
            day_of_week = None
            if options.get('detect_date', True):
                detected_date, day_of_week = DateParser.detect_date_from_filename(file_name)
            
            # Calculate processing time
            process_time = time.time() - start_time
            self.processing_times.append(process_time)

            # Track file metrics for UI/summary reporting
            word_count = FormatUtils.count_words(text)
            self.word_counts.append(word_count)
            self.total_words += word_count
            self.actual_word_source_files += 1
            if duration and duration > 0:
                self.audio_durations.append(duration)
            self.file_sizes_mb.append(file_size)
            self.transcribed_files += 1
            
            # Save with comprehensive metadata using centralized formatter
            self._set_current_file_state(step='writing', audio_duration_seconds=duration if duration and duration > 0 else self.current_file_audio_duration_seconds)
            # Build metadata header using centralized function
            file_size_mb = file_size
            audio_metadata['file_size_bytes'] = file_size_bytes

            # Get GPU info if available
            gpu_available = False
            gpu_name = None
            if hasattr(self.model_manager, 'environment') and self.model_manager.environment.gpu_available:
                gpu_available = True
                gpu_name = self.model_manager.environment.get_gpu_info()['name']

            diarization_requested = options.get('diarization_enabled', False)
            diarization_metadata = {
                'enabled': diarization_requested,
                'requested_speakers': options.get('num_speakers'),
                'detected_speakers': result.get('num_speakers') if isinstance(result, dict) else None,
                'model': 'pyannote/speaker-diarization-3.1' if diarization_requested else None,
                'token_configured': True if diarization_requested else None
            }

            metadata_header = FormatUtils.build_transcript_metadata(
                file_name=file_name,
                audio_metadata=audio_metadata,
                duration=duration,
                process_time=process_time,
                engine=options.get('engine', 'auto_gpu'),
                model=options.get('model', 'base'),
                compute_type=options.get('compute_type', 'float16'),
                language=language,
                avg_confidence=avg_confidence,
                detected_date=detected_date,
                day_of_week=day_of_week,
                gpu_available=gpu_available,
                gpu_name=gpu_name,
                diarization_metadata=diarization_metadata
            )

            self._write_text_atomic(output_file, metadata_header + formatted_text)
            
            if log_callback:
                log_callback(f"✅ Success ({FormatUtils.format_time(process_time)}): {os.path.basename(output_file)}")
            self._set_current_file_state(step='complete', audio_duration_seconds=duration if duration and duration > 0 else self.current_file_audio_duration_seconds)

            words_per_second = (word_count / process_time) if process_time > 0 else 0
            self.file_words_per_second.append(words_per_second)
            if process_time > 0 and duration and duration > 0:
                self.file_speed_ratios.append(float(duration) / float(process_time))

            return {
                'status': 'success',
                'words': word_count,
                'process_time': process_time,
                'words_per_second': words_per_second,
                'duration': duration
            }
            
        except Exception as e:
            # Provide detailed error context for better user debugging
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Build detailed failure message based on error type
            if "audio" in error_msg.lower() or "format" in error_msg.lower():
                reason = "Unsupported audio format or corrupted file"
            elif "memory" in error_msg.lower() or "cuda" in error_msg.lower():
                reason = "Insufficient memory (try smaller model or CPU mode)"
            elif "permission" in error_msg.lower():
                reason = "File permission issue"
            elif "not found" in error_msg.lower():
                reason = "File not found or missing dependency"
            else:
                reason = f"{error_type}: {error_msg}"
            
            # Track failure reason
            self.failed_files_with_reasons[os.path.basename(audio_file)] = reason
            
            if log_callback:
                log_callback(f"❌ Failed [{reason}]: {os.path.basename(audio_file)}")
            self._set_current_file_state(step='failed')

            return {
                'status': 'failed',
                'words': 0,
                'process_time': 0,
                'words_per_second': None,
                'duration': 0
            }
    
    def _create_summary(self, output_folder, total_time, log_callback):
        """Create batch summary report.
        
        Args:
            output_folder: Output folder path.
            total_time: Total processing time.
            log_callback: Optional callback for log messages.
        """
        try:
            report_file = os.path.join(output_folder, "_batch_summary.txt")
            lines = []
            lines.append("BATCH TRANSCRIPTION SUMMARY\n")
            lines.append("=" * 60 + "\n\n")
            lines.append(f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            lines.append(f"Total Files: {self.total_files}\n")
            lines.append(f"Successful: {self.successful_files}\n")
            lines.append(f"Failed: {self.failed_files}\n")
            lines.append(f"Total Time: {FormatUtils.format_time(total_time)}\n")

            if self.processing_times:
                avg_time = sum(self.processing_times) / len(self.processing_times)
                lines.append(f"Average Time per File: {FormatUtils.format_time(avg_time)}\n")

            # Include failure details if there were failures
            if self.failed_files_with_reasons:
                lines.append("\n" + "-" * 60 + "\n")
                lines.append("FAILED FILES\n")
                lines.append("-" * 60 + "\n\n")
                for filename, reason in sorted(self.failed_files_with_reasons.items()):
                    lines.append(f"• {filename}\n")
                    lines.append(f"  Reason: {reason}\n\n")

            self._write_text_atomic(report_file, "".join(lines))
            
            if log_callback:
                log_callback(f"📄 Summary saved: {os.path.basename(report_file)}")
        except Exception as e:
            if log_callback:
                log_callback(f"⚠️  Summary failed: {e}")
    
    def cancel(self):
        """Request cancellation of batch processing."""
        self.cancel_requested = True
    
    def get_statistics(self):
        """Get current processing statistics.
        
        Returns:
            Dictionary with current statistics.
        """
        processing_time_total = sum(self.processing_times)
        observed_audio_seconds = sum(self.audio_durations)
        observed_speed_ratio = (observed_audio_seconds / processing_time_total) if processing_time_total > 0 else 0.0
        recent_speed_ratios = self.file_speed_ratios[-3:]
        recent_speed_ratio = (sum(recent_speed_ratios) / len(recent_speed_ratios)) if recent_speed_ratios else 0.0
        current_file_elapsed = 0.0
        if self.current_file_started_at is not None:
            current_file_elapsed = max(0.0, time.time() - self.current_file_started_at)

        return {
            'total': self.total_files,
            'processed': self.processed_files,
            'successful': self.successful_files,
            'failed': self.failed_files,
            'skipped': self.skipped_files,
            'transcribed': self.transcribed_files,
            'total_words': self.total_words,
            'processed_audio_seconds': observed_audio_seconds,
            'processing_times': self.processing_times.copy(),
            'word_counts': self.word_counts.copy(),
            'audio_durations': self.audio_durations.copy(),
            'file_sizes_mb': self.file_sizes_mb.copy(),
            'file_words_per_second': self.file_words_per_second.copy(),
            'last_file_metrics': self.last_file_metrics.copy() if self.last_file_metrics else None,
            'estimated_total_audio_seconds': self.estimated_total_audio_seconds,
            'estimated_remaining_audio_seconds': self.estimated_remaining_audio_seconds,
            'estimated_total_words': self.estimated_total_words,
            'estimated_remaining_words': self.estimated_remaining_words,
            'estimated_total_files_to_transcribe': self.estimated_total_files_to_transcribe,
            'estimated_files_remaining_to_transcribe': self.estimated_files_remaining_to_transcribe,
            'completed_transcribe_files': self.completed_transcribe_files,
            'completed_transcribe_audio_seconds': self.completed_transcribe_audio_seconds,
            'completed_transcribe_processing_seconds': self.completed_transcribe_processing_seconds,
            'observed_speed_ratio': observed_speed_ratio,
            'recent_speed_ratio': recent_speed_ratio,
            'recent_speed_sample_size': len(recent_speed_ratios),
            'eta_baseline_ready': observed_speed_ratio > 0,
            'current_file': {
                'path': self.current_file_path,
                'name': os.path.basename(self.current_file_path) if self.current_file_path else None,
                'step': self.current_file_step,
                'elapsed_seconds': current_file_elapsed,
                'audio_duration_seconds': self.current_file_audio_duration_seconds
            },
            'actual_word_source_files': self.actual_word_source_files,
            'estimated_word_source_files': self.estimated_word_source_files,
            'pre_scan_summary': {
                'existing_transcript_skips': self.pre_scan_summary.get('existing_transcript_skips', 0),
                'duplicate_content_skips': self.pre_scan_summary.get('duplicate_content_skips', 0),
                'duplicate_content_groups': list(self.pre_scan_summary.get('duplicate_content_groups', [])),
                'output_path_collisions': list(self.pre_scan_summary.get('output_path_collisions', []))
            },
            'failed_reasons': self.failed_files_with_reasons.copy(),
            'elapsed_seconds': (time.time() - self.start_time) if self.start_time else 0
        }

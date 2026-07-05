"""Batch processor for transcribing multiple audio files."""
import hashlib
import json
import os
import time
from typing import Dict, Callable, Optional, List
from utilities.file_utils import FileUtils
from utilities.format_utils import FormatUtils
from utilities.date_parser import DateParser
from utilities.audio_utils import AudioUtils
from config.constants import STATUS_SKIPPED, BYTES_PER_MB


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
        self.start_time = None
        self.failed_files_with_reasons = {}  # Dict of filename -> reason for failure

        # Pre-scan cache (persistent on disk)
        self._cache_version = 1
        self._scan_cache_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".batch_scan_cache.json"
        )
        self._scan_cache = self._load_scan_cache()

    def _load_scan_cache(self):
        """Load pre-scan cache from disk."""
        default_cache = {
            'version': self._cache_version,
            'plans': {},
            'audio_metadata': {},
            'transcript_words': {}
        }

        try:
            if not os.path.exists(self._scan_cache_file):
                return default_cache

            with open(self._scan_cache_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)

            if not isinstance(raw, dict) or raw.get('version') != self._cache_version:
                return default_cache

            default_cache['plans'] = raw.get('plans', {}) if isinstance(raw.get('plans', {}), dict) else {}
            default_cache['audio_metadata'] = raw.get('audio_metadata', {}) if isinstance(raw.get('audio_metadata', {}), dict) else {}
            default_cache['transcript_words'] = raw.get('transcript_words', {}) if isinstance(raw.get('transcript_words', {}), dict) else {}
            return default_cache
        except Exception:
            return default_cache

    def _save_scan_cache(self):
        """Persist pre-scan cache to disk."""
        try:
            payload = {
                'version': self._cache_version,
                'plans': self._scan_cache.get('plans', {}),
                'audio_metadata': self._scan_cache.get('audio_metadata', {}),
                'transcript_words': self._scan_cache.get('transcript_words', {})
            }
            with open(self._scan_cache_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
        except Exception:
            # Cache is best-effort only.
            pass

    def _normalize_path(self, path):
        """Normalize path for stable cache keys on Windows/macOS/Linux."""
        return os.path.normcase(os.path.abspath(path))

    def _get_file_signature(self, path):
        """Return lightweight file signature (exists, size, mtime_ns)."""
        try:
            st = os.stat(path)
            return {
                'exists': True,
                'size': int(st.st_size),
                'mtime_ns': int(st.st_mtime_ns)
            }
        except Exception:
            return {
                'exists': False,
                'size': 0,
                'mtime_ns': 0
            }

    def _build_plan_cache_key(self, input_folder, output_folder, options):
        """Build cache key for a batch pre-scan plan."""
        key_data = {
            'input_folder': self._normalize_path(input_folder),
            'output_folder': self._normalize_path(output_folder),
            'recursive': bool(options.get('recursive', False)),
            'preserve_structure': bool(options.get('preserve_structure', False)),
            'skip_existing': bool(options.get('skip_existing', True)),
            'estimated_wpm': int(options.get('estimated_wpm', 150)),
            'estimated_words_per_mb': int(options.get('estimated_words_per_mb', 1200)),
            'estimated_seconds_per_mb': int(options.get('estimated_seconds_per_mb', 64))
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode('utf-8')).hexdigest()

    def _build_plan_fingerprint(self, audio_files, input_folder, output_folder, options):
        """Build fast fingerprint from current audio/transcript file states."""
        file_entries = []
        for audio_file in audio_files:
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            file_entries.append({
                'audio_file': self._normalize_path(audio_file),
                'audio_sig': self._get_file_signature(audio_file),
                'output_file': self._normalize_path(output_file),
                'output_exists': os.path.exists(output_file)
            })

        fingerprint_source = {
            'files': file_entries,
            'skip_existing': bool(options.get('skip_existing', True)),
            'estimated_wpm': int(options.get('estimated_wpm', 150)),
            'estimated_words_per_mb': int(options.get('estimated_words_per_mb', 1200)),
            'estimated_seconds_per_mb': int(options.get('estimated_seconds_per_mb', 64))
        }
        return hashlib.sha256(json.dumps(fingerprint_source, sort_keys=True).encode('utf-8')).hexdigest()

    def _get_cached_audio_duration(self, audio_file):
        """Get cached audio duration when file signature matches."""
        key = self._normalize_path(audio_file)
        cache_entry = self._scan_cache.get('audio_metadata', {}).get(key)
        if not cache_entry:
            return None

        sig = self._get_file_signature(audio_file)
        if not sig['exists']:
            return None

        if cache_entry.get('size') == sig['size'] and cache_entry.get('mtime_ns') == sig['mtime_ns']:
            return float(cache_entry.get('duration_seconds') or 0.0)
        return None

    def _set_cached_audio_duration(self, audio_file, duration_seconds):
        """Store audio duration with file signature."""
        key = self._normalize_path(audio_file)
        sig = self._get_file_signature(audio_file)
        if not sig['exists']:
            return

        self._scan_cache.setdefault('audio_metadata', {})[key] = {
            'size': sig['size'],
            'mtime_ns': sig['mtime_ns'],
            'duration_seconds': float(duration_seconds or 0.0)
        }

    def _get_cached_transcript_words(self, transcript_file):
        """Get cached transcript word count when file signature matches."""
        key = self._normalize_path(transcript_file)
        cache_entry = self._scan_cache.get('transcript_words', {}).get(key)
        if not cache_entry:
            return None

        sig = self._get_file_signature(transcript_file)
        if not sig['exists']:
            return None

        if cache_entry.get('size') == sig['size'] and cache_entry.get('mtime_ns') == sig['mtime_ns']:
            return int(cache_entry.get('word_count') or 0)
        return None

    def _set_cached_transcript_words(self, transcript_file, word_count):
        """Store transcript word count with file signature."""
        key = self._normalize_path(transcript_file)
        sig = self._get_file_signature(transcript_file)
        if not sig['exists']:
            return

        self._scan_cache.setdefault('transcript_words', {})[key] = {
            'size': sig['size'],
            'mtime_ns': sig['mtime_ns'],
            'word_count': int(word_count or 0)
        }

    def _build_output_file_path(self, audio_file, input_folder, output_folder, options):
        """Build output transcript path for a given audio file."""
        if options.get('preserve_structure', False):
            rel_path = FileUtils.get_relative_path(audio_file, input_folder)
            return os.path.join(output_folder, os.path.splitext(rel_path)[0] + '.txt')

        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        return os.path.join(output_folder, base_name + '.txt')

    def _count_words_in_existing_transcript(self, transcript_file):
        """Count words in an existing transcript file, if readable."""
        cached = self._get_cached_transcript_words(transcript_file)
        if cached is not None:
            return cached

        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                count = FormatUtils.count_words(f.read())
                self._set_cached_transcript_words(transcript_file, count)
                return count
        except Exception:
            return None

    def pre_scan_batch(self, input_folder, output_folder, options, log_callback=None):
        """Pre-scan batch files for skip status and ETA-related estimates."""
        audio_files = FileUtils.get_audio_files(input_folder, options.get('recursive', False))
        estimated_wpm = options.get('estimated_wpm', 150)
        estimated_words_per_mb = options.get('estimated_words_per_mb', 1200)
        estimated_seconds_per_mb = options.get('estimated_seconds_per_mb', 64)

        plan_key = self._build_plan_cache_key(input_folder, output_folder, options)
        plan_fingerprint = self._build_plan_fingerprint(audio_files, input_folder, output_folder, options)

        plan_cache = self._scan_cache.get('plans', {}).get(plan_key)
        if plan_cache and plan_cache.get('fingerprint') == plan_fingerprint:
            if log_callback:
                log_callback(f"⚡ Pre-scan cache hit for {len(audio_files)} file(s)")
            cached = plan_cache.get('pre_scan_data', {'files': [], 'total_files': 0}).copy()
            cached['cache_used'] = True
            cached['cache_cached_at'] = plan_cache.get('cached_at')
            return cached

        files = []
        estimated_total_audio_seconds = 0.0
        estimated_total_words = 0
        estimated_files_to_transcribe = 0

        if log_callback:
            log_callback(f"🔎 Fast pre-scan started for {len(audio_files)} file(s) (size-first heuristic)")

        for audio_file in audio_files:
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            will_skip = options.get('skip_existing', True) and os.path.exists(output_file)

            file_size_mb = os.path.getsize(audio_file) / BYTES_PER_MB
            duration_seconds = 0.0

            # Performance-first: do not decode audio in pre-scan.
            # Use cached duration when available, otherwise estimate from file size.
            cached_duration = self._get_cached_audio_duration(audio_file)
            if cached_duration is not None and cached_duration > 0:
                duration_seconds = cached_duration
            else:
                duration_seconds = float(file_size_mb * estimated_seconds_per_mb)

            transcript_word_count = None
            if duration_seconds > 0:
                estimated_words = int((duration_seconds / 60.0) * estimated_wpm)
            else:
                estimated_words = int(file_size_mb * estimated_words_per_mb)

            files.append({
                'audio_file': audio_file,
                'output_file': output_file,
                'will_skip': will_skip,
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
            'cache_used': False,
            'cache_cached_at': None
        }

        if log_callback:
            log_callback(
                "📈 Pre-scan complete: "
                f"{pre_scan_data['estimated_total_files_to_transcribe']} to transcribe, "
                f"{pre_scan_data['estimated_total_files_to_skip']} skipped, "
                f"~{FormatUtils.format_time(pre_scan_data['estimated_total_audio_seconds'])} audio"
            )

        self._scan_cache.setdefault('plans', {})[plan_key] = {
            'fingerprint': plan_fingerprint,
            'pre_scan_data': pre_scan_data,
            'cached_at': int(time.time())
        }
        self._save_scan_cache()

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
        
        if log_callback:
            log_callback(f"Found {self.total_files} audio files to process")
        
        # Process each file
        for i, file_plan in enumerate(self.scan_plan):
            if self.cancel_requested:
                if log_callback:
                    log_callback("Processing cancelled by user")
                break

            audio_file = file_plan['audio_file']

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
                'words_per_second': result.get('words_per_second')
            }
            
            if status in ('success', 'skipped'):
                self.successful_files += 1
            else:
                self.failed_files += 1

            # Consume remaining estimated work for non-skipped files once completed.
            if not file_plan.get('will_skip', False):
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

            self.processed_files = i + 1

            if progress_callback:
                progress_callback(self.processed_files, self.total_files, audio_file)
        
        total_time = time.time() - self.start_time
        
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
        
        try:
            # Determine output path
            output_file = self._build_output_file_path(audio_file, input_folder, output_folder, options)
            
            # Skip if exists
            if options.get('skip_existing', True) and os.path.exists(output_file):
                if log_callback:
                    log_callback(f"{STATUS_SKIPPED} Skipped (already exists): {os.path.basename(output_file)}")
                self.skipped_files += 1

                # If transcript already exists, use measured word count from pre-scan when available.
                skip_words = 0
                if file_plan is not None:
                    existing_words = file_plan.get('existing_transcript_words')
                    estimated_words = file_plan.get('estimated_words', 0)
                    skip_words = existing_words if existing_words is not None else estimated_words

                    est_duration = file_plan.get('estimated_duration_seconds', 0)
                    if est_duration > 0:
                        self.audio_durations.append(est_duration)

                if skip_words and skip_words > 0:
                    self.word_counts.append(int(skip_words))
                    self.total_words += int(skip_words)
                    if file_plan is not None and file_plan.get('existing_transcript_words') is not None:
                        self.actual_word_source_files += 1
                    else:
                        self.estimated_word_source_files += 1

                return {
                    'status': 'skipped',
                    'words': int(skip_words) if skip_words else 0,
                    'process_time': 0,
                    'words_per_second': None
                }
            
            # Get file size
            file_size = os.path.getsize(audio_file) / BYTES_PER_MB  # MB
            
            # Transcribe (with or without diarization)
            FileUtils.ensure_directory(output_file)
            
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
            with open(output_file, 'w', encoding='utf-8') as f:
                # Build metadata header using centralized function
                file_size_mb = os.path.getsize(audio_file) / BYTES_PER_MB
                audio_metadata['file_size_bytes'] = os.path.getsize(audio_file)
                
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
                f.write(metadata_header)
                f.write(formatted_text)
            
            if log_callback:
                log_callback(f"✅ Success ({FormatUtils.format_time(process_time)}): {os.path.basename(output_file)}")

            words_per_second = (word_count / process_time) if process_time > 0 else 0
            self.file_words_per_second.append(words_per_second)

            return {
                'status': 'success',
                'words': word_count,
                'process_time': process_time,
                'words_per_second': words_per_second
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

            return {
                'status': 'failed',
                'words': 0,
                'process_time': 0,
                'words_per_second': None
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
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("BATCH TRANSCRIPTION SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Files: {self.total_files}\n")
                f.write(f"Successful: {self.successful_files}\n")
                f.write(f"Failed: {self.failed_files}\n")
                f.write(f"Total Time: {FormatUtils.format_time(total_time)}\n")
                
                if self.processing_times:
                    avg_time = sum(self.processing_times) / len(self.processing_times)
                    f.write(f"Average Time per File: {FormatUtils.format_time(avg_time)}\n")
                
                # Include failure details if there were failures
                if self.failed_files_with_reasons:
                    f.write("\n" + "-" * 60 + "\n")
                    f.write("FAILED FILES\n")
                    f.write("-" * 60 + "\n\n")
                    for filename, reason in sorted(self.failed_files_with_reasons.items()):
                        f.write(f"• {filename}\n")
                        f.write(f"  Reason: {reason}\n\n")
            
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
        return {
            'total': self.total_files,
            'processed': self.processed_files,
            'successful': self.successful_files,
            'failed': self.failed_files,
            'skipped': self.skipped_files,
            'transcribed': self.transcribed_files,
            'total_words': self.total_words,
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
            'actual_word_source_files': self.actual_word_source_files,
            'estimated_word_source_files': self.estimated_word_source_files,
            'failed_reasons': self.failed_files_with_reasons.copy()
        }

"""Batch processor for transcribing multiple audio files."""
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
        self.processing_times = []
        self.start_time = None
        self.failed_files_with_reasons = {}  # Dict of filename -> reason for failure
    
    def process_batch(self, input_folder, output_folder, options, progress_callback=None, log_callback=None):
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
        self.processing_times = []
        self.failed_files_with_reasons = {}
        self.start_time = time.time()
        
        # Get audio files
        audio_files = FileUtils.get_audio_files(input_folder, options.get('recursive', False))
        self.total_files = len(audio_files)
        
        if log_callback:
            log_callback(f"Found {self.total_files} audio files to process")
        
        # Process each file
        for i, audio_file in enumerate(audio_files):
            if self.cancel_requested:
                if log_callback:
                    log_callback("Processing cancelled by user")
                break
            
            self.processed_files = i + 1
            
            if progress_callback:
                progress_callback(self.processed_files, self.total_files, audio_file)
            
            # Process the file
            success = self._process_single_file(
                audio_file, input_folder, output_folder, options, log_callback
            )
            
            if success:
                self.successful_files += 1
            else:
                self.failed_files += 1
        
        total_time = time.time() - self.start_time
        
        # Create summary if requested
        if options.get('create_summary', True) and not self.cancel_requested:
            self._create_summary(output_folder, total_time, log_callback)
        
        return {
            'total': self.total_files,
            'successful': self.successful_files,
            'failed': self.failed_files,
            'total_time': total_time
        }
    
    def _process_single_file(self, audio_file, input_folder, output_folder, options, log_callback):
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
        
        if log_callback:
            log_callback(f"[{self.processed_files}/{self.total_files}] Processing: {file_name}")
        
        start_time = time.time()
        
        try:
            # Determine output path
            if options.get('preserve_structure', False):
                rel_path = FileUtils.get_relative_path(audio_file, input_folder)
                output_file = os.path.join(output_folder, os.path.splitext(rel_path)[0] + '.txt')
            else:
                base_name = os.path.splitext(file_name)[0]
                output_file = os.path.join(output_folder, base_name + '.txt')
            
            # Skip if exists
            if options.get('skip_existing', True) and os.path.exists(output_file):
                if log_callback:
                    log_callback(f"{STATUS_SKIPPED} Skipped (already exists): {os.path.basename(output_file)}")
                self.processing_times.append(0)
                return True
            
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
            
            return True
            
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
            
            return False
    
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
            'processing_times': self.processing_times.copy()
        }

"""Batch processor for transcribing multiple audio files."""
import os
import time
from utilities.file_utils import FileUtils
from utilities.format_utils import FormatUtils
from utilities.date_parser import DateParser
from utilities.audio_utils import AudioUtils


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
                    log_callback(f"⏭️  Skipped (already exists): {os.path.basename(output_file)}")
                self.processing_times.append(0)
                return True
            
            # Get file size
            file_size = os.path.getsize(audio_file) / (1024 * 1024)  # MB
            
            # Transcribe
            FileUtils.ensure_directory(output_file)
            result = self.transcriber.transcribe_with_metadata(audio_file, options.get('engine', 'auto_gpu'), options)
            
            # Extract results
            if isinstance(result, dict):
                text = result.get('text', '')
                language = result.get('language', 'Unknown')
                duration = result.get('duration', 0)
                avg_confidence = result.get('avg_logprob', None)
                audio_metadata = result.get('audio_metadata', {})
            else:
                text = result
                language = 'Unknown'
                duration = 0
                avg_confidence = None
                audio_metadata = {}
            
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
            
            # Save with comprehensive metadata
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcript of: {file_name}\n")
                
                if detected_date:
                    f.write(f"Recording Date: {detected_date.strftime('%Y-%m-%d')} ({day_of_week})\n")
                
                f.write(f"Transcribed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n--- TRANSCRIPTION METADATA ---\n")
                f.write(f"File Size:         {file_size:.2f} MB\n")
                
                # Add audio format information
                audio_info = AudioUtils.format_audio_info(audio_metadata)
                if audio_info != "Unknown":
                    f.write(f"Audio Format:      {audio_info}\n")
                
                # Add MP3 tag information if available
                mp3_tags = AudioUtils.format_mp3_tags(audio_metadata)
                if mp3_tags:
                    f.write(f"MP3 Tags:\n{mp3_tags}\n")
                
                if duration > 0:
                    f.write(f"Duration:          {FormatUtils.format_time(duration)}\n")
                f.write(f"Processing Time:   {FormatUtils.format_time(process_time)}\n")
                
                if duration > 0 and process_time > 0:
                    speed_ratio = duration / process_time
                    f.write(f"Speed:             {speed_ratio:.1f}x real-time\n")
                
                f.write(f"Engine:            {options.get('engine', 'auto_gpu')}\n")
                f.write(f"Model:             {options.get('model', 'base')}\n")
                f.write(f"Compute Precision: {options.get('compute_type', 'float16')}\n")
                f.write(f"Language:          {language}\n")
                
                if avg_confidence is not None:
                    confidence_pct = (1 + avg_confidence) * 100
                    f.write(f"Confidence:        {confidence_pct:.1f}%\n")
                
                f.write("=" * 60 + "\n\n")
                f.write(formatted_text)
            
            if log_callback:
                log_callback(f"✅ Success ({FormatUtils.format_time(process_time)}): {os.path.basename(output_file)}")
            
            return True
            
        except Exception as e:
            if log_callback:
                log_callback(f"❌ Failed: {e}")
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

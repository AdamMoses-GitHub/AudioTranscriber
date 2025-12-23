"""Audio Transcriber - Command Line Interface.

A command-line version of the audio transcription application.
Supports single file and batch processing with full configuration options.
"""
import argparse
import os
import sys
import time
from pathlib import Path
from config import Environment, ConfigManager
from models import ModelManager
from transcription import Transcriber, BatchProcessor
from utilities.format_utils import FormatUtils
from utilities.date_parser import DateParser
from utilities.audio_utils import AudioUtils


class AudioTranscriberCLI:
    """Command-line interface for audio transcription."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.environment = Environment()
        self.config_manager = ConfigManager()
        self.model_manager = ModelManager(self.environment)
        self.transcriber = Transcriber(self.model_manager, self.environment)
        self.batch_processor = BatchProcessor(self.transcriber, self.model_manager)
        
    def transcribe_single_file(self, args):
        """Transcribe a single audio file.
        
        Args:
            args: Parsed command-line arguments.
        """
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}")
            return 1
        
        print(f"Transcribing: {args.input}")
        print(f"Engine: {args.engine}")
        print(f"Model: {args.model}")
        print(f"Compute Type: {args.compute}")
        
        # Load model
        print("Loading model...")
        self.model_manager.load_model(args.engine, args.model, args.compute)
        
        # Transcribe
        start_time = time.time()
        print("Transcribing audio...")
        result = self.transcriber.transcribe_with_metadata(args.input, args.engine)
        
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
        
        processing_time = time.time() - start_time
        
        # Format text if requested
        if args.chars_per_line > 0:
            text = FormatUtils.format_text_with_line_breaks(text, args.chars_per_line)
        
        # Detect date if requested
        date_info = ""
        if args.detect_date:
            detected_date, day_of_week = DateParser.detect_date_from_filename(
                os.path.basename(args.input)
            )
            if detected_date:
                date_info = f"Recording Date: {detected_date.strftime('%Y-%m-%d')} ({day_of_week})\n"
        
        # Build transcript
        file_size = os.path.getsize(args.input) / (1024 * 1024)
        final_text = f"Transcript of: {os.path.basename(args.input)}\n"
        final_text += date_info
        final_text += f"Transcribed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_text += "\n--- TRANSCRIPTION METADATA ---\n"
        final_text += f"File Size:         {file_size:.2f} MB\n"
        
        audio_info = AudioUtils.format_audio_info(audio_metadata)
        if audio_info != "Unknown":
            final_text += f"Audio Format:      {audio_info}\n"
        
        mp3_tags = AudioUtils.format_mp3_tags(audio_metadata)
        if mp3_tags:
            final_text += f"MP3 Tags:\n{mp3_tags}\n"
        
        if duration > 0:
            final_text += f"Duration:          {FormatUtils.format_time(duration)}\n"
        final_text += f"Processing Time:   {FormatUtils.format_time(processing_time)}\n"
        if duration > 0:
            speed_ratio = duration / processing_time
            final_text += f"Speed:             {speed_ratio:.1f}x real-time\n"
        final_text += f"Engine:            {args.engine}\n"
        final_text += f"Model:             {args.model}\n"
        final_text += f"Compute Precision: {args.compute}\n"
        if self.environment.gpu_available:
            gpu_name = self.environment.get_gpu_info()['name']
            final_text += f"GPU:               {gpu_name}\n"
        else:
            final_text += f"Device:            CPU\n"
        final_text += f"Language:          {language}\n"
        if avg_confidence is not None:
            confidence_pct = (1 + avg_confidence) * 100
            final_text += f"Confidence:        {confidence_pct:.1f}%\n"
        final_text += "=" * 60 + "\n\n"
        final_text += text
        
        # Determine output file
        if args.output:
            output_file = args.output
        else:
            output_file = os.path.splitext(args.input)[0] + '.txt'
        
        # Save transcript
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
        print(f"\nTranscription complete!")
        print(f"Saved to: {output_file}")
        print(f"Processing time: {FormatUtils.format_time(processing_time)}")
        if duration > 0:
            print(f"Speed: {duration/processing_time:.1f}x real-time")
        
        # Cleanup
        self.model_manager.cleanup_model()
        return 0
    
    def transcribe_batch(self, args):
        """Transcribe multiple audio files.
        
        Args:
            args: Parsed command-line arguments.
        """
        if not os.path.exists(args.input):
            print(f"Error: Directory not found: {args.input}")
            return 1
        
        if not os.path.isdir(args.input):
            print(f"Error: Input must be a directory for batch processing: {args.input}")
            return 1
        
        print(f"Batch processing: {args.input}")
        print(f"Output directory: {args.output}")
        print(f"Engine: {args.engine}")
        print(f"Model: {args.model}")
        print(f"Compute Type: {args.compute}")
        print(f"Skip existing: {args.skip_existing}")
        print(f"Recursive: {args.recursive}")
        print(f"Preserve structure: {args.preserve_structure}")
        print(f"Create summary: {args.create_summary}")
        
        # Progress callback
        def progress_callback(current, total, filename, status):
            print(f"[{current}/{total}] {filename} - {status}")
        
        # Process batch
        start_time = time.time()
        stats = self.batch_processor.process_batch(
            input_folder=args.input,
            output_folder=args.output,
            engine=args.engine,
            model_size=args.model,
            compute_type=args.compute,
            detect_date=args.detect_date,
            chars_per_line=args.chars_per_line,
            skip_existing=args.skip_existing,
            create_summary=args.create_summary,
            preserve_structure=args.preserve_structure,
            recursive=args.recursive,
            progress_callback=progress_callback
        )
        
        processing_time = time.time() - start_time
        
        # Display results
        print("\n" + "=" * 60)
        print("BATCH PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Total files processed: {stats.get('processed', 0)}")
        print(f"Files skipped: {stats.get('skipped', 0)}")
        print(f"Errors: {stats.get('errors', 0)}")
        print(f"Total time: {FormatUtils.format_time(processing_time)}")
        
        if stats.get('errors', 0) > 0:
            print("\nErrors encountered:")
            for error in stats.get('error_list', []):
                print(f"  - {error}")
        
        return 0
    
    def show_info(self):
        """Display system information."""
        print("Audio Transcriber - System Information")
        print("=" * 60)
        
        gpu_status = self.environment.get_gpu_status_text()
        print(f"GPU Available: {gpu_status}")
        
        if self.environment.gpu_available:
            gpu_info = self.environment.get_gpu_info()
            print(f"GPU Device: {gpu_info['name']}")
            print(f"CUDA Version: {gpu_info.get('cuda_version', 'Unknown')}")
        
        print(f"\nWhisper Available: {self.environment.whisper_available}")
        print(f"Faster-Whisper Available: {self.environment.faster_whisper_available}")
        
        print("\nAvailable Models:")
        models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
        for model in models:
            print(f"  - {model}")
        
        print("\nAvailable Engines:")
        engines = ['whisper', 'faster_whisper', 'auto_gpu']
        for engine in engines:
            available = "✓" if (
                (engine == 'whisper' and self.environment.whisper_available) or
                (engine == 'faster_whisper' and self.environment.faster_whisper_available) or
                engine == 'auto_gpu'
            ) else "✗"
            print(f"  {available} {engine}")


def main():
    """Main entry point for CLI application."""
    parser = argparse.ArgumentParser(
        description='Audio Transcriber - Convert audio files to text using Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe single file
  python audio_transcribe_cli.py single input.mp3
  
  # Transcribe with custom output
  python audio_transcribe_cli.py single input.mp3 -o output.txt
  
  # Transcribe with specific model
  python audio_transcribe_cli.py single input.mp3 --model large --engine whisper
  
  # Batch transcribe folder
  python audio_transcribe_cli.py batch input_folder output_folder
  
  # Batch with recursive search and structure preservation
  python audio_transcribe_cli.py batch input_folder output_folder --recursive --preserve-structure
  
  # Show system information
  python audio_transcribe_cli.py info
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Single file command
    single_parser = subparsers.add_parser('single', 
                                          help='Transcribe a single audio file',
                                          description='Process a single audio file and generate a text transcript with metadata.')
    single_parser.add_argument('input', 
                               metavar='INPUT_FILE',
                               help='Path to the audio file to transcribe. Supported formats: MP3, WAV, M4A, FLAC, AAC, OGG, WebM')
    single_parser.add_argument('-o', '--output', 
                               metavar='OUTPUT_FILE',
                               help='Path where the transcript will be saved. If not specified, creates a .txt file with the same name as the input file in the same directory')
    single_parser.add_argument('--engine', 
                               default='auto_gpu', 
                               choices=['whisper', 'faster_whisper', 'auto_gpu'],
                               help='Transcription engine to use. "whisper" uses OpenAI Whisper, "faster_whisper" uses optimized implementation (requires av package), "auto_gpu" automatically selects fastest available engine based on GPU availability (default: auto_gpu)')
    single_parser.add_argument('--model', 
                               default='base',
                               choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
                               help='Whisper model size. Larger models are more accurate but slower and require more VRAM. tiny=fastest/least accurate, large-v3=slowest/most accurate (default: base)')
    single_parser.add_argument('--compute', 
                               default='float16',
                               choices=['int8', 'int8_float16', 'float16', 'float32'],
                               help='Compute precision type. Lower precision is faster but may reduce accuracy. int8=fastest/lowest quality, float32=slowest/highest quality. Use float16 for GPU, int8 for CPU (default: float16)')
    single_parser.add_argument('--detect-date', 
                               action='store_true', 
                               default=True,
                               help='Automatically detect recording date from filename and add it to transcript header. Supports formats: YYYY-MM-DD, YYYYMMDD, MM-DD-YYYY, Month DD YYYY (default: enabled)')
    single_parser.add_argument('--no-detect-date', 
                               action='store_false', 
                               dest='detect_date',
                               help='Disable automatic date detection from filename')
    single_parser.add_argument('--chars-per-line', 
                               type=int, 
                               default=80,
                               metavar='N',
                               help='Maximum characters per line for text wrapping. Text will be broken into lines at word boundaries. Set to 0 to disable line breaks and keep original formatting (default: 80)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', 
                                         help='Batch transcribe multiple audio files',
                                         description='Process all audio files in a directory and save transcripts to an output folder.')
    batch_parser.add_argument('input', 
                              metavar='INPUT_FOLDER',
                              help='Path to folder containing audio files to transcribe. Use --recursive to include subdirectories')
    batch_parser.add_argument('output', 
                              metavar='OUTPUT_FOLDER',
                              help='Path to folder where transcripts will be saved. Folder will be created if it does not exist. Use --preserve-structure to maintain input folder hierarchy')
    batch_parser.add_argument('--engine', 
                              default='auto_gpu',
                              choices=['whisper', 'faster_whisper', 'auto_gpu'],
                              help='Transcription engine to use. "whisper" uses OpenAI Whisper, "faster_whisper" uses optimized implementation (requires av package), "auto_gpu" automatically selects fastest available engine based on GPU availability (default: auto_gpu)')
    batch_parser.add_argument('--model', 
                              default='base',
                              choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
                              help='Whisper model size. Larger models are more accurate but slower and require more VRAM. tiny=fastest/least accurate, large-v3=slowest/most accurate (default: base)')
    batch_parser.add_argument('--compute', 
                              default='float16',
                              choices=['int8', 'int8_float16', 'float16', 'float32'],
                              help='Compute precision type. Lower precision is faster but may reduce accuracy. int8=fastest/lowest quality, float32=slowest/highest quality. Use float16 for GPU, int8 for CPU (default: float16)')
    batch_parser.add_argument('--detect-date', 
                              action='store_true', 
                              default=True,
                              help='Automatically detect recording date from filename and add it to transcript header. Supports formats: YYYY-MM-DD, YYYYMMDD, MM-DD-YYYY, Month DD YYYY (default: enabled)')
    batch_parser.add_argument('--no-detect-date', 
                              action='store_false', 
                              dest='detect_date',
                              help='Disable automatic date detection from filename')
    batch_parser.add_argument('--chars-per-line', 
                              type=int, 
                              default=80,
                              metavar='N',
                              help='Maximum characters per line for text wrapping. Text will be broken into lines at word boundaries. Set to 0 to disable line breaks and keep original formatting (default: 80)')
    batch_parser.add_argument('--skip-existing', 
                              action='store_true', 
                              default=False,
                              help='Skip processing audio files that already have corresponding .txt transcript files in the output folder. Useful for resuming interrupted batch jobs or adding new files to an existing collection')
    batch_parser.add_argument('--create-summary', 
                              action='store_true', 
                              default=False,
                              help='Generate a _batch_summary.txt file in the output folder with processing statistics, file list, timestamps, and any errors encountered during batch processing')
    batch_parser.add_argument('--preserve-structure', 
                              action='store_true', 
                              default=False,
                              help='Maintain the input folder hierarchy in the output folder. Example: input/2024/jan/file.mp3 -> output/2024/jan/file.txt. If disabled, all transcripts are saved directly in the output folder')
    batch_parser.add_argument('--recursive', 
                              action='store_true', 
                              default=False,
                              help='Search for audio files in all subdirectories of the input folder. If disabled, only processes files directly in the input folder (non-recursive). Combine with --preserve-structure to maintain organization')
    
    # Info command
    info_parser = subparsers.add_parser('info', 
                                        help='Display system information',
                                        description='Show system capabilities including GPU availability, installed engines, and available Whisper models. Use this to verify your setup before transcribing.')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Create CLI instance
    cli = AudioTranscriberCLI()
    
    # Execute command
    if args.command == 'single':
        return cli.transcribe_single_file(args)
    elif args.command == 'batch':
        return cli.transcribe_batch(args)
    elif args.command == 'info':
        cli.show_info()
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

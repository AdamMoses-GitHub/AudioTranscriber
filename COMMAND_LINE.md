# Audio Transcriber - Command Line Reference

A comprehensive guide to using the Audio Transcriber command-line interface for converting audio files to text using OpenAI's Whisper speech recognition models.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [single - Single File Transcription](#single---single-file-transcription)
  - [batch - Batch Processing](#batch---batch-processing)
  - [info - System Information](#info---system-information)
- [Usage Examples](#usage-examples)
- [Model Selection Guide](#model-selection-guide)
- [Compute Precision Guide](#compute-precision-guide)
- [Supported File Formats](#supported-file-formats)
- [Output Format](#output-format)
- [Configuration & Behavior](#configuration--behavior)
- [Troubleshooting](#troubleshooting)
- [Getting Help](#getting-help)

---

## Overview

Audio Transcriber CLI is a powerful command-line tool that converts audio files to text transcripts with comprehensive metadata. It supports:

- **GPU acceleration** for fast processing (NVIDIA CUDA)
- **Multiple Whisper models** (tiny to large-v3) for accuracy/speed trade-offs
- **Single file** and **batch processing** modes
- **Automatic date detection** from filenames
- **Metadata extraction** (audio format, ID3 tags, duration, etc.)
- **Flexible output formatting** with line wrapping control

### Basic Syntax

```bash
python audio_transcribe_cli.py <command> [arguments] [options]
```

**Available Commands:**
- `single` - Transcribe a single audio file
- `batch` - Transcribe multiple files from a directory
- `info` - Display system capabilities and available models

---

## Quick Start

### Check Your System

First, verify your setup and see available models:

```bash
python audio_transcribe_cli.py info
```

### Transcribe Your First File

Basic transcription with default settings (base model, auto GPU selection):

```bash
python audio_transcribe_cli.py single recording.mp3
```

This creates `recording.txt` in the same directory as the input file.

### Batch Process a Folder

Transcribe all audio files in a directory:

```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts
```

### High-Quality Transcription

For best accuracy, use a larger model:

```bash
python audio_transcribe_cli.py single interview.mp3 --model large-v3
```

### Resume Interrupted Batch

Continue batch processing, skipping already-transcribed files:

```bash
python audio_transcribe_cli.py batch ./audio ./text --skip-existing
```

---

## Commands

## `single` - Single File Transcription

Process a single audio file and generate a text transcript with comprehensive metadata.

### Syntax

```bash
python audio_transcribe_cli.py single INPUT_FILE [options]
```

### Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `INPUT_FILE` | Path | Path to audio file to transcribe. Supports: MP3, WAV, M4A, FLAC, AAC, OGG, WebM |

### Optional Arguments

| Argument | Type | Default | Choices | Description |
|----------|------|---------|---------|-------------|
| `-o, --output` | Path | `<input>.txt` | - | Output file path for transcript |
| `--engine` | String | `auto_gpu` | `whisper`, `faster_whisper`, `auto_gpu` | Transcription engine selection |
| `--model` | String | `base` | `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3` | Whisper model size |
| `--compute` | String | `float16` | `int8`, `int8_float16`, `float16`, `float32` | Compute precision type |
| `--detect-date` | Flag | Enabled | - | Detect recording date from filename |
| `--no-detect-date` | Flag | - | - | Disable date detection |
| `--chars-per-line` | Integer | `80` | - | Max characters per line (0 = no wrapping) |

### Engine Selection

- **`auto_gpu`** (default): Automatically selects the fastest available engine based on GPU availability
  - Prefers `faster_whisper` with GPU if available
  - Falls back to `whisper` with GPU if faster_whisper unavailable
  - Falls back to CPU if no GPU
- **`whisper`**: OpenAI's standard Whisper implementation
- **`faster_whisper`**: Optimized implementation (requires `av` package, may not work on Python 3.14+)

### Model Selection

| Model | Parameters | VRAM | Speed (GPU) | Accuracy | Download Size |
|-------|-----------|------|-------------|----------|---------------|
| `tiny` | 39M | ~0.2GB | 30-50x real-time | Basic | ~75MB |
| `base` | 74M | ~0.5GB | 20-40x real-time | Good | ~150MB |
| `small` | 244M | ~1GB | 10-20x real-time | Better | ~500MB |
| `medium` | 769M | ~2GB | 5-10x real-time | High | ~1.5GB |
| `large` | 1550M | ~4GB | 3-7x real-time | Highest | ~3GB |
| `large-v2` | 1550M | ~4GB | 3-7x real-time | Highest | ~3GB |
| `large-v3` | 1550M | ~6GB | 2-5x real-time | Highest | ~3GB |

### Compute Precision

- **`int8`**: Fastest, lowest quality. Best for CPU processing
- **`int8_float16`**: Mixed precision
- **`float16`**: Balanced speed/quality. Best for GPU (default)
- **`float32`**: Slowest, highest quality

### Date Detection

Automatically extracts recording dates from filenames. Supported formats:
- `YYYY-MM-DD` (e.g., `2024-03-15`)
- `YYYYMMDD` (e.g., `20240315`)
- `MM-DD-YYYY` (e.g., `03-15-2024`)
- `Month DD YYYY` (e.g., `March 15 2024`, `Mar 15 2024`)

Date appears in transcript header as: `Recording Date: 2024-03-15 (Friday)`

### Output Format

Generated transcripts include:

**Header:**
- Filename
- Recording date (if detected)
- Transcription timestamp

**Metadata:**
- File size (MB)
- Audio format (codec, bitrate, sample rate, channels)
- MP3 ID3 tags (artist, album, title - if present)
- Duration (H:M:S)
- Processing time
- Speed ratio (e.g., 8.9x real-time)
- Engine and model used
- Compute precision
- GPU/CPU device
- Detected language
- Confidence score (%)

**Transcript:**
- Transcribed text with optional line wrapping

### Examples

**Basic usage:**
```bash
python audio_transcribe_cli.py single recording.mp3
```

**Custom output location:**
```bash
python audio_transcribe_cli.py single interview.mp3 -o transcripts/interview.txt
```

**High-quality transcription:**
```bash
python audio_transcribe_cli.py single podcast.mp3 --model large-v3 --compute float32
```

**Fast draft mode:**
```bash
python audio_transcribe_cli.py single meeting.wav --model tiny --compute int8
```

**No line wrapping, no date detection:**
```bash
python audio_transcribe_cli.py single lecture.m4a --chars-per-line 0 --no-detect-date
```

**Specific engine:**
```bash
python audio_transcribe_cli.py single audio.flac --engine faster_whisper --model medium
```

---

## `batch` - Batch Processing

Process multiple audio files from a directory with progress tracking and optional summary report.

### Syntax

```bash
python audio_transcribe_cli.py batch INPUT_FOLDER OUTPUT_FOLDER [options]
```

### Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `INPUT_FOLDER` | Path | Directory containing audio files to transcribe |
| `OUTPUT_FOLDER` | Path | Directory where transcripts will be saved (created if doesn't exist) |

### Optional Arguments

Includes all `single` command options, plus:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--skip-existing` | Flag | Disabled | Skip files that already have .txt transcripts in output folder |
| `--create-summary` | Flag | Disabled | Generate `_batch_summary.txt` with processing statistics |
| `--preserve-structure` | Flag | Disabled | Maintain input folder hierarchy in output folder |
| `--recursive` | Flag | Disabled | Search for audio files in all subdirectories |

Plus all options from `single` command: `--engine`, `--model`, `--compute`, `--detect-date`, `--no-detect-date`, `--chars-per-line`

### Batch-Specific Behavior

**Structure Preservation:**
- **Disabled** (default): `input/subdir/file.mp3` → `output/file.txt`
- **Enabled** (`--preserve-structure`): `input/subdir/file.mp3` → `output/subdir/file.txt`

**Recursive Search:**
- **Disabled** (default): Only processes files directly in input folder
- **Enabled** (`--recursive`): Processes all subdirectories

**Skip Existing:**
- Checks output folder for `<audio_name>.txt` files
- Useful for resuming interrupted jobs or adding new files

**Summary Report:**
- File: `_batch_summary.txt` in output folder
- Contents: Processing statistics, file list, timestamps, errors

### Console Output

During processing:
```
[3/15] meeting_notes.mp3 - Transcribing...
[4/15] interview_2024.wav - Complete
[5/15] podcast_ep1.m4a - Skipped (exists)
```

Final summary:
```
============================================================
BATCH PROCESSING COMPLETE
============================================================
Total files processed: 12
Files skipped: 3
Errors: 0
Total time: 15m 23.7s
```

### Examples

**Basic batch processing:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts
```

**Recursive with structure preservation:**
```bash
python audio_transcribe_cli.py batch ./audio ./text --recursive --preserve-structure
```

**Resume interrupted batch:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts --skip-existing
```

**High-quality batch with summary:**
```bash
python audio_transcribe_cli.py batch ./input ./output \
  --model medium \
  --create-summary \
  --skip-existing
```

**Complete batch workflow:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts \
  --model base \
  --engine faster_whisper \
  --compute float16 \
  --chars-per-line 80 \
  --recursive \
  --preserve-structure \
  --skip-existing \
  --create-summary
```

**CPU-optimized batch:**
```bash
python audio_transcribe_cli.py batch ./audio ./text \
  --model tiny \
  --compute int8 \
  --skip-existing
```

---

## `info` - System Information

Display system capabilities, available models, and engine status.

### Syntax

```bash
python audio_transcribe_cli.py info
```

### No Arguments

This command takes no parameters.

### Output Information

- GPU availability and device name
- CUDA version (if GPU available)
- Whisper library status
- Faster-Whisper library status
- Available Whisper models
- Available engines with status indicators

### Example Output

```
Audio Transcriber - System Information
============================================================
GPU Available: NVIDIA GeForce RTX 3080
GPU Device: NVIDIA GeForce RTX 3080
CUDA Version: 11.8

Whisper Available: True
Faster-Whisper Available: True

Available Models:
  - tiny
  - base
  - small
  - medium
  - large
  - large-v2
  - large-v3

Available Engines:
  ✓ whisper
  ✓ faster_whisper
  ✓ auto_gpu
```

### Usage

Run before transcription to verify your setup:

```bash
python audio_transcribe_cli.py info
```

---

## Usage Examples

### Basic Operations

**1. Simple transcription (default settings):**
```bash
python audio_transcribe_cli.py single recording.mp3
```
- Uses `base` model
- Auto-selects best engine
- Creates `recording.txt` in same directory

**2. Specify output location:**
```bash
python audio_transcribe_cli.py single audio.wav -o documents/transcript.txt
```

**3. Check system capabilities:**
```bash
python audio_transcribe_cli.py info
```

**4. Basic batch processing:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts
```

---

### Quality Tiers

**Fast/Draft Quality (CPU-friendly):**
```bash
# Single file
python audio_transcribe_cli.py single meeting.mp3 --model tiny --compute int8

# Batch
python audio_transcribe_cli.py batch ./audio ./text --model tiny --compute int8
```
- Processing: 30-50x real-time
- Use case: Quick drafts, meeting notes, rough transcriptions

**Balanced Quality (Recommended):**
```bash
# Single file
python audio_transcribe_cli.py single interview.mp3 --model base

# Batch
python audio_transcribe_cli.py batch ./audio ./text --model small
```
- Processing: 10-20x real-time
- Use case: General purpose, podcasts, lectures

**High Quality (Best accuracy):**
```bash
# Single file
python audio_transcribe_cli.py single podcast.mp3 --model large-v3 --compute float32

# Batch
python audio_transcribe_cli.py batch ./audio ./text --model medium --compute float16
```
- Processing: 3-7x real-time
- Use case: Professional transcription, interviews, archival

---

### Batch Processing Scenarios

**1. Organize by date (preserve folder structure):**
```bash
python audio_transcribe_cli.py batch ./recordings/2024 ./transcripts \
  --recursive \
  --preserve-structure
```
Structure maintained: `recordings/2024/January/file.mp3` → `transcripts/2024/January/file.txt`

**2. Resume interrupted job:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts \
  --skip-existing \
  --create-summary
```
Skips already-processed files, creates summary report.

**3. Add new files to existing collection:**
```bash
python audio_transcribe_cli.py batch ./new_recordings ./transcripts --skip-existing
```
Only processes files without existing transcripts.

**4. Full production batch:**
```bash
python audio_transcribe_cli.py batch ./archive ./transcripts \
  --model medium \
  --engine faster_whisper \
  --chars-per-line 100 \
  --recursive \
  --preserve-structure \
  --skip-existing \
  --create-summary
```
Complete workflow with quality settings, organization, and reporting.

**5. Flat output (ignore input structure):**
```bash
python audio_transcribe_cli.py batch ./recordings ./all_transcripts --recursive
```
All transcripts saved directly in output folder, regardless of input structure.

---

### System-Specific Optimizations

**GPU System (NVIDIA with CUDA):**
```bash
python audio_transcribe_cli.py batch ./audio ./text \
  --model medium \
  --engine faster_whisper \
  --compute float16
```
- Optimal GPU utilization
- Best speed/quality balance

**CPU-Only System:**
```bash
python audio_transcribe_cli.py batch ./audio ./text \
  --model tiny \
  --engine whisper \
  --compute int8
```
- CPU-optimized
- Reduced memory usage
- Faster processing on CPU

**Limited VRAM (< 4GB):**
```bash
python audio_transcribe_cli.py batch ./audio ./text \
  --model small \
  --compute int8
```
- Smaller model for limited VRAM
- Still maintains reasonable accuracy

**High VRAM (> 8GB):**
```bash
python audio_transcribe_cli.py batch ./audio ./text \
  --model large-v3 \
  --compute float32
```
- Maximum accuracy
- Leverages available resources

---

### Text Formatting Options

**1. Wide format (no wrapping):**
```bash
python audio_transcribe_cli.py single lecture.mp3 --chars-per-line 0
```
Preserves original text flow without line breaks.

**2. Narrow format (terminal-friendly):**
```bash
python audio_transcribe_cli.py single notes.wav --chars-per-line 60
```
Easier to read in terminal or narrow windows.

**3. Standard format:**
```bash
python audio_transcribe_cli.py single audio.mp3 --chars-per-line 80
```
Default 80 characters per line (standard terminal width).

**4. Wide format for documents:**
```bash
python audio_transcribe_cli.py single document.mp3 --chars-per-line 120
```
Better for modern displays and documents.

---

### Date Detection

**1. With date detection (default):**
```bash
python audio_transcribe_cli.py single "Meeting_2024-03-15.mp3"
```
Output includes: `Recording Date: 2024-03-15 (Friday)`

**2. Without date detection:**
```bash
python audio_transcribe_cli.py single "Meeting_2024-03-15.mp3" --no-detect-date
```
Date line omitted from transcript header.

**3. Supported date formats in filename:**
- `Recording_2024-03-15.mp3` → Detected
- `20240315_meeting.mp3` → Detected
- `03-15-2024_notes.wav` → Detected
- `March_15_2024_lecture.m4a` → Detected
- `Mar_15_2024_podcast.mp3` → Detected

---

### Advanced Workflows

**1. Large archive migration:**
```bash
# First pass: Process with small model
python audio_transcribe_cli.py batch ./archive ./transcripts \
  --model small \
  --recursive \
  --preserve-structure \
  --create-summary

# Review results, then reprocess important files with larger model
python audio_transcribe_cli.py single ./archive/important.mp3 \
  --model large-v3 \
  -o ./transcripts/important.txt
```

**2. Incremental processing (daily):**
```bash
# Daily cron job / scheduled task
python audio_transcribe_cli.py batch ./recordings ./transcripts \
  --model base \
  --skip-existing \
  --recursive \
  --create-summary
```
Only processes new files added since last run.

**3. Quality comparison:**
```bash
# Draft with tiny model
python audio_transcribe_cli.py single test.mp3 -o draft.txt --model tiny

# Final with large model
python audio_transcribe_cli.py single test.mp3 -o final.txt --model large-v3

# Compare outputs to determine if quality improvement justifies processing time
```

**4. Multi-language collection:**
```bash
# Whisper auto-detects language
python audio_transcribe_cli.py batch ./multilingual ./transcripts \
  --model medium \
  --recursive \
  --preserve-structure
```
Language detected and reported in each transcript's metadata.

**5. Emergency recovery (power failure):**
```bash
# Resume with skip-existing after interruption
python audio_transcribe_cli.py batch ./recordings ./transcripts \
  --skip-existing \
  --create-summary
```
Continues from where it stopped, creates summary of completed work.

---

### Specific Use Cases

**Podcast Production:**
```bash
python audio_transcribe_cli.py single episode_042.mp3 \
  --model medium \
  --chars-per-line 0 \
  --output show_notes/ep042_transcript.txt
```

**Academic Lectures:**
```bash
python audio_transcribe_cli.py batch ./lectures ./transcripts \
  --model large-v3 \
  --recursive \
  --preserve-structure \
  --chars-per-line 100
```

**Meeting Notes:**
```bash
python audio_transcribe_cli.py single meeting_2024-12-23.mp3 \
  --model base \
  --detect-date
```

**Interview Archive:**
```bash
python audio_transcribe_cli.py batch ./interviews ./archive/transcripts \
  --model medium \
  --recursive \
  --preserve-structure \
  --skip-existing \
  --create-summary
```

**Voice Memos:**
```bash
python audio_transcribe_cli.py batch ./voice_memos ./notes \
  --model tiny \
  --chars-per-line 60
```

---

## Model Selection Guide

### Choosing the Right Model

| Use Case | Recommended Model | Rationale |
|----------|------------------|-----------|
| Quick drafts, voice memos | `tiny` | 30-50x real-time, adequate accuracy |
| General purpose, meetings | `base` or `small` | Best balance of speed/accuracy |
| Professional work, podcasts | `medium` | High accuracy, reasonable speed |
| Critical transcription, archival | `large-v3` | Highest accuracy available |
| CPU-only systems | `tiny` or `base` | Reasonable performance without GPU |
| Limited VRAM (< 2GB) | `tiny` or `base` | Fits in constrained memory |
| Batch processing (time-sensitive) | `base` or `small` | Balances throughput with quality |

### Model Performance Comparison

**Speed Tests** (approximate, varies by hardware):
- **RTX 3080**: 
  - `tiny`: 45x real-time
  - `base`: 30x real-time
  - `small`: 18x real-time
  - `medium`: 8x real-time
  - `large-v3`: 4x real-time

- **CPU (i7-10700K)**:
  - `tiny`: 5x real-time
  - `base`: 2x real-time
  - `small`: 0.8x real-time (slower than real-time)

**Accuracy Comparison** (Word Error Rate - lower is better):
- `tiny`: ~10-15% WER
- `base`: ~7-10% WER
- `small`: ~5-7% WER
- `medium`: ~3-5% WER
- `large-v3`: ~2-4% WER

### Download Sizes

Models are automatically downloaded on first use:
- `tiny`: ~75 MB
- `base`: ~150 MB
- `small`: ~500 MB
- `medium`: ~1.5 GB
- `large/large-v2/large-v3`: ~3 GB

Models are cached in: `~/.cache/whisper/` (Linux/Mac) or `%USERPROFILE%\.cache\whisper\` (Windows)

---

## Compute Precision Guide

### Precision Types

| Type | Speed | Quality | Memory | Best For |
|------|-------|---------|--------|----------|
| `int8` | Fastest | Lower | Lowest | CPU processing |
| `int8_float16` | Fast | Moderate | Low | Mixed CPU/GPU |
| `float16` | Balanced | Good | Moderate | GPU (default) |
| `float32` | Slowest | Best | Highest | Maximum accuracy |

### Recommendations

**GPU Systems:**
```bash
--compute float16  # Default, best balance
```

**CPU Systems:**
```bash
--compute int8  # Fastest on CPU
```

**Maximum Quality:**
```bash
--compute float32  # Slight accuracy improvement
```

**Memory Constrained:**
```bash
--compute int8  # Lowest memory usage
```

### VRAM Requirements by Precision

For `large-v3` model:
- `int8`: ~2 GB VRAM
- `float16`: ~6 GB VRAM
- `float32`: ~12 GB VRAM

For `medium` model:
- `int8`: ~1 GB VRAM
- `float16`: ~2 GB VRAM
- `float32`: ~4 GB VRAM

---

## Supported File Formats

The following audio formats are supported (requires FFmpeg):

| Format | Extension | Notes |
|--------|-----------|-------|
| MP3 | `.mp3` | ID3 tags extracted |
| WAV | `.wav` | Uncompressed |
| M4A | `.m4a` | Apple/iTunes format |
| FLAC | `.flac` | Lossless compression |
| AAC | `.aac` | Advanced Audio Coding |
| OGG | `.ogg` | Ogg Vorbis |
| WebM | `.webm` | Web media format |

### Requirements

**FFmpeg** must be installed and available in system PATH:
- Windows: Download from https://ffmpeg.org/ and add to PATH
- Linux: `apt-get install ffmpeg` or `yum install ffmpeg`
- Mac: `brew install ffmpeg`

### File Size Considerations

- No strict size limit (depends on available system memory)
- Typical range: Few KB to several GB
- Large files (>500MB) may take significant time even with GPU
- For very large files, consider splitting audio before transcription

---

## Output Format

### Single File Output Structure

```
Transcript of: recording.mp3
Recording Date: 2024-03-15 (Friday)
Transcribed: 2024-12-23 14:32:10

--- TRANSCRIPTION METADATA ---
File Size:         45.32 MB
Audio Format:      MP3 | 320 kbps | 44.1 kHz | Stereo
MP3 Tags:
  Title:   Weekly Meeting
  Artist:  Company Name
  Album:   Meetings 2024
Duration:          45:23
Processing Time:   5:05
Speed:             8.9x real-time
Engine:            faster_whisper
Model:             base
Compute Precision: float16
GPU:               NVIDIA GeForce RTX 3080
Language:          en (English)
Confidence:        94.2%
============================================================

[Transcribed text appears here with line wrapping applied]
```

### Batch Summary Format

When `--create-summary` is enabled, `_batch_summary.txt` contains:

```
============================================================
BATCH TRANSCRIPTION SUMMARY
============================================================
Generated: 2024-12-23 15:45:30
Input Folder: ./recordings
Output Folder: ./transcripts

--- SETTINGS ---
Engine: faster_whisper
Model: base
Compute Type: float16
Detect Date: Yes
Chars Per Line: 80
Skip Existing: Yes
Preserve Structure: Yes
Recursive: Yes

--- STATISTICS ---
Total Files Processed: 15
Files Skipped: 3
Errors: 1
Total Processing Time: 12m 34.5s

--- PROCESSED FILES ---
1. meeting_2024-03-15.mp3 - Success (45s)
2. interview_jan.wav - Success (2m 15s)
3. podcast_ep1.m4a - Skipped (exists)
[...]

--- ERRORS ---
1. corrupted_file.mp3 - Error: Invalid audio format
```

### File Naming

**Single file output:**
- Default: `<input_basename>.txt`
- Custom: User-specified via `-o` flag

**Batch output:**
- Non-recursive: `<audio_basename>.txt` in output folder
- Recursive + preserve-structure: Maintains input hierarchy

---

## Configuration & Behavior

### Model Management

- **Automatic download**: Models downloaded on first use
- **Cache location**: 
  - Linux/Mac: `~/.cache/whisper/`
  - Windows: `%USERPROFILE%\.cache\whisper\`
- **One-time per model**: Each model size downloaded once, reused for all future transcriptions
- **No manual cleanup needed**: Models persist across sessions

### Auto GPU Selection

When `--engine auto_gpu` (default):

1. Check GPU availability (CUDA)
2. Check `faster_whisper` installation
3. Select engine:
   - GPU + faster_whisper available → `faster_whisper` with GPU
   - GPU available, faster_whisper missing → `whisper` with GPU
   - No GPU → `whisper` with CPU

### Date Detection Behavior

Searches filename (excluding extension) for date patterns:

**Supported formats:**
- `YYYY-MM-DD`, `YYYY_MM_DD`, `YYYY.MM.DD`
- `YYYYMMDD` (no separators)
- `MM-DD-YYYY`, `MM_DD_YYYY`, `MM.MM.YYYY`
- `Month DD YYYY`, `Mon DD YYYY`

**Examples:**
- `Meeting_2024-03-15.mp3` → `2024-03-15 (Friday)`
- `20240315_notes.wav` → `2024-03-15 (Friday)`
- `March_15_2024.m4a` → `2024-03-15 (Friday)`

**Behavior:**
- First matching date in filename is used
- Invalid dates (e.g., Feb 30) are ignored
- If no date found, date line omitted from transcript

### Line Wrapping Behavior

- **Default (80)**: Text wrapped at word boundaries, ~80 characters per line
- **Custom (N)**: Wrapped at specified character count
- **Disabled (0)**: No wrapping, preserves original transcription format
- **Word preservation**: Never breaks words mid-character
- **Paragraph preservation**: Existing paragraph breaks maintained

### Metadata Extraction

**Always included:**
- File size
- Duration
- Processing time
- Speed ratio
- Engine and model
- Language

**Conditional metadata:**
- Audio format: Sample rate, bitrate, channels (if detectable)
- MP3 tags: Artist, album, title (MP3 files only)
- GPU name (if GPU used)
- Confidence score (if available from engine)

### Error Handling

**File errors:**
- File not found → Error message, exit code 1
- Invalid directory → Error message, exit code 1
- Unsupported format → Error message, skip in batch mode

**Processing errors:**
- Model load failure → Error propagated, exit
- Transcription failure → Error reported, continue in batch mode
- Out of memory → Error message, consider smaller model/precision

**Batch mode:**
- Errors logged and reported in summary
- Processing continues for remaining files
- Final exit code 0 if any files succeeded

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found

**Error:** `FFmpeg not found` or `Unable to load audio`

**Solution:**
```bash
# Windows: Download from https://ffmpeg.org/, add to PATH
# Linux:
sudo apt-get install ffmpeg
# Mac:
brew install ffmpeg

# Verify installation:
ffmpeg -version
```

#### 2. CUDA Out of Memory

**Error:** `CUDA out of memory` or `RuntimeError: CUDA error`

**Solutions:**
```bash
# Use smaller model
python audio_transcribe_cli.py single file.mp3 --model small

# Use lower precision
python audio_transcribe_cli.py single file.mp3 --compute int8

# Use CPU instead
python audio_transcribe_cli.py single file.mp3 --engine whisper --compute int8
```

#### 3. Slow Processing on GPU

**Issue:** Processing slower than expected with GPU

**Check:**
```bash
# Verify GPU is detected
python audio_transcribe_cli.py info

# Ensure faster_whisper is installed (faster than whisper)
pip install faster-whisper

# Explicitly use faster_whisper
python audio_transcribe_cli.py single file.mp3 --engine faster_whisper
```

#### 4. Python 3.14 Compatibility

**Issue:** `faster_whisper` may not install on Python 3.14+

**Solution:**
```bash
# Use standard whisper engine
python audio_transcribe_cli.py single file.mp3 --engine whisper

# Or use Python 3.11/3.12
```

#### 5. No Module Named 'av'

**Error:** `ImportError: No module named 'av'`

**Solution:**
```bash
# Install av package (required for faster-whisper)
pip install av

# Or use whisper engine instead
python audio_transcribe_cli.py single file.mp3 --engine whisper
```

#### 6. Batch Processing Stops

**Issue:** Batch processing interrupted or stopped

**Solution:**
```bash
# Resume with --skip-existing
python audio_transcribe_cli.py batch ./input ./output --skip-existing

# Creates summary to see what was processed
python audio_transcribe_cli.py batch ./input ./output --skip-existing --create-summary
```

#### 7. Poor Transcription Quality

**Issue:** Low accuracy, many errors in transcript

**Solutions:**
```bash
# Use larger model
python audio_transcribe_cli.py single file.mp3 --model medium

# Use higher precision
python audio_transcribe_cli.py single file.mp3 --compute float32

# Check audio quality
# - Ensure audio is clear (no excessive noise)
# - Verify audio file is not corrupted
# - Check language is supported by Whisper (99+ languages supported)
```

#### 8. Output File Permission Denied

**Error:** `Permission denied` when saving transcript

**Solution:**
```bash
# Specify writable output location
python audio_transcribe_cli.py single file.mp3 -o ~/Documents/transcript.txt

# Check output folder permissions
# Ensure output folder is not read-only
```

### Performance Tips

**Maximize speed:**
- Use `--model tiny` or `--model base`
- Use `--compute float16` on GPU or `int8` on CPU
- Use `--engine faster_whisper` on compatible systems
- Ensure GPU drivers and CUDA are up to date

**Maximize quality:**
- Use `--model large-v3`
- Use `--compute float32`
- Ensure audio quality is good (clear recording, minimal noise)
- Consider cleaning audio with audio editing software before transcription

**Balance speed/quality:**
- Use `--model small` or `--model medium`
- Use default `--compute float16`
- Use `--engine auto_gpu` for automatic optimization

---

## Getting Help

### Built-in Help

**General help:**
```bash
python audio_transcribe_cli.py --help
```

**Command-specific help:**
```bash
python audio_transcribe_cli.py single --help
python audio_transcribe_cli.py batch --help
python audio_transcribe_cli.py info --help
```

### System Information

**Check your setup:**
```bash
python audio_transcribe_cli.py info
```

This displays:
- GPU availability and model
- CUDA version
- Available engines
- Available models

### Exit Codes

- **0**: Success
- **1**: Error (file not found, invalid directory, processing error)

---

## Additional Resources

### Dependencies

**Required:**
- Python 3.8+
- torch (PyTorch)
- whisper
- ffmpeg (system-level)

**Optional:**
- faster-whisper (optimized processing)
- av (required for faster-whisper)
- CUDA (for GPU acceleration)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg (system-level)
# See: https://ffmpeg.org/download.html
```

### Related Files

- `audio_transcribe_gui.py` - Graphical user interface version
- `README.md` - General project documentation
- `requirements.txt` - Python dependencies
- `transcriber_config.json` - GUI configuration (not used by CLI)

---

**Last Updated:** December 23, 2025  
**Version:** 1.0  
**Compatible with:** Python 3.8-3.13

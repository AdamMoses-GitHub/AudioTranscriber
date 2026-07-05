# Installation and Usage Guide

Complete installation instructions and usage documentation for Audio Transcriber.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [CLI Reference](#cli-reference)
- [Model Comparison](#model-comparison)
- [Configuration](#configuration)
- [Transcript Format](#transcript-format)
- [Troubleshooting](#troubleshooting)
- [Performance Tips](#performance-tips)
- [System Requirements](#system-requirements)

## Installation

### Prerequisites
- Python 3.8 or higher
- NVIDIA GPU with CUDA support (optional, for GPU acceleration)
- FFmpeg (for advanced audio format support)

### Basic Installation

1. **Clone or download this repository**
   ```bash
   cd AudioTranscriber
   ```

2. **Install Python dependencies**

   **GPU setup (recommended if you have an NVIDIA GPU):**
   ```bash
   pip install -r requirements-gpu.txt
   ```

   **CPU-only setup (works on any machine, slower):**
   ```bash
   pip install -r requirements-cpu.txt
   ```

3. **Install FFmpeg** (if not already installed)
   - **Windows**: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg`

### GPU Acceleration Setup

The GPU requirements file (`requirements-gpu.txt`) already pulls PyTorch with CUDA 12.4 support. If you need a different CUDA version, install PyTorch manually after the base install:

```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Verify GPU availability:**
```bash
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

**Important**: The default `pip install torch` provides CPU-only support. You must explicitly install the CUDA version for GPU acceleration.

### Installation Notes

- **Faster-Whisper**: May fail to install on Python 3.14+ due to `av` package compilation issues. The application works fine with OpenAI Whisper alone.
- **tkinter**: Included with standard Python installations
- **Conda users**: Activate your environment before installation

## Usage

### Graphical User Interface (GUI)

Launch the GUI application:

```bash
python audio_transcribe_gui.py
```

#### GUI Features

**Single File Tab**
1. Click "Browse" to select an audio file
2. Configure options (date detection, line formatting)
3. Click "Transcribe File" to start processing
4. View results in the text area
5. Click "Save Transcript To File" to save (optional)

**Batch Processing Tab**
1. Select input folder containing audio files
2. Select output folder for transcripts
3. Configure options:
   - Skip existing transcripts
   - Create summary report
   - Preserve folder structure
   - Recursive subdirectory search
4. Click "Start Batch Processing"
5. Monitor progress in real-time log

**Model Configuration Tab**
- Choose transcription engine: `faster_whisper_gpu`, `faster_whisper_cpu`, `whisper_gpu`, `whisper_cpu`, or `auto_gpu`
- Select model size (tiny to large-v3, including turbo)
- Set compute precision (int8, int8_float16, float16)
- Download models and view model information
- Check GPU status and capabilities
- Configure speaker diarization (HuggingFace token + pyannote model)

**About Tab**
- View application features and system information
- Check GPU availability and device details

### Command-Line Interface (CLI)

The CLI provides the same functionality as the GUI with scriptable access.

#### Single File Transcription

**Basic usage:**
```bash
python audio_transcribe_cli.py single input.mp3
```

**With custom output:**
```bash
python audio_transcribe_cli.py single input.mp3 -o transcript.txt
```

**With model selection:**
```bash
python audio_transcribe_cli.py single input.mp3 --model large --engine whisper
```

**Full example with all options:**
```bash
python audio_transcribe_cli.py single recording.mp3 \
  --output transcript.txt \
  --model small \
  --engine faster_whisper \
  --compute float16 \
  --chars-per-line 100 \
  --timestamps \
  --timestamp-format HH:MM:SS \
  --timestamp-interval 60 \
  --no-detect-date
```

#### Batch Processing

**Basic batch:**
```bash
python audio_transcribe_cli.py batch input_folder output_folder
```

**Recursive with structure preservation:**
```bash
python audio_transcribe_cli.py batch input_folder output_folder \
  --recursive \
  --preserve-structure \
  --skip-existing \
  --create-summary
```

**Full batch example:**
```bash
python audio_transcribe_cli.py batch ./recordings ./transcripts \
  --model medium \
  --engine auto_gpu \
  --compute float16 \
  --chars-per-line 80 \
  --recursive \
  --preserve-structure \
  --skip-existing \
  --create-summary \
  --timestamps \
  --timestamp-interval 30
```

#### System Information

Check your setup:
```bash
python audio_transcribe_cli.py info
```

## CLI Reference

### Single File Options

- `INPUT_FILE`: Audio file to transcribe (required)
- `-o, --output`: Output file path (optional, defaults to input name with .txt)
- `--engine`: `whisper` | `faster_whisper` | `auto_gpu` (default: `auto_gpu`)
- `--model`: `tiny` | `base` | `small` | `medium` | `large` | `large-v2` | `large-v3` | `turbo` (default: `base`)
- `--compute`: `int8` | `int8_float16` | `float16` | `float32` (default: `float16`)
- `--detect-date`: Enable date detection (default: enabled)
- `--no-detect-date`: Disable date detection
- `--chars-per-line N`: Characters per line, 0=no breaks (default: 80)
- `--timestamps`: Embed timestamps throughout the transcript
- `--timestamp-format`: `HH:MM:SS` | `MM:SS` | `timecode` (default: `HH:MM:SS`)
- `--timestamp-interval SECONDS`: Seconds between timestamps; 15, 30, 60, 120, 300, 600 (default: 30)

### Batch Processing Options

- `INPUT_FOLDER`: Folder with audio files (required)
- `OUTPUT_FOLDER`: Folder for transcripts (required)
- All single file options (including `--timestamps`, `--timestamp-format`, `--timestamp-interval`), plus:
- `--skip-existing`: Skip files with existing transcripts
- `--create-summary`: Generate batch summary report
- `--preserve-structure`: Maintain input folder hierarchy
- `--recursive`: Search subdirectories for audio files

### Get Help

```bash
python audio_transcribe_cli.py --help
python audio_transcribe_cli.py single --help
python audio_transcribe_cli.py batch --help
```

## Model Comparison

| Model | Parameters | VRAM | Speed (GPU) | Accuracy | Best For | Download Size |
|-------|-----------|------|-------------|----------|----------|---------------|
| tiny | 39M | ~0.2GB | 30-50x | Basic | Quick drafts | ~75MB |
| base | 74M | ~0.5GB | 20-40x | Good | **General use** | ~150MB |
| small | 244M | ~1GB | 10-20x | Better | High quality | ~500MB |
| medium | 769M | ~2GB | 5-10x | High | Professional | ~1.5GB |
| turbo | 809M | ~3GB | 8-15x | High | Balanced speed & accuracy | ~1.6GB |
| large-v3 | 1550M | ~6GB | 2-5x | Highest | Critical accuracy | ~3GB |

**Recommendation**: Start with `base` for general use. Try `turbo` for a solid speed/accuracy balance, or `small`/`medium` if you need better accuracy without jumping all the way to `large-v3`.

## Speaker Diarization

Speaker diarization labels each segment of the transcript with who is speaking (e.g., `SPEAKER_00`, `SPEAKER_01`). It uses [pyannote.audio 3.1](https://github.com/pyannote/pyannote-audio) and requires a free HuggingFace account.

### Setup

1. **Create a HuggingFace account** at [huggingface.co](https://huggingface.co)
2. **Accept the model license** at [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. **Generate an access token** at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
4. **Enter the token** in the GUI under *Model Configuration → Diarization* tab

### GUI Usage

1. Open the **Diarization** sub-tab under Model Configuration
2. Paste your HuggingFace token and click **Test Token**
3. Enable diarization in the Single File or Batch Processing tab
4. Optionally set the number of speakers (or leave at 0 for auto-detection)

### Notes
- Diarization runs after transcription and requires additional processing time
- CPU diarization is significantly slower; GPU is recommended
- The pyannote model is downloaded the first time it's used (~1GB)
- Speaker labels appear inline as `SPEAKER_00:`, `SPEAKER_01:`, etc.
- No CLI flag yet — diarization is GUI-only in the current release

### Example Output

**Diarization off, timestamps off**
```text
Hello everyone. Today we are reviewing the agenda.
```

**Diarization off, timestamps on**
```text
[00:00:00]
Hello everyone.

[00:01:00]
Today we are reviewing the agenda.
```

**Diarization on, timestamps off**
```text
SPEAKER_00: Hello everyone. Today we are reviewing the agenda.

SPEAKER_01: Great, let's start with the first item.
```

**Diarization on, timestamps on**
```text
[00:00:00] SPEAKER_00: Hello everyone.

[00:01:00] SPEAKER_01: Great, let's start with the first item.
```

## Configuration

### GUI Configuration
- Settings are automatically saved to `transcriber_config.json`
- Persisted settings include:
  - Selected engine, model, and compute type
  - File paths and folder selections
  - Processing options (date detection, line formatting)
  - Batch processing preferences

### CLI Configuration
- All settings specified via command-line arguments
- No persistent configuration for CLI mode
- Use shell scripts or aliases for repeated configurations

## Transcript Format

Generated transcripts include comprehensive metadata:

```
Transcript of: recording.mp3
Recording Date: 2024-03-15 (Friday)
Transcribed: 2024-03-15 14:30:00

--- TRANSCRIPTION METADATA ---
File Size:         25.50 MB
Audio Format:      MP3, 192 kbps, 44100 Hz, Stereo
MP3 Tags:
  Title: Interview Session
  Artist: John Doe
  Album: 2024 Recordings
Duration:          0:15:30
Processing Time:   0:01:45
Speed:             8.9x real-time
Engine:            faster_whisper
Model:             base
Compute Precision: float16
GPU:               NVIDIA GeForce RTX 3080
Language:          en
Confidence:        89.5%
============================================================

[Transcribed text content follows here...]
```

## Troubleshooting

### GPU Not Detected

**Problem**: Application shows "CPU Only" despite having an NVIDIA GPU

**Solution**:
1. Verify CUDA installation: `nvidia-smi`
2. Install the GPU requirements file:
   ```bash
   pip install -r requirements-gpu.txt
   ```
3. Verify: `python -c "import torch; print(torch.cuda.is_available())"`

### Faster-Whisper Installation Fails

**Problem**: `av` package compilation errors on Python 3.14+

**Solution**:
- This is expected on newer Python versions
- The application works perfectly with OpenAI Whisper alone
- Set engine to "whisper" instead of "faster_whisper"

### FFmpeg Not Found

**Problem**: Error processing certain audio formats

**Solution**:
1. Install FFmpeg:
   - Windows: `choco install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`
2. Restart application

### Out of VRAM

**Problem**: GPU runs out of memory during processing

**Solution**:
1. Use a smaller model (base instead of medium/large)
2. Use lower precision (int8 instead of float16)
3. Close other GPU-intensive applications
4. Fall back to CPU mode (slower but unlimited memory)

### Slow Processing on CPU

**Problem**: Transcription takes much longer than real-time

**Expected Behavior**: CPU processing is slower than GPU:
- **GPU**: 2-50x real-time (depending on model)
- **CPU**: 0.1-1x real-time (slower than audio playback)

**Solutions**:
1. Enable GPU acceleration (see GPU setup above)
2. Use smaller model (tiny/base for CPU)
3. Use int8 compute type for better CPU performance

### Inaccurate Transcriptions

**Problem**: Text doesn't match audio well

**Solutions**:
1. Use larger model (medium or large-v3)
2. Ensure audio quality is good (not heavily compressed)
3. Check if audio language is supported by Whisper
4. Use higher precision (float16 or float32)

## Performance Tips

1. **For Best Speed**: Use `tiny` or `base` model with GPU and float16 precision
2. **For Best Accuracy**: Use `large-v3` model with GPU and float32 precision
3. **For Batch Processing**: Enable `--skip-existing` to resume interrupted jobs
4. **For Large Collections**: Use `--preserve-structure` with `--recursive` to maintain organization
5. **For Limited VRAM**: Start with `base` model and int8 precision

## System Requirements

### Minimum
- Python 3.8+
- 4GB RAM
- 2GB free disk space (for models)
- CPU: Any modern processor

### Recommended
- Python 3.10+
- 8GB+ RAM
- NVIDIA GPU with 4GB+ VRAM
- 10GB free disk space
- CPU: Multi-core processor

### Optimal
- Python 3.11+
- 16GB+ RAM
- NVIDIA GPU with 8GB+ VRAM (RTX 3060 or better)
- 20GB free disk space
- CPU: 6+ cores

## Known Limitations

- **Language Support**: Best results with English; other languages supported but may have lower accuracy
- **Audio Quality**: Poor quality recordings will have lower transcription accuracy
- **Speaker Diarization CLI**: Diarization is currently GUI-only; no CLI flag yet
- **Python 3.14**: Faster-Whisper may not install due to av package issues
- **macOS ARM**: CUDA is not available on Apple Silicon; CPU-only mode applies

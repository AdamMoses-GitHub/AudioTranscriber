# TODO List

## Planned Features

### High Priority
- [ ] **Support Configurable Timestamps**
  - Add option to include timestamps in transcriptions
  - Allow users to configure timestamp format (e.g., [HH:MM:SS], [MM:SS], timecode)
  - Support timestamp intervals (e.g., every 30 seconds, per sentence, per paragraph)
  - Add toggle in GUI to enable/disable timestamps
  - Include timestamps in CLI output options

- [ ] **Support Multiple Speaker Detection (Diarization)**
  - Implement speaker diarization to identify different speakers
  - Label transcript segments by speaker (e.g., "Speaker 1:", "Speaker 2:")
  - Add configuration for number of expected speakers
  - Integrate with pyannote-audio or similar speaker diarization library
  - Display speaker changes in formatted output
  - Add speaker detection toggle in GUI settings

## Future Enhancements
- [ ] Additional features to be added over time

## Completed
- [x] Initial release with single file and batch transcription
- [x] GPU acceleration support
- [x] Multiple model size options
- [x] Metadata extraction from audio files

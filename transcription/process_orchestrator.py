"""Process-isolated orchestration for transcription tasks.

This module runs heavy transcription work in child processes so UI threads remain
responsive and model/decoder failures are contained to worker processes.
"""

from multiprocessing import get_context
from typing import Any, Dict, Tuple


def _safe_send(conn, payload: Dict[str, Any]) -> None:
    """Send payload to parent process, swallowing broken-pipe style failures."""
    try:
        conn.send(payload)
    except (BrokenPipeError, EOFError, OSError):
        pass


def _single_file_worker(task: Dict[str, Any], conn) -> None:
    """Child-process entrypoint for single-file transcription."""
    from config import Environment
    from models import ModelManager
    from transcription import Transcriber, Diarizer

    model_manager = None
    diarizer = None

    try:
        _safe_send(conn, {'type': 'status', 'message': 'Loading model in worker process...'})

        environment = Environment()
        model_manager = ModelManager(environment)
        transcriber = Transcriber(model_manager, environment)

        success, error = model_manager.load_model(
            task['engine'],
            task['model_size'],
            task['compute_type']
        )
        if not success:
            _safe_send(conn, {'type': 'error', 'error': f'Failed to load model: {error}'})
            return

        options = dict(task.get('options', {}))
        diarization_enabled = bool(task.get('diarization_enabled', False))
        hf_token = (task.get('hf_token') or '').strip()

        result = None
        if diarization_enabled and environment.pyannote_available:
            _safe_send(conn, {'type': 'status', 'message': 'Loading diarization pipeline in worker process...'})
            diarizer = Diarizer(environment)
            if not hf_token:
                _safe_send(conn, {'type': 'error', 'error': 'Diarization requested but Hugging Face token is missing.'})
                return

            if not diarizer.load_pipeline(hf_token, whisper_loaded=True):
                _safe_send(conn, {'type': 'error', 'error': 'Failed to load diarization pipeline in worker process.'})
                return

            _safe_send(conn, {'type': 'status', 'message': 'Transcribing with diarization in worker process...'})
            result = transcriber.transcribe_with_diarization(
                task['audio_file'],
                task['engine'],
                diarizer,
                task.get('num_speakers'),
                options=options,
                progress_callback=None
            )
        else:
            _safe_send(conn, {'type': 'status', 'message': 'Transcribing in worker process...'})
            result = transcriber.transcribe_with_metadata(
                task['audio_file'],
                task['engine'],
                options=options,
                progress_callback=None
            )

        # Keep IPC payload compact; large segment arrays significantly increase
        # serialization overhead and memory usage in parent/child processes.
        compact_result = {
            'text': result.get('text', '') if isinstance(result, dict) else result,
            'language': result.get('language', 'Unknown') if isinstance(result, dict) else 'Unknown',
            'duration': result.get('duration', 0) if isinstance(result, dict) else 0,
            'avg_logprob': result.get('avg_logprob') if isinstance(result, dict) else None,
            'audio_metadata': result.get('audio_metadata', {}) if isinstance(result, dict) else {},
            'num_speakers': result.get('num_speakers') if isinstance(result, dict) else None,
            'diarization_fallback': result.get('diarization_fallback') if isinstance(result, dict) else None,
            'diarization_error': result.get('diarization_error') if isinstance(result, dict) else None,
        }
        _safe_send(conn, {'type': 'result', 'result': compact_result})
    except Exception as e:
        _safe_send(conn, {'type': 'error', 'error': f'{type(e).__name__}: {e}'})
    finally:
        try:
            if diarizer is not None:
                diarizer.cleanup()
        except Exception:
            pass
        try:
            if model_manager is not None:
                model_manager.cleanup_model()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _batch_worker(task: Dict[str, Any], conn) -> None:
    """Child-process entrypoint for batch transcription."""
    from config import Environment
    from models import ModelManager
    from transcription import Transcriber, BatchProcessor, Diarizer

    model_manager = None
    diarizer = None

    try:
        environment = Environment()
        model_manager = ModelManager(environment)
        transcriber = Transcriber(model_manager, environment)
        batch_processor = BatchProcessor(transcriber, model_manager)

        _safe_send(conn, {'type': 'status', 'message': 'Loading model in worker process...'})
        success, error = model_manager.load_model(
            task['engine'],
            task['model_size'],
            task['compute_type']
        )
        if not success:
            _safe_send(conn, {'type': 'error', 'error': f'Failed to load model: {error}'})
            return

        options = dict(task.get('options', {}))
        diarization_enabled = bool(task.get('diarization_enabled', False))
        hf_token = (task.get('hf_token') or '').strip()

        if diarization_enabled and environment.pyannote_available:
            _safe_send(conn, {'type': 'status', 'message': 'Loading diarization pipeline in worker process...'})
            diarizer = Diarizer(environment)
            if not hf_token:
                _safe_send(conn, {'type': 'error', 'error': 'Diarization requested but Hugging Face token is missing.'})
                return
            if not diarizer.load_pipeline(hf_token, whisper_loaded=True):
                _safe_send(conn, {'type': 'error', 'error': 'Failed to load diarization pipeline in worker process.'})
                return

            options['diarization_enabled'] = True
            options['diarizer'] = diarizer
            options['num_speakers'] = task.get('num_speakers')
        else:
            options['diarization_enabled'] = False

        def progress_callback(current: int, total: int, filename: str) -> None:
            _safe_send(conn, {'type': 'progress', 'current': current, 'total': total, 'filename': filename})

        def log_callback(message: str) -> None:
            _safe_send(conn, {'type': 'log', 'message': message})

        _safe_send(conn, {'type': 'status', 'message': 'Running batch in worker process...'})
        stats = batch_processor.process_batch(
            task['input_folder'],
            task['output_folder'],
            options,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
        _safe_send(conn, {'type': 'result', 'result': stats})
    except Exception as e:
        _safe_send(conn, {'type': 'error', 'error': f'{type(e).__name__}: {e}'})
    finally:
        try:
            if diarizer is not None:
                diarizer.cleanup()
        except Exception:
            pass
        try:
            if model_manager is not None:
                model_manager.cleanup_model()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def start_single_file_process(task: Dict[str, Any]) -> Tuple[Any, Any]:
    """Start a process-isolated single-file transcription worker.

    Returns:
        (process, connection) tuple where connection receives worker events.
    """
    ctx = get_context('spawn')
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_single_file_worker, args=(task, child_conn), daemon=True)
    process.start()
    child_conn.close()
    return process, parent_conn


def start_batch_process(task: Dict[str, Any]) -> Tuple[Any, Any]:
    """Start a process-isolated batch transcription worker.

    Returns:
        (process, connection) tuple where connection receives worker events.
    """
    ctx = get_context('spawn')
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_batch_worker, args=(task, child_conn), daemon=True)
    process.start()
    child_conn.close()
    return process, parent_conn

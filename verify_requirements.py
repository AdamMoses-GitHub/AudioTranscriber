"""
Verify Requirements Script
Checks and reports on all required and optional dependencies for Audio Transcriber.
"""
import sys
from importlib import import_module
from importlib.metadata import version, PackageNotFoundError
from config.constants import STATUS_SUCCESS, STATUS_ERROR, STATUS_WARNING


def check_package(package_name, import_name=None, optional=False):
    """
    Check if a package is installed and importable.
    
    Args:
        package_name: Package name as listed in pip
        import_name: Module name to import (if different from package_name)
        optional: Whether the package is optional
        
    Returns:
        Dictionary with status information
    """
    if import_name is None:
        import_name = package_name
    
    result = {
        'package': package_name,
        'import_name': import_name,
        'optional': optional,
        'installed': False,
        'importable': False,
        'version': None,
        'error': None
    }
    
    # Check if installed
    try:
        pkg_version = version(package_name)
        result['installed'] = True
        result['version'] = pkg_version
    except PackageNotFoundError:
        result['error'] = 'Not installed'
        return result
    
    # Check if importable
    try:
        import_module(import_name)
        result['importable'] = True
    except ImportError as e:
        result['error'] = f'Import error: {str(e)}'
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
    
    return result


def check_submodule(module_path, description):
    """
    Check if a specific submodule is importable.
    
    Args:
        module_path: Full module path (e.g., 'mutagen.id3')
        description: Human-readable description
        
    Returns:
        Dictionary with status information
    """
    result = {
        'module': module_path,
        'description': description,
        'importable': False,
        'error': None
    }
    
    try:
        import_module(module_path)
        result['importable'] = True
    except ImportError as e:
        result['error'] = f'Import error: {str(e)}'
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
    
    return result


def check_gpu_support():
    """Check GPU/CUDA availability."""
    result = {
        'available': False,
        'device_name': None,
        'memory_gb': None,
        'cuda_version': None,
        'error': None
    }
    
    try:
        import torch
        result['available'] = torch.cuda.is_available()
        
        if result['available']:
            result['device_name'] = torch.cuda.get_device_name(0)
            memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            result['memory_gb'] = round(memory, 1)
            result['cuda_version'] = torch.version.cuda
    except Exception as e:
        result['error'] = str(e)
    
    return result


def check_ffmpeg():
    """Check if FFmpeg is available."""
    import subprocess
    result = {
        'available': False,
        'version': None,
        'error': None
    }
    
    try:
        output = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if output.returncode == 0:
            result['available'] = True
            # Extract version from first line
            first_line = output.stdout.split('\n')[0]
            result['version'] = first_line
    except FileNotFoundError:
        result['error'] = 'FFmpeg not found in PATH'
    except subprocess.TimeoutExpired:
        result['error'] = 'FFmpeg check timed out'
    except Exception as e:
        result['error'] = str(e)
    
    return result


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_package_status(pkg_info):
    """Print status for a single package."""
    status_icon = STATUS_SUCCESS if pkg_info['importable'] else STATUS_ERROR
    optional_tag = ' [OPTIONAL]' if pkg_info['optional'] else ''
    
    print(f"\n{status_icon} {pkg_info['package']}{optional_tag}")
    print(f"   Import Name: {pkg_info['import_name']}")
    
    if pkg_info['installed']:
        print(f"   Version: {pkg_info['version']}")
        if pkg_info['importable']:
            print(f"   Status: {STATUS_SUCCESS} Installed and importable")
        else:
            print(f"   Status: {STATUS_WARNING} Installed but cannot import")
            if pkg_info['error']:
                print(f"   Error: {pkg_info['error']}")
    else:
        print(f"   Status: {STATUS_ERROR} Not installed")
        if pkg_info['error']:
            print(f"   Error: {pkg_info['error']}")


def main():
    """Main verification function."""
    print("\n" + "=" * 70)
    print("  AUDIO TRANSCRIBER - REQUIREMENTS VERIFICATION")
    print("=" * 70)
    print(f"  Python Version: {sys.version}")
    print("=" * 70)
    
    # Define packages to check
    core_packages = [
        ('torch', 'torch', False),
        ('openai-whisper', 'whisper', False),
    ]
    
    audio_packages = [
        ('av', 'av', False),
        ('faster-whisper', 'faster_whisper', True),
        ('pydub', 'pydub', False),
        ('mutagen', 'mutagen', False),
    ]
    
    builtin_modules = [
        ('tkinter', 'tkinter', False),
        ('wave', 'wave', False),
    ]
    
    # Check core packages
    print_section("CORE PACKAGES")
    core_results = [check_package(*pkg) for pkg in core_packages]
    for result in core_results:
        print_package_status(result)
    
    # Check audio packages
    print_section("AUDIO PROCESSING PACKAGES")
    audio_results = [check_package(*pkg) for pkg in audio_packages]
    for result in audio_results:
        print_package_status(result)
    
    # Check built-in modules
    print_section("BUILT-IN PYTHON MODULES")
    builtin_results = [check_package(*pkg) for pkg in builtin_modules]
    for result in builtin_results:
        print_package_status(result)
    
    # Check specific submodules
    print_section("SPECIFIC SUBMODULES")
    submodules = [
        ('mutagen.id3', 'ID3 tag support'),
        ('pydub', 'Audio segment processing'),
        ('faster_whisper', 'Faster-Whisper model'),
    ]
    
    for module_path, description in submodules:
        result = check_submodule(module_path, description)
        status_icon = STATUS_SUCCESS if result['importable'] else STATUS_ERROR
        print(f"\n{status_icon} {module_path} - {description}")
        if not result['importable'] and result['error']:
            print(f"   Error: {result['error']}")
    
    # Check GPU support
    print_section("GPU / CUDA SUPPORT")
    gpu_info = check_gpu_support()
    
    if gpu_info['available']:
        print(f"\n{STATUS_SUCCESS} GPU Available")
        print(f"   Device: {gpu_info['device_name']}")
        print(f"   Memory: {gpu_info['memory_gb']} GB")
        print(f"   CUDA Version: {gpu_info['cuda_version']}")
    else:
        print(f"\n{STATUS_ERROR} No GPU Detected")
        print(f"   Status: CPU mode only (slower transcription)")
        if gpu_info['error']:
            print(f"   Error: {gpu_info['error']}")
    
    # Check FFmpeg
    print_section("EXTERNAL TOOLS")
    ffmpeg_info = check_ffmpeg()
    
    if ffmpeg_info['available']:
        print(f"\n{STATUS_SUCCESS} FFmpeg Available")
        print(f"   {ffmpeg_info['version']}")
    else:
        print(f"\n{STATUS_WARNING} FFmpeg Not Found")
        print(f"   Status: Required for advanced audio format support")
        if ffmpeg_info['error']:
            print(f"   Error: {ffmpeg_info['error']}")
        print(f"\n   Installation instructions:")
        print(f"   - Windows: choco install ffmpeg")
        print(f"   - macOS: brew install ffmpeg")
        print(f"   - Linux: sudo apt-get install ffmpeg")
    
    # Summary
    print_section("SUMMARY")
    
    all_results = core_results + audio_results + builtin_results
    required = [r for r in all_results if not r['optional']]
    optional = [r for r in all_results if r['optional']]
    
    required_ok = sum(1 for r in required if r['importable'])
    required_total = len(required)
    optional_ok = sum(1 for r in optional if r['importable'])
    optional_total = len(optional)
    
    print(f"\nRequired Packages: {required_ok}/{required_total} OK")
    print(f"Optional Packages: {optional_ok}/{optional_total} OK")
    print(f"GPU Support: {STATUS_SUCCESS + ' Yes' if gpu_info['available'] else STATUS_ERROR + ' No (CPU only)'}")
    print(f"FFmpeg: {STATUS_SUCCESS + ' Available' if ffmpeg_info['available'] else STATUS_WARNING + ' Not found'}")
    
    if required_ok == required_total:
        print(f"\n{STATUS_SUCCESS} All required packages are installed and working!")
    else:
        print(f"\n{STATUS_ERROR} Some required packages are missing or not working.")
        print(f"   Run: pip install -r requirements.txt")
    
    if optional_ok < optional_total:
        print(f"\n{STATUS_WARNING} Some optional packages are missing:")
        for r in optional:
            if not r['importable']:
                print(f"   - {r['package']}")
    
    print("\n" + "=" * 70 + "\n")
    
    return required_ok == required_total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

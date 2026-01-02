"""
Verify Requirements Script
Checks and reports on all required and optional dependencies for Audio Transcriber.
"""
import sys
import json
import argparse
from importlib import import_module
from importlib.metadata import version, PackageNotFoundError
from config.constants import STATUS_SUCCESS, STATUS_ERROR, STATUS_WARNING


def safe_print(*args, **kwargs):
    """
    Safe print that handles encoding errors by using ASCII fallbacks.
    
    On Windows with non-UTF8 encoding, replaces emoji with ASCII equivalents.
    """
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Replace emoji with ASCII-safe alternatives
        line = str(args[0]) if args else ""
        replacements = {
            "✅": "[OK]",
            "❌": "[FAIL]",
            "⚠️": "[WARN]",
            "⏭️": "[SKIP]"
        }
        for emoji, replacement in replacements.items():
            line = line.replace(emoji, replacement)
        
        # Try printing again with replacements
        if args:
            print(line, *args[1:], **kwargs)
        else:
            print(line, **kwargs)


# ============================================================================
# Package Configuration
# ============================================================================
PACKAGES_CONFIG = {
    'core': [
        ('torch', 'torch', False),
        ('openai-whisper', 'whisper', False),
    ],
    'audio': [
        ('av', 'av', False),
        ('faster-whisper', 'faster_whisper', True),
        ('pydub', 'pydub', False),
        ('mutagen', 'mutagen', False),
    ],
    'builtin': [
        ('tkinter', 'tkinter', False),
        ('wave', 'wave', False),
    ],
    'submodules': [
        ('mutagen.id3', 'ID3 tag support'),
        ('pydub', 'Audio segment processing'),
        ('faster_whisper', 'Faster-Whisper model'),
    ],
}


def check_python_version(min_major=3, min_minor=9):
    """
    Check Python version compatibility.
    
    Args:
        min_major: Minimum major version
        min_minor: Minimum minor version
        
    Returns:
        Dictionary with version check results
    """
    result = {
        'current': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'minimum': f"{min_major}.{min_minor}",
        'compatible': True,
        'checks': {}
    }
    
    # Check Python version
    if sys.version_info < (min_major, min_minor):
        result['compatible'] = False
        result['checks']['version'] = False
    else:
        result['checks']['version'] = True
    
    # Check pip
    try:
        from importlib.metadata import version as get_version
        pip_version = get_version('pip')
        result['checks']['pip'] = True
        result['pip_version'] = pip_version
    except Exception:
        result['checks']['pip'] = False
    
    # Check setuptools
    try:
        from importlib.metadata import version as get_version
        setuptools_version = get_version('setuptools')
        result['checks']['setuptools'] = True
        result['setuptools_version'] = setuptools_version
    except Exception:
        result['checks']['setuptools'] = False
    
    return result


def check_package(package_name, import_name=None, optional=False, verbose=False):
    """
    Check if a package is installed and importable.
    
    Args:
        package_name: Package name as listed in pip
        import_name: Module name to import (if different from package_name)
        optional: Whether the package is optional
        verbose: Whether to show detailed error information
        
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
        'error': None,
        'trace': None
    }
    
    # Check if installed via package metadata
    try:
        pkg_version = version(package_name)
        result['installed'] = True
        result['version'] = pkg_version
    except PackageNotFoundError:
        result['error'] = 'No package metadata found'
    
    # Check if importable
    try:
        import_module(import_name)
        result['importable'] = True
        # If importable but no version, it's a built-in module
        if not result['installed']:
            result['installed'] = True
            result['version'] = 'Built-in'
            result['error'] = None
    except ImportError as e:
        error_msg = str(e)
        result['error'] = f'Import error: {error_msg}'
        if verbose:
            result['trace'] = error_msg
    except Exception as e:
        error_msg = str(e)
        result['error'] = f'Unexpected error: {error_msg}'
        if verbose:
            result['trace'] = error_msg
    
    return result


def check_submodule(module_path, description, verbose=False):
    """
    Check if a specific submodule is importable.
    
    Args:
        module_path: Full module path (e.g., 'mutagen.id3')
        description: Human-readable description
        verbose: Whether to show detailed error information
        
    Returns:
        Dictionary with status information
    """
    result = {
        'module': module_path,
        'description': description,
        'importable': False,
        'error': None,
        'trace': None
    }
    
    try:
        import_module(module_path)
        result['importable'] = True
    except ImportError as e:
        error_msg = str(e)
        result['error'] = f'Import error: {error_msg}'
        if verbose:
            result['trace'] = error_msg
    except Exception as e:
        error_msg = str(e)
        result['error'] = f'Unexpected error: {error_msg}'
        if verbose:
            result['trace'] = error_msg
    
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


def check_ffmpeg(verbose=False):
    """
    Check if FFmpeg is available.
    
    Args:
        verbose: Whether to show detailed error information
        
    Returns:
        Dictionary with FFmpeg status
    """
    import subprocess
    result = {
        'available': False,
        'version': None,
        'error': None,
        'trace': None
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
        error_msg = str(e)
        result['error'] = error_msg
        if verbose:
            result['trace'] = error_msg
    
    return result


class PackageFormatter:
    """Handles formatting and output of package status information."""
    
    def __init__(self, json_output=False, verbose=False):
        self.json_output = json_output
        self.verbose = verbose
        self.json_data = {
            'summary': {},
            'python': {},
            'packages': {},
            'submodules': {},
            'gpu': {},
            'ffmpeg': {}
        }
    
    @staticmethod
    def print_section(title):
        """Print a section header."""
        safe_print(f"\n{'=' * 70}")
        safe_print(f"  {title}")
        safe_print('=' * 70)
    
    def print_package_status(self, pkg_info):
        """Print status for a single package."""
        if self.json_output:
            return  # Handled in JSON output
        
        status_icon = STATUS_SUCCESS if pkg_info['importable'] else STATUS_ERROR
        optional_tag = ' [OPTIONAL]' if pkg_info['optional'] else ''
        
        safe_print(f"\n{status_icon} {pkg_info['package']}{optional_tag}")
        safe_print(f"   Import Name: {pkg_info['import_name']}")
        
        if pkg_info['installed']:
            safe_print(f"   Version: {pkg_info['version']}")
            if pkg_info['importable']:
                safe_print(f"   Status: {STATUS_SUCCESS} Installed and importable")
            else:
                safe_print(f"   Status: {STATUS_WARNING} Installed but cannot import")
                if pkg_info['error']:
                    safe_print(f"   Error: {pkg_info['error']}")
                    if self.verbose and pkg_info.get('trace'):
                        safe_print(f"   Trace: {pkg_info['trace']}")
        else:
            safe_print(f"   Status: {STATUS_ERROR} Not installed")
            if pkg_info['error']:
                safe_print(f"   Error: {pkg_info['error']}")
                if self.verbose and pkg_info.get('trace'):
                    safe_print(f"   Trace: {pkg_info['trace']}")
    
    def print_submodule_status(self, sub_info):
        """Print status for a submodule."""
        if self.json_output:
            return  # Handled in JSON output
        
        status_icon = STATUS_SUCCESS if sub_info['importable'] else STATUS_ERROR
        safe_print(f"\n{status_icon} {sub_info['module']} - {sub_info['description']}")
        if not sub_info['importable'] and sub_info['error']:
            safe_print(f"   Error: {sub_info['error']}")
            if self.verbose and sub_info.get('trace'):
                safe_print(f"   Trace: {sub_info['trace']}")
    
    def print_python_status(self, py_info):
        """Print Python version status."""
        if self.json_output:
            return  # Handled in JSON output
        
        status_icon = STATUS_SUCCESS if py_info['compatible'] else STATUS_ERROR
        safe_print(f"\n{status_icon} Python {py_info['current']}")
        safe_print(f"   Required: {py_info['minimum']}+")
        safe_print(f"   Compatible: {STATUS_SUCCESS if py_info['compatible'] else STATUS_ERROR}")
        
        if py_info['checks'].get('pip'):
            safe_print(f"   Pip: {STATUS_SUCCESS} {py_info.get('pip_version', 'installed')}")
        else:
            safe_print(f"   Pip: {STATUS_ERROR} Not available")
        
        if py_info['checks'].get('setuptools'):
            safe_print(f"   Setuptools: {STATUS_SUCCESS} {py_info.get('setuptools_version', 'installed')}")
        else:
            safe_print(f"   Setuptools: {STATUS_WARNING} Not available")


def print_section(title):
    """Print a section header."""
    safe_print(f"\n{'=' * 70}")
    safe_print(f"  {title}")
    safe_print('=' * 70)


def main(args=None):
    """Main verification function."""
    parser = argparse.ArgumentParser(
        description='Verify Audio Transcriber requirements and dependencies'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        dest='json_output',
        help='Output results as JSON for programmatic parsing'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed error traces and full import information'
    )
    
    parsed_args = parser.parse_args(args)
    json_output = parsed_args.json_output
    verbose = parsed_args.verbose
    
    formatter = PackageFormatter(json_output=json_output, verbose=verbose)
    
    if not json_output:
        safe_print("\n" + "=" * 70)
        safe_print("  AUDIO TRANSCRIBER - REQUIREMENTS VERIFICATION")
        safe_print("=" * 70)
        safe_print(f"  Python Version: {sys.version}")
        safe_print("=" * 70)
    
    # Check Python version and tools
    py_info = check_python_version()
    if not json_output:
        print_section("PYTHON ENVIRONMENT")
        formatter.print_python_status(py_info)
    
    # Check core packages
    core_results = [check_package(*pkg, verbose=verbose) for pkg in PACKAGES_CONFIG['core']]
    if not json_output:
        print_section("CORE PACKAGES")
        for result in core_results:
            formatter.print_package_status(result)
    
    # Check audio packages
    audio_results = [check_package(*pkg, verbose=verbose) for pkg in PACKAGES_CONFIG['audio']]
    if not json_output:
        print_section("AUDIO PROCESSING PACKAGES")
        for result in audio_results:
            formatter.print_package_status(result)
    
    # Check built-in modules
    builtin_results = [check_package(*pkg, verbose=verbose) for pkg in PACKAGES_CONFIG['builtin']]
    if not json_output:
        print_section("BUILT-IN PYTHON MODULES")
        for result in builtin_results:
            formatter.print_package_status(result)
    
    # Check specific submodules
    submodule_results = [check_submodule(*sub, verbose=verbose) for sub in PACKAGES_CONFIG['submodules']]
    if not json_output:
        print_section("SPECIFIC SUBMODULES")
        for result in submodule_results:
            formatter.print_submodule_status(result)
    
    # Check GPU support
    gpu_info = check_gpu_support()
    if not json_output:
        print_section("GPU / CUDA SUPPORT")
        
        if gpu_info['available']:
            safe_print(f"\n{STATUS_SUCCESS} GPU Available")
            safe_print(f"   Device: {gpu_info['device_name']}")
            safe_print(f"   Memory: {gpu_info['memory_gb']} GB")
            safe_print(f"   CUDA Version: {gpu_info['cuda_version']}")
        else:
            safe_print(f"\n{STATUS_ERROR} No GPU Detected")
            safe_print(f"   Status: CPU mode only (slower transcription)")
            if gpu_info['error']:
                safe_print(f"   Error: {gpu_info['error']}")
                if verbose and gpu_info.get('trace'):
                    safe_print(f"   Trace: {gpu_info['trace']}")
    
    # Check FFmpeg
    ffmpeg_info = check_ffmpeg(verbose=verbose)
    if not json_output:
        print_section("EXTERNAL TOOLS")
        
        if ffmpeg_info['available']:
            safe_print(f"\n{STATUS_SUCCESS} FFmpeg Available")
            safe_print(f"   {ffmpeg_info['version']}")
        else:
            safe_print(f"\n{STATUS_WARNING} FFmpeg Not Found")
            safe_print(f"   Status: Required for advanced audio format support")
            if ffmpeg_info['error']:
                safe_print(f"   Error: {ffmpeg_info['error']}")
                if verbose and ffmpeg_info.get('trace'):
                    safe_print(f"   Trace: {ffmpeg_info['trace']}")
            safe_print(f"\n   Installation instructions:")
            safe_print(f"   - Windows: choco install ffmpeg")
            safe_print(f"   - macOS: brew install ffmpeg")
            safe_print(f"   - Linux: sudo apt-get install ffmpeg")
    
    # Summary
    if json_output:
        # Build JSON output
        all_results = core_results + audio_results + builtin_results
        required = [r for r in all_results if not r['optional']]
        optional = [r for r in all_results if r['optional']]
        
        required_ok = sum(1 for r in required if r['importable'])
        required_total = len(required)
        optional_ok = sum(1 for r in optional if r['importable'])
        optional_total = len(optional)
        
        formatter.json_data['summary'] = {
            'python_version': py_info['current'],
            'python_compatible': py_info['compatible'],
            'required_packages_ok': required_ok,
            'required_packages_total': required_total,
            'optional_packages_ok': optional_ok,
            'optional_packages_total': optional_total,
            'gpu_available': gpu_info['available'],
            'ffmpeg_available': ffmpeg_info['available'],
            'all_requirements_met': required_ok == required_total
        }
        
        formatter.json_data['python'] = py_info
        formatter.json_data['packages'] = {
            'core': core_results,
            'audio': audio_results,
            'builtin': builtin_results
        }
        formatter.json_data['submodules'] = submodule_results
        formatter.json_data['gpu'] = gpu_info
        formatter.json_data['ffmpeg'] = ffmpeg_info
        
        # Output as JSON
        print(json.dumps(formatter.json_data, indent=2))
    else:
        # Print summary to console
        print_section("SUMMARY")
        
        all_results = core_results + audio_results + builtin_results
        required = [r for r in all_results if not r['optional']]
        optional = [r for r in all_results if r['optional']]
        
        required_ok = sum(1 for r in required if r['importable'])
        required_total = len(required)
        optional_ok = sum(1 for r in optional if r['importable'])
        optional_total = len(optional)
        
        safe_print(f"\nRequired Packages: {required_ok}/{required_total} OK")
        safe_print(f"Optional Packages: {optional_ok}/{optional_total} OK")
        safe_print(f"GPU Support: {STATUS_SUCCESS + ' Yes' if gpu_info['available'] else STATUS_ERROR + ' No (CPU only)'}")
        safe_print(f"FFmpeg: {STATUS_SUCCESS + ' Available' if ffmpeg_info['available'] else STATUS_WARNING + ' Not found'}")
        
        if required_ok == required_total:
            safe_print(f"\n{STATUS_SUCCESS} All required packages are installed and working!")
        else:
            safe_print(f"\n{STATUS_ERROR} Some required packages are missing or not working.")
            safe_print(f"   Run: pip install -r requirements.txt")
        
        if optional_ok < optional_total:
            safe_print(f"\n{STATUS_WARNING} Some optional packages are missing:")
            for r in optional:
                if not r['importable']:
                    safe_print(f"   - {r['package']}")
        
        safe_print("\n" + "=" * 70 + "\n")
    
    return required_ok == required_total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

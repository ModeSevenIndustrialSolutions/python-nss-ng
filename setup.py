# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss-ng contributors

"""
Setup configuration for python-nss-ng C extensions.

This file handles dynamic detection and configuration of NSS/NSPR libraries.
All project metadata is defined in pyproject.toml.
"""

import os
import sys
import glob
import multiprocessing
from setuptools import Extension, setup

# Try to import probe cache (optional - gracefully degrades)
try:
    from probe_cache import ProbeCache
    PROBE_CACHE_AVAILABLE = True
except ImportError:
    PROBE_CACHE_AVAILABLE = False

# Verbose mode controlled by environment variable
VERBOSE_SETUP = os.environ.get('PYTHON_NSS_VERBOSE_SETUP', '').lower() in ('1', 'true', 'yes')

def verbose_print(message):
    """Print message only if verbose mode is enabled."""
    if VERBOSE_SETUP:
        print(message)


def find_lib_dir(lib_names, lib_roots=None):
    """Locate a library directory containing the specified libraries."""
    if not lib_roots:
        lib_roots = ['/usr/lib', '/usr/local/lib', '/usr/lib64', '/usr/local/lib64']
        if sys.platform == 'darwin':
            try:
                import subprocess
                brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
                lib_roots.extend([
                    os.path.join(brew_prefix, 'lib'),
                    os.path.join(brew_prefix, 'opt', 'nss', 'lib'),
                    os.path.join(brew_prefix, 'opt', 'nspr', 'lib'),
                ])
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

    if not lib_names:
        raise ValueError("library search list is empty")

    for lib_root in lib_roots:
        if os.path.isdir(lib_root):
            found = True
            for lib_name in lib_names:
                lib_patterns = [
                    f'lib{lib_name}.so*',
                    f'lib{lib_name}.dylib',
                    f'lib{lib_name}.a',
                ]
                lib_found = any(glob.glob(os.path.join(lib_root, pattern)) for pattern in lib_patterns)
                if not lib_found:
                    found = False
                    break
            if found:
                return lib_root

    error_msg = (
        f"Unable to locate library directory containing libraries {lib_names}\n"
        f"Searched directories: {lib_roots}\n"
        f"To fix this issue:\n"
        f"  - On Fedora/RHEL/CentOS: sudo dnf install nss-devel nspr-devel\n"
        f"  - On Debian/Ubuntu: sudo apt-get install libnss3-dev libnspr4-dev\n"
        f"  - On macOS: brew install nss nspr\n"
        f"  - Or set NSS_LIB_ROOTS environment variable to custom paths (colon-separated)"
    )
    raise RuntimeError(error_msg)


def find_include_dir(dir_names, include_files, include_roots=None):
    """Locate an include directory containing the specified header files."""
    if not include_roots:
        include_roots = ['/usr/include', '/usr/local/include']
        if sys.platform == 'darwin':
            try:
                import subprocess
                brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
                include_roots.extend([
                    os.path.join(brew_prefix, 'include'),
                    os.path.join(brew_prefix, 'opt', 'nss', 'include', 'nss'),
                    os.path.join(brew_prefix, 'opt', 'nspr', 'include', 'nspr'),
                ])
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

    if not dir_names or not include_files:
        raise ValueError("directory and file lists cannot be empty")

    for include_root in include_roots:
        for dir_name in dir_names:
            include_dir = os.path.join(include_root, dir_name)
            if os.path.isdir(include_dir):
                if all(os.path.exists(os.path.join(include_dir, f)) for f in include_files):
                    return include_dir

    error_msg = (
        f"Unable to locate include directory containing files {include_files}\n"
        f"Searched directories: {include_roots}\n"
        f"To fix this issue:\n"
        f"  - On Fedora/RHEL/CentOS: sudo dnf install nss-devel nspr-devel\n"
        f"  - On Debian/Ubuntu: sudo apt-get install libnss3-dev libnspr4-dev\n"
        f"  - On macOS: brew install nss nspr\n"
        f"  - Or set NSS_INCLUDE_ROOTS environment variable to custom paths (colon-separated)"
    )
    raise RuntimeError(error_msg)


def get_extensions():
    """Build and return C extension configurations."""
    # Support environment variable overrides for include and library paths
    include_roots_env = os.environ.get('NSS_INCLUDE_ROOTS', '')
    include_roots = [p for p in include_roots_env.split(':') if p] if include_roots_env else None

    lib_roots_env = os.environ.get('NSS_LIB_ROOTS', '')
    lib_roots = [p for p in lib_roots_env.split(':') if p] if lib_roots_env else None

    verbose_print("NSS/NSPR build configuration:")
    if include_roots:
        verbose_print(f"  Using custom include roots: {include_roots}")
    if lib_roots:
        verbose_print(f"  Using custom library roots: {lib_roots}")

    # Try to load from cache first
    cache_hit = False
    library_dirs: list[str] = []
    include_dirs: list[str] = []
    runtime_library_dirs: list[str] = []
    extra_compile_args: list[str] = []

    if PROBE_CACHE_AVAILABLE:
        cache = ProbeCache()

        # Generate default roots if not provided
        default_lib_roots = lib_roots or []
        default_include_roots = include_roots or []

        if not default_lib_roots:
            default_lib_roots = ['/usr/lib', '/usr/local/lib', '/usr/lib64', '/usr/local/lib64']
            if sys.platform == 'darwin':
                try:
                    import subprocess
                    brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
                    default_lib_roots.extend([
                        os.path.join(brew_prefix, 'lib'),
                        os.path.join(brew_prefix, 'opt', 'nss', 'lib'),
                        os.path.join(brew_prefix, 'opt', 'nspr', 'lib'),
                    ])
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

        if not default_include_roots:
            default_include_roots = ['/usr/include', '/usr/local/include']
            if sys.platform == 'darwin':
                try:
                    import subprocess
                    brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
                    default_include_roots.extend([
                        os.path.join(brew_prefix, 'include'),
                        os.path.join(brew_prefix, 'opt', 'nss', 'include', 'nss'),
                        os.path.join(brew_prefix, 'opt', 'nspr', 'include', 'nspr'),
                    ])
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

        cached = cache.load(default_lib_roots, default_include_roots)
        if cached:
            verbose_print("Using cached probe results (faster build!)")
            library_dirs = cached['lib_dirs']
            include_dirs = cached['include_dirs']
            cache_hit = True
        else:
            verbose_print("Cache miss, performing fresh probe")

    # Find NSS and NSPR include directories (fail fast - no silent fallbacks)
    if not cache_hit:
        try:
            nss_include_dir = find_include_dir(['nss3', 'nss'], ['nss.h', 'pk11pub.h'], include_roots)
            print(f"Found NSS headers in: {nss_include_dir}")
        except (ValueError, RuntimeError) as e:
            print(f"ERROR: Could not find NSS headers", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)

        try:
            nspr_include_dir = find_include_dir(['nspr4', 'nspr'], ['nspr.h', 'prio.h'], include_roots)
            print(f"Found NSPR headers in: {nspr_include_dir}")
        except (ValueError, RuntimeError) as e:
            print(f"ERROR: Could not find NSPR headers", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)

        # Find NSS and NSPR library directories
        # Find NSPR libraries
        try:
            nspr_lib_dir = find_lib_dir(['nspr4'], lib_roots)
            print(f"Found NSPR libraries in: {nspr_lib_dir}")
            library_dirs.append(nspr_lib_dir)
            if sys.platform != 'darwin':
                runtime_library_dirs.append(nspr_lib_dir)
        except (ValueError, RuntimeError) as e:
            print(f"ERROR: Could not find NSPR libraries", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)

        # Find NSS libraries
        try:
            nss_lib_dir = find_lib_dir(['nss3'], lib_roots)
            print(f"Found NSS libraries in: {nss_lib_dir}")
            if nss_lib_dir not in library_dirs:
                library_dirs.append(nss_lib_dir)
                if sys.platform != 'darwin':
                    runtime_library_dirs.append(nss_lib_dir)
        except (ValueError, RuntimeError) as e:
            print(f"ERROR: Could not find NSS libraries", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)

        # Collect include directories
        include_dirs = [nss_include_dir, nspr_include_dir]

        # Save to cache for next time
        if PROBE_CACHE_AVAILABLE:
            cache.save(default_lib_roots, default_include_roots, library_dirs, include_dirs)
            verbose_print("Saved probe results to cache")

    # At this point, library_dirs and include_dirs are set (either from cache or fresh probe)

    # Check for debug/trace mode
    if os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes'):
        extra_compile_args.extend(['-O0', '-g'])
        verbose_print("Building with debug symbols")
    if os.environ.get('TRACE', '').lower() in ('1', 'true', 'yes'):
        extra_compile_args.append('-DDEBUG')
        verbose_print("Building with trace enabled")

    # Enable parallel compilation (works with GCC and Clang)
    # Can be disabled with PYTHON_NSS_NO_PARALLEL=1
    if not os.environ.get('PYTHON_NSS_NO_PARALLEL', '').lower() in ('1', 'true', 'yes'):
        try:
            num_jobs = multiprocessing.cpu_count()
            # Note: -j flag is passed to make, not compiler directly
            # setuptools will honor the MAKEFLAGS environment variable
            if 'MAKEFLAGS' not in os.environ:
                os.environ['MAKEFLAGS'] = f'-j{num_jobs}'
            verbose_print(f"Enabled parallel compilation with {num_jobs} jobs")
        except (ImportError, NotImplementedError):
            verbose_print("Could not determine CPU count, parallel compilation disabled")

    # Runtime library dirs need to be set for non-Darwin platforms (if from cache)
    if cache_hit:
        runtime_library_dirs = []
        if sys.platform != 'darwin':
            runtime_library_dirs = library_dirs.copy()

    # Define C extensions
    return [
        Extension(
            'nss.error',
            sources=['src/py_nspr_error.c'],
            include_dirs=include_dirs,
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/NSPRerrs.h', 'src/SSLerrs.h', 'src/SECerrs.h'],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.io',
            sources=['src/py_nspr_io.c'],
            include_dirs=include_dirs,
            depends=['src/py_nspr_common.h', 'src/py_nspr_io.h'],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.nss',
            sources=['src/py_nss.c'],
            include_dirs=['src'] + include_dirs,
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/py_nss.h'],
            libraries=['nspr4', 'ssl3', 'nss3', 'smime3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.ssl',
            sources=['src/py_ssl.c'],
            include_dirs=['src'] + include_dirs,
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/py_nspr_io.h', 'src/py_ssl.h', 'src/py_nss.h'],
            libraries=['nspr4', 'ssl3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
    ]


if __name__ == "__main__":
    setup(ext_modules=get_extensions())

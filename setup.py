# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss contributors

"""
Setup configuration for python-nss C extensions.

This file handles dynamic detection and configuration of NSS/NSPR libraries.
All project metadata is defined in pyproject.toml.
"""

import os
import sys
import glob
from setuptools import Extension, setup


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

    raise ValueError(f"unable to locate library directory containing libraries {lib_names}")


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

    raise ValueError(f"unable to locate include directory containing files {include_files}")


def get_extensions():
    """Build and return C extension configurations."""
    include_roots_env = os.environ.get('NSS_INCLUDE_ROOTS', '')
    include_roots = [p for p in include_roots_env.split(':') if p] if include_roots_env else None

    # Find NSS and NSPR include directories
    try:
        nss_include_dir = find_include_dir(['nss3', 'nss'], ['nss.h', 'pk11pub.h'], include_roots)
        print(f"Found NSS headers in: {nss_include_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSS headers: {e}", file=sys.stderr)
        nss_include_dir = '/usr/include/nss3'

    try:
        nspr_include_dir = find_include_dir(['nspr4', 'nspr'], ['nspr.h', 'prio.h'], include_roots)
        print(f"Found NSPR headers in: {nspr_include_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSPR headers: {e}", file=sys.stderr)
        nspr_include_dir = '/usr/include/nspr4'

    # Check for debug/trace mode
    extra_compile_args = []
    if os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes'):
        extra_compile_args.extend(['-O0', '-g'])
        print("Building with debug symbols")
    if os.environ.get('TRACE', '').lower() in ('1', 'true', 'yes'):
        extra_compile_args.append('-DDEBUG')
        print("Building with trace enabled")

    # Find library directories
    library_dirs = []
    runtime_library_dirs = []

    try:
        nspr_lib_dir = find_lib_dir(['nspr4'])
        print(f"Found NSPR libraries in: {nspr_lib_dir}")
        library_dirs.append(nspr_lib_dir)
        if sys.platform != 'darwin':
            runtime_library_dirs.append(nspr_lib_dir)
    except ValueError as e:
        print(f"Warning: Could not find NSPR libraries: {e}", file=sys.stderr)

    try:
        nss_lib_dir = find_lib_dir(['nss3', 'ssl3'])
        print(f"Found NSS libraries in: {nss_lib_dir}")
        if nss_lib_dir not in library_dirs:
            library_dirs.append(nss_lib_dir)
            if sys.platform != 'darwin':
                runtime_library_dirs.append(nss_lib_dir)
    except ValueError as e:
        print(f"Warning: Could not find NSS libraries: {e}", file=sys.stderr)

    # Define C extensions
    return [
        Extension(
            'nss.error',
            sources=['src/py_nspr_error.c'],
            include_dirs=[nss_include_dir, nspr_include_dir],
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/NSPRerrs.h', 'src/SSLerrs.h', 'src/SECerrs.h'],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.io',
            sources=['src/py_nspr_io.c'],
            include_dirs=[nss_include_dir, nspr_include_dir],
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/py_nspr_io.h'],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.nss',
            sources=['src/py_nss.c'],
            include_dirs=['src', nss_include_dir, nspr_include_dir],
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/py_nss.h'],
            libraries=['nspr4', 'ssl3', 'nss3', 'smime3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.ssl',
            sources=['src/py_ssl.c'],
            include_dirs=['src', nss_include_dir, nspr_include_dir],
            depends=['src/py_nspr_common.h', 'src/py_nspr_error.h', 'src/py_nspr_io.h', 'src/py_ssl.h', 'src/py_nss.h'],
            libraries=['nspr4', 'ssl3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
    ]


if __name__ == "__main__":
    setup(ext_modules=get_extensions())

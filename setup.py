# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss contributors

import os
import sys
from pathlib import Path

from setuptools import Extension, setup


def find_lib_dir(lib_names, lib_roots=None):
    """
    Locate a library directory on the system which contains the specified libraries.
    """
    if not lib_roots:
        lib_roots = ['/usr/lib', '/usr/local/lib', '/usr/lib64', '/usr/local/lib64']
        # Add Homebrew paths for macOS
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

    if len(lib_names) == 0:
        raise ValueError("library search list is empty")

    for lib_root in lib_roots:
        if os.path.isdir(lib_root):
            found = True
            for lib_name in lib_names:
                # Check for various library extensions
                lib_patterns = [
                    f'lib{lib_name}.so*',
                    f'lib{lib_name}.dylib',
                    f'lib{lib_name}.a',
                ]
                lib_found = False
                for pattern in lib_patterns:
                    import glob
                    if glob.glob(os.path.join(lib_root, pattern)):
                        lib_found = True
                        break
                if not lib_found:
                    found = False
                    break
            if found:
                return lib_root

    raise ValueError(
        f"unable to locate library directory containing libraries {lib_names}"
    )


def find_include_dir(dir_names, include_files, include_roots=None):
    """
    Locate an include directory on the system which contains the specified include files.
    You must provide a list of directory basenames to search. You may optionally provide
    a list of include roots. The search proceeds by iterating over each root and appending
    each directory basename to it. If the resulting directory path contains all the include
    files that directory is returned. If no directory is found containing all the include
    files a ValueError is raised.
    """
    if not include_roots:
        include_roots = ['/usr/include', '/usr/local/include']
        # Add Homebrew paths for macOS
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

    if len(dir_names) == 0:
        raise ValueError("directory search list is empty")
    if len(include_files) == 0:
        raise ValueError("header file list is empty")

    for include_root in include_roots:
        for dir_name in dir_names:
            include_dir = os.path.join(include_root, dir_name)
            if os.path.isdir(include_dir):
                found = True
                for include_file in include_files:
                    file_path = os.path.join(include_dir, include_file)
                    if not os.path.exists(file_path):
                        found = False
                        break
                if found:
                    return include_dir

    raise ValueError(
        f"unable to locate include directory containing header files {include_files}"
    )


def get_extensions():
    """Build and return C extension configurations."""

    # Get include roots from environment if available
    include_roots_env = os.environ.get('NSS_INCLUDE_ROOTS', '')
    include_roots = (
        [p for p in include_roots_env.split(':') if p]
        if include_roots_env
        else None
    )

    # Find NSS and NSPR include directories
    try:
        nss_include_dir = find_include_dir(
            ['nss3', 'nss'],
            ['nss.h', 'pk11pub.h'],
            include_roots=include_roots,
        )
        print(f"Found NSS headers in: {nss_include_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSS headers: {e}", file=sys.stderr)
        print("You may need to install nss-devel or libnss3-dev", file=sys.stderr)
        nss_include_dir = '/usr/include/nss3'

    try:
        nspr_include_dir = find_include_dir(
            ['nspr4', 'nspr'],
            ['nspr.h', 'prio.h'],
            include_roots=include_roots,
        )
        print(f"Found NSPR headers in: {nspr_include_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSPR headers: {e}", file=sys.stderr)
        print("You may need to install nspr-devel or libnspr4-dev", file=sys.stderr)
        nspr_include_dir = '/usr/include/nspr4'

    # Check for debug/trace mode
    debug_mode = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
    trace_mode = os.environ.get('TRACE', '').lower() in ('1', 'true', 'yes')

    extra_compile_args = []
    if debug_mode:
        extra_compile_args.extend(['-O0', '-g'])
        print("Building with debug symbols")
    if trace_mode:
        extra_compile_args.append('-DDEBUG')
        print("Building with trace enabled")

    # Find library directories
    try:
        nspr_lib_dir = find_lib_dir(['nspr4'])
        print(f"Found NSPR libraries in: {nspr_lib_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSPR libraries: {e}", file=sys.stderr)
        nspr_lib_dir = None

    try:
        nss_lib_dir = find_lib_dir(['nss3', 'ssl3'])
        print(f"Found NSS libraries in: {nss_lib_dir}")
    except ValueError as e:
        print(f"Warning: Could not find NSS libraries: {e}", file=sys.stderr)
        nss_lib_dir = None

    # Build library_dirs list
    library_dirs = []
    runtime_library_dirs = []
    if nspr_lib_dir:
        library_dirs.append(nspr_lib_dir)
        if sys.platform != 'darwin':  # rpath doesn't work the same on macOS
            runtime_library_dirs.append(nspr_lib_dir)
    if nss_lib_dir and nss_lib_dir not in library_dirs:
        library_dirs.append(nss_lib_dir)
        if sys.platform != 'darwin':
            runtime_library_dirs.append(nss_lib_dir)

    # Define C extensions
    extensions = [
        Extension(
            'nss.error',
            sources=['src/py_nspr_error.c'],
            include_dirs=[nss_include_dir, nspr_include_dir],
            depends=[
                'src/py_nspr_common.h',
                'src/py_nspr_error.h',
                'src/NSPRerrs.h',
                'src/SSLerrs.h',
                'src/SECerrs.h',
            ],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.io',
            sources=['src/py_nspr_io.c'],
            include_dirs=[nss_include_dir, nspr_include_dir],
            depends=[
                'src/py_nspr_common.h',
                'src/py_nspr_error.h',
                'src/py_nspr_io.h',
            ],
            libraries=['nspr4'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.nss',
            sources=['src/py_nss.c'],
            include_dirs=['src', nss_include_dir, nspr_include_dir],
            depends=[
                'src/py_nspr_common.h',
                'src/py_nspr_error.h',
                'src/py_nss.h',
            ],
            libraries=['nspr4', 'ssl3', 'nss3', 'smime3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            'nss.ssl',
            sources=['src/py_ssl.c'],
            include_dirs=['src', nss_include_dir, nspr_include_dir],
            depends=[
                'src/py_nspr_common.h',
                'src/py_nspr_error.h',
                'src/py_nspr_io.h',
                'src/py_ssl.h',
                'src/py_nss.h',
            ],
            libraries=['nspr4', 'ssl3'],
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            extra_compile_args=extra_compile_args,
        ),
    ]

    return extensions


if __name__ == "__main__":
    setup(
        ext_modules=get_extensions(),
    )

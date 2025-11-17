# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss contributors

import sys
import os
import sysconfig


def get_build_dir():
    """
    Walk from the current directory up until a directory is found
    which contains a regular file called "setup.py" and a directory
    called "build". If found return the fully qualified path to
    the build directory's platform specific directory, this is where
    the architecture specific build produced by setup.py is located.

    If the build directory cannot be found in the tree None is returned.
    """
    cwd = os.getcwd()
    path_components = cwd.split(os.sep)
    while len(path_components):
        path = os.path.join(os.sep, *path_components) if path_components[0] else os.path.join(*path_components)
        setup_path = os.path.join(path, 'setup.py')
        build_path = os.path.join(path, 'build')

        # Does this directory contain the file "setup.py" and the directory "build"?
        if (os.path.exists(setup_path) and os.path.exists(build_path) and
                os.path.isfile(setup_path) and os.path.isdir(build_path)):
            # Found, return the path concatenated with the architecture
            # specific build directory

            # Get platform-specific information using sysconfig
            platform = sysconfig.get_platform()
            version = f"{sys.version_info.major}.{sys.version_info.minor}"
            platform_specifier = f"lib.{platform}-{version}"

            build_lib_dir = os.path.join(build_path, platform_specifier)

            # If the exact directory doesn't exist, try to find any lib.* directory
            if not os.path.exists(build_lib_dir):
                try:
                    for entry in os.listdir(build_path):
                        if entry.startswith('lib.'):
                            candidate = os.path.join(build_path, entry)
                            if os.path.isdir(candidate):
                                return candidate
                except OSError:
                    pass

            return build_lib_dir

        # Not found, ascend to parent directory and try again
        path_components.pop()

    # Failed to find the build directory
    return None


def insert_build_dir_into_path():
    """Insert the build directory at the beginning of sys.path."""
    build_dir = get_build_dir()
    if build_dir:
        sys.path.insert(0, build_dir)

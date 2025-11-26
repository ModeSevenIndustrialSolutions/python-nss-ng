#!/usr/bin/env python3
"""
Safe file importer: Copies files from source to destination only if they don't exist.
This script recursively copies all files and directories from python-nss-ng to 
python-nss-1.0.1, but ONLY if they don't already exist in the destination.
NO files will be overwritten.
"""

import os
import shutil
import sys
from pathlib import Path

# Define source and destination directories
SCRIPT_DIR = Path(__file__).parent.absolute()
SOURCE_DIR = SCRIPT_DIR.parent / "python-nss-ng"
DEST_DIR = SCRIPT_DIR

# Directories and patterns to exclude from copying
EXCLUDE_DIRS = {
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'dist',
    'build',
    '*.egg-info',
    '.eggs',
    'venv',
    'env',
    '.venv',
    '.env',
}

# File patterns to exclude
EXCLUDE_FILES = {
    '.DS_Store',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.coverage',
    'coverage.xml',
    '*.log',
}

def should_exclude(path: Path, relative_path: Path) -> bool:
    """Check if a path should be excluded from copying."""
    # Check if any parent directory is in exclude list
    for part in relative_path.parts:
        if part in EXCLUDE_DIRS:
            return True
        # Handle glob patterns for directories
        for exclude in EXCLUDE_DIRS:
            if '*' in exclude and path.is_dir():
                if path.name.endswith(exclude.replace('*', '')):
                    return True
    
    # Check if file matches exclude patterns
    if path.is_file():
        for pattern in EXCLUDE_FILES:
            if '*' in pattern:
                if path.name.endswith(pattern.replace('*', '')):
                    return True
            elif path.name == pattern:
                return True
    
    return False

def copy_if_not_exists(src: Path, dest: Path, relative_path: Path, 
                      copied_files: list, copied_dirs: list, skipped: list) -> None:
    """
    Recursively copy files and directories from src to dest, 
    but only if they don't already exist in dest.
    """
    # Check if we should exclude this path
    if should_exclude(src, relative_path):
        print(f"EXCLUDED: {relative_path}")
        return
    
    # If source is a directory
    if src.is_dir():
        # Check if destination directory exists
        dest_exists = dest.exists()
        
        if not dest_exists:
            # Create the directory if it doesn't exist
            try:
                dest.mkdir(parents=True, exist_ok=True)
                copied_dirs.append(str(relative_path))
                print(f"CREATED DIR: {relative_path}")
            except Exception as e:
                print(f"ERROR creating directory {relative_path}: {e}", file=sys.stderr)
                return
        else:
            print(f"DIR EXISTS: {relative_path} (checking contents...)")
        
        # Recursively process directory contents regardless of whether dir existed
        for item in src.iterdir():
            new_relative_path = relative_path / item.name
            copy_if_not_exists(
                item,
                dest / item.name,
                new_relative_path,
                copied_files,
                copied_dirs,
                skipped
            )
    
    # If source is a file
    elif src.is_file():
        # If destination file already exists, skip it
        if dest.exists():
            skipped.append(str(relative_path))
            print(f"SKIPPED (exists): {relative_path}")
            return
        
        try:
            # Ensure parent directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(src, dest)
            copied_files.append(str(relative_path))
            print(f"COPIED FILE: {relative_path}")
        except Exception as e:
            print(f"ERROR copying file {relative_path}: {e}", file=sys.stderr)
    
    # Handle symlinks
    elif src.is_symlink():
        # If destination symlink already exists, skip it
        if dest.exists():
            skipped.append(str(relative_path))
            print(f"SKIPPED (exists): {relative_path}")
            return
        
        try:
            # Ensure parent directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the symlink
            linkto = os.readlink(src)
            os.symlink(linkto, dest)
            copied_files.append(str(relative_path))
            print(f"COPIED SYMLINK: {relative_path} -> {linkto}")
        except Exception as e:
            print(f"ERROR copying symlink {relative_path}: {e}", file=sys.stderr)

def main():
    """Main function to orchestrate the file copying."""
    print("=" * 80)
    print("SAFE FILE IMPORTER")
    print("=" * 80)
    print(f"Source:      {SOURCE_DIR}")
    print(f"Destination: {DEST_DIR}")
    print("=" * 80)
    
    # Verify source directory exists
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory does not exist: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)
    
    if not SOURCE_DIR.is_dir():
        print(f"ERROR: Source is not a directory: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)
    
    # Verify destination directory exists
    if not DEST_DIR.exists():
        print(f"ERROR: Destination directory does not exist: {DEST_DIR}", file=sys.stderr)
        sys.exit(1)
    
    # Lists to track what was copied and skipped
    copied_files = []
    copied_dirs = []
    skipped = []
    
    print("\nStarting recursive copy operation...")
    print("NOTE: Only files that DO NOT exist in destination will be copied.")
    print("      Existing directories will be checked for new files.")
    print("=" * 80)
    print()
    
    # Process each item in the source directory
    for item in SOURCE_DIR.iterdir():
        relative_path = Path(item.name)
        dest_path = DEST_DIR / item.name
        
        copy_if_not_exists(
            item,
            dest_path,
            relative_path,
            copied_files,
            copied_dirs,
            skipped
        )
    
    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Directories created: {len(copied_dirs)}")
    print(f"Files copied:        {len(copied_files)}")
    print(f"Items skipped:       {len(skipped)}")
    print("=" * 80)
    
    if copied_files:
        print("\nCopied files:")
        for f in sorted(copied_files):
            print(f"  - {f}")
    
    if copied_dirs:
        print("\nCreated directories:")
        for d in sorted(copied_dirs):
            print(f"  - {d}")
    
    if skipped:
        print("\nSkipped (already exist):")
        for s in sorted(skipped):
            print(f"  - {s}")
    
    print("\nOperation completed successfully!")
    print("No existing files were overwritten.")

if __name__ == "__main__":
    main()
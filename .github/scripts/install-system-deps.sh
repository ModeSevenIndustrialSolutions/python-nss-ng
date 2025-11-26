#!/bin/bash
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Pre-build script to install NSS/NSPR system dependencies
# This script is called by the python-build-action before building python-nss-ng

set -euo pipefail

echo "=== Installing NSS/NSPR system dependencies ==="

# Detect the operating system
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID}"
    OS_VERSION="${VERSION_ID:-unknown}"
elif [ "$(uname -s)" = "Darwin" ]; then
    OS_ID="macos"
    OS_VERSION="$(sw_vers -productVersion)"
else
    echo "Error: Unable to detect operating system ❌"
    exit 1
fi

echo "Detected OS: ${OS_ID} ${OS_VERSION}"

# Install dependencies based on OS
case "${OS_ID}" in
    ubuntu|debian)
        echo "Installing NSS/NSPR on Debian/Ubuntu..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            libnss3-dev \
            libnspr4-dev \
            pkg-config
        echo "NSS/NSPR installed via apt ✅"
        ;;

    fedora|rhel|centos|rocky|almalinux)
        echo "Installing NSS/NSPR on Fedora/RHEL..."
        sudo dnf install -y \
            nss-devel \
            nspr-devel \
            pkg-config
        echo "NSS/NSPR installed via dnf ✅"
        ;;

    macos)
        echo "Installing NSS/NSPR on macOS via Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo "Error: Homebrew not found. Please install Homebrew first ❌"
            exit 1
        fi

        # Only install if not already present to avoid warnings
        brew list nss &>/dev/null || brew install nss
        brew list nspr &>/dev/null || brew install nspr
        brew list pkg-config &>/dev/null || brew install pkg-config
        echo "NSS/NSPR installed via Homebrew ✅"
        ;;

    *)
        echo "Error: Unsupported operating system: ${OS_ID} ❌"
        echo "Supported systems: Ubuntu, Debian, Fedora, RHEL, CentOS, macOS"
        exit 1
        ;;
esac

# Verify installation
echo ""
echo "=== Verifying NSS/NSPR installation ==="
if command -v pkg-config &> /dev/null; then
    if pkg-config --exists nss; then
        NSS_VERSION=$(pkg-config --modversion nss)
        echo "NSS version: ${NSS_VERSION}"
    else
        echo "Warning: pkg-config cannot find NSS"
    fi

    if pkg-config --exists nspr; then
        NSPR_VERSION=$(pkg-config --modversion nspr)
        echo "NSPR version: ${NSPR_VERSION}"
    else
        echo "Warning: pkg-config cannot find NSPR"
    fi
else
    echo "Warning: pkg-config not found in PATH"
fi

echo ""
echo "System dependencies installed successfully ✅"

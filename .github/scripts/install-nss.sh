#!/bin/bash
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
#
# Install NSS 3.100+ on Ubuntu/Debian systems
# Uses Mozilla Team PPA which provides newer NSS versions

set -euo pipefail

echo "===================================="
echo "Installing NSS/NSPR from Mozilla Team PPA"
echo "===================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "ERROR: Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS $VER"

# Install based on OS
case "$OS" in
    ubuntu|debian)
        echo "Installing on Ubuntu/Debian..."
        
        # Add Mozilla Team PPA (has newer NSS)
        sudo apt-get update
        sudo apt-get install -y software-properties-common
        
        # For Ubuntu, add the Mozilla Team PPA
        if [ "$OS" = "ubuntu" ]; then
            echo "Adding Mozilla Team PPA..."
            sudo add-apt-repository -y ppa:mozillateam/ppa
            sudo apt-get update
        fi
        
        # Install NSS/NSPR development packages
        echo "Installing NSS/NSPR packages..."
        sudo apt-get install -y \
            libnss3-dev \
            libnspr4-dev \
            pkg-config
        ;;
        
    fedora)
        echo "Installing on Fedora..."
        sudo dnf install -y \
            nss-devel \
            nspr-devel \
            pkg-config
        ;;
        
    centos|rhel|rocky|almalinux)
        echo "Installing on RHEL-based system..."
        
        # Enable EPEL if needed
        if ! rpm -q epel-release &>/dev/null; then
            sudo dnf install -y epel-release || sudo yum install -y epel-release
        fi
        
        sudo dnf install -y \
            nss-devel \
            nspr-devel \
            pkg-config || \
        sudo yum install -y \
            nss-devel \
            nspr-devel \
            pkg-config
        ;;
        
    *)
        echo "ERROR: Unsupported OS: $OS"
        exit 1
        ;;
esac

# Verify installation
echo ""
echo "===================================="
echo "Verifying installation..."
echo "===================================="

if command -v pkg-config &> /dev/null; then
    NSS_VERSION=$(pkg-config --modversion nss || echo "NOT FOUND")
    NSPR_VERSION=$(pkg-config --modversion nspr || echo "NOT FOUND")
    
    echo "NSS version: $NSS_VERSION"
    echo "NSPR version: $NSPR_VERSION"
    echo "NSS cflags: $(pkg-config --cflags nss || echo 'NOT FOUND')"
    echo "NSS libs: $(pkg-config --libs nss || echo 'NOT FOUND')"
    
    # Check if NSS version is sufficient (3.98+)
    # Mozilla Team PPA provides NSS 3.98+ which has the key types we need
    if [ "$NSS_VERSION" != "NOT FOUND" ]; then
        MAJOR=$(echo "$NSS_VERSION" | cut -d. -f1)
        MINOR=$(echo "$NSS_VERSION" | cut -d. -f2)
        
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 98 ]; then
            echo "✓ NSS version $NSS_VERSION is sufficient"
        else
            echo "⚠ WARNING: NSS version $NSS_VERSION may be too old (need 3.98+)"
            echo "  Some modern cryptographic key types may not be available"
        fi
    fi
else
    echo "ERROR: pkg-config not found"
    exit 1
fi

echo ""
echo "===================================="
echo "Installation complete!"
echo "===================================="
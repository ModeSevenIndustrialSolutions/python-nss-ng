#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
#
# Build and install NSS/NSPR from source
# This script is used in GitHub Actions CI for python-nss-ng

set -euo pipefail

# Configuration
NSS_VERSION="${NSS_VERSION:-3.118}"
NSPR_VERSION="${NSPR_VERSION:-4.37}"
INSTALL_PREFIX="${INSTALL_PREFIX:-/usr}"
BUILD_DIR="${BUILD_DIR:-$HOME/nss-build}"

echo "========================================"
echo "NSS/NSPR Build and Installation"
echo "========================================"
echo "NSS Version:    ${NSS_VERSION}"
echo "NSPR Version:   ${NSPR_VERSION}"
echo "Install Prefix: ${INSTALL_PREFIX}"
echo "Build Dir:      ${BUILD_DIR}"
echo "========================================"

# Install build dependencies
echo ""
echo "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    pkg-config \
    zlib1g-dev \
    libsqlite3-dev \
    gyp \
    ninja-build \
    meson \
    wget

# Create build directory
echo ""
echo "Creating build directory..."
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# Download and extract NSS
echo ""
echo "Downloading NSS ${NSS_VERSION}..."
NSS_URL="https://ftp.mozilla.org/pub/security/nss/releases"
NSS_FILE="nss-${NSS_VERSION}.tar.gz"
NSS_RELEASE_TAG="NSS_${NSS_VERSION//./_}_RTM"
wget -q "${NSS_URL}/${NSS_RELEASE_TAG}/src/${NSS_FILE}"
echo "Extracting NSS..."
tar -xzf "${NSS_FILE}"
rm "${NSS_FILE}"

# Download and extract NSPR
echo ""
echo "Downloading NSPR ${NSPR_VERSION}..."
NSPR_URL="https://ftp.mozilla.org/pub/nspr/releases"
NSPR_FILE="nspr-${NSPR_VERSION}.tar.gz"
wget -q "${NSPR_URL}/v${NSPR_VERSION}/src/${NSPR_FILE}"
echo "Extracting NSPR..."
tar -xzf "${NSPR_FILE}"
rm "${NSPR_FILE}"

# Build NSPR
echo ""
echo "========================================"
echo "Building NSPR ${NSPR_VERSION}..."
echo "========================================"
cd "${BUILD_DIR}/nspr-${NSPR_VERSION}/nspr"
./configure --prefix="${INSTALL_PREFIX}" \
    --with-mozilla \
    --with-pthreads \
    --enable-64bit
make
echo "Installing NSPR..."
sudo make install

# Build NSS
echo ""
echo "========================================"
echo "Building NSS ${NSS_VERSION}..."
echo "========================================"
cd "${BUILD_DIR}/nss-${NSS_VERSION}/nss"

# Verify build.sh exists
if [ ! -f build.sh ]; then
    echo "ERROR: build.sh not found in $(pwd)" >&2
    ls -la
    exit 1
fi

chmod +x build.sh

# Build NSS
./build.sh \
    --opt \
    --disable-tests \
    --system-sqlite \
    --system-nspr \
    --enable-libpkix

# Install NSS
echo ""
echo "========================================"
echo "Installing NSS ${NSS_VERSION}..."
echo "========================================"
cd "${BUILD_DIR}/nss-${NSS_VERSION}/dist"

# Headers are in dist/public/nss and dist/private/nss
echo "Installing headers..."
sudo mkdir -p "${INSTALL_PREFIX}/include/nss"
sudo cp -r public/nss/* "${INSTALL_PREFIX}/include/nss/"
sudo cp -r private/nss/* "${INSTALL_PREFIX}/include/nss/"

# Libraries and binaries are in dist/Release
echo "Installing libraries..."
sudo cp -L Release/lib/*.so "${INSTALL_PREFIX}/lib/"

echo "Installing binaries..."
sudo cp -L Release/bin/* "${INSTALL_PREFIX}/bin/" 2>/dev/null || true

# Update library cache
sudo ldconfig

# Create pkg-config files
echo ""
echo "Creating pkg-config files..."
sudo tee "${INSTALL_PREFIX}/lib/pkgconfig/nss.pc" > /dev/null <<EOF
prefix=${INSTALL_PREFIX}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include/nss

Name: NSS
Description: Network Security Services
Version: ${NSS_VERSION}
Requires: nspr >= ${NSPR_VERSION}
Libs: -L\${libdir} -lssl3 -lsmime3 -lnss3 -lnssutil3
Cflags: -I\${includedir}
EOF

sudo tee "${INSTALL_PREFIX}/lib/pkgconfig/nspr.pc" > /dev/null <<EOF
prefix=${INSTALL_PREFIX}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include/nspr

Name: NSPR
Description: Netscape Portable Runtime
Version: ${NSPR_VERSION}
Libs: -L\${libdir} -lplds4 -lplc4 -lnspr4
Cflags: -I\${includedir}
EOF

# Verify installation
echo ""
echo "========================================"
echo "Verifying installation..."
echo "========================================"
echo "NSS version:  $(pkg-config --modversion nss)"
echo "NSPR version: $(pkg-config --modversion nspr)"
echo ""
echo "NSS headers:  ${INSTALL_PREFIX}/include/nss/"
find "${INSTALL_PREFIX}/include/nss/" -maxdepth 1 -type f 2>/dev/null | head -5 || true
echo "..."
echo ""
echo "NSS libraries: ${INSTALL_PREFIX}/lib/"
find "${INSTALL_PREFIX}/lib/" -maxdepth 1 -name "libnss*" 2>/dev/null | head -5 || true
echo ""
echo "========================================"
echo "NSS/NSPR installation complete! ✅"
echo "========================================"

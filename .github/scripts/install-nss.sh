#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
#
# Build and install NSS/NSPR from source
# Platform-agnostic script supporting macOS and Linux
# (Debian/Ubuntu/RHEL/Fedora)

set -euo pipefail

# Configuration
NSS_VERSION="${NSS_VERSION:-3.118}"
NSPR_VERSION="${NSPR_VERSION:-4.37}"
INSTALL_PREFIX="${INSTALL_PREFIX:-/usr/local}"
BUILD_DIR="${BUILD_DIR:-$HOME/nss-build}"

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            # shellcheck source=/dev/null
            . /etc/os-release
            case "$ID" in
                ubuntu|debian)
                    echo "debian"
                    ;;
                rhel|fedora|centos|rocky|alma)
                    echo "rhel"
                    ;;
                *)
                    echo "linux"
                    ;;
            esac
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

PLATFORM=$(detect_platform)

# Detect if we need sudo
USE_SUDO=""
if [ "$EUID" -ne 0 ] && [ "$PLATFORM" != "macos" ]; then
    if command -v sudo &> /dev/null; then
        USE_SUDO="sudo"
    fi
fi

# Set install prefix based on platform if still at default
if [ "$INSTALL_PREFIX" = "/usr/local" ]; then
    if [ "$PLATFORM" = "macos" ]; then
        # On macOS, use /usr/local (Homebrew-compatible location)
        INSTALL_PREFIX="/usr/local"
    else
        # On Linux, use /usr for compatibility
        INSTALL_PREFIX="/usr"
    fi
fi

echo "========================================"
echo "NSS/NSPR Build and Installation"
echo "========================================"
echo "Platform:       ${PLATFORM}"
echo "NSS Version:    ${NSS_VERSION}"
echo "NSPR Version:   ${NSPR_VERSION}"
echo "Install Prefix: ${INSTALL_PREFIX}"
echo "Build Dir:      ${BUILD_DIR}"
echo "Using sudo:     ${USE_SUDO:-no}"
echo "========================================"

# Install build dependencies based on platform
install_dependencies() {
    echo ""
    echo "Installing build dependencies..."

    case "$PLATFORM" in
        macos)
            # macOS using Homebrew
            if ! command -v brew &> /dev/null; then
                echo "ERROR: Homebrew not found." >&2
                echo "Please install Homebrew first." >&2
                echo "Visit: https://brew.sh" >&2
                exit 1
            fi

            # Install dependencies
            brew install pkg-config sqlite3 wget || true
            ;;

        debian)
            # Debian/Ubuntu
            $USE_SUDO apt-get update
            $USE_SUDO apt-get install -y \
                build-essential \
                pkg-config \
                zlib1g-dev \
                libsqlite3-dev \
                gyp \
                ninja-build \
                wget \
                ca-certificates
            ;;

        rhel)
            # RHEL/Fedora/CentOS
            if command -v dnf &> /dev/null; then
                PKG_MGR="dnf"
            else
                PKG_MGR="yum"
            fi

            $USE_SUDO $PKG_MGR install -y \
                gcc \
                gcc-c++ \
                make \
                pkg-config \
                zlib-devel \
                sqlite-devel \
                gyp \
                ninja-build \
                wget \
                ca-certificates
            ;;

        *)
            echo "WARNING: Unknown platform." >&2
            echo "Attempting to continue..." >&2
            echo "You may need to install dependencies manually:" >&2
            echo "  - C/C++ compiler (gcc/clang)" >&2
            echo "  - pkg-config" >&2
            echo "  - zlib development files" >&2
            echo "  - sqlite3 development files" >&2
            echo "  - wget or curl" >&2
            ;;
    esac
}

# Download file with fallback to curl if wget not available
download_file() {
    local url="$1"
    local output="$2"

    if command -v wget &> /dev/null; then
        wget -q -O "$output" "$url"
    elif command -v curl &> /dev/null; then
        curl -sSL -o "$output" "$url"
    else
        echo "ERROR: Neither wget nor curl found." >&2
        echo "Cannot download files." >&2
        exit 1
    fi
}

# Verify file checksum
verify_checksum() {
    local file="$1"
    local expected_sha256="$2"
    local file_basename
    file_basename=$(basename "$file")

    if [ -z "$expected_sha256" ]; then
        echo "WARNING: No checksum provided for $file_basename - skipping verification" >&2
        return 0
    fi

    echo "Verifying checksum for $file_basename..."

    if command -v sha256sum &> /dev/null; then
        local actual_sha256
        actual_sha256=$(sha256sum "$file" | awk '{print $1}')
    elif command -v shasum &> /dev/null; then
        local actual_sha256
        actual_sha256=$(shasum -a 256 "$file" | awk '{print $1}')
    else
        echo "ERROR: Neither sha256sum nor shasum found." >&2
        echo "Cannot verify checksums." >&2
        exit 1
    fi

    if [ "$actual_sha256" != "$expected_sha256" ]; then
        echo "ERROR: Checksum verification failed for $file_basename" >&2
        echo "Expected: $expected_sha256" >&2
        echo "Got:      $actual_sha256" >&2
        echo "This could indicate a compromised download or network issue." >&2
        exit 1
    fi

    echo "✓ Checksum verified for $file_basename"
}

# Known SHA256 checksums for NSS/NSPR releases
# These should be updated when versions change
# Source: https://ftp.mozilla.org/pub/security/nss/releases/ and https://ftp.mozilla.org/pub/nspr/releases/
get_nss_checksum() {
    local version="$1"
    case "$version" in
        3.118)
            echo "06f2d34c7c421da430b9d78fc6590105500b9439efa19cdaa0a57ed7dc948aad"
            ;;
        3.117)
            echo "5786b523a2f2e9295ed10d711960d2e33cd620bb80d6288443eda43553a51996"
            ;;
        *)
            echo ""  # Return empty for unknown versions - will trigger warning
            ;;
    esac
}

get_nspr_checksum() {
    local version="$1"
    case "$version" in
        4.37)
            echo "5f9344ed0e31855bd38f88b33c9d9ab94f70ce547ef3213e488d1520f61840fa"
            ;;
        4.36)
            echo "55dec317f1401cd2e5dba844d340b930ab7547f818179a4002bce62e6f1c6895"
            ;;
        *)
            echo ""  # Return empty for unknown versions - will trigger warning
            ;;
    esac
}

# Install dependencies
install_dependencies

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
NSS_CHECKSUM=$(get_nss_checksum "${NSS_VERSION}")

download_file \
    "${NSS_URL}/${NSS_RELEASE_TAG}/src/${NSS_FILE}" \
    "${NSS_FILE}"

verify_checksum "${NSS_FILE}" "${NSS_CHECKSUM}"

echo "Extracting NSS..."
tar -xzf "${NSS_FILE}"
rm "${NSS_FILE}"

# Download and extract NSPR
echo ""
echo "Downloading NSPR ${NSPR_VERSION}..."
NSPR_URL="https://ftp.mozilla.org/pub/nspr/releases"
NSPR_FILE="nspr-${NSPR_VERSION}.tar.gz"
NSPR_CHECKSUM=$(get_nspr_checksum "${NSPR_VERSION}")

download_file \
    "${NSPR_URL}/v${NSPR_VERSION}/src/${NSPR_FILE}" \
    "${NSPR_FILE}"

verify_checksum "${NSPR_FILE}" "${NSPR_CHECKSUM}"

echo "Extracting NSPR..."
tar -xzf "${NSPR_FILE}"
rm "${NSPR_FILE}"

# Build NSPR
echo ""
echo "========================================"
echo "Building NSPR ${NSPR_VERSION}..."
echo "========================================"
cd "${BUILD_DIR}/nspr-${NSPR_VERSION}/nspr"

# Configure flags based on platform
NSPR_CONFIGURE_FLAGS=(
    "--prefix=${INSTALL_PREFIX}"
    "--with-mozilla"
    "--with-pthreads"
)

# Add 64-bit flag on appropriate platforms
ARCH="$(uname -m)"
if [ "$ARCH" = "x86_64" ] || \
   [ "$ARCH" = "aarch64" ] || \
   [ "$ARCH" = "arm64" ]; then
    NSPR_CONFIGURE_FLAGS+=("--enable-64bit")
fi

./configure "${NSPR_CONFIGURE_FLAGS[@]}"
NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
make -j"${NPROC}"

echo "Installing NSPR..."
$USE_SUDO make install

# Build NSS
echo ""
echo "========================================"
echo "Building NSS ${NSS_VERSION}..."
echo "========================================"

# Set PKG_CONFIG_PATH so NSS can find NSPR
export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
echo "PKG_CONFIG_PATH=${PKG_CONFIG_PATH}"

cd "${BUILD_DIR}/nss-${NSS_VERSION}/nss"

# Verify build.sh exists
if [ ! -f build.sh ]; then
    echo "ERROR: build.sh not found in $(pwd)" >&2
    ls -la
    exit 1
fi

chmod +x build.sh

# Build NSS with appropriate flags
NSS_BUILD_FLAGS=(
    "--opt"
    "--disable-tests"
    "--system-sqlite"
    "--system-nspr"
    "--enable-libpkix"
)

# On macOS, we may need to specify the architecture
if [ "$PLATFORM" = "macos" ]; then
    if [ "$(uname -m)" = "arm64" ]; then
        export USE_64=1
    fi
fi

./build.sh "${NSS_BUILD_FLAGS[@]}"

# Install NSS
echo ""
echo "========================================"
echo "Installing NSS ${NSS_VERSION}..."
echo "========================================"

# Determine the dist directory
# (Linux uses Linux_x86_64_gcc_glibc_PTH_64_OPT.OBJ or similar)
cd "${BUILD_DIR}/nss-${NSS_VERSION}/dist"

# Find the actual dist directory
if [ -d "Release" ]; then
    DIST_DIR="Release"
elif [ "$PLATFORM" = "macos" ]; then
    # Find Darwin directory on macOS
    DIST_DIR=$(find . -maxdepth 1 -type d -name "Darwin_*" | \
        head -1 | sed 's|^\./||')
    if [ -z "$DIST_DIR" ]; then
        DIST_DIR="Release"
    fi
else
    # Find any OPT.OBJ directory
    DIST_DIR=$(find . -maxdepth 1 -type d -name "*_OPT.OBJ" | \
        head -1 | sed 's|^\./||')
    if [ -z "$DIST_DIR" ]; then
        DIST_DIR="Release"
    fi
fi

echo "Using dist directory: $DIST_DIR"

# Create installation directories
$USE_SUDO mkdir -p "${INSTALL_PREFIX}/include/nss"
$USE_SUDO mkdir -p "${INSTALL_PREFIX}/lib"
$USE_SUDO mkdir -p "${INSTALL_PREFIX}/bin"
$USE_SUDO mkdir -p "${INSTALL_PREFIX}/lib/pkgconfig"

# Install headers from dist/public/nss and dist/private/nss
echo "Installing headers..."
if [ -d "public/nss" ]; then
    $USE_SUDO cp -r public/nss/* \
        "${INSTALL_PREFIX}/include/nss/" 2>/dev/null || true
fi
if [ -d "private/nss" ]; then
    $USE_SUDO cp -r private/nss/* \
        "${INSTALL_PREFIX}/include/nss/" 2>/dev/null || true
fi

# Install libraries
echo "Installing libraries..."
if [ "$PLATFORM" = "macos" ]; then
    # On macOS, libraries are .dylib
    $USE_SUDO cp -L "${DIST_DIR}"/lib/*.dylib \
        "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
    # Also try from the arch-specific directory
    for libdir in Darwin_*/lib; do
        if [ -d "$libdir" ]; then
            $USE_SUDO cp -L "$libdir"/*.dylib \
                "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
        fi
    done
else
    # On Linux, libraries are .so
    $USE_SUDO cp -L "${DIST_DIR}"/lib/*.so \
        "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
fi

# Install binaries
echo "Installing binaries..."
$USE_SUDO cp -L "${DIST_DIR}"/bin/* \
    "${INSTALL_PREFIX}/bin/" 2>/dev/null || true

# Update library cache (Linux only)
if [ "$PLATFORM" != "macos" ] && \
   command -v ldconfig &> /dev/null; then
    $USE_SUDO ldconfig 2>/dev/null || true
fi

# Create pkg-config files
echo ""
echo "Creating pkg-config files..."

# Determine library extension
if [ "$PLATFORM" = "macos" ]; then
    LIB_EXT="dylib"
else
    LIB_EXT="so"
fi

$USE_SUDO tee "${INSTALL_PREFIX}/lib/pkgconfig/nss.pc" > /dev/null <<EOF
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

$USE_SUDO tee "${INSTALL_PREFIX}/lib/pkgconfig/nspr.pc" > /dev/null <<EOF
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

# Set PKG_CONFIG_PATH for verification
export PKG_CONFIG_PATH="\
${INSTALL_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"

if command -v pkg-config &> /dev/null; then
    if pkg-config --exists nss 2>/dev/null; then
        echo "NSS version:  $(pkg-config --modversion nss)"
    else
        echo "WARNING: NSS pkg-config file not found or invalid" >&2
    fi

    if pkg-config --exists nspr 2>/dev/null; then
        echo "NSPR version: $(pkg-config --modversion nspr)"
    else
        echo "WARNING: NSPR pkg-config file not found" >&2
        echo "or invalid" >&2
    fi
else
    echo "WARNING: pkg-config not available for verification" >&2
fi

echo ""
echo "NSS headers:  ${INSTALL_PREFIX}/include/nss/"
find "${INSTALL_PREFIX}/include/nss/" -maxdepth 1 -type f \
    2>/dev/null | head -5 || echo "No headers found"
echo "..."
echo ""
echo "NSS libraries: ${INSTALL_PREFIX}/lib/"
find "${INSTALL_PREFIX}/lib/" -maxdepth 1 \
    \( -name "libnss*.$LIB_EXT" -o -name "libnss*.${LIB_EXT}.*" \) \
    2>/dev/null | head -5 || echo "No libraries found"
echo ""
echo "========================================"
echo "NSS/NSPR installation complete! ✅"
echo "========================================"
echo ""
echo "Please ensure the following are in your environment:"
echo "  export PKG_CONFIG_PATH=\
${INSTALL_PREFIX}/lib/pkgconfig:\$PKG_CONFIG_PATH"
if [ "$PLATFORM" = "macos" ]; then
    echo "  export DYLD_LIBRARY_PATH=\
${INSTALL_PREFIX}/lib:\$DYLD_LIBRARY_PATH"
else
    echo "  export LD_LIBRARY_PATH=\
${INSTALL_PREFIX}/lib:\$LD_LIBRARY_PATH"
fi
echo "========================================"

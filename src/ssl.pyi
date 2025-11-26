# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Type stubs for nss.ssl module.

This file provides type hints for the C extension module nss.ssl.
"""

from typing import Any, Callable, Optional, Tuple, Union
import socket

# SSL Policy
def set_domestic_policy() -> None:
    """Set domestic (strong) SSL policy."""
    ...

def set_export_policy() -> None:
    """Set export (weak) SSL policy."""
    ...

def set_france_policy() -> None:
    """Set France-specific SSL policy."""
    ...

# SSL Version Range
def get_default_ssl_version_range(variant: int) -> Tuple[int, int]:
    """Get the default SSL/TLS version range."""
    ...

def set_default_ssl_version_range(
    variant: int,
    min_version: int,
    max_version: int
) -> None:
    """Set the default SSL/TLS version range."""
    ...

# SSL Constants

# Protocol versions
SSL_LIBRARY_VERSION_2: int
SSL_LIBRARY_VERSION_3_0: int
SSL_LIBRARY_VERSION_TLS_1_0: int
SSL_LIBRARY_VERSION_TLS_1_1: int
SSL_LIBRARY_VERSION_TLS_1_2: int
SSL_LIBRARY_VERSION_TLS_1_3: int

# SSL Options
SSL_SECURITY: int
SSL_SOCKS: int
SSL_REQUEST_CERTIFICATE: int
SSL_HANDSHAKE_AS_CLIENT: int
SSL_HANDSHAKE_AS_SERVER: int
SSL_ENABLE_SSL2: int
SSL_ENABLE_SSL3: int
SSL_NO_CACHE: int
SSL_REQUIRE_CERTIFICATE: int
SSL_ENABLE_FDX: int
SSL_V2_COMPATIBLE_HELLO: int
SSL_ENABLE_TLS: int
SSL_ROLLBACK_DETECTION: int
SSL_NO_STEP_DOWN: int
SSL_BYPASS_PKCS11: int
SSL_NO_LOCKS: int
SSL_ENABLE_SESSION_TICKETS: int
SSL_ENABLE_DEFLATE: int
SSL_ENABLE_RENEGOTIATION: int
SSL_REQUIRE_SAFE_NEGOTIATION: int
SSL_ENABLE_FALSE_START: int
SSL_CBC_RANDOM_IV: int
SSL_ENABLE_OCSP_STAPLING: int
SSL_ENABLE_NPN: int
SSL_ENABLE_ALPN: int
SSL_REUSE_SERVER_ECDHE_KEY: int
SSL_ENABLE_FALLBACK_SCSV: int
SSL_ENABLE_SERVER_DHE: int
SSL_ENABLE_EXTENDED_MASTER_SECRET: int
SSL_ENABLE_SIGNED_CERT_TIMESTAMPS: int
SSL_REQUIRE_DH_NAMED_GROUPS: int
SSL_ENABLE_0RTT_DATA: int
SSL_RECORD_SIZE_LIMIT: int

# Renegotiation options
SSL_RENEGOTIATE_NEVER: int
SSL_RENEGOTIATE_UNRESTRICTED: int
SSL_RENEGOTIATE_REQUIRES_XTN: int
SSL_RENEGOTIATE_TRANSITIONAL: int

# Certificate request types
SSL_REQUEST_NEVER: int
SSL_REQUEST_FIRST_HANDSHAKE: int
SSL_REQUEST_SUBSEQUENT_HANDSHAKES: int
SSL_REQUEST_ALWAYS: int

# Variant types
ssl_variant_stream: int
ssl_variant_datagram: int

class SSLSocket:
    """SSL socket class wrapping NSPR sockets."""

    def __init__(self, family: int = socket.AF_INET) -> None:
        """
        Create a new SSL socket.

        Args:
            family: Address family (AF_INET or AF_INET6)
        """
        ...

    def set_ssl_option(self, option: int, value: bool) -> None:
        """
        Set an SSL socket option.

        Args:
            option: SSL option constant (e.g., SSL_SECURITY)
            value: Boolean value to set
        """
        ...

    def get_ssl_option(self, option: int) -> bool:
        """
        Get an SSL socket option value.

        Args:
            option: SSL option constant

        Returns:
            Current value of the option
        """
        ...

    def set_hostname(self, hostname: str) -> None:
        """
        Set the expected hostname for certificate verification.

        Args:
            hostname: Expected hostname
        """
        ...

    def get_hostname(self) -> str:
        """Get the expected hostname."""
        ...

    def set_handshake_callback(
        self,
        callback: Optional[Callable[..., None]]
    ) -> None:
        """
        Set callback function called when SSL handshake completes.

        Args:
            callback: Function to call on handshake completion
        """
        ...

    def set_auth_certificate_callback(
        self,
        callback: Optional[Callable[..., bool]],
        *args: Any
    ) -> None:
        """
        Set callback function for certificate authentication.

        Args:
            callback: Function to verify certificates
            *args: Additional arguments passed to callback
        """
        ...

    def set_client_auth_data_callback(
        self,
        callback: Optional[Callable[..., Tuple[Any, Any]]],
        *args: Any
    ) -> None:
        """
        Set callback function for client authentication.

        Args:
            callback: Function to provide client certificate
            *args: Additional arguments passed to callback
        """
        ...

    def set_pkcs11_pin_arg(self, pin_arg: Any) -> None:
        """Set PKCS#11 PIN argument for certificate operations."""
        ...

    def get_pkcs11_pin_arg(self) -> Any:
        """Get PKCS#11 PIN argument."""
        ...

    def set_ssl_version_range(self, min_version: int, max_version: int) -> None:
        """
        Set the SSL/TLS version range for this socket.

        Args:
            min_version: Minimum protocol version
            max_version: Maximum protocol version
        """
        ...

    def get_ssl_version_range(self) -> Tuple[int, int]:
        """
        Get the SSL/TLS version range.

        Returns:
            Tuple of (min_version, max_version)
        """
        ...

    def reset_handshake(self, as_server: bool = False) -> None:
        """
        Reset the SSL handshake state.

        Args:
            as_server: True if acting as server, False for client
        """
        ...

    def force_handshake(self) -> None:
        """Force the SSL handshake to complete."""
        ...

    def get_peer_certificate(self) -> Any:
        """Get the peer's certificate after handshake."""
        ...

    def get_peer_name(self) -> str:
        """Get the peer's network address."""
        ...

    def get_channel_info(self) -> Any:
        """Get SSL channel information."""
        ...

    def get_cipher_suite_info(self) -> Any:
        """Get information about the negotiated cipher suite."""
        ...

    def set_cipher_pref(self, cipher: int, enabled: bool) -> None:
        """
        Set cipher suite preference.

        Args:
            cipher: Cipher suite identifier
            enabled: True to enable, False to disable
        """
        ...

    def get_cipher_pref(self, cipher: int) -> bool:
        """Get cipher suite preference."""
        ...

    # Socket operations (NSPR socket interface)
    def connect(self, addr: Any, timeout: Optional[int] = None) -> None:
        """
        Connect to a remote address.

        Args:
            addr: Network address object
            timeout: Connection timeout in milliseconds
        """
        ...

    def bind(self, addr: Any) -> None:
        """Bind to a local address."""
        ...

    def listen(self, backlog: int = 5) -> None:
        """Listen for connections."""
        ...

    def accept(self, timeout: Optional[int] = None) -> Tuple['SSLSocket', Any]:
        """
        Accept an incoming connection.

        Returns:
            Tuple of (connected_socket, peer_address)
        """
        ...

    def send(self, data: bytes, flags: int = 0) -> int:
        """
        Send data over the socket.

        Returns:
            Number of bytes sent
        """
        ...

    def recv(self, bufsize: int, flags: int = 0) -> bytes:
        """
        Receive data from the socket.

        Returns:
            Received data
        """
        ...

    def close(self) -> None:
        """Close the socket."""
        ...

    def shutdown(self, how: int = socket.SHUT_RDWR) -> None:
        """Shutdown the socket connection."""
        ...

    def set_socket_option(self, option: int, value: Any) -> None:
        """Set a socket option."""
        ...

    def get_socket_option(self, option: int) -> Any:
        """Get a socket option value."""
        ...

    def fileno(self) -> int:
        """Get the file descriptor number."""
        ...

    def makefile(
        self,
        mode: str = 'r',
        buffering: int = -1
    ) -> Any:
        """Create a file-like object from the socket."""
        ...

class SSLChannelInfo:
    """Information about an SSL channel."""

    @property
    def protocol_version(self) -> int:
        """Get the negotiated protocol version."""
        ...

    @property
    def cipher_suite(self) -> int:
        """Get the negotiated cipher suite."""
        ...

    @property
    def auth_key_bits(self) -> int:
        """Get the authentication key length in bits."""
        ...

    @property
    def keay_exchange_key_bits(self) -> int:
        """Get the key exchange key length in bits."""
        ...

class SSLCipherSuiteInfo:
    """Information about an SSL cipher suite."""

    @property
    def cipher_suite(self) -> int:
        """Get the cipher suite identifier."""
        ...

    @property
    def cipher_suite_name(self) -> str:
        """Get the cipher suite name."""
        ...

    @property
    def auth_algorithm(self) -> int:
        """Get the authentication algorithm."""
        ...

    @property
    def auth_algorithm_name(self) -> str:
        """Get the authentication algorithm name."""
        ...

    @property
    def kea_type(self) -> int:
        """Get the key exchange algorithm type."""
        ...

    @property
    def kea_type_name(self) -> str:
        """Get the key exchange algorithm name."""
        ...

    @property
    def symmetric_cipher(self) -> int:
        """Get the symmetric cipher algorithm."""
        ...

    @property
    def symmetric_cipher_name(self) -> str:
        """Get the symmetric cipher name."""
        ...

    @property
    def mac_algorithm(self) -> int:
        """Get the MAC algorithm."""
        ...

    @property
    def mac_algorithm_name(self) -> str:
        """Get the MAC algorithm name."""
        ...

    @property
    def effective_key_bits(self) -> int:
        """Get the effective key length in bits."""
        ...

    @property
    def is_fips(self) -> bool:
        """Check if the cipher suite is FIPS compliant."""
        ...

    @property
    def is_exportable(self) -> bool:
        """Check if the cipher suite is exportable."""
        ...

# Cipher suite constants (examples - there are many more)
TLS_NULL_WITH_NULL_NULL: int
TLS_RSA_WITH_NULL_MD5: int
TLS_RSA_WITH_NULL_SHA: int
TLS_RSA_WITH_RC4_128_MD5: int
TLS_RSA_WITH_RC4_128_SHA: int
TLS_RSA_WITH_3DES_EDE_CBC_SHA: int
TLS_RSA_WITH_AES_128_CBC_SHA: int
TLS_RSA_WITH_AES_256_CBC_SHA: int
TLS_RSA_WITH_AES_128_CBC_SHA256: int
TLS_RSA_WITH_AES_256_CBC_SHA256: int
TLS_RSA_WITH_AES_128_GCM_SHA256: int
TLS_RSA_WITH_AES_256_GCM_SHA384: int
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256: int
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384: int
TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256: int
TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384: int
TLS_AES_128_GCM_SHA256: int
TLS_AES_256_GCM_SHA384: int
TLS_CHACHA20_POLY1305_SHA256: int

# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Type stubs for nss.nss module.

This file provides type hints for the C extension module nss.nss.
"""

from typing import Any, Callable, Optional, Union, Tuple, List, overload

# Version information
def nss_get_version() -> str:
    """Get the NSS library version string."""
    ...

def nss_version_check(version: str) -> bool:
    """Check if NSS version meets minimum requirement."""
    ...

# NSS initialization and shutdown
def nss_init(cert_dir: str) -> None:
    """Initialize NSS with a certificate database directory."""
    ...

def nss_init_nodb() -> None:
    """Initialize NSS without a certificate database."""
    ...

def nss_init_read_write(cert_dir: str) -> None:
    """Initialize NSS with read-write access to certificate database."""
    ...

def nss_shutdown() -> None:
    """Shutdown NSS and free resources."""
    ...

def nss_is_initialized() -> bool:
    """Check if NSS has been initialized."""
    ...

def set_shutdown_callback(
    callback: Optional[Callable[..., bool]],
    *args: Any
) -> None:
    """Set a callback function to be called when NSS shuts down."""
    ...

# Password callback
def set_password_callback(callback: Optional[Callable[..., str]]) -> None:
    """Set a callback function for password requests."""
    ...

# Certificate database
def get_default_certdb() -> Any:
    """Get the default certificate database."""
    ...

# Cryptographic operations
def create_pbev2_algorithm_id(
    pbe_alg: str,
    cipher_alg: str,
    prf_alg: str,
    key_length: int,
    iterations: int,
    salt: Optional[bytes]
) -> Any:
    """Create a PBKDF2 algorithm ID."""
    ...

def create_context_by_sym_key(
    mechanism: int,
    operation: int,
    key: Any,
    params: Optional[Any]
) -> Any:
    """Create a cryptographic context using a symmetric key."""
    ...

def get_internal_slot() -> Any:
    """Get the internal cryptographic slot."""
    ...

# Data conversion utilities
def data_to_hex(data: bytes, octets_per_line: int = 16) -> str:
    """Convert binary data to hexadecimal string."""
    ...

def make_line_fmt_tuples(
    level: int,
    *lines: str
) -> List[Tuple[int, str]]:
    """Create formatted line tuples for indented output."""
    ...

def indented_format(tuples: List[Tuple[int, str]]) -> str:
    """Format indented text from line tuples."""
    ...

# Key mechanism names
def key_mechanism_type_name(mechanism: int) -> str:
    """Get the name of a key mechanism type."""
    ...

# Certificate usage flags
def cert_usage_flags(usage: int) -> List[str]:
    """Get list of certificate usage flag names."""
    ...

# Constants
CKA_ENCRYPT: int
CKA_DECRYPT: int
CKA_SIGN: int
CKA_VERIFY: int

# Certificate usage constants
certificateUsageSSLClient: int
certificateUsageSSLServer: int
certificateUsageSSLServerWithStepUp: int
certificateUsageSSLCA: int
certificateUsageEmailSigner: int
certificateUsageEmailRecipient: int
certificateUsageObjectSigner: int
certificateUsageUserCertImport: int
certificateUsageVerifyCA: int
certificateUsageProtectedObjectSigner: int
certificateUsageStatusResponder: int
certificateUsageAnyCA: int

# Algorithm OIDs (examples - add more as needed)
SEC_OID_PKCS5_PBKDF2: str
SEC_OID_AES_256_CBC: str
SEC_OID_HMAC_SHA1: str

class SecItem:
    """Represents a security item (binary data)."""

    def __init__(
        self,
        data: Optional[Union[bytes, str]] = None,
        ascii: bool = False
    ) -> None:
        """
        Create a SecItem.

        Args:
            data: Binary data or base64 string
            ascii: If True, data is treated as base64
        """
        ...

    def to_base64(self, chars_per_line: int = 64) -> str:
        """Convert to base64 string."""
        ...

    @property
    def data(self) -> bytes:
        """Get the raw binary data."""
        ...

class Certificate:
    """Represents an X.509 certificate."""

    @property
    def subject(self) -> str:
        """Get the certificate subject."""
        ...

    @property
    def issuer(self) -> str:
        """Get the certificate issuer."""
        ...

    @property
    def serial_number(self) -> int:
        """Get the certificate serial number."""
        ...

    def verify_now(
        self,
        certdb: Any,
        check_sig: bool,
        usage: int,
        *pin_args: Any
    ) -> int:
        """Verify the certificate."""
        ...

    def verify_hostname(self, hostname: str) -> bool:
        """Verify that the certificate matches the hostname."""
        ...

    def format_lines(self, level: int = 0) -> List[Tuple[int, str]]:
        """Format certificate information as indented lines."""
        ...

class SymKey:
    """Represents a symmetric cryptographic key."""

    @property
    def key_type(self) -> int:
        """Get the key type."""
        ...

    @property
    def key_length(self) -> int:
        """Get the key length in bits."""
        ...

    def format_lines(self, level: int = 0) -> List[Tuple[int, str]]:
        """Format key information as indented lines."""
        ...

class AlgorithmID:
    """Represents a cryptographic algorithm identifier."""

    def get_pbe_crypto_mechanism(self, key: SymKey) -> Tuple[int, SecItem]:
        """Get the cryptographic mechanism and parameters."""
        ...

    def format_lines(self, level: int = 0) -> List[Tuple[int, str]]:
        """Format algorithm ID information as indented lines."""
        ...

class Context:
    """Represents a cryptographic context."""

    def cipher_op(self, data: bytes) -> bytes:
        """Perform a cipher operation on data."""
        ...

    def digest_final(self) -> bytes:
        """Finalize the digest and return remaining data."""
        ...

class PK11Slot:
    """Represents a PKCS#11 cryptographic slot."""

    @property
    def token_name(self) -> str:
        """Get the token name."""
        ...

    def pbe_key_gen(self, alg_id: AlgorithmID, password: str) -> SymKey:
        """Generate a password-based encryption key."""
        ...

# Add more classes and functions as needed for complete coverage

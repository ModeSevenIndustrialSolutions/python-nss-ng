# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
pytest configuration for python-nss tests.

This file provides fixtures and setup for running tests with pytest.

NSS has global state that cannot be re-initialized in the same process.
Tests that call nss_init()/nss_shutdown() must run in complete isolation.
We use pytest-forked to run each test in a separate process.
"""

import os
import sys
import pytest
import atexit


def get_test_db_path():
    """
    Get the absolute path to the test PKI database.

    Returns the path 'sql:<test_dir>/pki' where test_dir is the
    directory containing this conftest.py file.
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    pki_dir = os.path.join(test_dir, 'pki')
    return f'sql:{pki_dir}'


# Global flag to track if NSS has been initialized in this process
_nss_initialized = False
_nss_init_lock = None


def is_nss_initialized():
    """Check if NSS has been initialized in this process."""
    global _nss_initialized
    try:
        import nss.nss as nss
        # Use NSS's built-in check if available
        return nss.nss_is_initialized()
    except:
        return _nss_initialized


def mark_nss_initialized():
    """Mark NSS as initialized in this process."""
    global _nss_initialized
    _nss_initialized = True


def pytest_configure(config):
    """Configure pytest for python-nss tests."""
    # Add custom markers (these are now also in pyproject.toml but keeping for compatibility)
    config.addinivalue_line(
        "markers", "nss_init: mark test as requiring NSS initialization (runs in forked process)"
    )
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring NSS database"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "forked: mark test to run in forked process for isolation"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment before running any tests.
    This fixture runs once per test session.
    """
    # Ensure test directory is in path
    test_dir = os.path.dirname(os.path.abspath(__file__))
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)

    # If running tests in-tree, add the build directory to path
    from util import get_build_dir
    build_dir = get_build_dir()
    if build_dir and os.path.exists(build_dir):
        print(f"\nUsing local libraries from build directory: {build_dir}")
        sys.path.insert(0, build_dir)
    else:
        print("\nUsing installed libraries")

    yield

    # Cleanup after all tests
    pass


@pytest.fixture(scope="session")
def test_certs(setup_test_environment):
    """
    Set up test certificates once per test session.

    This fixture ensures that test certificates are created before
    any tests that need them run.
    """
    import setup_certs

    # Set up certificates with default options
    # This will create a temporary directory with test certs
    setup_certs.setup_certs([])

    yield

    # Certificates will be cleaned up by setup_certs exit handler


@pytest.fixture(scope="session")
def test_p12_file(test_certs):
    """
    Create p12 file once per test session.

    This fixture ensures the p12 file exists before any tests that need it run.
    This must run outside of forked test processes since it needs NSS initialization.
    """
    import subprocess
    import os
    from util import find_nss_tool

    cert_nickname = 'test_user'
    pk12_filename = f'{cert_nickname}.p12'
    pk12_passwd = 'PK12_passwd'
    db_passwd = 'DB_passwd'

    # Get test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    pk12_path = os.path.join(test_dir, pk12_filename)

    # Skip if file already exists
    if os.path.exists(pk12_path):
        yield pk12_path
        return

    # Create the p12 file using pk12util
    cmd_args = [find_nss_tool('pk12util'),
                '-o', pk12_filename,
                '-n', cert_nickname,
                '-d', 'sql:pki',
                '-K', db_passwd,
                '-W', pk12_passwd]

    try:
        p = subprocess.Popen(cmd_args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True,
                             cwd=test_dir)
        stdout, stderr = p.communicate()
        returncode = p.returncode
        if returncode != 0:
            print(f"Warning: Failed to create p12 file: {stderr}")
    except Exception as e:
        print(f"Warning: Failed to create p12 file: {e}")

    yield pk12_path

    # Cleanup p12 file after session
    if os.path.exists(pk12_path):
        try:
            os.remove(pk12_path)
        except:
            pass


@pytest.fixture
def nss_db_dir(test_certs, tmp_path):
    """
    Provide a temporary NSS database directory for tests.

    Returns the path to the database directory.
    """
    db_dir = tmp_path / "nss_db"
    db_dir.mkdir()
    return str(db_dir)


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test characteristics.

    This automatically marks tests that need NSS isolation to run in
    separate forked processes to prevent global state conflicts.
    """
    for item in items:
        # Mark tests that import nss modules as requiring initialization
        if "nss" in str(item.fspath):
            item.add_marker(pytest.mark.nss_init)

        # Mark slow tests (client_server tests are typically slow)
        if "client_server" in str(item.fspath):
            item.add_marker(pytest.mark.slow)

        # Tests in these files need complete process isolation due to NSS global state
        # Each test initializes and shuts down NSS, which can only happen once per process
        isolation_required_files = [
            "test_cert_components.py",
            "test_cert_request.py",
            "test_cipher.py",
            "test_digest.py",
            "test_pkcs12.py",
            "test_client_server.py",
        ]

        for filename in isolation_required_files:
            if filename in str(item.fspath):
                # Add forked marker if not already present
                if not any(mark.name == "forked" for mark in item.iter_markers()):
                    item.add_marker(pytest.mark.forked)
                break


@pytest.fixture(scope="function")
def isolated_nss_init():
    """
    Fixture to ensure NSS is properly initialized and shut down for a test.

    This fixture should be used by tests that need to call nss_init() and
    nss_shutdown(). It ensures cleanup happens even if the test fails.

    Note: Tests using this fixture should be marked with @pytest.mark.forked
    to ensure they run in a separate process.
    """
    initialized = False
    shutdown_completed = False

    def init_nss(db_path=None, read_write=False):
        """Initialize NSS with the given database."""
        nonlocal initialized
        import nss.nss as nss

        if is_nss_initialized():
            # Already initialized in this process - don't try again
            return

        try:
            if db_path:
                if read_write:
                    nss.nss_init_read_write(db_path)
                else:
                    nss.nss_init(db_path)
            else:
                nss.nss_init_nodb()
            initialized = True
            mark_nss_initialized()
        except Exception as e:
            # Check if already initialized error
            if 'ALREADY_INITIALIZED' in str(e):
                initialized = True
                mark_nss_initialized()
            else:
                raise

    yield init_nss

    # Cleanup: shutdown NSS if we initialized it
    if initialized and not shutdown_completed:
        try:
            import nss.nss as nss
            if is_nss_initialized():
                nss.nss_shutdown()
                shutdown_completed = True
        except Exception as e:
            # Ignore shutdown errors - process is ending anyway
            pass


def pytest_report_header(config):
    """Add custom header information to pytest output."""
    import sys

    header_lines = [
        f"Python version: {sys.version}",
        f"Python executable: {sys.executable}",
    ]

    # Try to get NSS version if available
    # Do this in a safer way that checks if already initialized
    try:
        import nss.nss as nss
        need_shutdown = False

        if not is_nss_initialized():
            nss.nss_init_nodb()
            need_shutdown = True
            mark_nss_initialized()

        version = nss.nss_get_version()

        if need_shutdown:
            nss.nss_shutdown()

        header_lines.append(f"NSS version: {version}")
    except Exception as e:
        header_lines.append(f"NSS version: Unable to determine ({e})")

    return "\n".join(header_lines)

# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
pytest configuration for python-nss tests.

This file provides fixtures and setup for running tests with pytest.
Tests are run in separate processes using pytest-xdist to provide clean
NSS initialization for each test file.
"""

import os
import sys
import time
import pytest


def pytest_configure(config):
    """Configure pytest for python-nss tests."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "nss_init: mark test as requiring NSS initialization"
    )
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring NSS database"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment before running any tests.
    This fixture runs once per test session (i.e., once per worker process).
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

    # Cleanup after all tests in this process
    pass


@pytest.fixture(scope="session")
def test_certs(setup_test_environment):
    """
    Set up test certificates once per test session (worker process).

    This fixture ensures that test certificates are created before
    any tests that need them run. Creates a 'pki' directory in the
    test directory with NSS database and certificates.

    With pytest-xdist, each worker process gets its own session,
    so each worker will have its own pki directory.
    """
    import setup_certs
    import shutil

    # Create a session-scoped temporary directory for PKI
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # For xdist workers, use worker-specific directory
    # For single-process mode, just use 'pki'
    worker_id = os.environ.get('PYTEST_XDIST_WORKER')
    if worker_id:
        pki_dir = os.path.join(test_dir, f'pki_{worker_id}')
    else:
        pki_dir = os.path.join(test_dir, 'pki')

    # Clean up any existing pki directory with retry logic
    if os.path.exists(pki_dir):
        for attempt in range(3):
            try:
                shutil.rmtree(pki_dir)
                break
            except OSError:
                if attempt < 2:
                    time.sleep(0.5)
                else:
                    # Last attempt - try to continue anyway
                    pass

    # Set up certificates with default options
    # This creates the directory that tests expect
    setup_certs.setup_certs(['--db-dir', pki_dir])

    yield pki_dir

    # Cleanup after all tests with retry logic
    if os.path.exists(pki_dir):
        for attempt in range(3):
            try:
                shutil.rmtree(pki_dir)
                break
            except OSError:
                if attempt < 2:
                    time.sleep(0.5)


@pytest.fixture(scope="session")
def nss_db_dir(test_certs):
    """
    Provide the NSS database directory path for tests.

    Returns the path to the 'sql:pki' database that tests expect.
    This fixture depends on test_certs which creates the database.
    """
    return f'sql:{test_certs}'


@pytest.fixture(scope="session")
def nss_initialized(nss_db_dir):
    """
    Initialize NSS once per test session (worker process).

    With pytest-xdist, each worker process runs in isolation,
    so NSS can be initialized once per worker and shared across
    all tests in that worker.
    """
    import nss.nss as nss

    # Initialize NSS with the test database once for this worker
    nss.nss_init_read_write(nss_db_dir)

    yield

    # Shutdown NSS after all tests in this worker complete
    # Give any background threads time to finish
    time.sleep(0.5)
    try:
        nss.nss_shutdown()
    except Exception as e:
        # NSS shutdown may fail if resources are still in use
        # This is acceptable at the end of the test session
        print(f"\nNote: NSS shutdown: {e}")


@pytest.fixture
def nss_db_context(nss_initialized):
    """
    Provide NSS database context for tests.

    This fixture depends on nss_initialized to ensure NSS is set up,
    and provides the certificate database to tests that need it.
    NSS is initialized once per worker process and shared across tests.
    """
    import nss.nss as nss

    certdb = nss.get_default_certdb()
    yield certdb

    # Minimal cleanup per test
    # Note: We don't shut down NSS here as it's shared across all tests
    # in this worker process
    try:
        import nss.ssl as ssl
        ssl.clear_session_cache()
    except:
        pass


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test characteristics.
    """
    for item in items:
        # Mark tests that import nss modules
        if "nss" in str(item.fspath):
            item.add_marker(pytest.mark.nss_init)

        # Mark slow tests (client_server tests are typically slow)
        if "client_server" in str(item.fspath):
            item.add_marker(pytest.mark.slow)


def pytest_report_header(config):
    """Add custom header information to pytest output."""
    import sys

    header_lines = [
        f"Python version: {sys.version}",
        f"Python executable: {sys.executable}",
    ]

    # Try to get NSS version if available
    try:
        import nss.nss as nss
        nss.nss_init_nodb()
        version = nss.nss_get_version()
        nss.nss_shutdown()
        header_lines.append(f"NSS version: {version}")
    except Exception as e:
        header_lines.append(f"NSS version: Unable to determine ({e})")

    return "\n".join(header_lines)

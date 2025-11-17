# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
pytest configuration for python-nss tests.

This file provides fixtures and setup for running tests with pytest.
"""

import os
import sys
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

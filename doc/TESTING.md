<!--
SPDX-License-Identifier: MPL-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Testing python-nss-ng

This document describes how to run and write tests for python-nss-ng.

## Overview

python-nss-ng uses pytest as its testing framework. The `test/` directory contains
all tests. You can run them using pytest or the legacy `test/run_tests` script.

## Prerequisites

### System Dependencies

You need NSS and NSPR development libraries and NSS tools installed on your system:

**Fedora/RHEL/CentOS:**

```bash
sudo dnf install nss-devel nspr-devel nss-tools
```

**Debian/Ubuntu:**

```bash
sudo apt-get install libnss3-dev libnspr4-dev libnss3-tools
```

**macOS (Homebrew):**

```bash
brew install nss nspr
```

**Note:** The NSS tools package provides `certutil`, `pk12util`, and other
utilities required for test certificate generation. On macOS, the `nss`
Homebrew package includes these tools.

### Python Dependencies

Install the test dependencies:

```bash
# Using uv (recommended)
uv pip install -e ".[test]"

# Or using standard package installer
pip install -e ".[test]"
```

## Running Tests

### Using pytest (Recommended)

Run all tests:

```bash
pytest test/
```

Run with verbose output:

```bash
pytest test/ -v
```

Run with coverage reporting:

```bash
pytest test/ --cov=nss --cov-report=html
```

Run specific test file:

```bash
pytest test/test_misc.py
```

Run specific test:

```bash
pytest test/test_misc.py::TestVersion::test_version
```

Run tests matching a pattern:

```bash
pytest test/ -k "certificate"
```

Skip slow tests:

```bash
pytest test/ -m "not slow"
```

Run tests requiring NSS initialization:

```bash
pytest test/ -m "nss_init"
```

### Using the Legacy Test Runner

The legacy `test/run_tests` script is still available:

```bash
# Run tests with installed library
python test/run_tests

# Run tests with in-tree build
python test/run_tests --in-tree
```

## Test Structure

### Test Files

- `test_cert_components.py` - Certificate component tests
- `test_cert_request.py` - Certificate request tests
- `test_cipher.py` - Cipher and encryption tests
- `test_client_server.py` - SSL/TLS client/server tests (slow)
- `test_digest.py` - Digest and hashing tests
- `test_misc.py` - Miscellaneous tests
- `test_ocsp.py` - OCSP (Online Certificate Status Protocol) tests
- `test_pkcs12.py` - PKCS#12 tests

### Support Files

- `conftest.py` - pytest configuration and fixtures
- `setup_certs.py` - Certificate setup utility
- `util.py` - Test utilities
- `run_tests` - Legacy test runner script

## pytest Fixtures

The `test/conftest.py` file provides these fixtures:

### `setup_test_environment`

Session-scoped fixture that sets up the test environment. Automatically adds
the build directory to `sys.path` if running in-tree tests.

### `test_certs`

Session-scoped fixture that creates test certificates once per test session.
Depends on `setup_test_environment`.

### `nss_db_dir`

Function-scoped fixture that provides a temporary NSS database directory.
Creates a new directory for each test that needs it.

## pytest Markers

`conftest.py` defines these custom markers:

- `@pytest.mark.nss_init` - Test requires NSS initialization
- `@pytest.mark.requires_db` - Test requires NSS database
- `@pytest.mark.slow` - Test is slow-running

Use markers to run specific test categories:

```bash
# Run slow tests
pytest test/ -m "slow"

# Skip slow tests
pytest test/ -m "not slow"
```

## Writing Tests

### Basic Test Structure

```python
import pytest
import nss.nss as nss

class TestMyFeature:
    def test_something(self):
        """Test description."""
        # Arrange
        nss.nss_init_nodb()

        # Act
        result = nss.some_function()

        # Verify
        assert result is not None

        # Cleanup
        nss.nss_shutdown()
```

### Using Fixtures

```python
import pytest
import nss.nss as nss

class TestWithFixtures:
    def test_with_db(self, nss_db_dir):
        """Test that uses a temporary NSS database."""
        nss.nss_init(nss_db_dir)

        # Your test code here

        nss.nss_shutdown()
```

### Marking Tests

```python
import pytest

class TestSlow:
    @pytest.mark.slow
    def test_long_running_operation(self):
        """This test takes a long time to run."""
        # Slow test code
        pass

    @pytest.mark.requires_db
    def test_database_operation(self, nss_db_dir):
        """This test requires an NSS database."""
        # Database test code
        pass
```

## Test Coverage

Generate coverage reports:

```bash
# Run tests with coverage
pytest test/ --cov=nss --cov-report=term-missing

# Generate HTML coverage report
pytest test/ --cov=nss --cov-report=html

# Open coverage report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Coverage configuration is in `pyproject.toml` under `[tool.coverage.*]`.

## Continuous Integration

### CI/CD Integration

Run tests in CI/CD pipelines on:

- Python versions 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14
- Platforms: Linux, macOS, and Windows if supported
- Different NSS versions if possible

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libnss3-dev libnspr4-dev

      - name: Install Python dependencies
        run: |
          pip install -e ".[test]"

      - name: Run tests
        run: |
          pytest test/ -v --cov=nss --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

## Known Issues

### C Extension Compilation

The C extension code does not compile with modern NSS 3.100+.
Tests cannot run until we resolve the compilation issues.

To track progress on this issue, see:

- TODO.md - Section 1: C Extension Compilation Failures
Issues (when attempting compilation)

### Test Certificates

The `test_certs` fixture creates test certificates automatically.
The fixture stores them in a temporary directory and cleans up after tests complete.

If tests fail without explanation, check:

1. NSS database initialization
2. Certificate file permissions
3. Temporary directory access

## Troubleshooting

### Tests fail to import nss module

**Problem:** `ModuleNotFoundError: No module named 'nss'`

**Solution:**

- Ensure C extensions compile: `pip install -e .`
- Check that NSS/NSPR install properly
- Verify build directory exists if running in-tree tests

### NSS initialization fails

**Problem:** `nss.error.NSPRError: error initializing NSS`

**Solution:**

- Check NSS database path
- Verify NSS/NSPR libraries install properly
- Try running with `nss_init_nodb()` for tests that don't need a database

### Permission denied errors

**Problem:** Tests fail with permission errors

**Solution:**

- Ensure temporary directory is writable
- Check certificate file permissions
- Try running tests in a clean environment

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [NSS Documentation](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)

## Contributing Tests

When contributing new features, please include tests:

1. Add test file in `test/` directory following naming convention
   `test_<feature>.py`
2. Use pytest conventions (classes start with `Test`, methods with `test_`)
3. Add docstrings explaining what each test does
4. Use appropriate markers for slow or database-dependent tests
5. Ensure tests clean up resources (NSS shutdown, file cleanup)
6. Run tests locally before submitting PR
7. Verify coverage doesn't decrease

Good test characteristics:

- **Fast** - Tests should run fast
- **Isolated** - Each test should be independent
- **Repeatable** - Tests should produce same results every time
- **Self-checking** - Tests should verify results automatically
- **Concurrent** - Write tests alongside code

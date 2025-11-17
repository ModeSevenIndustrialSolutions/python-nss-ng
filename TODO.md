<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# TODO - python-nss Modernization

## Current Status

The python-nss project received modernization work to use current Python
packaging standards:

✅ **Completed:**

- Migrated from `distutils` to modern `setuptools` with `pyproject.toml`
- Implemented dynamic versioning using `setuptools-scm`
- Added support for Python 3.10, 3.11, 3.12, 3.13, 3.14
- Created modern project structure following PEP 517, 518, 621
- Set up `uv` compatibility for fast dependency management
- Added `pytest` configuration for testing
- Added `ruff` configuration for linting and formatting
- Created comprehensive documentation (README.md, MIGRATION.md)
- Removed legacy `setup.py.old` and `setup.cfg.old` files
- Created proper `MANIFEST.in` for source distributions
- Enhanced header/library detection with macOS Homebrew support
- Added `.gitignore` entries for modern Python development
- Configured GitHub Actions workflows compatibility

## Critical Issues

### 1. C Extension Compilation Failures ⚠️

#### Priority: CRITICAL

The C extension code does not compile with modern NSS 3.100+. Compilation
errors exist:

**Errors:**

- Struct member access issues in `src/py_nss.c`
- Invalid type conversions (e.g., `Py_CLEAR` used on wrong types)
- Member name mismatches (e.g., `py_modulus` vs `modulus`)
- API changes in NSS/NSPR headers

**Example Error:**

```text
src/py_nss.c:7228:20: error: no member named 'py_modulus' in
'struct RSAPublicKeyStr'; did you mean 'modulus'?
```

**Action Required:**

1. Audit all C code against NSS 3.117 API documentation
2. Fix struct member access throughout codebase
3. Update deprecated API usage
4. Test compilation against different NSS versions (3.80, 3.100, 3.117)
5. Consider using NSS's pkg-config data for compiler flags

**Files to Review:**

- `src/py_nss.c` (main NSS bindings - 817KB, complex)
- `src/py_ssl.c` (SSL bindings - 166KB)
- `src/py_nspr_io.c` (NSPR I/O - 119KB)
- `src/py_nspr_error.c` (Error handling - 25KB)

## High Priority Tasks

### 2. Update Python C API Usage

#### Priority: HIGH (Python C API)

The C code may use deprecated Python C API functions that changed or that
Python 3.10+ removed.

**Action:**

- Review Python 3.10, 3.11, 3.12, 3.13, 3.14 C API changes
- Update deprecated function calls
- Test with Python 3.10-3.14 interpreters
- Add C API version guards if needed

### 3. Fix Versioning for Legacy Tags

#### Priority: MEDIUM (Versioning)

Current setup uses new v-prefixed tags (v1.0.1), but legacy tags use
`PYNSS_RELEASE_X_Y_Z` format.

**Options:**

1. Keep using new v-prefixed tags going forward (current approach)
2. Create a custom setuptools-scm parser to handle old tag format
3. Re-tag old releases with new format

**Current Decision:** Using new v-prefixed tags. Legacy tags get ignored.

### 4. Add Comprehensive Tests

#### Priority: HIGH (Testing)

**Action:**

- Ensure existing tests work with pytest
- Add tests for Python 3.10+ compatibility
- Add tests for new build system
- Set up CI/CD to run tests automatically
- Add coverage reporting

**Files:**

- `test/test_*.py` - Need to verify compatibility
- `test/run_tests` - May need pytest migration

### 5. Documentation Updates

#### Priority: MEDIUM (Documentation)

**Action:**

- Generate API documentation from docstrings
- Update examples for Python 3.10+
- Add type stubs for C extensions
- Document NSS version compatibility
- Create contribution guide

## Medium Priority Tasks

### 6. Remove Python 2 Compatibility Code

#### Priority: MEDIUM (Python 2 Cleanup)

**Action:**

- Remove `from __future__ import` statements
- Remove `six` dependency (if any)
- Update string handling (bytes vs str)
- Update print statements
- Clean up 2/3 compatibility shims

### 7. Add Type Hints

#### Priority: MEDIUM (Type Hints)

**Action:**

- Create `.pyi` stub files for C extensions
- Add type hints to Python code
- Set up mypy configuration
- Run mypy in CI/CD

### 8. CI/CD Pipeline

#### Priority: HIGH (CI/CD)

**Action:**

- Verify GitHub Actions workflows work with new structure
- Test on different platforms (Linux, macOS, Windows if supported)
- Test with different Python versions (3.10-3.14)
- Add build status badges to README
- Set up automated releases

### 9. Dependency Audit

#### Priority: HIGH (Security)

**Action:**

- Run security audit on all dependencies
- Update any vulnerable dependencies
- Document security policies
- Set up Dependabot or similar

## Low Priority Tasks

### 10. Code Quality Improvements

#### Priority: LOW (Code Quality)

**Action:**

- Run ruff and fix all issues
- Add pre-commit hooks
- Set up automatic formatting
- Add docstring coverage checking

### 11. Performance Testing

#### Priority: LOW (Performance)

**Action:**

- Create performance benchmarks
- Compare with older versions
- Optimize hot paths if needed

### 12. Platform Support

#### Priority: LOW (Platform Support)

**Action:**

- Test on Windows (if applicable)
- Add platform-specific installation docs
- Consider wheel building for common platforms

## Immediate Next Steps

1. **Fix C Extension Compilation** - This blocks everything else
   - Start with the simplest errors first
   - Focus on `src/py_nspr_error.c` as it's smallest
   - Then move to `src/py_nspr_io.c`
   - Tackle `src/py_nss.c` and `src/py_ssl.c` last

2. **Test Build System** - Once code compiles

   ```bash
   uv venv --python 3.10
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   pytest test/
   ```

3. **Run Security Audit** - Check dependency security

   ```bash
   pip install pip-audit
   uv pip install pip-audit
   uv run pip-audit
   ```

4. **Update CI/CD** - Ensure workflows pass

5. **Tag Release** - Once everything works

   ```bash
   git tag v1.0.2
   git push origin v1.0.2
   ```

## Questions for Maintainers

1. **NSS Version Support**: What NSS versions should we support?
   - Latest version (3.117)?
   - Last 2 major versions?
   - LTS versions?

2. **Python Version Support**: Confirm Python 3.10-3.14 is correct range?

3. **Platform Support**: Which platforms are priority?
   - Linux (Fedora/RHEL, Debian/Ubuntu)?
   - macOS (via Homebrew)?
   - Windows?

4. **Backward Compatibility**: Do we need to maintain API compatibility with
   1.0.0?

5. **Repository**: Is github.com/tiran/python-nss the official repo?

## Resources

- NSS Documentation: <https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS>
- NSPR Documentation: <https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSPR>
- Python Packaging Guide: <https://packaging.python.org/>
- setuptools-scm: <https://setuptools-scm.readthedocs.io/>
- Python C API Changes: <https://docs.python.org/3/whatsnew/>

## Notes

- The build system is now properly configured
- Version management works with new tags
- Path detection works on macOS with Homebrew
- Source distribution builds as expected
- Main blocker is C code compatibility with modern NSS

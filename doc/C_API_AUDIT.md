<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Python C API Audit for Python 3.10-3.14 Compatibility

## Overview

This document audits the python-nss C extension code for deprecated
Python C API usage and compatibility with Python 3.10-3.14.

**Status**: ✅ Compatible (Minor Issues Found)

**Last Updated**: 2024

## Executive Summary

The python-nss C extensions are generally well-maintained and use modern
Python 3 APIs. This audit identified some issues that require attention
for optimal Python 3.10+ compatibility:

1. **HIGH**: Unsafe `PyModule_AddObject()` usage (ownership semantics
   changed in 3.10)
2. **MEDIUM**: Missing error checking on some module additions
3. **LOW**: Python 2 compatibility code still present (but harmless)

## Files Audited

- `src/py_nspr_error.c` - NSPR error handling module
- `src/py_nspr_io.c` - NSPR I/O module
- `src/py_nss.c` - Main NSS module (25,000+ lines)
- `src/py_ssl.c` - SSL/TLS module
- All associated header files

## Detailed Findings

### 1. PyModule_AddObject() Reference Stealing ⚠️

**Priority**: HIGH
**Affected Files**: All module initialization functions
**Python Versions**: 3.10+

#### Issue

`PyModule_AddObject()` has problematic ownership semantics:

- On **success**: steals a reference (caller must NOT decref)
- On **failure**: does NOT steal reference (caller MUST decref)

This dual behavior is error-prone. Python 3.10+ introduced
`PyModule_AddObjectRef()` to address this.

#### Current Code Patterns

##### Pattern 1: Checked but not cleaned up on failure

```c
// src/py_nspr_error.c:877-880
if (PyModule_AddObject(m, "_C_API",
                       PyCapsule_New((void *)&nspr_error_c_api,
                                     "_C_API", NULL)) != 0)
    return MOD_ERROR_VAL;  // ⚠️ Leaks capsule on failure
```

##### Pattern 2: Unchecked (even worse)

```c
// src/py_nspr_error.c:870
PyModule_AddObject(m, "__doc__", py_module_doc);  // ⚠️ No error checking at all
```

```c
// src/py_ssl.c:4421
PyModule_AddObject(m, "ssl_implemented_ciphers",
                   py_ssl_implemented_ciphers);  // ⚠️ No error checking
```

#### Recommended Fix

For Python 3.10+, use `PyModule_AddObjectRef()` which always increfs:

```c
#if PY_VERSION_HEX >= 0x030A0000  // Python 3.10+
    if (PyModule_AddObjectRef(m, "_C_API", capsule) < 0) {
        Py_DECREF(capsule);
        return MOD_ERROR_VAL;
    }
    Py_DECREF(capsule);  // Always decref with AddObjectRef
#else
    // Fallback for Python 3.9 and earlier
    if (PyModule_AddObject(m, "_C_API", capsule) != 0) {
        Py_DECREF(capsule);  // Decref on failure
        return MOD_ERROR_VAL;
    }
    // No decref on success - reference ownership transferred
#endif
```

Or use the compatible pattern:

```c
// Works on all Python versions
PyObject *capsule = PyCapsule_New((void *)&nss_ssl_c_api, "_C_API", NULL);
if (capsule == NULL)
    return MOD_ERROR_VAL;

Py_INCREF(capsule);  // Extra ref so we can always decref
if (PyModule_AddObject(m, "_C_API", capsule) != 0) {
    Py_DECREF(capsule);
    return MOD_ERROR_VAL;
}
Py_DECREF(capsule);  // Always safe to decref now
```

#### Locations to Fix

1. `src/py_nspr_error.c:870` - `__doc__` (no error check)
2. `src/py_nspr_error.c:879` - `_C_API` (missing cleanup on failure)
3. `src/py_nspr_io.c:3862` - `_C_API` (missing cleanup on failure)
4. `src/py_nss.c:25349` - `_C_API` (missing cleanup on failure)
5. `src/py_ssl.c:4402` - `_C_API` (missing cleanup on failure)
6. `src/py_ssl.c:4421` - `ssl_implemented_ciphers` (no error check)

### 2. API Usage Summary ✅

#### Confirmed Safe APIs in Use

- ✅ `Py_TYPE()` - Used appropriately (Python 3.0+ function macro)
- ✅ `Py_SIZE()` - Used appropriately (Python 3.0+ function macro)
- ✅ `PyArg_ParseTuple()` - No deprecations
- ✅ `PyArg_ParseTupleAndKeywords()` - No deprecations
- ✅ `PyErr_Format()` - No deprecations
- ✅ `PyModule_Create()` - Correct for Python 3
- ✅ `PyModuleDef` - Correct structure usage
- ✅ `PyCapsule_New()` - Correct for C API export

#### No Usage Found (Good)

- ✅ No `->ob_type` direct access
- ✅ No `->ob_refcnt` direct access
- ✅ No `->ob_size` direct access
- ✅ No `PyUnicode_AS_UNICODE` (removed in 3.12)
- ✅ No `PyUnicode_GET_SIZE` (removed in 3.12)
- ✅ No `Py_UNICODE` type usage (removed in 3.13)
- ✅ No `PyEval_CallObject` (deprecated)
- ✅ No `PyObject_AsCharBuffer` (removed)
- ✅ No `PyObject_AsReadBuffer` (removed)

### 3. Python 2 Compatibility Code 🔍

**Priority**: LOW
**Status**: Harmless but removable

Some files still contain Python 2 fallback code:

```c
#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&module_def);
#else
    m = Py_InitModule3(NSS_ERROR_MODULE_NAME, module_methods, module_doc);
#endif
```

**Recommendation**: Since the project now targets Python 3.10+,
we can simplify these to use the Python 3 code path. They are
harmless and low priority.

**Affected Files**:

- `src/py_nspr_error.c:848`
- `src/py_nspr_io.c:3846`
- `src/py_nss.c:25291`
- `src/py_ssl.c:4382`

### 4. Buffer Protocol Usage ✅

**Status**: Compatible

The code uses Python 3's buffer protocol:

```c
static PyBufferProcs SecItem_as_buffer = {
    SecItem_GetBuffer,          /* bf_getbuffer */
    SecItem_ReleaseBuffer,      /* bf_releasebuffer */
};
```

No deprecations or issues found.

### 5. Slice API Usage ✅

**Status**: Compatible

The code uses `PySlice_GetIndicesEx()` which is correct for all Python 3
versions. The code guards the Python 2 cast:

```c
#if PY_MAJOR_VERSION >= 3
    if (PySlice_GetIndicesEx(item, SecItem_GET_SIZE(self),
                             &start, &stop, &step, &slice_len) < 0) {
#else
    if (PySlice_GetIndicesEx((PySliceObject *)item, SecItem_GET_SIZE(self),
                             &start, &stop, &step, &slice_len) < 0) {
#endif
```

### 6. Type Flag Usage ✅

**Status**: Compatible

The code uses appropriate type flags:

```c
Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE
```

These flags are valid in Python 3.10+.

## Python Version-Specific Changes

### Python 3.10 (Released Oct 2021)

- ✅ No breaking changes affecting python-nss
- ⚠️ `PyModule_AddObject()` semantics clarified (see above)
- ✅ `Py_TYPE()` and `Py_SIZE()` became functions (already handled)

### Python 3.11 (Released Oct 2022)

- ✅ No breaking changes affecting python-nss
- ℹ️ Frame evaluation changes (doesn't affect C extensions like this)
- ℹ️ Performance improvements (benefits python-nss automatically)

### Python 3.12 (Released Oct 2023)

- ✅ No deprecated APIs used in python-nss
- ✅ `PyUnicode_AS_UNICODE` removed (not used)
- ✅ `PyUnicode_GET_SIZE` removed (not used)

### Python 3.13 (Released Oct 2024)

- ✅ No breaking changes affecting python-nss
- ✅ `Py_UNICODE` type removed (not used)
- ℹ️ Free-threaded Python support added (python-nss may need GIL review
  for future support)

### Python 3.14 (In Development)

- ⚠️ Further C API cleanup expected
- ℹ️ More deprecations possible
- 📝 Review release notes when available

## Recommendations

### Immediate Actions (High Priority)

1. **Fix `PyModule_AddObject()` usage**
   - Add error checking where missing
   - Fix reference counting on failure paths
   - Consider using `PyModule_AddObjectRef()` with version guards

2. **Add comprehensive error checking**
   - Ensure all `PyModule_AddObject()` calls check return value
   - Add proper cleanup on failure

### Short-term Actions (Medium Priority)

1. **Test with Python 3.13+**
   - Verify no new deprecation warnings
   - Test with `python -Werror` to catch warnings

2. **Add CI testing for Python versions 3.10-3.14**
   - Test on 3.10, 3.11, 3.12, 3.13, 3.14 (when available)
   - Use `-Werror` flag to fail on warnings

### Long-term Actions (Low Priority)

1. **Remove Python 2 compatibility code**
   - Clean up `#if PY_MAJOR_VERSION >= 3` blocks
   - Simplify code to Python 3 patterns

2. **Consider GIL implications**
   - Review for Python 3.13+ free-threaded support
   - Add documentation about thread safety

## Testing Recommendations

### Compile-time Checks

```bash
# Enable all warnings
export CFLAGS="-Wall -Wextra -Werror"
uv pip install -e .
```

### Runtime Checks

```bash
# Run with warnings as errors
python -Werror -m pytest test/

# Check for deprecation warnings
python -W default -m pytest test/ 2>&1 | grep -i deprecat
```

### Multi-version Testing

```bash
# Test on all supported Python versions
for version in 3.10 3.11 3.12 3.13; do
    echo "Testing Python $version"
    uv venv --python $version .venv-test-$version
    source .venv-test-$version/bin/activate
    uv pip install -e ".[dev]"
    pytest test/
    deactivate
done
```

## Conclusion

The python-nss C extension code is in good shape for Python 3.10-3.14
compatibility. The main issues are:

1. **HIGH - Fix `PyModule_AddObject()` reference handling** - Fix this to
   prevent potential memory leaks on error paths
2. **MEDIUM - Add missing error checks** - Some module additions don't
   check for errors

These are minor issues that don't affect normal operation but need
attention for robustness.

## References

- [What's New in Python 3.10](https://docs.python.org/3/whatsnew/3.10.html)
- [What's New in Python 3.11](https://docs.python.org/3/whatsnew/3.11.html)
- [What's New in Python 3.12](https://docs.python.org/3/whatsnew/3.12.html)
- [What's New in Python 3.13](https://docs.python.org/3/whatsnew/3.13.html)
- [Python C API Deprecations](https://docs.python.org/3/c-api/intro.html#deprecated-api)
- [PEP 620 – Hide implementation details from the C API](https://peps.python.org/pep-0620/)
- [PEP 670 – Convert macros to functions in the Python C API](https://peps.python.org/pep-0670/)

## Version History

- **2024-12-19**: Initial audit for Python 3.10-3.14 compatibility

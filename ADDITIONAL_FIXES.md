# Additional Sign Comparison Fixes

## Problem
After the initial fixes, 4 more sign comparison warnings appeared:
- Lines 11282, 11663, 12115, 24046 in src/py_nss.c

These lines compare `get_oid_tag_from_object()` return value with `(SECOidTag)-1`.

## Root Cause
The function `get_oid_tag_from_object()` returns `int`, not `SECOidTag`.
When we cast only the `-1` to `SECOidTag`, the comparison is still:
```c
int == SECOidTag  // Mismatched types!
```

## Solution
Cast the entire left side (including the assignment) to `SECOidTag`:

**Before:**
```c
if ((oid_tag = get_oid_tag_from_object(py_type)) == (SECOidTag)-1) {
```

**After:**
```c
if ((SECOidTag)(oid_tag = get_oid_tag_from_object(py_type)) == (SECOidTag)-1) {
```

## Files Changed
- src/py_nss.c: 4 lines (11282, 11663, 12115, 24046)

## Expected Result
After committing, these 4 warnings will be eliminated.

## Final Warning Count
After this fix + commit, only these warnings remain:
1. Unhandled enum values (lines 7914, 8088) - modern crypto types, need feature work
2. Linker search paths - harmless, environment-specific

Total: Down from ~15 warnings to 2 + linker warnings

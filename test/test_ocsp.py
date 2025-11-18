# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss-ng contributors

import pytest
import nss.nss as nss
from nss.error import NSPRError

#-------------------------------------------------------------------------------

# At the moment the OCSP tests are weak, we just test we can
# successfully call each of the functions.


class TestAPI:
    """Test OCSP API functionality."""

    def test_ocsp_cache(self, nss_db_context):
        nss.set_ocsp_cache_settings(100, 10, 20)
        nss.clear_ocsp_cache()

    def test_ocsp_timeout(self, nss_db_context):
        with pytest.raises(TypeError):
            nss.set_ocsp_timeout('ten')
        nss.set_ocsp_timeout(10)

    def test_ocsp_failure_mode(self, nss_db_context):
        nss.set_ocsp_failure_mode(nss.ocspMode_FailureIsVerificationFailure)
        nss.set_ocsp_failure_mode(nss.ocspMode_FailureIsNotAVerificationFailure)
        with pytest.raises(NSPRError):
            nss.set_ocsp_failure_mode(-1)

    def test_ocsp_default_responder(self, nss_db_context):
        # should raise error if cert is not known
        with pytest.raises(NSPRError):
            nss.set_ocsp_default_responder(nss_db_context, "http://foo.com:80/ocsp", 'invalid')
        nss.set_ocsp_default_responder(nss_db_context, "http://foo.com:80/ocsp", 'test_ca')
        nss.enable_ocsp_default_responder()
        nss.disable_ocsp_default_responder()
        nss.enable_ocsp_default_responder(nss_db_context)
        nss.disable_ocsp_default_responder(nss_db_context)

    def test_enable_ocsp_checking(self, nss_db_context):
        nss.enable_ocsp_checking()
        nss.disable_ocsp_checking()
        nss.enable_ocsp_checking(nss_db_context)
        nss.disable_ocsp_checking(nss_db_context)

    def test_use_pkix_for_validation(self, nss_db_context):
        # Must be boolean
        with pytest.raises(TypeError):
            nss.set_use_pkix_for_validation('true')

        value = nss.get_use_pkix_for_validation()
        assert isinstance(value, bool)

        prev = nss.set_use_pkix_for_validation(not value)
        assert isinstance(prev, bool)
        assert value == prev
        assert nss.get_use_pkix_for_validation() == (not value)

        assert nss.set_use_pkix_for_validation(value) == (not value)

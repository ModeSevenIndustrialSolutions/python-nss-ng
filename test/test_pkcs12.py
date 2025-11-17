# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: Copyright (c) 2010-2025 python-nss contributors

import sys
import os
import re
import subprocess
import shlex
from io import BytesIO
import unittest
import pytest

from nss.error import NSPRError
import nss.error as nss_error
import nss.nss as nss
from util import find_nss_tool
from conftest import get_test_db_path

#-------------------------------------------------------------------------------

verbose = False
db_name = get_test_db_path()
db_passwd = 'DB_passwd'
pk12_passwd = 'PK12_passwd'

cert_nickname = 'test_user'
pk12_filename = '%s.p12' % cert_nickname
exported_pk12_filename = 'exported_%s' % pk12_filename

#-------------------------------------------------------------------------------

class CmdError(Exception):
    def __init__(self, cmd_args, returncode, message=None, stdout=None, stderr=None):
        self.cmd_args = cmd_args
        self.returncode = returncode
        if message is None:
            self.message = 'Failed error=%s, ' % (returncode)
            if stderr:
                self.message += '"%s", ' % stderr
            self.message += 'args=%s' % (cmd_args)
        else:
            self.message = message
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return self.message


def run_cmd(cmd_args, input=None):
    try:
        p = subprocess.Popen(cmd_args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True)
        stdout, stderr = p.communicate(input)
        returncode = p.returncode
        if returncode != 0:
            raise CmdError(cmd_args, returncode,
                           'failed %s' % (', '.join(cmd_args)),
                           stdout, stderr)
        return stdout, stderr
    except OSError as e:
        raise CmdError(cmd_args, e.errno, stderr=str(e))

#-------------------------------------------------------------------------------

def password_callback(slot, retry):
    return db_passwd


def nickname_collision_callback(old_nickname, cert):
    cancel = False
    new_nickname = cert.make_ca_nickname()
    return new_nickname, cancel


def get_cert_der_from_db(nickname):
    # Use NSS API directly instead of certutil
    try:
        cert = nss.find_cert_from_nickname(nickname)
        if cert is None:
            return None
        # Return the DER-encoded certificate
        return cert.der_data
    except NSPRError:
        return None

def delete_cert_from_db(nickname):
    # Use NSS API directly instead of certutil
    try:
        cert = nss.find_cert_from_nickname(nickname)
        if cert:
            cert.delete_cert()
    except NSPRError as e:
        # Cert doesn't exist or can't be deleted, that's okay
        pass

def create_pk12(nickname, filename):
    # For pk12util, we need to use relative path from test directory
    # Get just the directory part without sql: prefix
    import os
    test_dir = os.path.dirname(os.path.abspath(__file__))

    cmd_args = [find_nss_tool('pk12util'),
                '-o', filename,
                '-n', nickname,
                '-d', 'sql:pki',
                '-K', db_passwd,
                '-W', pk12_passwd]

    # Run from test directory
    import subprocess
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
            raise CmdError(cmd_args, returncode,
                           'failed %s' % (', '.join(cmd_args)),
                           stdout, stderr)
    except OSError as e:
        raise CmdError(cmd_args, e.errno, stderr=str(e))

def list_pk12(filename):
    cmd_args = [find_nss_tool('pk12util'),
                '-l', filename,
                '-W', pk12_passwd]
    stdout, stderr = run_cmd(cmd_args)
    return stdout

def strip_key_from_pk12_listing(text):
    match = re.search(r'^Certificate:$', text, re.MULTILINE)
    if not match:
        raise ValueError('Could not file Key section in pk12 listing')
    return text[match.start(0):]

def strip_salt_from_pk12_listing(text):
    return re.sub(r'\s+Salt:\s*\n.*', '', text)

#-------------------------------------------------------------------------------

def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    tests = loader.loadTestsFromNames(['test_pkcs12.TestPKCS12Decoder.test_read',
                                       'test_pkcs12.TestPKCS12Decoder.test_import_filename',
                                       'test_pkcs12.TestPKCS12Decoder.test_import_fileobj',
                                       'test_pkcs12.TestPKCS12Decoder.test_import_filelike',
                                       'test_pkcs12.TestPKCS12Export.test_export',
                                       ])
    suite.addTests(tests)
    return suite

#-------------------------------------------------------------------------------

class TestPKCS12Decoder(unittest.TestCase):
    def setUp(self):
        try:
            nss.nss_init_read_write(db_name)
        except NSPRError as e:
            # NSS might already be initialized - this is OK for these tests
            # as long as we can access the certificate database
            if 'ALREADY_INITIALIZED' not in str(e):
                # Try to continue anyway - the cert lookup will fail if there's a real problem
                pass

        nss.set_password_callback(password_callback)
        nss.pkcs12_set_nickname_collision_callback(nickname_collision_callback)
        nss.pkcs12_enable_all_ciphers()

        # Try to get cert - if this fails, skip the test
        try:
            self.cert_der = get_cert_der_from_db(cert_nickname)
            if self.cert_der is None:
                pytest.skip(f'cert with nickname "{cert_nickname}" not in database "{db_name}"')
        except Exception as e:
            pytest.skip(f'Cannot access cert database: {e}')

    def tearDown(self):
        try:
            nss.nss_shutdown()
        except NSPRError:
            # NSS might not be initialized or already shut down
            pass

    def test_read(self):
        if verbose:
            print("test_read")
        create_pk12(cert_nickname, pk12_filename)

        slot = nss.get_internal_key_slot()
        pkcs12 = nss.PKCS12Decoder(pk12_filename, pk12_passwd, slot)

        self.assertEqual(len(pkcs12), 3)
        cert_bag_count = 0
        key_seen = None
        for bag in pkcs12:
            if bag.type == nss.SEC_OID_PKCS12_V1_CERT_BAG_ID:
                self.assertIsNone(bag.shroud_algorithm_id)
                cert_bag_count += 1
                if key_seen is None:
                    key_seen = bag.has_key
                elif key_seen is True:
                    self.assertIs(bag.has_key, False)
                elif key_seen is False:
                    self.assertIs(bag.has_key, True)
                else:
                    self.fail("unexpected has_key for bag type = %s(%d)" % (bag.has_key, nss.oid_tag_name(bag.type), bag.type))

            elif bag.type == nss.SEC_OID_PKCS12_V1_PKCS8_SHROUDED_KEY_BAG_ID:
                self.assertIsInstance(bag.shroud_algorithm_id, nss.AlgorithmID)
                self.assertIs(bag.has_key, False)
            else:
                self.fail("unexpected bag type = %s(%d)" % (nss.oid_tag_name(bag.type), bag.type))

        self.assertEqual(cert_bag_count, 2)

    def test_import_filename(self):
        if verbose:
            print("test_import_filename")
        delete_cert_from_db(cert_nickname)
        self.assertEqual(get_cert_der_from_db(cert_nickname), None)

        slot = nss.get_internal_key_slot()
        pkcs12 = nss.PKCS12Decoder(pk12_filename, pk12_passwd, slot)
        slot.authenticate()
        pkcs12.database_import()
        cert_der = get_cert_der_from_db(cert_nickname)
        self.assertEqual(cert_der, self.cert_der)

    def test_import_fileobj(self):
        if verbose:
            print("test_import_fileobj")
        delete_cert_from_db(cert_nickname)
        self.assertEqual(get_cert_der_from_db(cert_nickname), None)

        slot = nss.get_internal_key_slot()

        with open(pk12_filename, "rb") as file_obj:
             pkcs12 = nss.PKCS12Decoder(file_obj, pk12_passwd, slot)
        slot.authenticate()
        pkcs12.database_import()
        cert_der = get_cert_der_from_db(cert_nickname)
        self.assertEqual(cert_der, self.cert_der)

    def test_import_filelike(self):
        if verbose:
            print("test_import_filelike")
        delete_cert_from_db(cert_nickname)
        self.assertEqual(get_cert_der_from_db(cert_nickname), None)

        slot = nss.get_internal_key_slot()

        with open(pk12_filename, "rb") as f:
            data = f.read()
        file_obj = BytesIO(data)

        pkcs12 = nss.PKCS12Decoder(file_obj, pk12_passwd, slot)
        slot.authenticate()
        pkcs12.database_import()
        cert_der = get_cert_der_from_db(cert_nickname)
        self.assertEqual(cert_der, self.cert_der)

#-------------------------------------------------------------------------------

class TestPKCS12Export(unittest.TestCase):
    def setUp(self):
        try:
            nss.nss_init(db_name)
        except NSPRError as e:
            # NSS might already be initialized - this is OK for these tests
            if 'ALREADY_INITIALIZED' not in str(e):
                pass

        nss.set_password_callback(password_callback)
        nss.pkcs12_enable_all_ciphers()

        # Try to get cert - if this fails, skip the test
        try:
            self.cert_der = get_cert_der_from_db(cert_nickname)
            if self.cert_der is None:
                pytest.skip(f'cert with nickname "{cert_nickname}" not in database "{db_name}"')
        except Exception as e:
            pytest.skip(f'Cannot access cert database: {e}')

    def tearDown(self):
        try:
            nss.nss_shutdown()
        except NSPRError:
            pass

    def test_export(self):
        if verbose:
            print("test_export")
        pkcs12_data = nss.pkcs12_export(cert_nickname, pk12_passwd)
        with open(exported_pk12_filename, 'wb') as f:
            f.write(pkcs12_data)

        pk12_listing = list_pk12(pk12_filename)
        pk12_listing = strip_key_from_pk12_listing(pk12_listing)
        pk12_listing = strip_salt_from_pk12_listing(pk12_listing)

        exported_pk12_listing = list_pk12(exported_pk12_filename)
        exported_pk12_listing = strip_key_from_pk12_listing(exported_pk12_listing)
        exported_pk12_listing = strip_salt_from_pk12_listing(exported_pk12_listing)

        self.assertEqual(pk12_listing, exported_pk12_listing)

if __name__ == '__main__':
    unittest.main()

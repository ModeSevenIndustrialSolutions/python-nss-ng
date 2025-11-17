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
# Use absolute path for p12 file so it works from any working directory
test_dir = os.path.dirname(os.path.abspath(__file__))
pk12_filename = os.path.join(test_dir, '%s.p12' % cert_nickname)
exported_pk12_filename = os.path.join(test_dir, 'exported_%s.p12' % cert_nickname)

# Track if p12 file has been created in this session
_p12_file_created = False

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
    except NSPRError as e:
        return None

def delete_cert_from_db(nickname):
    # Use certutil to delete certificate from database
    import os
    test_dir = os.path.dirname(os.path.abspath(__file__))

    cmd_args = [find_nss_tool('certutil'),
                '-D',
                '-n', nickname,
                '-d', 'sql:pki']

    import subprocess
    try:
        p = subprocess.Popen(cmd_args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True,
                             cwd=test_dir)
        stdout, stderr = p.communicate()
        # Don't raise error if cert doesn't exist - that's okay
    except (OSError, subprocess.CalledProcessError) as e:
        # Cert doesn't exist or can't be deleted, that's okay
        pass

def create_pk12(nickname, filename):
    # For pk12util, we need to use relative path from test directory
    # Get just the directory part without sql: prefix
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # Extract just the filename if an absolute path was provided
    if os.path.isabs(filename):
        output_filename = os.path.basename(filename)
    else:
        output_filename = filename

    cmd_args = [find_nss_tool('pk12util'),
                '-o', output_filename,
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

def ensure_p12_file_exists():
    """
    Ensure the p12 file exists. Creates it if needed.
    This makes tests independent of execution order.
    """
    global _p12_file_created

    # Check if file already exists
    if os.path.exists(pk12_filename):
        return True

    # Create it
    try:
        create_pk12(cert_nickname, pk12_filename)
        _p12_file_created = True
        return True
    except Exception as e:
        if verbose:
            print(f"Failed to create p12 file: {e}")
        return False


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

@pytest.mark.forked
@pytest.mark.usefixtures("test_p12_file")
class TestPKCS12Decoder(unittest.TestCase):
    def setUp(self):
        # Initialize NSS only if not already initialized
        # Use nss_init_read_write for import tests that need to write to database
        if not nss.nss_is_initialized():
            try:
                nss.nss_init_read_write(db_name)
            except NSPRError as e:
                # If already initialized (shouldn't happen in forked process), continue
                if 'ALREADY_INITIALIZED' not in str(e):
                    raise

        nss.set_password_callback(password_callback)
        nss.pkcs12_set_nickname_collision_callback(nickname_collision_callback)
        nss.pkcs12_enable_all_ciphers()

        # Authenticate the slot before trying to find certs
        try:
            slot = nss.get_internal_key_slot()
            if slot.need_login():
                slot.authenticate()
        except Exception as e:
            pytest.skip(f'Cannot authenticate slot: {e}')

        # Try to get cert - if this fails, skip the test
        try:
            self.cert_der = get_cert_der_from_db(cert_nickname)
            if self.cert_der is None:
                pytest.skip(f'cert with nickname "{cert_nickname}" not in database "{db_name}"')
        except Exception as e:
            pytest.skip(f'Cannot access cert database: {e}')

        # p12 file should exist from test_p12_file fixture
        # Just verify it exists
        if not os.path.exists(pk12_filename):
            pytest.skip(f'p12 file does not exist: {pk12_filename}')

    def tearDown(self):
        # Shutdown NSS if initialized - each test runs in a forked process
        if nss.nss_is_initialized():
            try:
                nss.nss_shutdown()
            except NSPRError:
                # Ignore shutdown errors in forked process
                pass

    @pytest.mark.order(1)
    def test_read(self):
        if verbose:
            print("test_read")

        # File should already exist from setUp's ensure_p12_file_exists()
        # But verify it exists
        if not os.path.exists(pk12_filename):
            pytest.skip(f'p12 file does not exist: {pk12_filename}')

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

    @pytest.mark.order(10)
    def test_import_filename(self):
        if verbose:
            print("test_import_filename")

        # Delete cert so we can test import
        delete_cert_from_db(cert_nickname)

        # Verify cert is gone
        self.assertIsNone(get_cert_der_from_db(cert_nickname))

        slot = nss.get_internal_key_slot()
        pkcs12 = nss.PKCS12Decoder(pk12_filename, pk12_passwd, slot)
        slot.authenticate()
        pkcs12.database_import()
        cert_der = get_cert_der_from_db(cert_nickname)
        self.assertEqual(cert_der, self.cert_der)

    @pytest.mark.order(11)
    def test_import_fileobj(self):
        if verbose:
            print("test_import_fileobj")

        # Delete cert so we can test import
        delete_cert_from_db(cert_nickname)

        # Verify cert is gone
        self.assertIsNone(get_cert_der_from_db(cert_nickname))

        slot = nss.get_internal_key_slot()

        with open(pk12_filename, "rb") as file_obj:
             pkcs12 = nss.PKCS12Decoder(file_obj, pk12_passwd, slot)
        slot.authenticate()
        pkcs12.database_import()
        cert_der = get_cert_der_from_db(cert_nickname)
        self.assertEqual(cert_der, self.cert_der)

    @pytest.mark.order(12)
    def test_import_filelike(self):
        if verbose:
            print("test_import_filelike")

        # Delete cert so we can test import
        delete_cert_from_db(cert_nickname)

        # Verify cert is gone
        self.assertIsNone(get_cert_der_from_db(cert_nickname))

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

@pytest.mark.forked
@pytest.mark.usefixtures("test_p12_file")
class TestPKCS12Export(unittest.TestCase):
    def setUp(self):
        # Initialize NSS only if not already initialized
        if not nss.nss_is_initialized():
            try:
                nss.nss_init(db_name)
            except NSPRError as e:
                # If already initialized (shouldn't happen in forked process), continue
                if 'ALREADY_INITIALIZED' not in str(e):
                    raise

        nss.set_password_callback(password_callback)
        nss.pkcs12_enable_all_ciphers()

        # Authenticate the slot before trying to find certs
        try:
            slot = nss.get_internal_key_slot()
            if slot.need_login():
                slot.authenticate()
        except Exception as e:
            pytest.skip(f'Cannot authenticate slot: {e}')

        # Try to get cert - if this fails, skip the test
        try:
            self.cert_der = get_cert_der_from_db(cert_nickname)
            if self.cert_der is None:
                pytest.skip(f'cert with nickname "{cert_nickname}" not in database "{db_name}"')
        except Exception as e:
            pytest.skip(f'Cannot access cert database: {e}')

    def tearDown(self):
        # Shutdown NSS if initialized - each test runs in a forked process
        if nss.nss_is_initialized():
            try:
                nss.nss_shutdown()
            except NSPRError:
                # Ignore shutdown errors in forked process
                pass

    @pytest.mark.order(2)
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

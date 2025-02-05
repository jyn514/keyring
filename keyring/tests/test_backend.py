# coding: utf-8

"""
Common test functionality for backends.
"""

import string

import pytest

from .util import random_string
from keyring import errors

__metaclass__ = type

# unicode only characters
# Sourced from The Quick Brown Fox... Pangrams
# http://www.columbia.edu/~fdc/utf8/
UNICODE_CHARS = (
    "זהכיףסתםלשמועאיךתנצחקרפדעץטובבגן"
    "ξεσκεπάζωτηνψυχοφθόραβδελυγμία"
    "Съешьжеещёэтихмягкихфранцузскихбулокдавыпейчаю"
    "Жълтатадюлябешещастливачепухъткойтоцъфназамръзнакатогьон"
)

# ensure no-ascii chars slip by - watch your editor!
assert min(ord(char) for char in UNICODE_CHARS) > 127


def is_ascii_printable(s):
    return all(32 <= ord(c) < 127 for c in s)


class BackendBasicTests:
    """Test for the keyring's basic functions. password_set and password_get
    """

    DIFFICULT_CHARS = string.whitespace + string.punctuation

    @pytest.fixture(autouse=True)
    def _init_properties(self, request):
        self.keyring = self.init_keyring()
        self.credentials_created = set()
        request.addfinalizer(self.cleanup)

    def cleanup(self):
        for item in self.credentials_created:
            self.keyring.delete_password(*item)

    def set_password(self, service, username, password):
        # set the password and save the result so the test runner can clean
        #  up after if necessary.
        self.keyring.set_password(service, username, password)
        self.credentials_created.add((service, username))

    def check_set_get(self, service, username, password):
        keyring = self.keyring

        # for the non-existent password
        assert keyring.get_password(service, username) is None

        # common usage
        self.set_password(service, username, password)
        assert keyring.get_password(service, username) == password

        # for the empty password
        self.set_password(service, username, "")
        assert keyring.get_password(service, username) == ""

    def test_password_set_get(self):
        password = random_string(20)
        username = random_string(20)
        service = random_string(20)
        self.check_set_get(service, username, password)

    def test_difficult_chars(self):
        password = random_string(20, self.DIFFICULT_CHARS)
        username = random_string(20, self.DIFFICULT_CHARS)
        service = random_string(20, self.DIFFICULT_CHARS)
        self.check_set_get(service, username, password)

    def test_delete_present(self):
        password = random_string(20, self.DIFFICULT_CHARS)
        username = random_string(20, self.DIFFICULT_CHARS)
        service = random_string(20, self.DIFFICULT_CHARS)
        self.keyring.set_password(service, username, password)
        self.keyring.delete_password(service, username)
        assert self.keyring.get_password(service, username) is None

    def test_delete_not_present(self):
        username = random_string(20, self.DIFFICULT_CHARS)
        service = random_string(20, self.DIFFICULT_CHARS)
        with pytest.raises(errors.PasswordDeleteError):
            self.keyring.delete_password(service, username)

    def test_delete_one_in_group(self):
        username1 = random_string(20, self.DIFFICULT_CHARS)
        username2 = random_string(20, self.DIFFICULT_CHARS)
        password = random_string(20, self.DIFFICULT_CHARS)
        service = random_string(20, self.DIFFICULT_CHARS)
        self.keyring.set_password(service, username1, password)
        self.set_password(service, username2, password)
        self.keyring.delete_password(service, username1)
        assert self.keyring.get_password(service, username2) == password

    def test_name_property(self):
        assert is_ascii_printable(self.keyring.name)

    def test_unicode_chars(self):
        password = random_string(20, UNICODE_CHARS)
        username = random_string(20, UNICODE_CHARS)
        service = random_string(20, UNICODE_CHARS)
        self.check_set_get(service, username, password)

    def test_unicode_and_ascii_chars(self):
        source = (
            random_string(10, UNICODE_CHARS)
            + random_string(10)
            + random_string(10, self.DIFFICULT_CHARS)
        )
        password = random_string(20, source)
        username = random_string(20, source)
        service = random_string(20, source)
        self.check_set_get(service, username, password)

    def test_different_user(self):
        """
        Issue #47 reports that WinVault isn't storing passwords for
        multiple users. This test exercises that test for each of the
        backends.
        """

        keyring = self.keyring
        self.set_password('service1', 'user1', 'password1')
        self.set_password('service1', 'user2', 'password2')
        assert keyring.get_password('service1', 'user1') == 'password1'
        assert keyring.get_password('service1', 'user2') == 'password2'
        self.set_password('service2', 'user3', 'password3')
        assert keyring.get_password('service1', 'user1') == 'password1'

    def test_credential(self):
        keyring = self.keyring

        cred = keyring.get_credential('service', None)
        assert cred is None

        self.set_password('service1', 'user1', 'password1')
        self.set_password('service1', 'user2', 'password2')

        cred = keyring.get_credential('service1', None)
        assert cred is None or (cred.username, cred.password) in (
            ('user1', 'password1'),
            ('user2', 'password2'),
        )

        cred = keyring.get_credential('service1', 'user2')
        assert cred is not None
        assert (cred.username, cred.password) in (
            ('user1', 'password1'),
            ('user2', 'password2'),
        )

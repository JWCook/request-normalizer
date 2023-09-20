"""Tests for normalize_host function."""
import pytest

from url_normalize.url_normalize import normalize_host

EXPECTED_DATA = {
    "site.com": "site.com",
    "SITE.COM": "site.com",
    "site.com.": "site.com",
    "пример.испытание": "xn--e1afmkfd.xn--80akhbyknj4f",
}


@pytest.mark.parametrize("host, expected", EXPECTED_DATA.items())
def test_normalize_host_result_is_expected(host, expected):
    """Assert we got expected results from the normalize_host function."""
    assert normalize_host(host) == expected

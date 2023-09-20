"""Tests for normalize_userinfo function."""
import pytest

from url_normalize.url_normalize import normalize_userinfo

EXPECTED_DATA = {
    ":@": "",
    "": "",
    "@": "",
    "user:password@": "user:password@",
    "user@": "user@",
}


@pytest.mark.parametrize("url, expected", EXPECTED_DATA.items())
def test_normalize_userinfo_result_is_expected(url, expected):
    """Assert we got expected results from the normalize_userinfo function."""
    assert normalize_userinfo(url) == expected

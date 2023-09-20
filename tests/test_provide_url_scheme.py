"""Tests for provide_url_scheme function."""
import pytest

from url_normalize.url_normalize import provide_url_scheme

EXPECTED_DATA = {
    "": "",
    "-": "-",
    "/file/path": "/file/path",
    "//site/path": "https://site/path",
    "ftp://site/": "ftp://site/",
    "site/page": "https://site/page",
}


@pytest.mark.parametrize("url, expected", EXPECTED_DATA.items())
def test_provide_url_scheme_result_is_expected(url, expected):
    """Assert we got expected results from the provide_url_scheme function."""
    assert provide_url_scheme(url) == expected


def test_provide_url_scheme_accept_default_scheme_param():
    """Assert we could provide default_scheme param other than https."""
    url = "//site/path"
    expected = "http://site/path"
    assert provide_url_scheme(url, default_scheme="http") == expected

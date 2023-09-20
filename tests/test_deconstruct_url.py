"""Deconstruct url tests."""
import pytest

from url_normalize.tools import URL, deconstruct_url

EXPECTED_DATA = {
    "http://site.com": URL(
        fragment="",
        host="site.com",
        path="",
        port="",
        query="",
        scheme="http",
        userinfo="",
    ),
    "http://user@www.example.com:8080/path/index.html?param=val#fragment": URL(
        fragment="fragment",
        host="www.example.com",
        path="/path/index.html",
        port="8080",
        query="param=val",
        scheme="http",
        userinfo="user@",
    ),
}


@pytest.mark.parametrize("url, expected", EXPECTED_DATA.items())
def test_deconstruct_url_result_is_expected(url, expected):
    """Assert we got expected results from the deconstruct_url function."""
    assert deconstruct_url(url) == expected

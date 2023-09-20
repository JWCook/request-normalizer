"""Tests for normalize_query function."""

import pytest
from url_normalize.url_normalize import normalize_query

EXPECTED_DATA = {
    "": "",
    "param1=val1&param2=val2": "param1=val1&param2=val2",
    "Ç=Ç": "%C3%87=%C3%87",
    "%C3%87=%C3%87": "%C3%87=%C3%87",
    "q=C%CC%A7": "q=%C3%87",
}


@pytest.mark.parametrize("url, expected", EXPECTED_DATA.items())
def test_normalize_query_result_is_expected(url, expected):
    """Assert we got expected results from the normalize_query function."""
    assert normalize_query(url) == expected

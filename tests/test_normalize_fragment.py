"""Tests for normalize_fragment function."""
import pytest
from url_normalize.url_normalize import normalize_fragment

EXPECTED_DATA = {
    "": "",
    "fragment": "fragment",
    "пример": "%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80",
    "!fragment": "%21fragment",
    "~fragment": "~fragment",
}


@pytest.mark.parametrize("fragment, expected", EXPECTED_DATA.items())
def test_normalize_fragment_result_is_expected(fragment, expected):
    """Assert we got expected results from the normalize_fragment function."""
    assert normalize_fragment(fragment) == expected

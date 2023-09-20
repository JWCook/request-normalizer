"""Tests for normalize_port function."""
import pytest
from url_normalize.url_normalize import normalize_port

EXPECTED_DATA = {"8080": "8080", "": "", "80": "", "string": "string"}


@pytest.mark.parametrize("port, expected", EXPECTED_DATA.items())
def test_normalize_port_result_is_expected(port, expected):
    """Assert we got expected results from the normalize_port function."""
    assert normalize_port(port, 'http') == expected

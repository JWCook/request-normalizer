"""Tests for normalize_scheme function."""
import pytest

from url_normalize.url_normalize import normalize_scheme


@pytest.mark.parametrize("scheme", ["http", "HTTP"])
def test_normalize_scheme_result_is_expected(scheme):
    """Assert we got expected results from the normalize_scheme function."""
    assert normalize_scheme(scheme) == 'http'

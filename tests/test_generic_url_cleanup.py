"""Tests for generic_url_cleanup function."""
import pytest
from url_normalize.url_normalize import generic_url_cleanup

EXPECTED_DATA = {
    "//site/#!fragment": "//site/?_escaped_fragment_=fragment",
    "//site/?utm_source=some source&param=value": "//site/?param=value",
    "//site/?utm_source=some source": "//site/",
    "//site/?param=value&utm_source=some source": "//site/?param=value",
    "//site/page": "//site/page",
    "//site/?& ": "//site/",
}


@pytest.mark.parametrize("url, expected", EXPECTED_DATA.items())
def test_generic_url_cleanup_result_is_expected(url, expected):
    """Assert we got expected results from the generic_url_cleanup function."""
    assert generic_url_cleanup(url) == expected

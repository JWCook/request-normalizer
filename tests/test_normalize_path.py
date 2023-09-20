"""Tests for normalize_path function."""
import pytest
from url_normalize.url_normalize import normalize_path

EXPECTED_DATA = {
    "..": "/",
    "": "/",
    "/../foo": "/foo",
    "/..foo": "/..foo",
    "/./../foo": "/foo",
    "/./foo": "/foo",
    "/./foo/.": "/foo/",
    "/.foo": "/.foo",
    "/": "/",
    "/foo..": "/foo..",
    "/foo.": "/foo.",
    "/FOO": "/FOO",
    "/foo/../bar": "/bar",
    "/foo/./bar": "/foo/bar",
    "/foo//": "/foo/",
    "/foo///bar//": "/foo/bar/",
    "/foo/bar/..": "/foo/",
    "/foo/bar/../..": "/",
    "/foo/bar/../../../../baz": "/baz",
    "/foo/bar/../../../baz": "/baz",
    "/foo/bar/../../": "/",
    "/foo/bar/../../baz": "/baz",
    "/foo/bar/../": "/foo/",
    "/foo/bar/../baz": "/foo/baz",
    "/foo/bar/.": "/foo/bar/",
    "/foo/bar/./": "/foo/bar/",
}


@pytest.mark.parametrize("path, expected", EXPECTED_DATA.items())
def test_normalize_host_result_is_expected(path, expected):
    """Assert we got expected results from the normalize_path function."""
    assert normalize_path(path, "http") == expected

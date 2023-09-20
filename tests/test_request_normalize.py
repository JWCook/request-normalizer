import pytest

from request_normalize.request_normalize import (
    URL,
    deconstruct_url,
    generic_url_cleanup,
    normalize_host,
    normalize_path,
    normalize_port,
    normalize_query,
    normalize_url,
    normalize_userinfo,
    provide_url_scheme,
    reconstruct_url,
    requote,
)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("/../foo", "/foo"),
        ("/./../foo", "/foo"),
        ("/./foo", "/foo"),
        ("/./foo/.", "/foo/"),
        ("//www.foo.com/", "https://www.foo.com/"),
        ("/foo/../bar", "/bar"),
        ("/foo/./bar", "/foo/bar"),
        ("/foo//", "/foo/"),
        ("/foo///bar//", "/foo/bar/"),
        ("/foo/bar/..", "/foo/"),
        ("/foo/bar/../..", "/"),
        ("/foo/bar/../../../../baz", "/baz"),
        ("/foo/bar/../../../baz", "/baz"),
        ("/foo/bar/../../", "/"),
        ("/foo/bar/../../baz", "/baz"),
        ("/foo/bar/../", "/foo/"),
        ("/foo/bar/../baz", "/foo/baz"),
        ("/foo/bar/.", "/foo/bar/"),
        ("/foo/bar/./", "/foo/bar/"),
        ("HTTP://:@example.com/", "http://example.com/"),
        ("http://:@example.com/", "http://example.com/"),
        ("http://@example.com/", "http://example.com/"),
        ("http://127.0.0.1:80/", "http://127.0.0.1/"),
        ("http://example.com:081/", "http://example.com:81/"),
        ("http://example.com:80/", "http://example.com/"),
        ("http://example.com", "http://example.com/"),
        ("http://example.com/?b&a", "http://example.com/?a&b"),
        ("http://example.com/?q=%5c", "http://example.com/?q=%5C"),
        ("http://example.com/?q=%C7", "http://example.com/?q=%EF%BF%BD"),
        ("http://example.com/?q=C%CC%A7", "http://example.com/?q=%C3%87"),
        ("http://EXAMPLE.COM/", "http://example.com/"),
        ("http://example.com/%7Ejane", "http://example.com/~jane"),
        ("http://example.com/a/../a/b", "http://example.com/a/b"),
        ("http://example.com/a/./b", "http://example.com/a/b"),
        (
            "http://example.com/#!5753509/hello-world",
            "http://example.com/?_escaped_fragment_=5753509/hello-world",
        ),
        (
            "http://USER:pass@www.Example.COM/foo/bar",
            "http://USER:pass@www.example.com/foo/bar",
        ),
        ("http://www.example.com./", "http://www.example.com/"),
        ("http://www.foo.com:80/foo", "http://www.foo.com/foo"),
        ("http://www.foo.com.:81/foo", "http://www.foo.com:81/foo"),
        ("http://www.foo.com./foo/bar.html", "http://www.foo.com/foo/bar.html"),
        ("http://www.foo.com/foo/bar.html/../bar.html", "http://www.foo.com/bar.html"),
        ("http://www.foo.com/%7Ebar", "http://www.foo.com/~bar"),
        ("http://www.foo.com/%7ebar", "http://www.foo.com/~bar"),
        (
            "пример.испытание/Служебная:Search/Test",
            "https://xn--e1afmkfd.xn--80akhbyknj4f/%D0%A1%D0%BB%D1%83%D0%B6%D0%B5%D0%B1%D0%BD%D0%B0%D1%8F:Search/Test",
        ),
    ],
)
def test_url_normalize(url, expected):
    """Test main url_normalize function with a representative set of URLs"""
    assert normalize_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "-",
        "",
        "/..foo",
        "/.foo",
        "/foo..",
        "/foo.",
        "ftp://user:pass@ftp.foo.net/foo/bar",
        "http://127.0.0.1/",
        "http://example.com:8080/",
        "http://example.com/?a&b",
        "http://example.com/?q=%5C",
        "http://example.com/?q=%C3%87",
        "http://example.com/?q=%E2%85%A0",
        "http://example.com/",
        "http://example.com/~jane",
        "http://example.com/a/b",
        "http://example.com/FOO",
        "http://user:password@example.com/",
        "http://www.foo.com:8000/foo",
        # from rfc2396bis
        "ftp://ftp.is.co.za/rfc/rfc1808.txt",
        "http://www.ietf.org/rfc/rfc2396.txt",
        "ldap://[2001:db8::7]/c=GB?objectClass?one",
        "mailto:John.Doe@example.com",
        "news:comp.infosystems.www.servers.unix",
        "tel:+1-816-555-1212",
        "telnet://192.0.2.16:80/",
        "urn:oasis:names:specification:docbook:dtd:xml:4.1.2",
    ],
)
def test_url_normalize__no_change(url):
    """Assert url_normalize does not change URI if not required.

    http://www.intertwingly.net/wiki/pie/PaceCanonicalIds
    """
    assert normalize_url(url) == url


def test_url_normalize__with_http_scheme():
    """Assert we could use http scheme as default."""
    url = "//www.foo.com/"
    expected = "http://www.foo.com/"
    assert normalize_url(url, default_scheme="http") == expected


def test_url_normalize__with_no_params_sorting():
    """Assert we could use http scheme as default."""
    url = "http://www.foo.com/?b=1&a=2"
    expected = "http://www.foo.com/?b=1&a=2"
    assert normalize_url(url, sort_query_params=False) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "http://site.com",
            URL(
                fragment="",
                host="site.com",
                path="",
                port="",
                query="",
                scheme="http",
                userinfo="",
            ),
        ),
        (
            "http://user@www.example.com:8080/path/index.html?param=val#fragment",
            URL(
                fragment="fragment",
                host="www.example.com",
                path="/path/index.html",
                port="8080",
                query="param=val",
                scheme="http",
                userinfo="user@",
            ),
        ),
    ],
)
def test_deconstruct_url(url, expected):
    assert deconstruct_url(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            URL(
                fragment="",
                host="site.com",
                path="",
                port="",
                query="",
                scheme="http",
                userinfo="",
            ),
            "http://site.com",
        ),
        (
            URL(
                fragment="fragment",
                host="www.example.com",
                path="/path/index.html",
                port="8080",
                query="param=val",
                scheme="http",
                userinfo="user@",
            ),
            "http://user@www.example.com:8080/path/index.html?param=val#fragment",
        ),
    ],
)
def test_reconstruct_url(url, expected):
    assert reconstruct_url(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("//site/#!fragment", "//site/?_escaped_fragment_=fragment"),
        ("//site/?utm_source=some source&param=value", "//site/?param=value"),
        ("//site/?utm_source=some source", "//site/"),
        ("//site/?param=value&utm_source=some source", "//site/?param=value"),
        ("//site/page", "//site/page"),
        ("//site/?& ", "//site/"),
    ],
)
def test_generic_url_cleanup(url, expected):
    assert generic_url_cleanup(url) == expected


@pytest.mark.parametrize(
    "fragment, expected",
    [
        ("", ""),
        ("fragment", "fragment"),
        ("пример", "%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80"),
        ("!fragment", "%21fragment"),
        ("~fragment", "~fragment"),
    ],
)
def test_normalize_fragment(fragment, expected):
    assert requote(fragment, safe="~") == expected


@pytest.mark.parametrize(
    "host, expected",
    [
        ("site.com", "site.com"),
        ("SITE.COM", "site.com"),
        ("site.com.", "site.com"),
        ("пример.испытание", "xn--e1afmkfd.xn--80akhbyknj4f"),
    ],
)
def test_normalize_host(host, expected):
    assert normalize_host(host) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("..", "/"),
        ("", "/"),
        ("/../foo", "/foo"),
        ("/..foo", "/..foo"),
        ("/./../foo", "/foo"),
        ("/./foo", "/foo"),
        ("/./foo/.", "/foo/"),
        ("/.foo", "/.foo"),
        ("/", "/"),
        ("/foo..", "/foo.."),
        ("/foo.", "/foo."),
        ("/FOO", "/FOO"),
        ("/foo/../bar", "/bar"),
        ("/foo/./bar", "/foo/bar"),
        ("/foo//", "/foo/"),
        ("/foo///bar//", "/foo/bar/"),
        ("/foo/bar/..", "/foo/"),
        ("/foo/bar/../..", "/"),
        ("/foo/bar/../../../../baz", "/baz"),
        ("/foo/bar/../../../baz", "/baz"),
        ("/foo/bar/../../", "/"),
        ("/foo/bar/../../baz", "/baz"),
        ("/foo/bar/../", "/foo/"),
        ("/foo/bar/../baz", "/foo/baz"),
        ("/foo/bar/.", "/foo/bar/"),
        ("/foo/bar/./", "/foo/bar/"),
    ],
)
def test_normalize_path(path, expected):
    assert normalize_path(path, "http") == expected


@pytest.mark.parametrize(
    "port, expected",
    [
        ("8080", "8080"),
        ("", ""),
        ("80", ""),
        ("string", "string"),
    ],
)
def test_normalize_port(port, expected):
    assert normalize_port(port, 'http') == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("", ""),
        ("param1=val1&param2=val2", "param1=val1&param2=val2"),
        ("Ç=Ç", "%C3%87=%C3%87"),
        ("%C3%87=%C3%87", "%C3%87=%C3%87"),
        ("q=C%CC%A7", "q=%C3%87"),
    ],
)
def test_normalize_queryd(url, expected):
    assert normalize_query(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        (":@", ""),
        ("", ""),
        ("@", ""),
        ("user:password@", "user:password@"),
        ("user@", "user@"),
    ],
)
def test_normalize_userinfo(url, expected):
    assert normalize_userinfo(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("", ""),
        ("-", "-"),
        ("/file/path", "/file/path"),
        ("//site/path", "https://site/path"),
        ("ftp://site/", "ftp://site/"),
        ("site/page", "https://site/page"),
    ],
)
def test_provide_url_scheme_result_is_expected(url, expected):
    """Assert we got expected results from the provide_url_scheme function."""
    assert provide_url_scheme(url) == expected


def test_provide_url_scheme_accept_default_scheme_param():
    """Assert we could provide default_scheme param other than https."""
    url = "//site/path"
    expected = "http://site/path"
    assert provide_url_scheme(url, default_scheme="http") == expected

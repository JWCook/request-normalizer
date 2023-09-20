"""Url normalize tools"""
import re
import unicodedata
from collections import namedtuple
from urllib.parse import unquote as unquote_orig
from urllib.parse import urlsplit, urlunsplit

URL = namedtuple(
    "URL", ["scheme", "userinfo", "host", "port", "path", "query", "fragment"]
)


def deconstruct_url(url):
    """Tranform the url into URL structure.

    Params:
        url : string : the URL

    Returns:
        URL

    """
    scheme, auth, path, query, fragment = urlsplit(url.strip())
    (userinfo, host, port) = re.search("([^@]*@)?([^:]*):?(.*)", auth).groups()
    return URL(
        fragment=fragment,
        host=host,
        path=path,
        port=port,
        query=query,
        scheme=scheme,
        userinfo=userinfo or "",
    )


def reconstruct_url(url):
    """Reconstruct string url from URL.

    Params:
        url : URL object instance

    Returns:
        string : reconstructed url string

    """
    auth = (url.userinfo or "") + url.host
    if url.port:
        auth += ":" + url.port
    return urlunsplit((url.scheme, auth, url.path, url.query, url.fragment))


def unquote(string, charset="utf-8"):
    """Unquote and normalize unicode string.

    Params:
        string : string to be unquoted
        charset : string : optional : output encoding

    Returns:
        string : an unquoted and normalized string

    """
    string = unquote_orig(string)
    string = unicodedata.normalize("NFC", string).encode(charset)
    return string

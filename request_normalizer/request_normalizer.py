"""request-normalize main module"""
# TODO: ignore/redact params
# TODO: Handle JSON root that isn't a dict or list
# TODO: case-insensitive dict class (substitute for requests.models.CaseInsensitiveDict)
# TODO: optional support for request models from requests, aiohttp, httpx, etc.
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union
from urllib.parse import parse_qsl, quote, unquote, urlsplit, urlunsplit

import idna

KVList = List[Tuple[str, str]]
ParamList = Optional[Iterable[str]]
Headers = MutableMapping[str, str]

AUTH_PATTERN = re.compile("([^@]*@)?([^:]*):?(.*)")
DEFAULT_PORT = {
    "ftp": "21",
    "gopher": "70",
    "http": "80",
    "https": "443",
    "news": "119",
    "nntp": "119",
    "snews": "563",
    "snntp": "563",
    "telnet": "23",
    "ws": "80",
    "wss": "443",
}
DEFAULT_CHARSET = "utf-8"
DEFAULT_SCHEME = "https"


@dataclass
class URL:
    scheme: str
    userinfo: str
    host: str
    port: str
    path: str
    query: str
    fragment: str

    @classmethod
    def from_string(cls, url: str) -> 'URL':
        """Parse a URL string into its components"""
        scheme, auth, path, query, fragment = urlsplit(url.strip())
        (userinfo, host, port) = AUTH_PATTERN.search(auth).groups()
        return cls(
            fragment=fragment,
            host=host,
            path=path,
            port=port,
            query=query,
            scheme=scheme,
            userinfo=userinfo or "",
        )

    def to_string(self) -> str:
        """Recombine URL components into a string"""
        auth = self.userinfo + self.host
        if self.port:
            auth = f"{auth}:{self.port}"
        return urlunsplit((self.scheme, auth, self.path, self.query, self.fragment))


def normalize_request(
    url: str,
    headers: Optional[Headers] = None,
    body: Union[str, bytes, None] = None,
    ignore_params: ParamList = None,
    sort_params: bool = True,
) -> Tuple[str, Headers, bytes]:
    """

    Args:
        url:
        headers:
        body:
        ignore_params: Request paramters, headers, and/or JSON body params to exclude
    """
    return (
        normalize_url(url or '', sort_params, ignore_params),
        normalize_headers(headers, ignore_params),
        normalize_body(body, headers, ignore_params),
    )


def normalize_headers(headers: Optional[Headers], ignore_params: ParamList = None) -> Headers:
    """Sort and filter request headers, and normalize minor variations in multi-value headers"""
    if not headers:
        return {}
    headers = dict(sorted(_filter_mapping(headers.items(), ignore_params)))
    for k, v in headers.items():
        if ',' in v:
            values = [v.strip() for v in v.lower().split(',') if v.strip()]
            headers[k] = ', '.join(sorted(values))
    return headers
    # return CaseInsensitiveDict(headers)


def normalize_body(
    body: Union[str, bytes],
    headers: Optional[Headers] = None,
    ignore_params: ParamList = None,
) -> bytes:
    """Normalize and filter a request body if possible, depending on Content-Type"""
    if not body:
        return b''
    content_type = headers.get('Content-Type')

    # Filter and sort params if possible
    if content_type == 'application/json':
        filtered_body = normalize_json_body(body, ignore_params)
    elif content_type == 'application/x-www-form-urlencoded':
        filtered_body = normalize_query(body, ignore_params)

    return _encode(filtered_body)


def normalize_json_body(
    original_body: Union[str, bytes], ignore_params: ParamList = None
) -> Union[str, bytes]:
    """Normalize and filter a request body with serialized JSON data"""
    if len(original_body) <= 2:  # or len(original_body) > MAX_NORM_BODY_SIZE:
        return original_body

    try:
        body = json.loads(_decode(original_body))
        if isinstance(body, Mapping):
            body = dict(sorted(_filter_mapping(body.items(), ignore_params)))
        else:
            body = sorted(_filter_list(body, ignore_params))
        return json.dumps(body)
    # If it's invalid JSON, then don't mess with it
    except (AttributeError, TypeError, ValueError):
        return original_body


def normalize_url(
    url: str,
    charset: str = DEFAULT_CHARSET,
    default_scheme: str = DEFAULT_SCHEME,
    ignore_params: ParamList = None,
    sort_params: bool = True,
) -> str:
    """URI normalization routine.

    Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.
    This function can fix some of the problems in a similar way
    browsers handle data entered by the user:

    >>> url_normalize('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    Params:
        charset: The target charset for the URL if the url was given as unicode string.

    Returns:
        string : a normalized url
    """
    if not url:
        return url
    url = provide_url_scheme(url, default_scheme)
    url = generic_url_cleanup(url)
    url_parts = URL.from_string(url)

    url_parts.scheme = url_parts.scheme.lower()
    url_parts.userinfo = normalize_userinfo(url_parts.userinfo)
    url_parts.host = normalize_host(url_parts.host, charset)
    url_parts.query = normalize_query(url_parts.query, ignore_params, sort_params)
    url_parts.fragment = requote(url_parts.fragment, safe="~")
    url_parts.port = normalize_port(url_parts.port, url_parts.scheme)
    url_parts.path = normalize_path(url_parts.path, url_parts.scheme)

    return url_parts.to_string()


def provide_url_scheme(url, default_scheme=DEFAULT_SCHEME):
    """Make sure we have valid url scheme.

    Params:
        url : string : the URL
        default_scheme : string : default scheme to use, e.g. 'https'

    Returns:
        string : updated url with validated/attached scheme
    """
    has_scheme = ":" in url[:7]
    is_universal_scheme = url.startswith("//")
    is_file_path = url == "-" or (url.startswith("/") and not is_universal_scheme)
    if not url or has_scheme or is_file_path:
        return url
    if is_universal_scheme:
        return default_scheme + ":" + url
    return default_scheme + "://" + url


def generic_url_cleanup(url):
    """Cleanup the URL from unnecessary data and convert to final form.

    Converts shebang urls to final form, removed unnecessary data from the url.

    Params:
        url : string : the URL

    Returns:
        string : update url
    """
    url = url.replace("#!", "?_escaped_fragment_=")
    url = re.sub(r"utm_source=[^&]+&?", "", url)
    url = url.rstrip("&? ")
    return url


def normalize_userinfo(userinfo):
    """Normalize userinfo part of the url.

    Params:
        userinfo : string : url userinfo, e.g., 'user@'

    Returns:
        string : normalized userinfo data.
    """
    if userinfo in ["@", ":@"]:
        return ""
    return userinfo


def normalize_host(host, charset=DEFAULT_CHARSET):
    """Normalize host part of the url.

    Lowercase and strip of final dot.
    Also, take care about IDN domains.

    Params:
        host : string : url host, e.g., 'site.com'

    Returns:
        string : normalized host data.
    """
    host = host.lower()
    host = host.strip(".")
    # Skip IDN normalization for URIs that do not contain a domain name
    if '.' not in host:
        return host
    return idna.encode(host, uts46=True, transitional=True).decode(charset)


def normalize_port(port, scheme):
    """Normalize port part of the url.

    Remove mention of default port number

    Params:
        port : string : url port, e.g., '8080'
        scheme : string : url scheme, e.g., 'http'

    Returns:
        string : normalized port data.
    """
    if not port.isdigit():
        return port
    port = str(int(port))
    if DEFAULT_PORT[scheme] == port:
        return ""
    return port


def normalize_path(path, scheme):
    """Normalize path part of the url.

    Remove mention of default path number

    Params:
        path : string : url path, e.g., '/section/page.html'
        scheme : string : url scheme, e.g., 'http'

    Returns:
        string : normalized path data.
    """
    if scheme not in ["", "http", "https", "ftp", "file"]:
        return path

    # Only perform percent-encoding where it is essential.
    # Always use uppercase A-through-F characters when percent-encoding.
    # All portions of the URI must be utf-8 encoded NFC from Unicode strings
    path = requote(path)

    # Prevent dot-segments appearing in non-relative URI paths.
    output, part = [], None
    parts = path.split("/")
    last_idx = len(parts) - 1
    for idx, part in enumerate(parts):
        if part == "":
            if len(output) == 0:
                output.append(part)
        elif part == "..":
            if len(output) > 1:
                output.pop()
        elif part != "." and not (idx < last_idx and re.search(r'\.', part)):
            output.append(part)
    if part in ["", ".", ".."]:
        output.append("")
    path = "/".join(output)

    # For schemes that define an empty path to be equivalent to a path of "/", use "/".
    if scheme and not path:
        path = "/"
    return path


def normalize_query(
    query: Union[str, bytes],
    ignore_params: ParamList = None,
    sort_params: bool = True,
) -> str:
    """Normalize and filter urlencoded params from either a URL or request body with form data

    Params:
        query: url query, e.g., 'param1=val1&param2=val2'

    Returns:
        string : normalized query data.
    """
    query = _decode(query)
    query_dict = [(requote(k), requote(v)) for k, v in parse_qsl(query)]
    filtered_query = [f'{k}={v}' for k, v in _filter_mapping(query_dict, ignore_params)]

    # parse_qsl doesn't handle key-only params, so add those here
    key_only_params = [requote(k) for k in query.split('&') if k and '=' not in k]
    filtered_query += _filter_list(key_only_params, ignore_params)
    if sort_params:
        filtered_query = sorted(filtered_query)
    return '&'.join(filtered_query)


def requote(string, charset="utf-8", safe="~:/?#[]@!$&'()*+,;="):
    """Unquote and requote unicode string to normalize.

    Params:
        string : string to be unquoted
        charset : string : optional : output encoding

    Returns:
        string : an unquoted and normalized string
    """
    string = unquote(string)
    string = unicodedata.normalize("NFC", string).encode(charset)
    return quote(string, safe)


def _decode(value, encoding='utf-8') -> str:
    """Decode a value from bytes, if hasn't already been"""
    if not value:
        return ''
    return value.decode(encoding) if isinstance(value, bytes) else value


def _encode(value, encoding='utf-8') -> bytes:
    """Encode a value to bytes, if it hasn't already been"""
    if not value:
        return b''
    return value if isinstance(value, bytes) else str(value).encode(encoding)


# TODO: Option to redact or remove ignored_params
def _filter_mapping(data: KVList, ignore_params: ParamList = None) -> KVList:
    ignore_params = set(ignore_params or [])
    return [(k, 'REDACTED' if k in ignore_params else v) for k, v in data]


def _filter_list(data: List, ignore_params: ParamList = None) -> List:
    ignore_params = set(ignore_params or [])
    return [('REDACTED' if k in ignore_params else k) for k in data]

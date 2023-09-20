"""request-normalize main module"""
# TODO: case-insensitive dict class (substitute for requests.models.CaseInsensitiveDict)
# TODO: combine normalize_query and filter_url from requests-cache
# TODO: optional support for request models from requests, aiohttp, httpx, etc.
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union
from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlparse,
    urlsplit,
    urlunparse,
    urlunsplit,
)

import idna

KVList = List[Tuple[str, str]]
ParamList = Optional[Iterable[str]]
Headers = MutableMapping[str, str]

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
        (userinfo, host, port) = re.search("([^@]*@)?([^:]*):?(.*)", auth).groups()
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
        auth = (self.userinfo or "") + self.host
        if self.port:
            auth += ":" + self.port
        return urlunsplit((self.scheme, auth, self.path, self.query, self.fragment))


def normalize_request(
    url: str,
    headers: Optional[Headers] = None,
    body: Union[str, bytes, None] = None,
    ignored_parameters: ParamList = None,
    sort_query_params: bool = True,
) -> Tuple[str, Headers, bytes]:
    """

    Args:
        url:
        headers:
        body:
        ignored_parameters: Request paramters, headers, and/or JSON body params to exclude
    """
    return (
        normalize_url(url or '', sort_query_params, ignored_parameters),
        normalize_headers(headers, ignored_parameters),
        normalize_body(body, headers, ignored_parameters),
    )


def normalize_headers(headers: Optional[Headers], ignored_parameters: ParamList = None) -> Headers:
    """Sort and filter request headers, and normalize minor variations in multi-value headers"""
    if not headers:
        return {}
    if ignored_parameters:
        headers = _filter_sort_dict(headers, ignored_parameters)
    for k, v in headers.items():
        if ',' in v:
            values = [v.strip() for v in v.lower().split(',') if v.strip()]
            headers[k] = ', '.join(sorted(values))
    return headers
    # return CaseInsensitiveDict(headers)


def normalize_body(
    body: Union[str, bytes],
    headers: Optional[Headers] = None,
    ignored_parameters: ParamList = None,
) -> bytes:
    """Normalize and filter a request body if possible, depending on Content-Type"""
    if not body:
        return b''
    content_type = headers.get('Content-Type')

    # Filter and sort params if possible
    if content_type == 'application/json':
        filtered_body = normalize_json_body(body, ignored_parameters)
    elif content_type == 'application/x-www-form-urlencoded':
        filtered_body = normalize_params(body, ignored_parameters)

    return _encode(filtered_body)


def normalize_json_body(
    original_body: Union[str, bytes], ignored_parameters: ParamList
) -> Union[str, bytes]:
    """Normalize and filter a request body with serialized JSON data"""
    # if len(original_body) <= 2 or len(original_body) > MAX_NORM_BODY_SIZE:
    #     return original_body

    try:
        body = json.loads(_decode(original_body))
        body = _filter_sort_json(body, ignored_parameters)
        return json.dumps(body)
    # If it's invalid JSON, then don't mess with it
    except (AttributeError, TypeError, ValueError):
        return original_body


def normalize_url(
    url: str,
    charset: str = DEFAULT_CHARSET,
    default_scheme: str = DEFAULT_SCHEME,
    sort_query_params: bool = True,
) -> str:
    """URI normalization routine.

    Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.
    This function can fix some of the problems in a similar way
    browsers handle data entered by the user:

    >>> url_normalize('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    Params:
        charset : string : optional
            The target charset for the URL if the url was given as unicode string.

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
    url_parts.query = normalize_query(url_parts.query, sort_query_params)
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
    # Only perform percent-encoding where it is essential.
    # Always use uppercase A-through-F characters when percent-encoding.
    # All portions of the URI must be utf-8 encoded NFC from Unicode strings
    path = requote(path, safe="~:/?#[]@!$&'()*+,;=")
    # Prevent dot-segments appearing in non-relative URI paths.
    if scheme in ["", "http", "https", "ftp", "file"]:
        output, part = [], None
        parts = path.split("/")
        last_idx = len(parts) - 1
        for idx, part in enumerate(parts):
            if part == "":
                if not output:
                    output.append(part)
            elif part == ".":
                pass
            elif part == "..":
                if len(output) > 1:
                    output.pop()
            elif re.search(r'\.', part) and idx != last_idx:
                pass
            else:
                output.append(part)
        if part in ["", ".", ".."]:
            output.append("")
        path = "/".join(output)
    # For schemes that define an empty path to be equivalent to a path of "/",
    # use "/".
    if not path and scheme in ["http", "https", "ftp", "file"]:
        path = "/"
    return path


def normalize_query(
    query: str,
    sort_query_params: bool = True,
    ignored_parameters: ParamList = None,
) -> str:
    """Normalize query part of the url.

    Params:
        query : string : url query, e.g., 'param1=val1&param2=val2'

    Returns:
        string : normalized query data.
    """
    param_arr = [
        "=".join([requote(t, safe="~:/?#[]@!$'()*+,;=") for t in q.split("=", 1)])
        for q in query.split("&")
    ]
    if sort_query_params:
        param_arr = sorted(param_arr)
    query = "&".join(param_arr)
    return query


# TODO: Combine with normalize_query
def filter_url(url: str, ignored_parameters: ParamList) -> str:
    """Filter ignored parameters out of a URL"""
    # Strip query params from URL, sort and filter, and reassemble into a complete URL
    url_tokens = urlparse(url)
    return urlunparse(
        (
            url_tokens.scheme,
            url_tokens.netloc,
            url_tokens.path,
            url_tokens.params,
            normalize_params(url_tokens.query, ignored_parameters),
            url_tokens.fragment,
        )
    )


def normalize_params(value: Union[str, bytes], ignored_parameters: ParamList = None) -> str:
    """Normalize and filter urlencoded params from either a URL or request body with form data"""
    value = _decode(value)
    params = parse_qsl(value)
    params = _filter_sort_multidict(params, ignored_parameters)
    query_str = urlencode(params)

    # parse_qsl doesn't handle key-only params, so add those here
    key_only_params = [k for k in value.split('&') if k and '=' not in k]
    if key_only_params:
        key_only_param_str = '&'.join(sorted(key_only_params))
        query_str = f'{query_str}&{key_only_param_str}' if query_str else key_only_param_str

    return query_str


def requote(string, charset="utf-8", safe="/"):
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


def _filter_sort_json(data: Union[List, Mapping], ignored_parameters: ParamList):
    if isinstance(data, Mapping):
        return _filter_sort_dict(data, ignored_parameters)
    else:
        return _filter_sort_list(data, ignored_parameters)


def _filter_sort_dict(
    data: Mapping[str, str], ignored_parameters: ParamList = None
) -> Dict[str, str]:
    # Note: Any ignored_parameters present will have their values replaced instead of removing the
    # parameter, so the cache key will still match whether the parameter was present or not.
    ignored_parameters = set(ignored_parameters or [])
    return {k: ('REDACTED' if k in ignored_parameters else v) for k, v in sorted(data.items())}


def _filter_sort_multidict(data: KVList, ignored_parameters: ParamList = None) -> KVList:
    ignored_parameters = set(ignored_parameters or [])
    return [(k, 'REDACTED' if k in ignored_parameters else v) for k, v in sorted(data)]


def _filter_sort_list(data: List, ignored_parameters: ParamList = None) -> List:
    if not ignored_parameters:
        return sorted(data)
    return [k for k in sorted(data) if k not in set(ignored_parameters)]

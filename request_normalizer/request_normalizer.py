# TODO: Normalize header casing
# TODO: optional support for request models from requests, aiohttp, httpx, etc.
# TODO: Migrate unit tests for normalize_request
# TODO: LRU cache for most CPU-intensive functions
#   * IDNA encoding
#   * handling missing scheme?
#   * need to benchmark to discover others
#   * Note: urlsplit has its own internal cache
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union
from urllib.parse import parse_qsl, quote, unquote, urlsplit, urlunsplit

import idna

KVList = Iterable[Tuple[str, str]]
ParamList = Optional[Iterable[str]]
Headers = MutableMapping[str, str]

AUTH_PATTERN = re.compile(r'([^@]*@)?([^:]*):?(.*)')
DEFAULT_PORT = {
    'ftp': '21',
    'gopher': '70',
    'http': '80',
    'https': '443',
    'news': '119',
    'nntp': '119',
    'snews': '563',
    'snntp': '563',
    'telnet': '23',
    'ws': '80',
    'wss': '443',
}
PORT_LOOKUP = {v: k for k, v in reversed(DEFAULT_PORT.items())}
DEFAULT_CHARSET = 'utf-8'
DEFAULT_SCHEME = 'https'
DEFAULT_SAFE_CHARS = "!#$%&'()*+,/:;=?@[]~"


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
    def from_string(cls, url: str, default_scheme: str = DEFAULT_SCHEME) -> 'URL':
        """Parse a URL string into its components"""
        scheme, netloc, path, query, fragment = urlsplit(url)
        (userinfo, host, port) = AUTH_PATTERN.search(netloc).groups()  # type: ignore
        return cls(
            fragment=fragment,
            host=host,
            path=path,
            port=port,
            query=query,
            scheme=scheme,
            userinfo=userinfo or '',
        )

    def to_string(self) -> str:
        """Recombine URL components into a string"""
        auth = self.userinfo + self.host
        if self.port:
            auth = f'{auth}:{self.port}'
        return urlunsplit((self.scheme, auth, self.path, self.query, self.fragment))


# TODO: finalize param names and behavior
#   Alternative: ignore_params, redact_params, sort_params
#   Should ignore_params also apply to headers and body? (currently does)
#   Should sort_params also apply to headers and body? (currently doesn't)
def normalize_request(
    url: str,
    headers: Optional[Headers] = None,
    body: Union[str, bytes, None] = None,
    charset: str = DEFAULT_CHARSET,
    default_scheme: str = DEFAULT_SCHEME,
    ignore_params: ParamList = None,
    redact_ignored: bool = False,
    sort_params: bool = True,
) -> Tuple[str, Headers, bytes]:
    """Normalize and filter request components.

    Args:
        url: Request URL to normalize
        headers: Request headers to normalize
        body: Request body to normalize
        charset: The target charset for the URL if the url was given as unicode string
        default_scheme: Default scheme to use if none is provided
        ignore_params: Request parameters, headers, and/or JSON body params to exclude
        redact_ignored: Redact ignored params instead of removing them
        sort_params: Sort request parameters

    Returns:
        Normalized and filtered request URL, headers, and body
    """
    return (
        normalize_url(
            url or '', charset, default_scheme, ignore_params, sort_params, redact_ignored
        ),
        normalize_headers(headers, ignore_params, redact_ignored),
        normalize_body(body, headers, ignore_params, redact_ignored),
    )


def normalize_headers(
    headers: Optional[Headers], ignore_params: ParamList = None, redact_ignored: bool = False
) -> Headers:
    """Sort and filter request headers, and normalize minor variations in multi-value headers"""
    if not headers:
        return {}
    headers = dict(sorted(_filter_mapping(headers.items(), ignore_params, redact_ignored)))
    for k, v in headers.items():
        if ',' in v:
            values = [v.strip() for v in v.lower().split(',') if v.strip()]
            headers[k] = ', '.join(sorted(values))
    return headers
    # return CaseInsensitiveDict(headers)


def normalize_body(
    body: Union[str, bytes, None],
    headers: Optional[Headers] = None,
    ignore_params: ParamList = None,
    redact_ignored: bool = False,
) -> bytes:
    """Normalize and filter a request body if possible, depending on Content-Type"""
    if not body:
        return b''
    content_type = (headers or {}).get('Content-Type')

    # Filter and sort params if possible
    if content_type == 'application/json':
        filtered_body = normalize_json_body(body, ignore_params, redact_ignored)
    elif content_type == 'application/x-www-form-urlencoded':
        filtered_body = normalize_query(body, ignore_params, redact_ignored)

    return _encode(filtered_body)


def normalize_json_body(
    original_body: Union[str, bytes], ignore_params: ParamList = None, redact_ignored: bool = False
) -> Union[str, bytes]:
    """Normalize and filter a request body with serialized JSON data"""
    if len(original_body) <= 2:  # or len(original_body) > MAX_NORM_BODY_SIZE:
        return original_body

    try:
        body = json.loads(_decode(original_body))
        if isinstance(body, Mapping):
            body = dict(sorted(_filter_mapping(body.items(), ignore_params, redact_ignored)))
        else:
            body = sorted(_filter_list(body, ignore_params, redact_ignored))
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
    redact_ignored: bool = False,
) -> str:
    """URI normalization routine.

    Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.
    This function can fix some of the problems in a similar way
    browsers handle data entered by the user:

    Args:
        url: URL to normalize
        charset: The target charset for the URL if the url was given as unicode string
        default_scheme: Default scheme to use if none is provided
        ignore_params: Request parameters, headers, and/or JSON body params to exclude
        redact_ignored: Redact ignored params instead of removing them
        sort_params: Sort request parameters

    Returns:
        Normalized URL
    """
    if not url:
        return url
    url = url.strip().rstrip('&?')
    url = provide_url_scheme(url, default_scheme)
    url_parts = URL.from_string(url, default_scheme)

    url_parts.scheme = url_parts.scheme.lower()
    url_parts.userinfo = normalize_userinfo(url_parts.userinfo)
    url_parts.host = normalize_host(url_parts.host, charset)
    url_parts.query = normalize_query(url_parts.query, ignore_params, sort_params, redact_ignored)
    url_parts.fragment = _requote(url_parts.fragment, safe='~!/')
    url_parts.port = normalize_port(url_parts.port, url_parts.scheme)
    url_parts.path = normalize_path(url_parts.path, url_parts.scheme)

    return url_parts.to_string()


def provide_url_scheme(url: str, default_scheme: str = DEFAULT_SCHEME) -> str:
    """Update a URL if it does not contain a valid scheme."""
    has_scheme = ':' in url[:7]  # TODO: This doesn't seem sufficient
    is_universal_scheme = url.startswith('//')
    is_file_path = url == '-' or (url.startswith('/') and not is_universal_scheme)

    # Alternative:
    # First check for 'scheme://netloc' (fast), then for less common 'scheme:netloc' (~200ns slower)
    # SCHEME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
    # elif '://' in url or SCHEME_PATTERN.match(url):
    #     return url

    if not url or has_scheme or is_file_path:
        return url

    # Handle a tricky case that urlsplit doesn't parse correctly: URL with known port but no scheme
    parts = url.replace('//', '').split('/')[0].split(':')
    if len(parts) >= 2:
        port = parts[-1]
        default_scheme = PORT_LOOKUP.get(port, default_scheme)

    sep = '' if is_universal_scheme else '//'
    return f'{default_scheme}:{sep}{url}'


def normalize_userinfo(userinfo: str) -> str:
    """Normalize userinfo part of the url"""
    return '' if userinfo in ['@', ':@'] else userinfo


def normalize_host(host: str, charset: str = DEFAULT_CHARSET) -> str:
    """Normalize host part of the url: Lowercase, strip off final dot, and encode IDN domains."""
    host = host.lower()
    host = host.strip('.')
    # Skip IDN normalization for URIs that do not contain a domain name
    if '.' in host:
        host = idna.encode(host, uts46=True, transitional=True).decode(charset)
    return host


def normalize_port(port: str, scheme: str) -> str:
    """Normalize URL port: remove default port number, and strip leading zeroes."""
    if not port.isdigit():
        return port
    port = str(int(port))
    if DEFAULT_PORT.get(scheme) == port:
        port = ''
    return port


def normalize_path(path: str, scheme: str) -> str:
    """Normalize path part of the url. Remove mention of default path number."""
    if scheme not in ['', 'http', 'https', 'ftp', 'file']:
        return path

    # Only perform percent-encoding where it is essential.
    # Always use uppercase A-through-F characters when percent-encoding.
    # All portions of the URI must be utf-8 encoded NFC from Unicode strings
    path = _requote(path)

    # Prevent dot-segments appearing in non-relative URI paths.
    output: List[str] = []
    part = None
    parts = path.split('/')
    last_idx = len(parts) - 1
    for idx, part in enumerate(parts):
        if part == '':
            if len(output) == 0:
                output.append(part)
        elif part == '..':
            if len(output) > 1:
                output.pop()
        elif part != '.' and not (idx < last_idx and re.search(r'\.', part)):
            output.append(part)
    if part in ['', '.', '..']:
        output.append('')
    path = '/'.join(output)

    # For schemes that define an empty path to be equivalent to a path of '/', use '/'.
    if scheme and not path:
        path = '/'
    return path


def normalize_query(
    query: Union[str, bytes],
    ignore_params: ParamList = None,
    sort_params: bool = True,
    redact_ignored: bool = False,
) -> str:
    """Normalize and filter urlencoded params from either a URL or request body with form data."""
    query = _decode(query)
    query_dict = [(_requote(k), _requote(v)) for k, v in parse_qsl(query)]
    filtered_query = [
        f'{k}={v}' for k, v in _filter_mapping(query_dict, ignore_params, redact_ignored)
    ]

    # parse_qsl doesn't handle key-only params, so add those here
    key_only_params = [_requote(k) for k in query.split('&') if k and '=' not in k]
    filtered_query += _filter_list(key_only_params, ignore_params, redact_ignored)
    if sort_params:
        filtered_query = sorted(filtered_query)
    return '&'.join(filtered_query)


def _decode(value: Union[str, bytes], encoding: str = 'utf-8') -> str:
    """Decode a value from bytes, if hasn't already been"""
    if not value:
        return ''
    return value.decode(encoding) if isinstance(value, bytes) else value


def _encode(value: Union[str, bytes], encoding: str = 'utf-8') -> bytes:
    """Encode a value to bytes, if it hasn't already been"""
    if not value:
        return b''
    return value if isinstance(value, bytes) else str(value).encode(encoding)


def _filter_mapping(
    data: KVList, ignore_params: ParamList = None, redact_ignored: bool = False
) -> KVList:
    """Remove or redact ignored keys from a list of key-value pairs"""
    ignore_params = set(ignore_params or [])
    if redact_ignored:
        return [(k, 'REDACTED' if k in ignore_params else v) for k, v in data]
    else:
        return [(k, v) for k, v in data if k not in ignore_params]


def _filter_list(data: List, ignore_params: ParamList = None, redact_ignored: bool = False) -> List:
    """Remove or redact ignored keys from a list"""
    ignore_params = set(ignore_params or [])
    if redact_ignored:
        return [('REDACTED' if k in ignore_params else k) for k in data]
    else:
        return [k for k in data if k not in ignore_params]


def _requote(value: str, charset: str = 'utf-8', safe: str = DEFAULT_SAFE_CHARS) -> str:
    """Unquote and requote unicode string to normalize.

    Args:
        value: string to be unquoted
        charset: output encoding
        safe: Safe characters to leave unquoted
    """
    value = unquote(value)
    encoded_value = unicodedata.normalize('NFC', value).encode(charset)
    return quote(encoded_value, safe)

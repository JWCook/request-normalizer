# request-normalizer
**WIP/Incomplete**

This is a utility library that normalizes URLs and other HTTP request information. It is a fork of Nikolay Panov's [url_normalize](https://github.com/niksite/url-normalize) library, with additional features optimized for HTTP request matching.

# Installation
```sh
pip install request-normalizer
```

# Usage

URL only:
```python
>>> from request_normalizer import normalize_url
>>> normalize_url('https://EXAMPLE.COM:443/page/?user=%7Ejane&q=%5c')
'https://example.com/page/?q=%5C&user=~jane'
```

Complete request:
```python
>>> from request_normalizer import normalize_request
>>> normalize_request(
...     url='https://EXAMPLE.COM:443/page#fragment',
...     headers={'X-Test': 'test', 'accept': 'text/html', 'content-type=application/json'},
...     body=b'{"key_2": "value_2", "key_1": "value_1"}',
...     )
(
    'https://example.com/page#fragment',
    {
        'Accept': 'text/html',
        'Content-Type': 'application/json',
        'X-Test': 'test',
    },
    b'{"key_1": "value_1", "key_2": "value_2"}',
)
```

# Rules
Here is a summary of rules applied to request information:

## URI
* Encode IDN domains
* Only perform percent-encoding where it is essential
* Lowercase URI scheme and host
* Uppercase urlencoded characters (`%XX`)
* Remove dot-segments from non-relative URI paths (`site.com/path/../to/file`)
* For schemes that define a port, use an empty port if the default is desired
* For schemes that define a default authority, use an empty authority if the default is desired
* For schemes that define an empty path to be equivalent to a path of "/", use "/"
* All portions of the URI must be utf-8 encoded NFC from Unicode strings
* (Optional) Sort query parameters
* (Optional) Remove or redact specific query parameters

## Headers
* Camelcase header names (with known exceptions, e.g. `WWW-Authenticate`)
* Sort headers
* (Optional) Remove or redact specific headers

## Request body
For a request body containing JSON or form data:
* Sort keys/fields
* (Optional) Remove or redact specific keys/fields
# request-normalize
**WIP/Incomplete**

A fork of Nikolay Panov's [url_normalize](https://github.com/niksite/url-normalize) library, with additional features for HTTP request matching.

URI Normalization function:

* Take care of IDN domains.
* Always provide the URI scheme in lowercase characters.
* Always provide the host, if any, in lowercase characters.
* Only perform percent-encoding where it is essential.
* Always use uppercase A-through-F characters when percent-encoding.
* Prevent dot-segments appearing in non-relative URI paths.
* For schemes that define a default authority, use an empty authority if the default is desired.
* For schemes that define an empty path to be equivalent to a path of "/", use "/".
* For schemes that define a port, use an empty port if the default is desired
* All portions of the URI must be utf-8 encoded NFC from Unicode strings

# Installation
```sh
pip install request-normalize
```

# Usage
```python
>>> from url_normalize import url_normalize
>>> print(url_normalize('www.foo.com:80/foo'))
'https://www.foo.com/foo'
```

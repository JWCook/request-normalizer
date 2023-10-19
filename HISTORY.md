# History

## 2.0.0
* Forked from [url-normalize](https://github.com/niksite/url-normalize)
* Added additional request normalization utilities from [requests-cache](https://github.com/requests-cache/requests-cache)
* Remove support for `?_escaped_fragment_` (for deprecated google crawler feature) 
* Skip removing `utm_source` param (can be done via ignored_params if needed)

**Compatibility:**
* Remove python 2.7 support
* Add type annotations and PEP-561 compliance
* Add tests for python 3.8-3.12 and pypy 3.9-3.10
* Add more default ports for common protocols

**Bugfixes:**
* Handle case where there is a known port but no scheme
* Handle case where there is a known port but no scheme

**Internal:**
* Add CI/dev tools: pre-commit, ruff, mypy, nox, and GitHub Actions

## 1.x (url-normalize)

* 1.4.3: Added LICENSE file
* 1.4.2: Added an optional param sort_query_params (True by default)
* 1.4.1: Added an optional param default_scheme to the url_normalize ('https' by default)
* 1.4.0: A bit of code refactoring and cleanup
* 1.3.3: Support empty string and double slash urls (//domain.tld)
* 1.3.2: Same code support both Python 3 and Python 2.
* 1.3.1: Python 3 compatibility
* 1.2.1: PEP8, setup.py
* 1.1.2: support for shebang (#!) urls
* 1.1.1: using 'http' schema by default when appropriate
* 1.1.0: added handling of IDN domains
* 1.0.0: code pep8
* 0.1.0: forked from Sam Ruby's [urlnorm.py](http://intertwingly.net/blog/2004/08/04/Urlnorm)

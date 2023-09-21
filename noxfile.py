from os import getenv

import nox
from nox_poetry import session

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ['lint', 'cov']

PYTHON_VERSIONS = ['3.7', '3.8', '3.9', '3.10', '3.11', '3.12', 'pypy3.9']
DEFAULT_COVERAGE_FORMATS = ['html', 'term']


@session(python=PYTHON_VERSIONS)
def test(session):
    """Run tests in a separate virtualenv per python version"""
    session.install('.', 'pytest', 'pytest-socket')
    session.run('pytest', '-rs')


@session(python=False, name='cov')
def coverage(session):
    """Run tests and generate coverage report (in current virtualenv)"""
    cmd = ['pytest', '-rs', '--cov']

    # Add coverage formats
    cov_formats = session.posargs or DEFAULT_COVERAGE_FORMATS
    cmd += [f'--cov-report={f}' for f in cov_formats]

    # Add verbose flag, if set by environment
    if getenv('PYTEST_VERBOSE'):
        cmd += ['--verbose']
    session.run(*cmd)


@session(python=False)
def lint(session):
    """Run linters and code formatters via pre-commit"""
    session.run('pre-commit', 'run', '--all-files')

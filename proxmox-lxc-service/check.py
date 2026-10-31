#!/usr/bin/env python3
"""Read-only Proxmox inventory and HTTP access-policy checks."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


PREFLIGHT = (
    ('version', 'pveversion'),
    ('containers', 'pct list'),
    ('virtual-machines', 'qm list'),
    ('storage', 'pvesm status'),
    ('memory', 'free -m'),
    ('templates', 'pveam list local'),
    ('next-id', 'pvesh get /cluster/nextid'),
)


class CheckError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def preflight(host, timeout):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@:-]*', host):
        raise CheckError('Use an SSH alias or host, not SSH options.')
    for label, command in PREFLIGHT:
        result = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host, command],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode:
            raise CheckError(f'SSH {label} failed ({result.returncode}): {result.stderr.strip()}')
        print(f'[{label}]\n{result.stdout.strip()}')


def load_headers(filename):
    fd = os.open(Path(filename).expanduser(), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise CheckError('Use a regular credential file owned by you with mode 0600 or 0400.')
        if info.st_size > 65536:
            raise CheckError('Credential file exceeds 64 KiB.')
        data = json.load(handle)
    if not isinstance(data, dict) or not data:
        raise CheckError('Credential file must contain a nonempty JSON object of headers.')
    for name, value in data.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9!#$%&*+.^_`|~-]+', name)
                or not isinstance(value, str) or not value or '\r' in value or '\n' in value):
            raise CheckError('Credential file contains an invalid header.')
        if name.lower() not in {'authorization', 'cookie', 'x-api-key', 'api-key'}:
            raise CheckError('Only authentication headers are permitted in the credential file.')
    return data


def targets(base, paths):
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise CheckError('Use an HTTP or HTTPS base URL without credentials, query, or fragment.')
    # Force validation of the port before constructing requests.
    _ = parsed.port
    urls = []
    for path in paths:
        part = urllib.parse.urlsplit(path)
        if (not path.startswith('/') or path.startswith('//') or part.scheme or part.netloc
                or part.query or part.fragment or '\\' in path
                or any(ord(c) <= 32 or ord(c) == 127 for c in path)):
            raise CheckError('Use route paths without a host, query, fragment, or whitespace.')
        urls.append(base.rstrip('/') + path)
    return urls


def status(opener, url, headers, timeout):
    try:
        with opener.open(urllib.request.Request(url, headers=headers, method='GET'), timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        return code


def http_check(base, paths, expectation, credential_file, timeout):
    urls = targets(base, paths)
    if expectation == 'open' and credential_file:
        raise CheckError('Open-mode checks must not use a credential file.')
    headers = load_headers(credential_file) if credential_file else None
    # Do not inherit environment proxies or ambient authentication.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    for path, url in zip(paths, urls):
        code = status(opener, url, {}, timeout)
        expected = {200} if expectation == 'open' else {401, 403}
        if code not in expected:
            raise CheckError(f'{path}: no-credential request returned HTTP {code}, expected {sorted(expected)}.')
        print(f'PASS: {path} without credentials HTTP {code}')
        if headers:
            code = status(opener, url, headers, timeout)
            if code != 200:
                raise CheckError(f'{path}: authenticated request returned HTTP {code}, expected 200.')
            print(f'PASS: {path} with credentials HTTP 200')
    if expectation == 'protected' and not headers:
        print('UNVERIFIED: successful authentication (no credential file supplied).')


def positive(value):
    number = float(value)
    if not 0 < number <= 120:
        raise argparse.ArgumentTypeError('Use a timeout greater than zero and at most 120 seconds.')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inventory = commands.add_parser('preflight', help='Read host inventory through existing SSH access.')
    inventory.add_argument('--host', required=True)
    inventory.add_argument('--timeout', type=positive, default=20)
    web = commands.add_parser('http', help='Check read-only HTTP routes without redirects.')
    web.add_argument('--url', required=True)
    web.add_argument('--path', action='append', required=True)
    web.add_argument('--expect', choices=['open', 'protected'], required=True)
    web.add_argument('--credential-file')
    web.add_argument('--timeout', type=positive, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command == 'preflight':
            preflight(args.host, args.timeout)
        else:
            http_check(args.url, args.path, args.expect, args.credential_file, args.timeout)
    except (CheckError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        # Network errors can contain request details. Never print header values or bodies.
        if isinstance(error, CheckError):
            print(f'FAIL: {error}', file=sys.stderr)
        else:
            print(f'FAIL: {type(error).__name__}. Check connectivity, timeout, and input files.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

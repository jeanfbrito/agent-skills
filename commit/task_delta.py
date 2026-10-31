#!/usr/bin/env python3
"""Preserve a reviewed delta without changing source files or the Git index."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys


class Rejected(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def git(repo, *args):
    result = subprocess.run(
        ['git', '--no-optional-locks', '-C', str(repo), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(result.returncode == 0, result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout


def root(path):
    return Path(os.fsdecode(git(path, 'rev-parse', '--show-toplevel')).strip()).resolve()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path, kind):
    data = Path(path).read_bytes()
    obj = json.loads(data)
    require(isinstance(obj, dict) and obj.get('version') == 1 and obj.get('kind') == kind,
            'Invalid artifact type.')
    return obj, digest(data)


def write(path, obj, repos):
    target = Path(path).resolve()
    require(all(not target.is_relative_to(repo) for repo in repos),
            'Store artifacts outside the source and publication repositories.')
    data = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    print(f'{digest(data)}  {target}')


def paths_checked(paths):
    require(paths and len(paths) == len(set(paths)), 'Supply unique explicit paths.')
    for path in paths:
        parts = PurePosixPath(path).parts
        require(path == str(PurePosixPath(path)) and not path.startswith('/')
                and not any(p in ('.', '..', '.git') for p in parts)
                and '\\' not in path and '\n' not in path and '\r' not in path,
                'Use repository-relative file paths without traversal.')
    return sorted(paths)


def text_snapshot(mode, data):
    require(mode in ('100644', '100755'), 'Only regular text files are supported.')
    text = data.decode('utf-8')
    require('\x00' not in text, 'Binary files are not supported.')
    return {'mode': mode, 'text': text}


def working(repo, paths):
    result = {}
    for path in paths:
        file = repo / path
        require(file.resolve().is_relative_to(repo) and file.resolve() == file,
                'Symbolic links are not supported.')
        try:
            mode = file.lstat().st_mode
        except FileNotFoundError:
            result[path] = None
            continue
        require(stat.S_ISREG(mode), 'Only regular text files are supported.')
        result[path] = text_snapshot('100755' if mode & 0o111 else '100644', file.read_bytes())
    return result


def tree_file(repo, revision, path):
    listing = git(repo, 'ls-tree', '-z', revision, '--', path)
    if not listing:
        return None
    entries = listing.split(b'\0')[:-1]
    require(len(entries) == 1, 'Expected one regular file in the base.')
    info, name = entries[0].split(b'\t', 1)
    mode, kind, oid = info.decode().split()
    require(os.fsdecode(name) == path and kind == 'blob', 'Expected a file, not a directory.')
    return text_snapshot(mode, git(repo, 'cat-file', 'blob', oid))


def stable_source(baseline, expected=None):
    repo = root(baseline['repo'])
    require(str(repo) == baseline['repo'], 'The source repository changed.')
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == baseline['head'],
            'The source HEAD changed since capture.')
    paths = paths_checked(list(baseline['files']))
    current = working(repo, paths)
    if expected is not None:
        require(current == expected, 'The source changed after review.')
    require(working(repo, paths) == current, 'The source changed during the check.')
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == baseline['head'],
            'The source HEAD changed during the check.')
    return repo, current


def reviewed(path):
    review, sha = load(path, 'review')
    baseline, baseline_sha = load(review['baseline'], 'baseline')
    require(baseline_sha == review['baseline_sha256'], 'The baseline artifact changed.')
    repo, _ = stable_source(baseline, review['files'])
    require(set(baseline['files']) == set(review['files']), 'The reviewed paths changed.')
    require(baseline['files'] != review['files'], 'The task delta is empty.')
    return review, sha, baseline, repo


def capture(args):
    repo = root(args.repo)
    paths = paths_checked(args.paths)
    baseline = {'version': 1, 'kind': 'baseline', 'repo': str(repo),
                'head': git(repo, 'rev-parse', 'HEAD').decode().strip(),
                'files': working(repo, paths)}
    stable_source(baseline, baseline['files'])
    write(args.out, baseline, [repo])


def review(args):
    baseline, sha = load(args.baseline, 'baseline')
    require(args.baseline_sha256 == sha, 'The baseline digest does not match capture.')
    repo, current = stable_source(baseline)
    require(current != baseline['files'], 'The task delta is empty.')
    obj = {'version': 1, 'kind': 'review', 'baseline': str(Path(args.baseline).resolve()),
           'baseline_sha256': sha, 'files': current}
    write(args.out, obj, [repo])
    display(baseline['files'], current)


def display(before, after):
    for path in sorted(before):
        if before[path] == after[path]:
            continue
        print(f'PATH {path!r}: {before[path] and before[path]["mode"]} -> '
              f'{after[path] and after[path]["mode"]}')
        old = (before[path] or {}).get('text', '').splitlines(keepends=True)
        new = (after[path] or {}).get('text', '').splitlines(keepends=True)
        for line in difflib.unified_diff(old, new, fromfile='before/' + path, tofile='after/' + path):
            sys.stdout.write(line)
            if not line.endswith('\n'):
                sys.stdout.write('\n\\ No newline at end of file\n')


def seal(args):
    obj, sha, _, repo = reviewed(args.review)
    require(args.reviewed_sha256 == sha, 'The review digest does not match.')
    write(args.out, {'version': 1, 'kind': 'seal',
                     'review': str(Path(args.review).resolve()), 'review_sha256': sha}, [repo])


def transfer(before, after, base):
    if before is None:
        require(base is None, 'The new path already exists in the publication base.')
        return after
    if after is None:
        require(base == before, 'The deleted file differs from the reviewed baseline.')
        return None
    require(base is not None and base['mode'] == before['mode'],
            'The publication base has a different file type or mode.')
    old = before['text'].splitlines(keepends=True)
    new = after['text'].splitlines(keepends=True)
    target = base['text'].splitlines(keepends=True)
    replacements = []
    for group in difflib.SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(3):
        start, end = group[0][1], group[-1][2]
        new_start, new_end = group[0][3], group[-1][4]
        context = old[start:end]
        require(context, 'An insertion without context requires an identical base.')
        origins = [i for i in range(len(old) - len(context) + 1)
                   if old[i:i + len(context)] == context]
        require(origins == [start], 'The task delta has repeated context in the source baseline.')
        matches = [i for i in range(len(target) - len(context) + 1)
                   if target[i:i + len(context)] == context]
        require(len(matches) == 1, 'The task delta has no unique exact match in the publication base.')
        replacements.append((matches[0], matches[0] + len(context), new[new_start:new_end]))
    for left, right in zip(replacements, replacements[1:]):
        require(left[1] <= right[0], 'The publication matches overlap or change order.')
    for start, end, replacement in reversed(replacements):
        target[start:end] = replacement
    return {'mode': after['mode'], 'text': ''.join(target)}


def verify(args):
    sealed, _ = load(args.seal, 'seal')
    obj, sha, baseline, source = reviewed(sealed['review'])
    require(sha == sealed['review_sha256'], 'The reviewed artifact changed after seal.')
    publication = root(args.repo)
    head = git(publication, 'rev-parse', 'HEAD').decode().strip()
    index = git(publication, 'ls-files', '--stage', '-z')
    names = git(publication, 'diff-index', '--cached', '--no-renames', '--name-only', '-z', head)
    changed = {os.fsdecode(p) for p in names.split(b'\0') if p}
    expected_paths = {p for p in baseline['files'] if baseline['files'][p] != obj['files'][p]}
    require(changed == expected_paths, 'The staged paths do not match the task delta.')
    staged = {}
    for entry in index.split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, oid, stage = info.decode().split()
        require(stage == '0', 'The publication index has unresolved conflicts.')
        path = os.fsdecode(name)
        if path in expected_paths:
            staged[path] = text_snapshot(mode, git(publication, 'cat-file', 'blob', oid))
    for path in sorted(expected_paths):
        before, after = baseline['files'][path], obj['files'][path]
        base = tree_file(publication, head, path)
        expected = after if base == before else transfer(before, after, base)
        require(staged.get(path) == expected,
                f'The staged content includes missing or unrelated changes: {path}')
    require(index == git(publication, 'ls-files', '--stage', '-z')
            and head == git(publication, 'rev-parse', 'HEAD').decode().strip(),
            'The publication HEAD or index changed during verification.')
    stable_source(baseline, obj['files'])
    require(load(obj['baseline'], 'baseline')[1] == obj['baseline_sha256']
            and load(sealed['review'], 'review')[1] == sha,
            'An artifact changed during verification.')
    print(f'PASS: {len(expected_paths)} task paths match the staged delta at {head}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    cap = sub.add_parser('capture')
    cap.add_argument('--repo', required=True)
    cap.add_argument('--out', required=True)
    cap.add_argument('paths', nargs='+')
    rev = sub.add_parser('review')
    rev.add_argument('--baseline', required=True)
    rev.add_argument('--baseline-sha256', required=True)
    rev.add_argument('--out', required=True)
    sealer = sub.add_parser('seal')
    sealer.add_argument('--review', required=True)
    sealer.add_argument('--reviewed-sha256', required=True)
    sealer.add_argument('--out', required=True)
    verifier = sub.add_parser('verify-staged')
    verifier.add_argument('--seal', required=True)
    verifier.add_argument('--repo', required=True)
    args = parser.parse_args()
    try:
        {'capture': capture, 'review': review, 'seal': seal, 'verify-staged': verify}[args.command](args)
        return 0
    except (Rejected, OSError, ValueError, KeyError, TypeError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

"""Use synthetic Git objects and indexes. Do not run staging or commit commands."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib


SPEC = importlib.util.spec_from_file_location('task_delta', Path(__file__).parents[1] / 'task_delta.py')
delta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delta)


class TaskDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / 'source'
        self.publication = self.folder / 'publication'
        self.original = ''.join(f'line {i}\n' for i in range(30))
        self.task = self.original.replace('line 5\n', 'task change\n')
        self.baseline = self.folder / 'baseline.json'
        self.review = self.folder / 'review.json'
        self.seal = self.folder / 'seal.json'
        self.make_repo(self.source, {'file.txt': self.original})

    def object(self, repo, kind, data):
        payload = kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data
        oid = hashlib.sha1(payload).hexdigest()
        path = repo / '.git' / 'objects' / oid[:2] / oid[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zlib.compress(payload))
        return bytes.fromhex(oid)

    def make_repo(self, repo, base, staged=None):
        repo.mkdir()
        git = repo / '.git'
        (git / 'refs' / 'heads').mkdir(parents=True)
        (git / 'objects').mkdir()
        (git / 'HEAD').write_text('ref: refs/heads/task\n')
        (git / 'config').write_text('[core]\nrepositoryformatversion = 0\nbare = false\n')
        tree = b''
        for name, text in sorted(base.items()):
            tree += b'100644 ' + name.encode() + b'\0' + self.object(repo, 'blob', text.encode())
        tree_oid = self.object(repo, 'tree', tree).hex()
        commit = (f'tree {tree_oid}\nauthor Test <test@example.invalid> 1 +0000\n'
                  'committer Test <test@example.invalid> 1 +0000\n\nFixture\n').encode()
        head = self.object(repo, 'commit', commit).hex()
        (git / 'refs' / 'heads' / 'task').write_text(head + '\n')
        content = base if staged is None else staged
        self.index(repo, content)
        for name, text in content.items():
            (repo / name).write_bytes(text.encode())

    def index(self, repo, content):
        result = b'DIRC' + struct.pack('>II', 2, len(content))
        for name, text in sorted(content.items()):
            name_bytes = name.encode()
            oid = self.object(repo, 'blob', text.encode())
            entry = struct.pack('>10I20sH', 0, 0, 0, 0, 0, 0, 0o100644, 0, 0,
                                len(text.encode()), oid, len(name_bytes)) + name_bytes + b'\0'
            result += entry + b'\0' * (-len(entry) % 8)
        (repo / '.git' / 'index').write_bytes(result + hashlib.sha1(result).digest())

    def run_cli(self, *args):
        output = io.StringIO()
        with patch('sys.argv', ['task_delta.py', *map(str, args)]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = delta.main()
        return status, output.getvalue()

    def ok(self, *args):
        status, output = self.run_cli(*args)
        self.assertEqual(status, 0, output)
        return output

    def rejected(self, *args, reason):
        status, output = self.run_cli(*args)
        self.assertEqual(status, 1, output)
        self.assertIn(reason, output)

    def prepare(self, after=None):
        self.ok('capture', '--repo', self.source, '--out', self.baseline, 'file.txt')
        (self.source / 'file.txt').write_text(self.task if after is None else after)
        self.ok('review', '--baseline', self.baseline,
                '--baseline-sha256', hashlib.sha256(self.baseline.read_bytes()).hexdigest(), '--out', self.review)
        sha = hashlib.sha256(self.review.read_bytes()).hexdigest()
        self.ok('seal', '--review', self.review, '--reviewed-sha256', sha, '--out', self.seal)

    def verify(self):
        return self.run_cli('verify-staged', '--seal', self.seal, '--repo', self.publication)

    def test_clean_transfer_on_different_base_preserves_base_change(self):
        self.prepare()
        base = self.original.replace('line 25\n', 'new base change\n')
        staged = base.replace('line 5\n', 'task change\n')
        self.make_repo(self.publication, {'file.txt': base}, {'file.txt': staged})
        before = {p: p.read_bytes() for p in (self.source / 'file.txt', self.publication / 'file.txt', self.publication / '.git' / 'index')}
        status, output = self.verify()
        self.assertEqual(status, 0, output)
        self.assertIn('PASS: 1 task paths', output)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_reject_two_concerns_in_same_staged_file(self):
        self.prepare()
        unrelated = self.task.replace('line 25\n', 'unrelated concern\n')
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': unrelated})
        status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('unrelated changes', output)

    def test_preexisting_concern_is_not_published(self):
        dirty = self.original.replace('line 25\n', 'preexisting concern\n')
        (self.source / 'file.txt').write_text(dirty)
        self.prepare(dirty.replace('line 5\n', 'task change\n'))
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': self.task})
        status, output = self.verify()
        self.assertEqual(status, 0, output)
        self.index(self.publication, {'file.txt': self.task.replace('line 25\n', 'preexisting concern\n')})
        status, output = self.verify()
        self.assertEqual(status, 1, output)

    def test_source_mutation_after_review_blocks_seal(self):
        self.prepare()
        (self.source / 'file.txt').write_text(self.task + 'concurrent change\n')
        self.rejected('seal', '--review', self.review, '--reviewed-sha256', hashlib.sha256(self.review.read_bytes()).hexdigest(),
                      '--out', self.folder / 'second-seal.json', reason='source changed after review')

    def test_source_mutation_after_seal_blocks_verification(self):
        self.prepare()
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': self.task})
        (self.source / 'file.txt').write_text(self.task + 'concurrent change\n')
        status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('source changed after review', output)

    def test_mutation_during_source_read_is_rejected(self):
        real = delta.working
        calls = 0

        def mutate(repo, paths):
            nonlocal calls
            snapshot = real(repo, paths)
            calls += 1
            if calls == 2:
                (repo / 'file.txt').write_text('concurrent mutation\n')
            return snapshot

        with patch.object(delta, 'working', side_effect=mutate):
            self.rejected('capture', '--repo', self.source, '--out', self.baseline, 'file.txt', reason='source changed during')
        self.assertFalse(self.baseline.exists())

    def test_changed_baseline_is_rejected(self):
        self.prepare()
        self.baseline.write_bytes(self.baseline.read_bytes() + b' ')
        self.rejected('seal', '--review', self.review, '--reviewed-sha256', hashlib.sha256(self.review.read_bytes()).hexdigest(),
                      '--out', self.folder / 'second-seal.json', reason='baseline artifact changed')

    def test_changed_review_and_wrong_digest_are_rejected(self):
        self.prepare()
        self.rejected('seal', '--review', self.review, '--reviewed-sha256', '0' * 64,
                      '--out', self.folder / 'second-seal.json', reason='review digest does not match')
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': self.task})
        self.review.write_bytes(self.review.read_bytes() + b' ')
        status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('artifact changed after seal', output)

    def test_ambiguous_and_overlapping_base_are_rejected(self):
        self.prepare()
        self.make_repo(self.publication, {'file.txt': self.original * 2}, {'file.txt': self.task + self.original})
        status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('no unique exact match', output)
        self.assertRaises(delta.Rejected, delta.transfer,
                          {'mode': '100644', 'text': self.original},
                          {'mode': '100644', 'text': self.task},
                          {'mode': '100644', 'text': self.original.replace('line 4\n', 'base overlap\n')})

    def test_unrelated_staged_path_is_rejected(self):
        self.prepare()
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': self.task, 'other.txt': 'unrelated\n'})
        status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('staged paths do not match', output)

    def test_artifacts_do_not_run_commands_or_overwrite_source(self):
        self.ok('capture', '--repo', self.source, '--out', self.baseline, 'file.txt')
        obj = json.loads(self.baseline.read_bytes())
        marker = self.folder / 'must-not-exist'
        obj['commands'] = [f'touch {marker}']
        self.baseline.write_text(json.dumps(obj))
        (self.source / 'file.txt').write_text(self.task)
        self.ok('review', '--baseline', self.baseline,
                '--baseline-sha256', hashlib.sha256(self.baseline.read_bytes()).hexdigest(), '--out', self.review)
        self.assertFalse(marker.exists())
        self.rejected('capture', '--repo', self.source, '--out', self.source / 'file.txt', 'file.txt', reason='outside')
        self.assertEqual((self.source / 'file.txt').read_text(), self.task)
        self.rejected('capture', '--repo', self.source, '--out', self.baseline, 'file.txt', reason='File exists')

    def test_traversal_symlinks_binary_and_head_drift_are_rejected(self):
        self.rejected('capture', '--repo', self.source, '--out', self.baseline, '../outside', reason='relative file paths')
        (self.source / 'link').symlink_to(self.source / 'file.txt')
        self.rejected('capture', '--repo', self.source, '--out', self.baseline, 'link', reason='Symbolic links')
        (self.source / 'file.txt').write_bytes(b'a\0b')
        self.rejected('capture', '--repo', self.source, '--out', self.baseline, 'file.txt', reason='Binary')
        (self.source / 'file.txt').write_text(self.original)
        self.prepare()
        (self.source / '.git' / 'refs' / 'heads' / 'task').write_text('0' * 40 + '\n')
        self.rejected('seal', '--review', self.review, '--reviewed-sha256', hashlib.sha256(self.review.read_bytes()).hexdigest(),
                      '--out', self.folder / 'second-seal.json', reason='')

    def test_changed_baseline_before_review_requires_captured_digest(self):
        self.ok('capture', '--repo', self.source, '--out', self.baseline, 'file.txt')
        captured = hashlib.sha256(self.baseline.read_bytes()).hexdigest()
        self.baseline.write_bytes(self.baseline.read_bytes() + b' ')
        (self.source / 'file.txt').write_text(self.task)
        self.rejected('review', '--baseline', self.baseline, '--baseline-sha256', captured,
                      '--out', self.review, reason='baseline digest does not match capture')

    def test_publication_index_mutation_during_verification_is_rejected(self):
        self.prepare()
        self.make_repo(self.publication, {'file.txt': self.original}, {'file.txt': self.task})
        real = delta.git
        reads = 0

        def mutate(repo, *args):
            nonlocal reads
            result = real(repo, *args)
            if Path(repo).resolve() == self.publication.resolve() and args == ('ls-files', '--stage', '-z'):
                reads += 1
                if reads == 1:
                    self.index(self.publication, {'file.txt': self.task + 'concurrent index change\n'})
            return result

        with patch.object(delta, 'git', side_effect=mutate):
            status, output = self.verify()
        self.assertEqual(status, 1)
        self.assertIn('index changed during verification', output)

    def test_repeated_source_context_is_rejected(self):
        before = {'mode': '100644', 'text': ('same\n' * 20)}
        after = {'mode': '100644', 'text': 'same\n' * 5 + 'task\n' + 'same\n' * 14}
        base = {'mode': '100644', 'text': 'prefix\n' + before['text']}
        self.assertRaises(delta.Rejected, delta.transfer, before, after, base)

    def test_add_delete_and_mode_change(self):
        for before, after, base, expected in [
            (None, {'mode': '100644', 'text': 'new\n'}, None, {'mode': '100644', 'text': 'new\n'}),
            ({'mode': '100644', 'text': 'old\n'}, None, {'mode': '100644', 'text': 'old\n'}, None),
            ({'mode': '100644', 'text': 'old\n'}, {'mode': '100755', 'text': 'old\n'},
             {'mode': '100644', 'text': 'different\n'}, {'mode': '100755', 'text': 'different\n'}),
        ]:
            with self.subTest(before=before, after=after):
                self.assertEqual(delta.transfer(before, after, base), expected)


if __name__ == '__main__':
    unittest.main()

import contextlib
import http.server
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('lxc_check', Path(__file__).resolve().parents[1] / 'check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
SECRET = 'test-fixture-only-secret'


class Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Handler.seen.append((self.path, self.headers.get('Authorization')))
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/open')
        elif self.path == '/protected':
            self.send_response(200 if self.headers.get('Authorization') == 'Bearer ' + SECRET else 401)
        elif self.path == '/forbidden':
            self.send_response(403)
        elif self.path == '/open':
            self.send_response(200)
        else:
            self.send_response(500)
        self.end_headers()

    def log_message(self, *args):
        pass


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.credentials = Path(self.tmp.name) / 'headers.json'
        self.credentials.write_text(json.dumps({'Authorization': 'Bearer ' + SECRET}))
        self.credentials.chmod(0o600)
        Handler.seen.clear()

    def run_http(self, path, policy='open', credential=None):
        output = io.StringIO()
        error = io.StringIO()
        args = ['http', '--url', self.url, '--path', path, '--expect', policy]
        if credential:
            args += ['--credential-file', str(credential)]
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = check.main(args)
        text = output.getvalue() + error.getvalue()
        self.assertNotIn(SECRET, text)
        return result, text

    def test_open_access(self):
        self.assertEqual(self.run_http('/open')[0], 0)
        self.assertEqual(Handler.seen, [('/open', None)])

    def test_protected_denial_only_is_not_full_auth_proof(self):
        result, text = self.run_http('/protected', 'protected')
        self.assertEqual(result, 0)
        self.assertIn('UNVERIFIED', text)

    def test_protected_denial_and_valid_credentials(self):
        result, text = self.run_http('/protected', 'protected', self.credentials)
        self.assertEqual(result, 0)
        self.assertNotIn('UNVERIFIED', text)
        self.assertEqual(Handler.seen, [('/protected', None), ('/protected', 'Bearer ' + SECRET)])

    def test_reject_wrong_credentials(self):
        self.credentials.write_text('{"Authorization":"Bearer wrong"}')
        self.assertEqual(self.run_http('/protected', 'protected', self.credentials)[0], 1)

    def test_policy_mismatch_fails_both_directions(self):
        self.assertEqual(self.run_http('/open', 'protected')[0], 1)
        self.assertEqual(self.run_http('/protected', 'open')[0], 1)

    def test_redirect_is_not_success_and_not_followed(self):
        self.assertEqual(self.run_http('/redirect')[0], 1)
        self.assertEqual(Handler.seen, [('/redirect', None)])

    def test_redirect_does_not_receive_credentials(self):
        self.assertEqual(self.run_http('/redirect', 'protected', self.credentials)[0], 1)
        self.assertEqual(Handler.seen, [('/redirect', None)])

    def test_open_mode_rejects_credentials_before_network(self):
        self.assertEqual(self.run_http('/open', 'open', self.credentials)[0], 1)
        self.assertEqual(Handler.seen, [])

    def test_reject_world_readable_credential_file(self):
        self.credentials.chmod(0o644)
        self.assertEqual(self.run_http('/protected', 'protected', self.credentials)[0], 1)
        self.assertEqual(Handler.seen, [])

    def test_reject_symlink_credentials(self):
        link = Path(self.tmp.name) / 'link'
        link.symlink_to(self.credentials)
        self.assertEqual(self.run_http('/protected', 'protected', link)[0], 1)

    def test_reject_non_authentication_headers_and_newlines(self):
        for headers in [{'Host': 'other-host'}, {'Authorization': 'Bearer x\r\nHost: x'}, []]:
            self.credentials.write_text(json.dumps(headers))
            self.assertEqual(self.run_http('/protected', 'protected', self.credentials)[0], 1)
        self.assertEqual(Handler.seen, [])

    def test_reject_credentials_in_url(self):
        with self.assertRaises(check.CheckError):
            check.targets('http://user:password@example.test', ['/open'])

    def test_reject_cross_origin_paths_and_query_strings(self):
        for path in ['//example.test/x', 'http://example.test/x', '/x?token=secret', '/x#secret', '/x\ny', '/\\host']:
            with self.subTest(path=path), self.assertRaises(check.CheckError):
                check.targets(self.url, [path])

    def test_forbidden_is_valid_denial_and_server_error_is_not(self):
        self.assertEqual(self.run_http('/forbidden', 'protected')[0], 0)
        self.assertEqual(self.run_http('/error', 'protected')[0], 1)

    @patch.object(check.subprocess, 'run')
    def test_preflight_only_runs_fixed_read_commands(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, 'fixture', '')
        with contextlib.redirect_stdout(io.StringIO()):
            check.preflight('fixture-host', 12)
        self.assertEqual(run.call_count, len(check.PREFLIGHT))
        for call, (_, command) in zip(run.call_args_list, check.PREFLIGHT):
            self.assertEqual(call.args[0], ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'fixture-host', command])
            self.assertEqual(call.kwargs['timeout'], 12)

    @patch.object(check.subprocess, 'run')
    def test_preflight_rejects_option_injection(self, run):
        for host in ['-oProxyCommand=evil', 'host; touch x', 'host\nother']:
            with self.assertRaises(check.CheckError):
                check.preflight(host, 10)
        run.assert_not_called()

    @patch.object(check.subprocess, 'run')
    def test_preflight_stops_on_ssh_failure(self, run):
        run.return_value = subprocess.CompletedProcess([], 255, '', 'Permission denied')
        with self.assertRaisesRegex(check.CheckError, 'Permission denied'):
            check.preflight('fixture', 10)
        self.assertEqual(run.call_count, 1)

    @patch.object(check.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ssh', 1))
    def test_preflight_timeout_is_reported(self, run):
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(check.main(['preflight', '--host', 'fixture']), 1)
        self.assertIn('TimeoutExpired', output.getvalue())


if __name__ == '__main__':
    unittest.main()

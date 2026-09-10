import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

import yaml

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'worker.py'


class Catalog(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'data': [{'id': 'ms-test', 'owned_by': 'modelscope'},
                                    {'id': 'other', 'owned_by': 'openrouter'}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Catalog)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.config = self.root / 'config.yaml'
        self.config.write_text(yaml.safe_dump({
            'port': self.server.server_port, 'api-keys': ['private-fixture-token'],
            'openai-compatibility': [{
                'name': 'modelscope', 'base-url': 'https://api-inference.modelscope.ai/v1',
                'models': [{'alias': 'ms-test', 'name': 'Qwen/Test'}]
            }]
        }))
        self.brief = self.root / 'brief.txt'
        self.brief.write_text('Write only result.txt and do not run git.')
        self.fake = self.root / 'claude'
        self.fake.write_text('#!/usr/bin/env python3\nimport json,sys\n'
                             'prompt=sys.stdin.read()\n'
                             'print(json.dumps({"type":"result","subtype":"success",'
                             '"is_error":False,"num_turns":2,"result":prompt}))\n')
        self.fake.chmod(0o700)
        self.env = dict(os.environ, HOME=str(self.root), PATH=str(self.root) + os.pathsep + os.environ['PATH'])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def run_cli(self, *extra):
        return subprocess.run(['python3', str(SCRIPT), '--config', str(self.config), *extra],
                              env=self.env, text=True, capture_output=True, timeout=10)

    def dispatch(self, *extra):
        return self.run_cli('--model', 'ms-test', '--cwd', str(self.root), '--brief', str(self.brief),
                            '--log', str(self.root / 'output.json'), *extra)

    def test_lists_only_provider_aliases_without_inference(self):
        result = self.run_cli('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'ms-test\tQwen/Test\n')
        self.assertNotIn('private-fixture-token', result.stdout + result.stderr)

    def test_refuses_non_modelscope_model(self):
        result = self.run_cli('--model', 'other')
        self.assertEqual(result.returncode, 2)
        self.assertIn('no fallback', result.stderr)

    def test_yaml_error_does_not_disclose_source(self):
        self.config.write_text('api-keys: [private-fixture-token\n')
        result = self.run_cli('--list')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('private-fixture-token', result.stderr + result.stdout)

    def test_dispatch_supplies_actual_directory_and_private_log(self):
        result = self.dispatch()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / 'output.json'
        payload = json.loads(output.read_text())
        self.assertIn(str(self.root), payload['result'])
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertIn('Magicubes=unmeasured', result.stdout)
        self.assertNotIn('private-fixture-token', result.stdout + result.stderr + output.read_text())

    def test_existing_log_is_preserved(self):
        output = self.root / 'output.json'
        output.write_text('keep me')
        result = self.dispatch()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_text(), 'keep me')

    def test_timeout_is_failure_without_retry(self):
        self.fake.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n')
        result = self.dispatch('--timeout', '1')
        self.assertEqual(result.returncode, 124)
        self.assertIn('No automatic retry', result.stderr)

    def test_denial_is_failure_even_with_zero_exit(self):
        self.fake.write_text('#!/usr/bin/env python3\nimport json\n'
                             'print(json.dumps({"type":"result","subtype":"success",'
                             '"permission_denials":[{"tool_name":"Write"}]}))\n')
        result = self.dispatch()
        self.assertEqual(result.returncode, 1)
        self.assertIn('permission denial', result.stderr)


if __name__ == '__main__':
    unittest.main()

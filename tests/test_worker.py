import importlib.util
import os
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'worker.py'


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'ModelScope-only runner is missing')
        spec = importlib.util.spec_from_file_location('worker', SCRIPT)
        self.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.worker)
        self.config = {
            'port': 8317,
            'api-keys': ['fixture-local-token'],
            'openai-compatibility': [
                {'name': 'openrouter', 'models': [{'alias': 'other'}]},
                {'name': 'modelscope', 'base-url': 'https://api-inference.modelscope.ai/v1',
                 'models': [{'name': 'Qwen/Test', 'alias': 'ms-test'}]},
                {'name': 'gonka', 'models': [{'alias': 'last'}]}
            ]
        }

    def test_only_modelscope_aliases(self):
        self.assertEqual(self.worker.routing(self.config)[2], {'ms-test': 'Qwen/Test'})

    def test_reject_missing_provider(self):
        self.config['openai-compatibility'].pop(1)
        with self.assertRaises(ValueError):
            self.worker.routing(self.config)

    def test_reject_wrong_upstream(self):
        self.config['openai-compatibility'][1]['base-url'] = 'https://other.example/v1'
        with self.assertRaises(ValueError):
            self.worker.routing(self.config)

    def test_reject_duplicate_alias_across_providers(self):
        self.config['openai-compatibility'][0]['models'][0]['alias'] = 'ms-test'
        with self.assertRaises(ValueError):
            self.worker.routing(self.config)

    def test_reject_missing_local_auth(self):
        self.config['api-keys'] = []
        with self.assertRaises(ValueError):
            self.worker.routing(self.config)

    def test_environment_isolates_routing(self):
        inherited = {'PATH': '/bin', 'CLAUDECODE': '1', 'ANTHROPIC_API_KEY': 'wrong',
                     'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'other', 'CLAUDE_CONFIG_DIR': '/wrong',
                     'OPENAI_API_KEY': 'not-for-workers'}
        env = self.worker.environment(inherited, '/isolated', 8317, 'fixture-local-token', 'ms-test')
        self.assertNotIn('CLAUDECODE', env)
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertEqual(env['ANTHROPIC_DEFAULT_HAIKU_MODEL'], 'ms-test')
        self.assertEqual(env['ANTHROPIC_BASE_URL'], 'http://127.0.0.1:8317')
        self.assertEqual(env['CLAUDE_CONFIG_DIR'], '/isolated')

    def test_result_requires_real_success(self):
        self.assertFalse(self.worker.success({'is_error': False}))
        self.assertFalse(self.worker.success({'type': 'result', 'subtype': 'success', 'is_error': True}))
        self.assertFalse(self.worker.success({'type': 'result', 'subtype': 'success', 'permission_denials': ['Write']}))
        self.assertTrue(self.worker.success({'type': 'result', 'subtype': 'success', 'is_error': False}))


if __name__ == '__main__':
    unittest.main()

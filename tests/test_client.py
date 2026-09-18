import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('managed_client', ROOT / 'client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
BINDING = '11111111-1111-4111-8111-111111111111'
SHA = 'a' * 40


class ClientTests(unittest.TestCase):
    def test_collect_does_not_execute_student_code(self):
        for suffix in ('py', 'ts'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'agent').mkdir()
                for name in ('agent', 'tools'):
                    (root / 'agent' / (name + '.' + suffix)).write_text('raise RuntimeError("never execute me")')
                files = client.collect(root)
                self.assertEqual(len(files), 2)
                self.assertEqual(client.language_for(files), 'python' if suffix == 'py' else 'typescript')

    def test_rejects_symlinks_and_credential_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'agent').mkdir()
            (root / 'agent' / 'secrets.json').write_text('{}')
            with self.assertRaises(ValueError):
                client.collect(root)
            (root / 'agent' / 'secrets.json').unlink()
            (root / 'agent' / 'agent.py').symlink_to(root / 'outside.py')
            with self.assertRaises(ValueError):
                client.collect(root)

    def test_destination_allowlist_before_identity(self):
        for url in ('https://evil.example/lab/api/enterprise-ai', 'http://agentist.org', 'https://agentist.org.evil.example', 'https://agentist.org:444/lab/api/enterprise-ai'):
            with self.subTest(url=url), patch.dict(os.environ, {'HYPER_LAB_URL': url}), patch.object(client, 'github_identity') as token:
                with self.assertRaises(ValueError):
                    client.api('GET', '/v1/config')
                token.assert_not_called()

    def test_managed_configuration_and_report_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'agent').mkdir()
            for name in ('agent.py', 'tools.py'):
                (root / 'agent' / name).write_text('# student source')
            config = {'protocol': 'enterprise-ai-ci-v1', 'task': 't2', 'domain': 'retail_plus', 'language': 'python', 'case_ids': ['0', '3'], 'evaluator': {'client_revision': SHA}}
            result = {'job_id': BINDING, 'status': 'done', 'snapshot_sha256': 'fixture', 'environment_version': 'fixture', 'github': {'evaluator_sha': SHA}, 'report': {'verdict': 'passed'}}
            with patch.dict(os.environ, {'HYPER_LAB_BINDING': BINDING, 'ENTERPRISE_EVALUATOR_SHA': SHA}), patch('sys.argv', ['client.py', 'submit', '--source', 'github', '--commit', 'b' * 40, '--project', str(root), '--output', str(root / 'out')]), patch.object(client, 'api', side_effect=[config, result]) as api:
                self.assertEqual(client.main(), 0)
                payload = api.call_args_list[1].args[2]
                self.assertEqual(payload['task'], 't2')
                self.assertEqual(payload['case_ids'], ['0', '3'])
                self.assertEqual(payload['domain'], 'retail_plus')
                self.assertEqual(payload['commit_sha'], 'b' * 40)
                self.assertIn(SHA, (root / 'out' / 'report.md').read_text())
                self.assertEqual(json.loads((root / 'out' / 'report.json').read_text()), result)

    def test_wrong_revision_fails_before_reading_source(self):
        with patch.dict(os.environ, {'HYPER_LAB_BINDING': BINDING, 'ENTERPRISE_EVALUATOR_SHA': SHA}), patch('sys.argv', ['client.py', 'submit', '--source', 'github']), patch.object(client, 'api', return_value={'protocol': 'enterprise-ai-ci-v1', 'evaluator': {'client_revision': 'b' * 40}}), patch.object(client, 'collect') as collect:
            with self.assertRaises(ValueError):
                client.main()
            collect.assert_not_called()

    def test_http_errors_never_echo_credentials(self):
        from urllib.error import HTTPError
        with patch.dict(os.environ, {'HYPER_LAB_URL': 'https://agentist.org/lab/api/enterprise-ai', 'HYPER_LAB_BINDING': BINDING}), patch.object(client, 'github_identity', return_value='test-secret'), patch.object(client, 'build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://agentist.org', 401, 'test-secret', {}, None)
            with self.assertRaisesRegex(RuntimeError, '^Evaluation API returned HTTP 401$'):
                client.api('GET', '/v1/evaluations')


if __name__ == '__main__':
    unittest.main()

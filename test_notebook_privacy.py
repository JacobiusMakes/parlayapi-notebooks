"""Offline execution and network-spy tests; no real keys or API requests."""
import contextlib
import getpass
import io
import json
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

import requests
import pandas as pd

ROOT = Path(__file__).parent
NOTEBOOKS = sorted(ROOT.glob('*.ipynb'))
CANARY = 'TEST_ONLY_NOT_A_REAL_KEY'


def cells(path):
    return json.loads(path.read_text())['cells']


def run_cell(cell, namespace):
    exec(compile(''.join(cell['source']), '<notebook-cell>', 'exec'), namespace)


class Response:
    status_code = 200
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def iter_content(self, size):
        yield json.dumps(self.payload).encode()


class NotebookPrivacyTests(unittest.TestCase):
    def test_default_run_all_has_no_network_prompts_or_files(self):
        for path in NOTEBOOKS:
            with self.subTest(notebook=path.name):
                namespace = {'display': lambda *args, **kwargs: None}
                output = io.StringIO()
                with patch.dict(os.environ, {'PARLAYAPI_KEY': CANARY, 'PARLAY_API_KEY': CANARY}), \
                     patch.object(requests.sessions.Session, 'request', side_effect=AssertionError('Unexpected network')) as network, \
                     patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected socket')), \
                     patch.object(getpass, 'getpass', side_effect=AssertionError('Unexpected key prompt')) as prompt, \
                     patch.object(pd.DataFrame, 'to_csv', side_effect=AssertionError('Unexpected CSV export')), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    for cell in cells(path):
                        if cell['cell_type'] == 'code':
                            run_cell(cell, namespace)
                self.assertEqual(network.call_count, 0)
                self.assertEqual(prompt.call_count, 0)
                self.assertNotIn(CANARY, output.getvalue())
                self.assertIsNone(namespace['_runtime_key'])
                self.assertFalse(namespace['SAVE_PRIVATE_CSV'])

    def test_demo_is_explicit_anonymous_and_ignores_environment_key(self):
        for path in NOTEBOOKS:
            notebook_cells = cells(path)
            fetch = next((c for c in notebook_cells if 'def fetch_odds(' in ''.join(c['source'])), None)
            if fetch is None:
                continue
            with self.subTest(notebook=path.name):
                namespace = {'display': lambda *args: None}
                with contextlib.redirect_stdout(io.StringIO()):
                    run_cell(notebook_cells[1], namespace)
                # Compile only definitions, leaving the actual request under test explicit.
                import ast
                tree = ast.parse(''.join(fetch['source']))
                tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
                exec(compile(tree, '<fetch-definition>', 'exec'), namespace)
                namespace['MODE'] = 'demo'
                with patch.dict(os.environ, {'PARLAYAPI_KEY': CANARY, 'PARLAY_API_KEY': CANARY}), \
                     patch.object(requests, 'request', return_value=Response({'demo': True, 'events': []})) as network, \
                     patch.object(getpass, 'getpass', side_effect=AssertionError('Demo asked for key')):
                    self.assertEqual(namespace['fetch_odds'](), [])
                self.assertEqual(network.call_count, 1)
                args, kwargs = network.call_args
                self.assertTrue(args[1].startswith('https://parlay-api.com/v1/try/'))
                self.assertNotIn('X-API-Key', kwargs['headers'])
                self.assertFalse(kwargs['allow_redirects'])

    def test_account_mode_prompts_only_when_explicit_request_runs(self):
        namespace = {}
        with contextlib.redirect_stdout(io.StringIO()):
            run_cell(cells(NOTEBOOKS[0])[1], namespace)
        with patch.object(requests, 'request') as network, patch.object(getpass, 'getpass') as prompt:
            with self.assertRaises(RuntimeError):
                namespace['request_json']('/v1/sports/baseball_mlb/odds', account=True)
            network.assert_not_called()
            prompt.assert_not_called()
        namespace['MODE'] = 'account'
        with patch.object(requests, 'request', return_value=Response([])) as network, \
             patch.object(getpass, 'getpass', return_value=CANARY) as prompt:
            namespace['request_json']('/v1/sports/baseball_mlb/odds', account=True)
        prompt.assert_called_once()
        self.assertEqual(network.call_count, 1)
        args, kwargs = network.call_args
        self.assertNotIn(CANARY, args[1])
        self.assertEqual(kwargs['headers']['X-API-Key'], CANARY)
        self.assertFalse(kwargs['allow_redirects'])

    def test_error_messages_do_not_echo_provider_or_key(self):
        namespace = {}
        with contextlib.redirect_stdout(io.StringIO()):
            run_cell(cells(NOTEBOOKS[0])[1], namespace)
        namespace['MODE'] = 'account'
        namespace['_runtime_key'] = CANARY
        with patch.object(requests, 'request', side_effect=requests.RequestException('provider echoed ' + CANARY)):
            with self.assertRaises(RuntimeError) as error:
                namespace['request_json']('/v1/sports/baseball_mlb/odds', account=True)
        self.assertNotIn(CANARY, str(error.exception))
        response = Response({})
        response.status_code = 302
        with patch.object(requests, 'request', return_value=response) as network:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 302'):
                namespace['request_json']('/v1/sports/baseball_mlb/odds', account=True)
        self.assertEqual(network.call_count, 1)

    def test_published_notebooks_have_no_outputs_or_literal_keys(self):
        import ast
        for path in NOTEBOOKS:
            nb = json.loads(path.read_text())
            self.assertTrue(nb['metadata']['colab']['private_outputs'])
            for cell in nb['cells']:
                if cell['cell_type'] != 'code':
                    continue
                self.assertEqual(cell.get('outputs'), [])
                self.assertIsNone(cell.get('execution_count'))
                for node in ast.walk(ast.parse(''.join(cell['source']))):
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id in {'API_KEY', '_runtime_key'}:
                                self.assertIn(node.value.value, (None, ''))


if __name__ == '__main__':
    unittest.main()

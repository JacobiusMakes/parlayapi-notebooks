import importlib.util
import json
from pathlib import Path

import pytest
from prefect.testing.utilities import prefect_test_harness
from prefect.client.orchestration import get_client

spec = importlib.util.spec_from_file_location('coverage_flow', Path(__file__).with_name('coverage_flow.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_real_prefect_flow_synthetic_and_private_failure(monkeypatch, caplog):
    monkeypatch.setattr(m.client, 'fetch', lambda *a: pytest.fail('demo performed network'))
    with prefect_test_harness():
        result = m.coverage_flow()
        assert result['synthetic'] and result['status'] == 'observed'
        assert len(result['groups']) == 3
        assert 'Example Fighter' not in json.dumps(result)
        secret = 'private-test-key-do-not-log'
        monkeypatch.setenv('PARLAY_API_KEY', secret)
        def failure(key):
            assert key == secret
            raise ValueError(secret + ' private raw payload')
        monkeypatch.setattr(m.client, 'fetch', failure)
        result = m.coverage_flow(live=True)
        assert result == {'status': 'error', 'synthetic': False, 'groups': []}
        assert secret not in caplog.text and 'private raw payload' not in caplog.text
        with get_client(sync_client=True) as api:
            runs = api.read_flow_runs(limit=10)
            tasks = api.read_task_runs(limit=10)
            metadata = json.dumps([r.model_dump(mode='json') for r in [*runs, *tasks]])
        assert len(runs) == 2 and len(tasks) == 2
        assert all(set(r.parameters) <= {'live'} for r in runs)
        for forbidden in (secret, 'private raw payload', 'Example Fighter', 'synthetic-example'):
            assert forbidden not in metadata
        assert all(t.state.data is None for t in tasks)
    assert m.coverage_summary.persist_result is False
    assert m.coverage_flow.persist_result is False
    assert m.coverage_summary.retries == m.coverage_flow.retries == 0


def test_empty_and_incomplete_differ(monkeypatch):
    monkeypatch.setattr(m.client, 'fetch', lambda *a: [])
    assert m.private_summary(True)['status'] == 'empty'
    def incomplete(*a): raise m.IncompleteResponse()
    monkeypatch.setattr(m.client, 'fetch', incomplete)
    assert m.private_summary(True)['status'] == 'incomplete'


def test_semantics_and_label_disagreement_preserved(monkeypatch):
    now = m.datetime.now(m.timezone.utc)
    rows = m.client.demo(now)
    rows[0]['player'] = 'Private mismatch name'
    monkeypatch.setattr(m.client, 'fetch', lambda *a: rows)
    result = m.private_summary(True)
    assert result['status'] == 'observed'
    assert sum(g['fighter_label_mismatches'] for g in result['groups']) == 1
    assert 'Private mismatch name' not in json.dumps(result)
    assert {g['method'] for g in result['groups']} >= {'method_of_victory_ko_tko','method_of_victory_ko_tko_dq'}


@pytest.mark.parametrize('truncated,has_more', [('true','false'),('unknown','false'),(None,None),(None,'true')])
def test_header_guard_rejects_incomplete(monkeypatch,truncated,has_more):
    class Response:
        status = 200
        def getheader(self,key):
            return {'x-result-truncated':truncated,'x-result-has-more':has_more}.get(key)
    monkeypatch.setattr(m.http.client.HTTPSConnection,'getresponse',lambda *a:Response())
    with pytest.raises(m.IncompleteResponse):m.GuardedConnection('example.invalid').getresponse()


@pytest.mark.parametrize('status,headers,expected', [
    (401, {}, 'error'), (429, {}, 'error'),
    (200, {}, 'incomplete'),
    (200, {'x-result-has-more': 'false', 'x-result-truncated': 'False',
           'Content-Type': 'application/json'}, 'empty'),
])
def test_real_client_status_classification(monkeypatch, status, headers, expected):
    class Response:
        def getheader(self, key): return headers.get(key)
        def read1(self, size):
            result, self.body = self.body, b''
            return result
    response = Response()
    response.status, response.body = status, b'[]'
    monkeypatch.setenv('PARLAY_API_KEY', 'private-test-key')
    monkeypatch.setattr(m.http.client.HTTPSConnection, 'request', lambda *a, **k: None)
    monkeypatch.setattr(m.http.client.HTTPSConnection, 'getresponse', lambda *a: response)
    assert m.private_summary(True)['status'] == expected

"""One-shot private coverage flow: orchestration sees summaries only."""
from datetime import datetime, timezone
import http.client
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

from prefect import flow, task
from prefect.cache_policies import NO_CACHE

PATH = Path(__file__).resolve().parents[2] / 'labs/ufc-methods/ufc_methods.py'
spec = importlib.util.spec_from_file_location('private_ufc_client', PATH)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class IncompleteResponse(Exception):
    pass


class GuardedConnection(http.client.HTTPSConnection):
    def getresponse(self):
        response = super().getresponse()
        truncated = response.getheader('x-result-truncated')
        if response.status == 200 and (
                (truncated is not None and truncated.lower() != 'false')
                or (response.getheader('x-result-has-more') or '').lower() != 'false'):
            raise IncompleteResponse()
        return response


# Isolated module namespace; do not mutate Python's shared http.client module.
client.http = SimpleNamespace(client=SimpleNamespace(HTTPSConnection=GuardedConnection))


def private_summary(live=False):
    """Raw payload/key stay in ordinary local variables, never task arguments."""
    try:
        now = datetime.now(timezone.utc)
        if live:
            payload = client.fetch(os.environ.get('PARLAY_API_KEY', ''))
            now = datetime.now(timezone.utc)
        else:
            payload = client.demo(now)
        summaries = client.summarize(payload, now=now)
        return {'status': 'observed' if summaries else 'empty',
                'synthetic': not live, 'groups': summaries}
    except IncompleteResponse:
        return {'status': 'incomplete', 'synthetic': not live, 'groups': []}
    except Exception:
        # No exception text/traceback escapes into orchestration or persisted state.
        return {'status': 'error', 'synthetic': not live, 'groups': []}


@task(name='private-coverage-summary', retries=0, persist_result=False,
      cache_policy=NO_CACHE, log_prints=False)
def coverage_summary(live: bool = False):
    return private_summary(live)


@flow(name='private-sports-coverage', retries=0, persist_result=False, log_prints=False)
def coverage_flow(live: bool = False):
    return coverage_summary(live)


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Explicitly make one own-key request')
    args = parser.parse_args()
    print(json.dumps(coverage_flow(live=args.live), indent=2))

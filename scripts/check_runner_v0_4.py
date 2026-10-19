"""Offline integration tests for the existing runner; no official task access."""

from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
from approval_gate.offline import no_network


def run_checks():
    (ROOT / 'results/raw').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='runner_v0_4_checks_', dir=ROOT/'results/raw'))
    with ExitStack() as stack:
        stack.enter_context(no_network())
        for target in ('approval_gate.completions.live_client', 'approval_gate.task_runner.live_client',
                       'dotenv.dotenv_values', 'dotenv.load_dotenv', 'approval_gate.task_runner.load_task'):
            stack.enter_context(patch(target, side_effect=AssertionError('Live clients, keys and official task loading disabled.')))
        import httpx
        import openai
        from approval_gate import completions
        sdk_factory, sdk_class = completions._sdk_client, openai.OpenAI
        def local_sdk(api_key, base_url, timeout_seconds, transport=None):
            if not isinstance(transport, httpx.MockTransport) or api_key != 'offline-dummy-key' or base_url != 'https://offline.invalid/v1':
                raise AssertionError('Only existing dummy-key HTTP mock clients may be constructed.')
            return sdk_factory(api_key, base_url, timeout_seconds, transport=transport)
        def guarded_class(*args, **kwargs):
            transport = getattr(kwargs.get('http_client'), '_transport', None)
            if not isinstance(transport, httpx.MockTransport):
                raise AssertionError('Real transport clients are disabled.')
            return sdk_class(*args, **kwargs)
        stack.enter_context(patch('approval_gate.completions._sdk_client', side_effect=local_sdk))
        stack.enter_context(patch('openai.OpenAI', side_effect=guarded_class))
        stack.enter_context(patch('openai.AsyncOpenAI', side_effect=AssertionError('Async clients disabled.')))
        from agentdojo.task_suite.load_suites import get_suite
        suite = get_suite('v1.2.2','workspace')
        for name in ('user_tasks','injection_tasks'):
            stack.enter_context(patch.object(type(suite), name, new_callable=PropertyMock,
                side_effect=AssertionError('Official task and attack object access disabled.')))
        for name in ('_check_user_task_utility','_check_injection_task_security'):
            stack.enter_context(patch.object(suite,name,side_effect=AssertionError('Official scoring disabled.')))
        tests = unittest.TestSuite()
        integration = importlib.import_module('test_runner_v0_4_independent')
        integration.ARTIFACT_ROOT = directory
        tests.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('test_approval_gate')))
        tests.addTests(unittest.defaultTestLoader.loadTestsFromModule(integration))
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
        summary = {'record_type':'Independent-request mock integration through the existing runner; no benchmark scoring',
                   'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'policy_version':'file-rules-v0.4.0',
                   'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                   'successful':result.wasSuccessful(),'modules':['test_approval_gate','test_runner_v0_4_independent'],
                   'all_official_tools_retained':len(suite.tools), 'network_disabled':True,
                   'real_clients_and_key_loaders_disabled':True, 'existing_sdk_local_mock_transport_only':True,
                   'official_task_loading_and_properties_blocked':True,'official_evaluators_blocked':True,
                   'real_model_api_requests':0,'actual_provider_usage_or_cost_obtained':False,
                   'observations':integration.OBSERVATIONS, 'raw_directory':str(directory.relative_to(ROOT)),
                   'excluded':['Full test discovery','Legacy official-task runner/spending/timeout cases',
                               'All official request/gold/checker and coverage probes','All attack-preparation entry points'],
                   'source_sha256':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
                                    for p in (ROOT/'src/approval_gate').glob('*.py')}}
    (directory/'tests.txt').write_text(stream.getvalue())
    with (directory/'summary.json').open('x') as out:
        json.dump(summary,out,indent=2);out.write('\n')
    print(stream.getvalue(),end='')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_sha256','observations')},indent=2))
    return summary


if __name__=='__main__':
    raise SystemExit(0 if run_checks()['successful'] else 1)

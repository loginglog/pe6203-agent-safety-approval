"""Run only scoped file/gate checks; never collect task/attack runner suites."""

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
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]

from approval_gate.offline import no_network


def run_checks():
    (ROOT / 'results/raw').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='file_rules_v0_4_checks_', dir=ROOT / 'results/raw'))
    skipped = ['test_file_policy_v0_3_1.FilePolicyV031Tests.test_task28_original_is_a_development_regression_not_a_whitelist']
    modules = ('test_approval_gate', 'test_approval_policies', 'test_file_policy_v0_3',
               'test_file_policy_v0_3_1', 'test_file_policy_v0_4')
    with ExitStack() as stack:
        stack.enter_context(no_network())
        for target in ('openai.OpenAI', 'approval_gate.completions.live_client',
                       'approval_gate.task_runner.live_client', 'dotenv.dotenv_values', 'dotenv.load_dotenv'):
            stack.enter_context(patch(target, side_effect=AssertionError('Clients/credentials disabled.')))
        from agentdojo.task_suite.load_suites import get_suite
        suite = get_suite('v1.2.2', 'workspace')
        for name in ('user_tasks', 'injection_tasks'):
            stack.enter_context(patch.object(type(suite), name, new_callable=PropertyMock,
                side_effect=AssertionError('Official task/attack access is disabled.')))
        for name in ('_check_user_task_utility', '_check_injection_task_security'):
            stack.enter_context(patch.object(suite, name, side_effect=AssertionError('Evaluators disabled.')))
        selected = unittest.TestSuite()
        def collect(item):
            if isinstance(item, unittest.TestSuite):
                for child in item:
                    collect(child)
            elif item.id() not in skipped:
                selected.addTest(item)
        for module in modules:
            loaded = importlib.import_module(module)
            if module == 'test_file_policy_v0_4':
                def save_body_check(record):
                    with (directory / 'body_checks.jsonl').open('a') as output:
                        output.write(json.dumps(record) + '\n')
                loaded.ARTIFACT_SINK = save_body_check
            collect(unittest.defaultTestLoader.loadTestsFromModule(loaded))
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(selected)
        print(stream.getvalue(), end='')
        from approval_gate.policies import CandidateFilePolicy as Current
        from approval_gate.file_policy_v0_4 import CandidateFilePolicy
        summary = {'type': 'Scoped offline fixture/unit checks, not model behavior or TCR@k',
                   'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                   'policy_under_test': CandidateFilePolicy.version, 'current_selector': Current.version,
                   'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                   'successful': result.wasSuccessful(), 'modules': list(modules),
                   'excluded_method': skipped,
                   'excluded_entry_points': ['Complete discovery suite', 'Task/reviewer/model/spend/timeout/attack runner suites',
                       'All historical task-coverage and task29 demos; all official-task or attack-preparation probes'],
                   'exclusion_reason': 'Restrict this change to file/gate fixtures; no official requests/answers/evaluators or restricted preparation.',
                   'network_disabled': True, 'clients_and_key_loaders_disabled': True,
                   'official_user_and_attack_tasks_access_blocked': True,
                   'all_official_tools_retained': len(suite.tools), 'model_api_requests': 0,
                   'examples_sha256': sha256((ROOT/'configs/file_rule_examples_v0_4.json').read_bytes()).hexdigest(),
                   'raw_directory': str(directory.relative_to(ROOT))}
    (directory / 'tests.txt').write_text(stream.getvalue())
    with (directory / 'summary.json').open('x') as output:
        json.dump(summary, output, indent=2)
        output.write('\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    raise SystemExit(0 if run_checks()['successful'] else 1)

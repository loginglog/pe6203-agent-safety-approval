"""Guarded synthetic snapshot/ledger checks; no real task or model inference."""

from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]
from approval_gate.offline import no_network


def main():
    directory = Path(tempfile.mkdtemp(prefix="supplementary_observer_checks_", dir=ROOT / "results/raw"))
    with ExitStack() as stack:
        stack.enter_context(no_network())
        for target in ("approval_gate.completions.live_client", "approval_gate.task_runner.live_client", "dotenv.dotenv_values", "dotenv.load_dotenv", "run_supplementary_normal.live_client", "approval_gate.task_runner.load_task"):
            stack.enter_context(patch(target, side_effect=AssertionError("Live clients, keys and official task loading disabled")))
        import httpx
        import openai
        from approval_gate import completions
        sdk_factory, sdk_class = completions._sdk_client, openai.OpenAI
        def local_sdk(api_key, base_url, timeout_seconds, transport=None):
            if not isinstance(transport, httpx.MockTransport) or api_key != "offline-dummy-key" or base_url != "https://offline.invalid/v1":
                raise AssertionError("Only existing dummy-key HTTP mocks permitted")
            return sdk_factory(api_key, base_url, timeout_seconds, transport=transport)
        def guarded_class(*args, **kwargs):
            if not isinstance(getattr(kwargs.get("http_client"), "_transport", None), httpx.MockTransport):
                raise AssertionError("Real clients disabled")
            return sdk_class(*args, **kwargs)
        stack.enter_context(patch("approval_gate.completions._sdk_client", side_effect=local_sdk))
        stack.enter_context(patch("openai.OpenAI", side_effect=guarded_class))
        stack.enter_context(patch("openai.AsyncOpenAI", side_effect=AssertionError("Async disabled")))
        from agentdojo.task_suite.load_suites import get_suite
        suite = get_suite("v1.2.2", "workspace")
        for name in ("user_tasks", "injection_tasks"):
            stack.enter_context(patch.object(type(suite), name, new_callable=PropertyMock, side_effect=AssertionError("Official tasks disabled")))
        for name in ("_check_user_task_utility", "_check_injection_task_security"):
            stack.enter_context(patch.object(suite, name, side_effect=AssertionError("Official evaluators disabled")))
        import test_supplementary_observer as tests
        tests.ARTIFACT_ROOT = directory
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    summary = {"record_type": "Synthetic observer and non-resetting allocation-ledger checks", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "successful": result.wasSuccessful(), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "real_model_requests": 0, "official_tasks_and_evaluators_disabled": True, "network_and_live_key_loaders_disabled": True,
        "script_sha256": sha256((ROOT / "scripts/run_supplementary_normal.py").read_bytes()).hexdigest(),
        "test_sha256": sha256((ROOT / "tests/test_supplementary_observer.py").read_bytes()).hexdigest(), "raw_directory": str(directory.relative_to(ROOT))}
    (directory / "tests.txt").write_text(output.getvalue())
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(output.getvalue(), end="")
    print(json.dumps(summary, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

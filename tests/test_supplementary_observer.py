"""Synthetic observer/ledger checks, not official task completion or safety data."""

from dataclasses import replace
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.task_suite.load_suites import get_suite
from approval_gate import task_runner as runner
from approval_gate.completions import mock_client
from approval_gate.offline import fingerprint
from test_task_runner import completion
from run_supplementary_normal import observed_run, SlotLedger

ARTIFACT_ROOT = None


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.logs = Path(tempfile.mkdtemp(prefix="observer_fixture_", dir=ARTIFACT_ROOT or runner.ROOT / "results/raw"))
        official_registry = get_suite("v1.2.2", "workspace")
        self.env = official_registry.load_and_inject_default_environment({}).model_copy(deep=True)
        self.file = next(iter(self.env.cloud_drive.files.values()))
        self.file.filename = "observer-test.txt"
        self.before = self.env.model_copy(deep=True)
        # Only the registry/fixture are real. No official task, gold or evaluator.
        self.suite = SimpleNamespace(tools=official_registry.tools, _check_user_task_utility=lambda *args: None)
        self.config = runner.RunConfig(task_id="independent/observer_fixture", strategy="full-approve", k=0)
        self.request = 'Read the file "observer-test.txt".'
        self.task = SimpleNamespace(ID=self.config.task_id, PROMPT=self.request)

    def execute(self, responses, *, observer=True, config=None, expected=None):
        client, requests = mock_client(responses)
        env = self.env.model_copy(deep=True)
        try:
            with patch.object(runner, "load_task", return_value=(self.suite, self.task, env)) as loader:
                original = runner.load_task
                if observer:
                    result, record_path = observed_run(config or self.config, client=client, log_root=self.logs,
                        snapshot_dir=self.logs / "snapshots", expected_request=expected or self.request, mode="mock")
                    record = json.loads((runner.ROOT / record_path).read_text())
                else:
                    result = runner.run_task(config or self.config, client=client, log_root=self.logs, mode="mock")
                    record = None
                self.assertIs(runner.load_task, original)
                self.assertEqual(loader.call_count, 1)
        finally:
            client.close()
        self.assertEqual(self.env, self.before, "Input fixture must remain isolated")
        return result, record, requests

    def test_observer_preserves_requests_registry_and_state(self):
        responses = [completion(tool="search_files_by_filename", args={"filename": self.file.filename}), completion("Read in synthetic test.")]
        plain, _, expected = self.execute(responses, observer=False)
        observed, record, actual = self.execute(responses)
        self.assertEqual(expected, actual)
        self.assertEqual(len(actual[0]["tools"]), 24)
        self.assertEqual(observed["environment_sha256_before"], plain["environment_sha256_before"])
        self.assertEqual(observed["environment_sha256_after"], plain["environment_sha256_after"])
        self.assertFalse(record["model_visible_inputs_changed"])
        before = json.loads((self.logs / "snapshots/environment_before.json").read_text())
        after = json.loads((self.logs / "snapshots/environment_after.json").read_text())
        self.assertEqual(before, after)
        self.assertIsNone(observed["task_utility"], "Stub score is unavailable, not an official native success")

    def test_partial_mutation_snapshot_matches_real_dependency(self):
        config = replace(self.config, max_agent_turns=1)
        result, record, _ = self.execute([completion(tool="append_to_file", args={"file_id": self.file.id_, "content": "\nSynthetic append."})], config=config)
        before = json.loads((self.logs / "snapshots/environment_before.json").read_text())
        after = json.loads((self.logs / "snapshots/environment_after.json").read_text())
        self.assertEqual(after["cloud_drive"]["files"][self.file.id_]["content"], before["cloud_drive"]["files"][self.file.id_]["content"] + "\nSynthetic append.")
        self.assertEqual(after["inbox"], before["inbox"])
        self.assertEqual(after["calendar"], before["calendar"])
        self.assertEqual(result["status"], "stopped")
        self.assertFalse(result["final_answer_received"])
        self.assertTrue(result["environment_changed"])
        self.assertEqual(record["environment_sha256_before"], fingerprint(self.env))

    def test_zero_budget_has_no_review_or_body_and_snapshot_unchanged(self):
        config = replace(self.config, strategy="full-escalate")
        result, _, requests = self.execute([completion(tool="search_files_by_filename", args={"filename": self.file.filename}), completion("Blocked in synthetic test.")], config=config)
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["review_budget_used"], 0)
        self.assertEqual(result["tool_bodies_entered"], 0)
        self.assertFalse(result["environment_changed"])

    def test_prompt_mismatch_stops_before_requests(self):
        client, requests = mock_client([])
        try:
            with patch.object(runner, "load_task", return_value=(self.suite, self.task, self.env)) as loader:
                original = runner.load_task
                with self.assertRaises(ValueError):
                    observed_run(self.config, client=client, log_root=self.logs, snapshot_dir=self.logs / "mismatch", expected_request="Different approved task", mode="mock")
                self.assertIs(runner.load_task, original)
                self.assertEqual(loader.call_count, 1)
        finally:
            client.close()
        self.assertEqual(requests, [])
        self.assertFalse((self.logs / "mismatch/observer.json").exists())

    def test_loader_failure_is_preserved_and_patch_restored(self):
        client, requests = mock_client([])
        try:
            with patch.object(runner, "load_task", side_effect=ValueError("Synthetic loader failure")) as loader:
                with self.assertRaises(ValueError):
                    observed_run(self.config, client=client, log_root=self.logs, snapshot_dir=self.logs / "failed", expected_request=self.request, mode="mock")
                self.assertIs(runner.load_task, loader)
        finally:
            client.close()
        self.assertEqual(requests, [])
        self.assertFalse((self.logs / "failed/observer.json").exists())

    def test_allocation_slots_never_released_or_reinitialized(self):
        path = self.logs / "ledger.json"
        ledger = SlotLedger(path, ceiling="0.20")
        result = {"spending": {"accounted_usd": "0.001", "unsettled_reservations": 0}, "log_directory": "synthetic"}
        ledger.begin("a"); ledger.finish("a", result)
        with self.assertRaises(ValueError): ledger.begin("a")
        ledger.begin("b"); ledger.finish("b", result)
        with self.assertRaises(ValueError): ledger.begin("c")
        saved = path.read_bytes()
        with self.assertRaises(ValueError): SlotLedger(path, ceiling="1.80")
        self.assertEqual(path.read_bytes(), saved)
        self.assertEqual(json.loads(saved)["allocated_usd"], "0.20")

    def test_incomplete_attempt_keeps_slot_and_blocks_next(self):
        ledger = SlotLedger(self.logs / "interrupted.json")
        ledger.begin("active")
        with self.assertRaises(ValueError): ledger.begin("next")
        record = json.loads(ledger.path.read_text())
        self.assertEqual(record["allocated_usd"], "0.10")
        self.assertEqual(record["entries"][0]["state"], "allocated_before_credentials")

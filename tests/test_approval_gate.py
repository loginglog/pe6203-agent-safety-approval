"""Exercise the real AgentDojo runtime and independently observe body entry."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
import json
from pathlib import Path
import tempfile
import unittest

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop
from agentdojo.functions_runtime import FunctionCall
from agentdojo.types import text_content_block_from_string

from approval_gate import ApprovalGate, Decision, DecisionContext, PolicyDecision, ReviewDecision
from approval_gate.offline import TASK_REQUEST, create_call, messages_for, no_network, workspace_fixture
from approval_gate.scripted import ScriptedPolicy, ScriptedReviewer


def policy_result(decision):
    return PolicyDecision(decision, "Scripted test decision.")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.network = no_network()
        self.network.__enter__()
        self.addCleanup(self.network.__exit__, None, None, None)
        self.env, self.runtime, self.calls = workspace_fixture()
        self.before = self.env.model_copy(deep=True)

    def make_executor(self, decisions, reviews=(), k=1):
        self.policy = ScriptedPolicy([policy_result(d) for d in decisions])
        self.reviewer = ScriptedReviewer(reviews)
        self.factory = ApprovalGate(self.policy, self.reviewer)
        return self.factory.new_task("offline-task", TASK_REQUEST, k)

    def run_calls(self, executor, calls=None):
        calls = [create_call("test-file")] if calls is None else calls
        return executor.query(TASK_REQUEST, self.runtime, self.env, messages_for(calls))[3]

    def assert_blocked(self, executor, messages):
        self.assertEqual(self.calls, [])
        self.assertEqual(self.env, self.before)
        self.assertFalse(executor.records[-1]["tool_executed"])
        self.assertFalse(executor.records[-1]["runtime_dispatched"])
        self.assertFalse(executor.records[-1]["final_authorized"])
        self.assertIn("ApprovalDenied", messages[-1]["error"])
        self.assertIn("ApprovalDenied", messages[-1]["content"][0]["content"])

    def assert_created(self, executor):
        self.assertEqual(self.calls, ["create_file"])
        self.assertNotEqual(self.env, self.before)
        self.assertEqual(len(self.env.cloud_drive.files), len(self.before.cloud_drive.files) + 1)
        self.assertEqual(self.before.inbox, self.env.inbox)
        self.assertEqual(self.before.calendar, self.env.calendar)
        self.assertTrue(executor.records[-1]["tool_executed"])
        self.assertTrue(executor.records[-1]["final_authorized"])
        self.assertIsNone(executor.records[-1]["tool_error"])

    def test_direct_approve(self):
        executor = self.make_executor([Decision.APPROVE])
        self.run_calls(executor)
        self.assert_created(executor)
        self.assertEqual(len(self.reviewer.contexts), 0)
        self.assertEqual(executor.used, 0)

    def test_direct_deny(self):
        executor = self.make_executor([Decision.DENY])
        self.assert_blocked(executor, self.run_calls(executor))
        self.assertEqual(len(self.reviewer.contexts), 0)

    def test_reviewer_approve(self):
        executor = self.make_executor([Decision.ESCALATE], [ReviewDecision(True, "Approved by test reviewer.")])
        self.run_calls(executor)
        self.assert_created(executor)
        self.assertEqual(executor.used, 1)
        self.assertEqual(len(self.reviewer.contexts), 1)
        self.assertEqual(executor.records[0]["reviewer_result"], "approve")

    def test_reviewer_deny_still_consumes_budget(self):
        executor = self.make_executor([Decision.ESCALATE], [ReviewDecision(False, "Denied by test reviewer.")])
        self.assert_blocked(executor, self.run_calls(executor))
        self.assertEqual(executor.used, 1)
        self.assertEqual(len(self.reviewer.contexts), 1)
        self.assertEqual(executor.records[0]["reviewer_result"], "deny")

    def test_zero_budget_never_calls_reviewer(self):
        executor = self.make_executor([Decision.ESCALATE], [ReviewDecision(True, "Unused.")], k=0)
        self.assert_blocked(executor, self.run_calls(executor))
        self.assertEqual(len(self.reviewer.contexts), 0)
        self.assertEqual(executor.used, 0)

    def test_exhaustion_across_turns_and_later_direct_approval(self):
        executor = self.make_executor(
            [Decision.ESCALATE, Decision.ESCALATE, Decision.APPROVE],
            [ReviewDecision(False, "Denied.")], k=1,
        )
        self.run_calls(executor, [create_call("first")])
        second = self.run_calls(executor, [create_call("second")])
        self.assert_blocked(executor, second)
        self.assertEqual(executor.records[1]["blocked_reason"], "Review budget exhausted.")
        self.run_calls(executor, [create_call("third")])
        self.assert_created(executor)
        self.assertEqual(executor.used, 1)
        self.assertEqual(len(self.reviewer.contexts), 1)

    def test_multiple_calls_individual_decisions_and_observed_history(self):
        executor = self.make_executor(
            [Decision.APPROVE, Decision.DENY, Decision.ESCALATE, Decision.ESCALATE],
            [ReviewDecision(True, "Approved.")], k=1,
        )
        proposals = [create_call(label) for label in ("first", "blocked", "reviewed", "exhausted")]
        original = deepcopy(proposals)
        messages = self.run_calls(executor, proposals)
        self.assertEqual(proposals, original)
        self.assertEqual(len(messages), 6)
        self.assertEqual([m["tool_call_id"] for m in messages[2:]], [c.id for c in proposals])
        self.assertEqual(self.calls, ["create_file", "create_file"])
        created = {f.filename for f in self.env.cloud_drive.files.values()} - {
            f.filename for f in self.before.cloud_drive.files.values()
        }
        self.assertEqual(created, {"first.txt", "reviewed.txt"})
        self.assertEqual([r["tool_executed"] for r in executor.records], [True, False, True, False])
        self.assertEqual([r["budget_used_after"] for r in executor.records], [0, 0, 1, 1])
        self.assertEqual(len(self.policy.contexts), 4)
        history = json.loads(self.policy.contexts[2].observed_history_json)
        self.assertEqual([m["role"] for m in history], ["user", "assistant", "tool", "tool"])
        self.assertEqual(history[-1]["tool_call_id"], "blocked")

    def test_new_task_has_fresh_budget_even_with_identical_prompt(self):
        executor = self.make_executor(
            [Decision.ESCALATE, Decision.ESCALATE],
            [ReviewDecision(False, "Denied."), ReviewDecision(True, "Approved.")], k=1,
        )
        self.run_calls(executor)
        next_task = self.factory.new_task("next-task", TASK_REQUEST, 1)
        self.assertEqual(next_task.used, 0)
        self.run_calls(next_task, [create_call("new-task")])
        self.assert_created(next_task)
        self.assertEqual(executor.used, 1)
        self.assertEqual(next_task.used, 1)
        self.assertEqual(len(self.reviewer.contexts), 2)
        self.assertEqual(next_task.records[0]["budget_used_before"], 0)

    def test_context_excludes_environment_oracle_and_extra_args(self):
        executor = self.make_executor([Decision.ESCALATE], [ReviewDecision(False, "Denied.")])
        call = create_call("context")
        call.placeholder_args = {"gold": "ORACLE_CANARY"}
        messages = messages_for([call])
        messages[-1]["evaluation_label"] = "ORACLE_CANARY"
        executor.query(TASK_REQUEST, self.runtime, self.env, messages, {
            "environment": self.env, "attack_goal": "ORACLE_CANARY", "gold": "ORACLE_CANARY",
        })
        for context in [*self.policy.contexts, *self.reviewer.contexts]:
            self.assertEqual({f.name for f in fields(context)}, {
                "task_request", "tool_name", "arguments_json", "observed_history_json",
            })
            self.assertNotIn("ORACLE_CANARY", repr(context))
            self.assertNotIn("placeholder_args", context.observed_history_json)
            self.assertNotIn("cloud_drive", context.arguments_json)
            with self.assertRaises(FrozenInstanceError):
                context.task_request = "Changed"
        self.assertEqual(self.env, self.before)

    def test_nested_function_calls_cannot_bypass_gate(self):
        executor = self.make_executor([Decision.APPROVE])
        call = create_call("nested")
        call.args["content"] = FunctionCall(function="delete_file", args={"file_id": "0"})
        self.assert_blocked(executor, self.run_calls(executor, [call]))
        self.assertIn("Nested", executor.records[0]["blocked_reason"])

    def test_invalid_arguments_do_not_enter_body(self):
        executor = self.make_executor([Decision.APPROVE])
        messages = self.run_calls(executor, [FunctionCall(function="create_file", args={})])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.env, self.before)
        self.assertTrue(executor.records[0]["runtime_dispatched"])
        self.assertFalse(executor.records[0]["tool_executed"])
        self.assertIn("ValidationError", messages[-1]["error"])

    def test_official_tool_body_error_is_logged(self):
        executor = self.make_executor([Decision.APPROVE])
        messages = self.run_calls(executor, [FunctionCall(function="delete_file", args={"file_id": "absent"})])
        self.assertEqual(self.calls, ["delete_file"])
        self.assertEqual(self.env, self.before)
        self.assertTrue(executor.records[0]["tool_executed"])
        self.assertIsNotNone(messages[-1]["error"])
        self.assertEqual(executor.records[0]["tool_error"], messages[-1]["error"])

    def test_unknown_tool_is_not_executed(self):
        executor = self.make_executor([Decision.APPROVE])
        messages = self.run_calls(executor, [FunctionCall(function="unknown", args={})])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.env, self.before)
        self.assertFalse(executor.records[0]["runtime_dispatched"])
        self.assertFalse(executor.records[0]["tool_executed"])
        self.assertIn("Invalid tool", messages[-1]["error"])

    def test_policy_and_reviewer_failure_are_fail_closed(self):
        for policy_values, review_values, expected_used in [
            ([], [], 0),
            (["not a decision"], [], 0),
            ([policy_result(Decision.ESCALATE)], [], 1),
            ([policy_result(Decision.ESCALATE)], ["not a review"], 1),
        ]:
            with self.subTest(expected_used=expected_used, review_values=review_values):
                policy = ScriptedPolicy(policy_values)
                reviewer = ScriptedReviewer(review_values)
                executor = ApprovalGate(policy, reviewer).new_task("failure", TASK_REQUEST, 1)
                self.assert_blocked(executor, self.run_calls(executor))
                self.assertEqual(executor.used, expected_used)
                self.assertIsNotNone(executor.records[0]["approval_error"])

    def test_missing_reviewer_denies_without_spending_budget(self):
        executor = ApprovalGate(ScriptedPolicy([policy_result(Decision.ESCALATE)])).new_task(
            "no-reviewer", TASK_REQUEST, 1,
        )
        self.assert_blocked(executor, self.run_calls(executor))
        self.assertEqual(executor.used, 0)

    def test_read_only_call_executes_even_without_state_change(self):
        executor = self.make_executor([Decision.APPROVE])
        self.run_calls(executor, [FunctionCall(function="list_files", args={})])
        self.assertEqual(self.calls, ["list_files"])
        self.assertEqual(self.env, self.before)
        self.assertTrue(executor.records[0]["tool_executed"])

    def test_isolated_fixtures_and_unchanged_runtime_registry(self):
        other_env, _, _ = workspace_fixture()
        original_runs = {k: f.run for k, f in self.runtime.functions.items()}
        executor = self.make_executor([Decision.APPROVE])
        self.run_calls(executor)
        self.assertEqual(other_env, self.before)
        self.assertEqual(original_runs, {k: f.run for k, f in self.runtime.functions.items()})

    def test_records_are_complete_and_not_overwritten(self):
        executor = self.make_executor([Decision.DENY])
        self.run_calls(executor)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.jsonl"
            executor.save_records(path)
            saved = json.loads(path.read_text())
            self.assertEqual(saved, executor.records[0])
            for key in ("tool_name", "arguments", "policy_decision", "policy_reason", "escalated",
                        "reviewer_result", "budget_used_before", "budget_used_after", "budget_remaining",
                        "final_authorized", "tool_executed", "tool_error"):
                self.assertIn(key, saved)
            with self.assertRaises(FileExistsError):
                executor.save_records(path)

    def test_budget_and_task_binding_validation(self):
        for k in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                self.make_executor([], k=k)
        executor = self.make_executor([])
        with self.assertRaises(ValueError):
            executor.query("A different task", self.runtime, self.env, [])
        self.assertEqual(self.calls, [])

    def test_string_list_normalization_matches_official_executor(self):
        executor = self.make_executor([Decision.APPROVE])
        call = FunctionCall(function="send_email", args={
            "recipients": "['offline@example.com']", "subject": "Offline test", "body": "Fixture only.",
        })
        original = deepcopy(call)
        messages = self.run_calls(executor, [call])
        self.assertEqual(call, original)
        self.assertEqual(self.calls, ["send_email"])
        self.assertIsNone(messages[-1]["error"])
        self.assertEqual(json.loads(self.policy.contexts[0].arguments_json)["recipients"], ["offline@example.com"])

    def test_official_pipeline_loop_delivers_denial_to_next_element(self):
        executor = self.make_executor([Decision.DENY])

        class ScriptedAssistant(BasePipelineElement):
            def query(inner, query, runtime, env=None, messages=None, extra_args=None):
                self.assertIn("ApprovalDenied", messages[-1]["error"])
                final = {"role": "assistant", "content": [text_content_block_from_string("Operation was blocked.")], "tool_calls": None}
                return query, runtime, env, [*messages, final], extra_args

        pipeline = AgentPipeline([ToolsExecutionLoop([executor, ScriptedAssistant()])])
        output = pipeline.query(TASK_REQUEST, self.runtime, self.env, messages_for([create_call("blocked")]))
        self.assertEqual(output[3][-1]["content"][0]["content"], "Operation was blocked.")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.env, self.before)


if __name__ == "__main__":
    unittest.main()

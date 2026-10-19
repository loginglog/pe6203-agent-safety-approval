"""Offline monetary limits, stop latches, and real fixture execution checks."""

from dataclasses import replace
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

from approval_gate.completions import APIRequestError, CompletionGateway, mock_client
from approval_gate.spend_control import SpendControl, SpendControlError
from approval_gate.task_runner import RunConfig, main
from approval_gate.executor import Decision, PolicyDecision
import test_task_runner as fixtures


def settings(**updates):
    result = {"budget_usd": "0.10", "prompt_usd_per_token": "0.000000165",
              "completion_usd_per_token": "0.00000066", "context_tokens": 128000,
              "max_request_bytes": 64000, "agent_max_tokens": 512, "reviewer_max_tokens": 256,
              "model": "openai/gpt-4o-mini", "pricing_source": "Synthetic offline fixture",
              "verified_at_utc": "2026-10-17T00:00:00Z"}
    result.update(updates)
    return result


class SpendTests(unittest.TestCase):
    setUp = fixtures.RunnerTests.setUp
    run_mock = fixtures.RunnerTests.run_mock

    def config(self, **updates):
        return replace(RunConfig(strategy="candidate", spend_control=settings()), **updates)

    def test_both_components_reserve_and_settle_once(self):
        result, requests, _, records = self.run_mock([
            fixtures.completion(tool="list_files"), fixtures.review(), fixtures.completion("Done."),
        ], self.config())
        self.assertEqual(self.body_calls, ["list_files"])
        self.assertEqual(result["review_budget_used"], 1)
        self.assertEqual(result["api_requests_attempted"], 3)
        self.assertEqual(result["spending"]["unsettled_reservations"], 0)
        self.assertEqual(Decimal(result["usage"]["agent"]["estimated_cost"]), Decimal("0.00000594"))
        self.assertEqual(Decimal(result["usage"]["reviewer"]["estimated_cost"]), Decimal("0.00000297"))
        self.assertEqual(result["usage"]["policy"]["estimated_cost"], "0")
        self.assertIsNone(result["usage"]["agent"]["provider_bill_cost"])
        self.assertTrue(records[0]["tool_executed"])
        for request in requests:
            self.assertFalse(request["provider"]["allow_fallbacks"])
            self.assertTrue(request["provider"]["require_parameters"])
            self.assertEqual(request["provider"]["max_price"], {"prompt": .165, "completion": .66, "request": 0})

    def test_insufficient_initial_budget_sends_nothing(self):
        result, requests, _, _ = self.run_mock([], self.config(spend_control=settings(budget_usd="0.001")))
        self.assertEqual(requests, [])
        self.assertEqual(self.body_calls, [])
        self.assertEqual(result["spending"]["stop_reason"], "INSUFFICIENT_REMAINING_BUDGET")

    def test_remaining_budget_checked_before_reviewer(self):
        first = fixtures.completion(tool="list_files")
        first["usage"] = {"prompt_tokens": 127000, "completion_tokens": 2, "total_tokens": 127002}
        result, requests, _, records = self.run_mock([first], self.config(spend_control=settings(budget_usd="0.03")))
        self.assertEqual(len(requests), 1)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(result["review_budget_used"], 1)
        self.assertFalse(records[0]["tool_executed"])
        self.assertEqual(result["spending"]["stop_reason"], "INSUFFICIENT_REMAINING_BUDGET")

    def test_missing_agent_usage_stops_before_proposals_execute(self):
        result, requests, _, _ = self.run_mock([fixtures.completion(tool="list_files", usage=False)], self.config())
        self.assertEqual(len(requests), 1)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(result["spending"]["unsettled_reservations"], 1)
        self.assertIsNone(result["usage"]["agent"]["estimated_cost"])
        self.assertEqual(result["spending"]["stop_reason"], "MISSING_TOKEN_USAGE")

    def test_missing_reviewer_usage_blocks_tool_and_next_agent_request(self):
        result, requests, messages, records = self.run_mock([
            fixtures.completion(tool="list_files"), fixtures.review(usage=False),
        ], self.config())
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(records[0]["reviewer_result"], "error")
        self.assertIn("ApprovalDenied", messages[-1]["content"][0]["content"])
        self.assertEqual(result["status"], "stopped")

    def test_failed_review_stops_without_retry_or_next_agent_call(self):
        result, requests, _, records = self.run_mock([
            fixtures.completion(tool="list_files"), {"mock_error": "connection"},
        ], self.config())
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(result["spending"]["stop_reason"], "REQUEST_FAILED_COST_UNKNOWN")
        self.assertEqual(records[0]["reviewer_result"], "error")

    def test_invalid_review_stops_but_valid_denial_can_reach_agent(self):
        result, requests, _, _ = self.run_mock([
            fixtures.completion(tool="list_files"), fixtures.completion("{}"),
        ], self.config())
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["spending"]["stop_reason"], "REVIEWER_FORMAT_ERROR")
        result, requests, _, records = self.run_mock([
            fixtures.completion(tool="list_files"), fixtures.review(False), fixtures.completion("Blocked."),
        ], self.config())
        self.assertEqual(len(requests), 3)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(records[0]["reviewer_result"], "deny")
        self.assertIsNone(result["spending"]["stop_reason"])

    def test_same_batch_cannot_execute_later_autoapproved_call_after_service_failure(self):
        first = fixtures.completion(tool="list_files")
        first["choices"][0]["message"]["tool_calls"].append({
            "id": "next-call", "type": "function", "function": {"name": "create_file", "arguments": json.dumps({"filename": "never.txt", "content": "Must not execute."})}})
        # This independent pipeline guard blocks later calls regardless of their policy decision.
        with patch("approval_gate.policies.CandidateFilePolicy.decide", side_effect=[
            PolicyDecision(Decision.ESCALATE, "Offline first call."),
            PolicyDecision(Decision.APPROVE, "Must not be reached after service failure."),
        ]):
            result, requests, _, records = self.run_mock([first, {"mock_error": "connection"}], self.config())
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(len(records), 2)
        self.assertIsNone(records[1]["policy_decision"])
        self.assertFalse(result["environment_changed"])

    def test_request_size_and_output_caps_are_enforced_before_network(self):
        for control, payload in [
            (settings(max_request_bytes=10), {"max_tokens": 512}),
            (settings(), {"max_tokens": 513}), (settings(), {}),
            (settings(), {"max_tokens": 512, "extra_body": {"models": ["another-model"]}}),
        ]:
            budget = SpendControl(control)
            with self.assertRaises(SpendControlError):
                budget.reserve("agent", control["model"], payload)
            self.assertEqual(budget.events, [])

    def test_output_or_cost_overrun_stops_and_keeps_reservation(self):
        for usage in [
            {"prompt_tokens": 10, "completion_tokens": 513, "total_tokens": 523},
            {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "cost": 1},
            {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "cost": -1},
        ]:
            response = fixtures.completion(tool="list_files")
            response["usage"] = usage
            result, requests, _, _ = self.run_mock([response], self.config())
            self.assertEqual(len(requests), 1)
            self.assertEqual(self.body_calls, [])
            self.assertEqual(result["spending"]["unsettled_reservations"], 1)

    def test_live_cli_requires_verified_budget_before_key_lookup(self):
        with patch("approval_gate.task_runner.live_client", side_effect=AssertionError("No key lookup")) as factory:
            with self.assertRaises(ValueError):
                main(["--enable-api", "--log-root", str(self.logs)])
        factory.assert_not_called()

    def test_reported_cost_is_separate_from_estimate_and_invoice(self):
        response = fixtures.completion("Done.")
        response["usage"]["cost"] = 0.000004
        response["provider"] = "Synthetic provider"
        result, _, _, _ = self.run_mock([response], self.config())
        self.assertEqual(result["usage"]["agent"]["provider_reported_cost_usd_credits"], "0.000004")
        self.assertEqual(Decimal(result["spending"]["accounted_usd"]), Decimal("0.000004"))
        self.assertEqual(result["usage"]["agent"]["response_providers"], ["Synthetic provider"])
        self.assertIsNone(result["usage"]["agent"]["provider_bill_cost"])


if __name__ == "__main__":
    unittest.main()

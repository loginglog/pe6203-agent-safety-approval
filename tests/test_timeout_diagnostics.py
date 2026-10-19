"""Offline timeout provenance, request limits, redaction and ledger reconciliation."""

from dataclasses import replace
from decimal import Decimal
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

from approval_gate.completions import (
    APIRequestError, CompletionGateway, RunStoppedError, TaskDeadlineError,
    _sdk_client, mock_client,
    input_summary,
)
from approval_gate.spend_control import SpendControl
from approval_gate.task_runner import RunConfig, ROOT, main
from approval_gate.offline import no_network
import test_task_runner as fixtures
from test_spend_control import settings


class TimeoutTests(unittest.TestCase):
    setUp = fixtures.RunnerTests.setUp
    run_mock = fixtures.RunnerTests.run_mock

    def make_transport(self, responses=None, exception=None):
        captured = []
        queue = list(responses or [])
        def respond(request):
            captured.append({"timeout": request.extensions.get("timeout"),
                             "json": json.loads(request.content)})
            if exception:
                raise exception("Synthetic sensitive error: DO_NOT_LOG_ME", request=request)
            return httpx.Response(200, json=queue.pop(0), request=request)
        client = _sdk_client("offline-dummy-key", "https://offline.invalid/v1", 5,
                             httpx.MockTransport(respond))
        self.addCleanup(client.close)
        return client, captured

    def test_client_timeout_explicit_even_when_matching_httpx_default(self):
        client, captured = self.make_transport([fixtures.completion("Done.")])
        self.assertEqual(client.timeout, 5)
        self.assertEqual(client._client.timeout.as_dict(), dict.fromkeys(("connect", "read", "write", "pool"), 5))
        self.assertEqual(client.max_retries, 0)
        CompletionGateway(client, 1).complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
        self.assertEqual(captured[0]["timeout"], dict.fromkeys(("connect", "read", "write", "pool"), 5))

    def test_both_component_overrides_reach_actual_sdk_transport(self):
        client, captured = self.make_transport([fixtures.completion("Done."), fixtures.review()])
        gateway = CompletionGateway(client, 2, component_timeouts={"agent": 90, "reviewer": 30})
        gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
        gateway.complete("reviewer", "openai/gpt-4o-mini", messages=[], max_tokens=256)
        self.assertEqual([r["timeout"]["read"] for r in captured], [90, 30])
        self.assertNotIn("timeout", captured[0]["json"])
        self.assertEqual([e["io_timeout_seconds"]["read"] for e in gateway.events], [90, 30])

    def test_cli_component_and_task_settings_are_recorded_without_credentials(self):
        path = self.logs / "responses.json"
        path.write_text(json.dumps([fixtures.completion("Done.")]))
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            code = main(["--mock-responses", str(path), "--log-root", str(self.logs),
                         "--timeout-seconds", "40", "--agent-timeout-seconds", "90",
                         "--reviewer-timeout-seconds", "30", "--task-timeout-seconds", "240"])
        self.assertEqual(code, 0)
        directory = ROOT / json.loads(output.getvalue())["log_directory"]
        metadata = json.loads((directory / "config.json").read_text())["timeout_configuration"]
        self.assertEqual(metadata["component_io_timeout_seconds"]["agent"]["read"], 90)
        self.assertEqual(metadata["component_io_timeout_seconds"]["reviewer"]["read"], 30)
        self.assertEqual(metadata["task_timeout_seconds"], 240)
        self.assertIsNone(metadata["request_wall_clock_timeout_seconds"])
        event = json.loads((directory / "api_calls.jsonl").read_text())
        self.assertEqual(event["io_timeout_seconds"]["read"], 90)
        self.assertIsNotNone(event["ended_at_utc"])

    def test_actual_sdk_timeout_causes_classify_without_messages_or_headers(self):
        for kind, phase in [(httpx.ConnectTimeout, "connect"), (httpx.ReadTimeout, "read"),
                            (httpx.WriteTimeout, "write"), (httpx.PoolTimeout, "pool")]:
            with self.subTest(phase=phase):
                client, captured = self.make_transport(exception=kind)
                spend = SpendControl(settings())
                gateway = CompletionGateway(client, 6, spend_control=spend,
                                            component_timeouts={"agent": 30})
                with self.assertRaises(APIRequestError):
                    gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
                with self.assertRaises(RunStoppedError):
                    gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
                self.assertEqual(len(captured), 1)
                event = gateway.events[0]
                self.assertEqual(event["error_category"], "APITimeoutError")
                self.assertEqual(event["exception_phase"], phase)
                self.assertEqual(event["stage_at_error"], "sdk_request")
                self.assertIn(kind.__name__, event["exception_type_chain"])
                self.assertIsNotNone(event["ended_at_utc"])
                self.assertIsNone(event["input_tokens"])
                self.assertIsNone(event["provider_reported_cost"])
                self.assertEqual(spend.summary()["unsettled_reservations"], 1)
                self.assertEqual(Decimal(spend.summary()["accounted_usd"]), Decimal("0.02145792"))
                saved = json.dumps(event)
                for sensitive in ("DO_NOT_LOG_ME", "offline-dummy-key", "Authorization", "headers"):
                    self.assertNotIn(sensitive, saved)

    def test_timeout_after_real_fixture_tool_preserves_counts_and_budget(self):
        client, captured = self.make_transport([
            fixtures.completion(tool="list_files"), fixtures.review(),
        ])
        # Replace only the mock transport's response handler for the third request.
        original = client._client._transport.handler
        def third_timeout(request):
            if len(captured) == 2:
                captured.append({"timeout": request.extensions.get("timeout"), "json": json.loads(request.content)})
                raise httpx.ReadTimeout("Synthetic post-tool timeout", request=request)
            return original(request)
        client._client._transport.handler = third_timeout
        from approval_gate.task_runner import run_task
        result = run_task(RunConfig(strategy="candidate", spend_control=settings()),
                          mode="mock", client=client, log_root=self.logs)
        self.assertEqual(result["api_requests_attempted"], 3)
        self.assertEqual(result["agent_turns"], 2)
        self.assertEqual(result["review_budget_used"], 1)
        self.assertEqual(result["usage"]["reviewer"]["api_requests_attempted"], 1)
        self.assertEqual(result["stop_reason"], "REQUEST_TIMEOUT")
        self.assertEqual(self.body_calls, ["list_files"])
        self.assertFalse(result["environment_changed"])
        self.assertIsNone(result["task_utility"])
        self.assertIsNone(result["usage"]["agent"]["estimated_cost"])
        self.assertEqual(result["spending"]["unsettled_reservations"], 1)
        self.assertEqual(captured[-1]["json"]["messages"][-1]["role"], "tool")
        self.assertEqual(len(captured), 3)

    def test_reviewer_timeout_prevents_tool_and_later_requests(self):
        client, captured = self.make_transport([fixtures.completion(tool="list_files")])
        original = client._client._transport.handler
        def review_timeout(request):
            if len(captured) == 1:
                captured.append({"timeout": request.extensions.get("timeout")})
                raise httpx.ReadTimeout("Synthetic review timeout", request=request)
            return original(request)
        client._client._transport.handler = review_timeout
        from approval_gate.task_runner import run_task
        result = run_task(RunConfig(strategy="candidate", spend_control=settings()),
                          mode="mock", client=client, log_root=self.logs)
        self.assertEqual(result["api_requests_attempted"], 2)
        self.assertEqual(result["review_budget_used"], 1)
        self.assertEqual(self.body_calls, [])
        self.assertEqual(result["stop_reason"], "REQUEST_TIMEOUT")
        self.assertEqual(len(captured), 2)

    def test_expired_task_deadline_sends_no_request_or_reservation(self):
        client, captured = self.make_transport([])
        spend = SpendControl(settings())
        gateway = CompletionGateway(client, 6, spend_control=spend, task_deadline=9)
        with patch("approval_gate.completions.monotonic", return_value=10):
            with self.assertRaises(TaskDeadlineError):
                gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
        self.assertEqual(captured, [])
        self.assertEqual(spend.summary()["accounted_usd"], "0")
        self.assertEqual(gateway.stop_reason, "TASK_DEADLINE_EXCEEDED")

    def test_remaining_task_time_clamps_io_settings(self):
        client, captured = self.make_transport([fixtures.completion("Done.")])
        gateway = CompletionGateway(client, 1, component_timeouts={"agent": 90}, task_deadline=50)
        with patch("approval_gate.completions.monotonic", return_value=40):
            gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
        self.assertEqual(captured[0]["timeout"], dict.fromkeys(("connect", "read", "write", "pool"), 10))

    def test_late_response_is_accounted_but_not_used_for_execution(self):
        client, captured = self.make_transport([fixtures.completion(tool="list_files")])
        spend = SpendControl(settings())
        gateway = CompletionGateway(client, 6, spend_control=spend,
                                    component_timeouts={"agent": 30}, task_deadline=20)
        # Before request, before timeout construction, start, after response, finally.
        with patch("approval_gate.completions.monotonic", side_effect=[10, 10, 10, 21, 21]):
            with self.assertRaises(APIRequestError):
                gateway.complete("agent", "openai/gpt-4o-mini", messages=[], max_tokens=512)
        self.assertEqual(len(captured), 1)
        self.assertEqual(spend.summary()["unsettled_reservations"], 0)
        self.assertEqual(gateway.stop_reason, "TASK_DEADLINE_EXCEEDED")
        self.assertEqual(gateway.events[0]["stage_at_error"], "task_deadline_check")
        self.assertTrue(gateway.events[0]["response_received"])

    def test_task_deadline_at_tool_boundary_blocks_real_body_entry(self):
        from approval_gate.task_runner import run_task
        client, captured = self.make_transport([fixtures.completion(tool="list_files")])
        with patch("approval_gate.task_runner.monotonic", return_value=0), \
                patch("approval_gate.completions.monotonic", side_effect=[0, 0, 0, 0, 0, 21]):
            result = run_task(RunConfig(strategy="candidate", spend_control=settings(), task_timeout_seconds=20),
                              mode="mock", client=client, log_root=self.logs)
        self.assertEqual(len(captured), 1)
        self.assertEqual(result["review_budget_used"], 0)
        self.assertEqual(self.body_calls, [])
        self.assertFalse(result["environment_changed"])
        self.assertEqual(result["stop_reason"], "TASK_DEADLINE_EXCEEDED")

    def test_recorded_fee_margin_and_reservation_formula(self):
        run = ROOT / 'results/raw/restricted_live_task26_ibfuh53n/task_run_2vr9pgmj'
        if not run.exists():
            self.skipTest('Private historical logs are intentionally not distributed')
        config = json.loads((run / 'config.json').read_text())['configuration']['spend_control']
        api = [json.loads(line) for line in (run / 'api_calls.jsonl').read_text().splitlines()]
        spend = SpendControl(config)
        reported, estimates = Decimal(0), Decimal(0)
        for event in api[:2]:
            cap = 512 if event['component'] == 'agent' else 256
            reservation = spend.reserve(event['component'], config['model'], {'max_tokens': cap})
            spend.settle(reservation, dict(event))
            reported += Decimal(str(event['provider_reported_cost']))
            estimates += Decimal(event['estimated_cost_usd'])
        pending = spend.reserve('agent', config['model'], {'max_tokens': 512})
        self.assertEqual(reported, Decimal('0.00041865'))
        self.assertEqual(estimates - reported, Decimal('0.000041865'))
        self.assertEqual(Decimal(pending['reserved_usd']), Decimal('0.02145792'))
        self.assertEqual(Decimal(spend.summary()['accounted_usd']), Decimal('0.021918435'))
        self.assertEqual(reported + Decimal(pending['reserved_usd']), Decimal('0.02187657'))
        self.assertEqual(estimates, reported * Decimal('1.10'))

    def test_invalid_timeout_settings_rejected_and_defaults_unchanged(self):
        self.assertEqual(RunConfig().component_timeouts(), {'agent':30,'reviewer':30})
        self.assertIsNone(RunConfig().task_timeout_seconds)
        for field in ('timeout_seconds','agent_timeout_seconds','reviewer_timeout_seconds','task_timeout_seconds'):
            for value in (0,-1,True,float('inf'),float('nan')):
                with self.assertRaises(ValueError):
                    replace(RunConfig(),**{field:value}).validate()

    def test_input_sizes_distinguish_text_and_json_without_changing_payload(self):
        body = "Offline text.\n"
        payload = {"messages": [{"role": "user", "content": "Inspect the fixture."},
                                {"role": "tool", "content": [{"type": "text", "text": body}]}]}
        before = json.dumps(payload)
        summary = input_summary(payload)
        self.assertEqual(summary["tool_text_characters"], len(body))
        self.assertEqual(summary["tool_text_utf8_bytes"], len(body.encode()))
        self.assertGreater(summary["tool_content_json_utf8_bytes"], len(body))
        self.assertIsNone(summary["input_token_estimate"])
        self.assertNotIn("Offline text", json.dumps(summary))
        self.assertEqual(json.dumps(payload), before)


if __name__ == '__main__':
    unittest.main()

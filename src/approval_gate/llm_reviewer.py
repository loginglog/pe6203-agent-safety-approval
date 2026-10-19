"""Versioned, judgment-only LLM reviewer with strict fail-closed parsing."""

import json

from .completions import strict_json
from .executor import ReviewDecision


class ReviewerRequestError(RuntimeError):
    pass


class ReviewerFormatError(RuntimeError):
    pass


class LLMReviewer:
    prompt_version = "reviewer-v1"

    def __init__(self, gateway, model, prompt, tool_definitions, max_tokens=256, event_sink=None):
        self.gateway = gateway
        self.model = model
        self.prompt = prompt
        self.tool_definitions = tool_definitions
        self.max_tokens = max_tokens
        self.events = []
        self.event_sink = event_sink

    def review(self, context):
        event = {"prompt_version": self.prompt_version, "result": None, "reason": None,
                 "error_category": None, "payload": None}
        try:
            payload = {
                "original_user_task": context.task_request,
                "proposed_operation": {"tool_name": context.tool_name,
                                       "arguments": strict_json(context.arguments_json)},
                "tool_definition": self.tool_definitions.get(context.tool_name),
                "observed_history": strict_json(context.observed_history_json),
            }
            event["payload"] = payload
            try:
                response = self.gateway.complete(
                    "reviewer", self.model,
                    messages=[{"role": "system", "content": self.prompt},
                              {"role": "user", "content": json.dumps(payload)}],
                    response_format={"type": "json_object"}, temperature=0,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                event["error_category"] = type(exc).__name__
                raise ReviewerRequestError(type(exc).__name__) from None
            try:
                if len(response["choices"]) != 1:
                    raise ValueError("Expected one review")
                choice = response["choices"][0]
                message = choice["message"]
                if (choice.get("finish_reason") != "stop" or message.get("role") != "assistant"
                        or message.get("tool_calls") or message.get("function_call") or message.get("refusal")):
                    raise ValueError("Review was incomplete or attempted a tool call")
                value = strict_json(message["content"])
                if (not isinstance(value, dict) or set(value) != {"decision", "reason"}
                        or value["decision"] not in ("approve", "deny")
                        or not isinstance(value["reason"], str)
                        or not 1 <= len(value["reason"].strip()) <= 500):
                    raise ValueError("Invalid review schema")
            except Exception:
                event["error_category"] = "ReviewerFormatError"
                if self.gateway.spend_control:
                    self.gateway.spend_control.stop_reason = "REVIEWER_FORMAT_ERROR"
                raise ReviewerFormatError("Invalid or incomplete review response") from None
            event.update(result=value["decision"], reason=value["reason"].strip())
            return ReviewDecision(value["decision"] == "approve", value["reason"].strip())
        except (ReviewerFormatError, ReviewerRequestError):
            raise
        except Exception:
            event["error_category"] = "ReviewerFormatError"
            raise ReviewerFormatError("Invalid review context") from None
        finally:
            self.events.append(event)
            if self.event_sink:
                self.event_sink(event)

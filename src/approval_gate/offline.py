"""Offline fixtures and independent body counters for the demo and tests.

These counters and environment snapshots stay outside decision contexts.
They measure execution, not task-completion or safety scores.
"""

from contextlib import contextmanager
from hashlib import sha256
import json
from unittest.mock import patch

from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import text_content_block_from_string


TASK_REQUEST = "Create only the test files authorized by the approval gate in the fixture drive."


@contextmanager
def no_network():
    """Make accidental socket connections fail during offline verification."""
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is disabled for offline verification.")
    with patch("socket.socket.connect", blocked), patch("socket.socket.connect_ex", blocked), \
            patch("socket.create_connection", blocked), patch("socket.getaddrinfo", blocked):
        yield


def workspace_fixture():
    """Load an independent copy of AgentDojo's bundled workspace fixture."""
    suite = get_suite("v1.2.2", "workspace")
    env = suite.load_and_inject_default_environment({}).model_copy(deep=True)
    body_calls = []
    functions = []
    for function in suite.tools:
        def counted(*args, _function=function, **kwargs):
            body_calls.append(_function.name)
            return _function.run(*args, **kwargs)
        functions.append(function.model_copy(update={"run": counted}))
    return env, FunctionsRuntime(functions), body_calls


def create_call(label, call_id=None):
    return FunctionCall(
        function="create_file", args={"filename": label + ".txt", "content": "Offline approval fixture."},
        id=call_id or label,
    )


def messages_for(calls, query=TASK_REQUEST):
    return [
        {"role": "user", "content": [text_content_block_from_string(query)]},
        {"role": "assistant", "content": None, "tool_calls": calls},
    ]


def fingerprint(env):
    return sha256(json.dumps(env.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()

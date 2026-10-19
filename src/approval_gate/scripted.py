"""Deterministic test doubles, not a developed policy or an LLM reviewer."""

from collections import deque


class ScriptedPolicy:
    def __init__(self, responses):
        self.responses = deque(responses)
        self.contexts = []

    def decide(self, context):
        self.contexts.append(context)
        if not self.responses:
            raise RuntimeError("No scripted policy response remains.")
        return self.responses.popleft()


class ScriptedReviewer:
    def __init__(self, responses):
        self.responses = deque(responses)
        self.contexts = []

    def review(self, context):
        self.contexts.append(context)
        if not self.responses:
            raise RuntimeError("No scripted reviewer response remains.")
        return self.responses.popleft()

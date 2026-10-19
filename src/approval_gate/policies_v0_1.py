"""Two course baselines and a deliberately narrow candidate file rule policy.

Only the original task_request supplies constraints. Tool outputs, arguments,
and observed messages cannot introduce or revoke authorization in this version.
"""

import re

from .executor import Decision, DecisionContext, PolicyDecision


READ_TOOLS = frozenset({
    "list_files", "search_files", "search_files_by_filename", "get_file_by_id",
})
WRITE_TOOLS = frozenset({"create_file", "append_to_file", "delete_file", "share_file"})

# The full tool implementations, not just their names, establish these scopes.
# All four read tools return content, so a global reading ban also blocks lists
# and searches. There is no narrower metadata-only path in this tool set.
ACTION_TOOLS = {
    "list": frozenset({"list_files"}),
    "search": frozenset({"search_files", "search_files_by_filename"}),
    "read": READ_TOOLS,
    "create": frozenset({"create_file"}),
    "append to": frozenset({"append_to_file"}),
    "delete": frozenset({"delete_file"}),
    "share": frozenset({"share_file"}),
}


class FullApprovePolicy:
    version = "full-approve-v1"

    def decide(self, context: DecisionContext) -> PolicyDecision:
        return PolicyDecision(Decision.APPROVE, f"{self.version}: approve every proposed call.")


class FullEscalatePolicy:
    version = "full-escalate-v1"

    def decide(self, context: DecisionContext) -> PolicyDecision:
        return PolicyDecision(Decision.ESCALATE, f"{self.version}: send every proposed call to the gate's reviewer path.")


def _parse_request(request: str) -> frozenset[str] | None:
    """Parse a complete controlled-English request, or decline all interpretation.

    A clause is ACTION files, or (Do not | Don't) ACTION [any] files.
    Clauses use periods/newlines as separators. Partial matches are never used.
    """
    clauses = [" ".join(c.split()).casefold() for c in re.split(r"[.\n]", request) if c.strip()]
    if not clauses:
        return None
    positive = {f"{action} files" for action in ACTION_TOOLS}
    negative = {
        f"{prefix} {action} {quantifier}files": action
        for prefix in ("do not", "don't")
        for action in ACTION_TOOLS
        for quantifier in ("", "any ")
    }
    forbidden = set()
    for clause in clauses:
        if clause in negative:
            forbidden.update(ACTION_TOOLS[negative[clause]])
        elif clause not in positive:
            return None
    return frozenset(forbidden)


class CandidateFilePolicy:
    """Candidate v0.1.0: exact global bans, then read/write classification.

    Unknown language is escalated for every tool, including otherwise read-only
    tools. A parsed positive clause does not authorize a write automatically.
    """

    version = "file-rules-v0.1.0"

    def decide(self, context: DecisionContext) -> PolicyDecision:
        forbidden = _parse_request(context.task_request)
        if forbidden is None:
            return PolicyDecision(Decision.ESCALATE, f"{self.version}: task request is outside the supported controlled-English grammar.")
        if context.tool_name in forbidden:
            return PolicyDecision(Decision.DENY, f"{self.version}: original task request explicitly forbids this file operation.")
        if context.tool_name in READ_TOOLS:
            return PolicyDecision(Decision.APPROVE, f"{self.version}: classified file query; no supported task prohibition applies.")
        if context.tool_name in WRITE_TOOLS:
            return PolicyDecision(Decision.ESCALATE, f"{self.version}: file mutation or sharing requires review.")
        return PolicyDecision(Decision.ESCALATE, f"{self.version}: tool is outside the classified file-tool set.")

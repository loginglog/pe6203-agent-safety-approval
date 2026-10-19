"""Bounded intent, restriction, and object-scope rules; no model calls."""

from dataclasses import dataclass
import json
import re

import yaml

from .executor import Decision, PolicyDecision
from .policies_v0_1 import ACTION_TOOLS, READ_TOOLS, WRITE_TOOLS


DRIVE = r"(?:\s+(?:in|on|from)\s+(?:the|my|our)\s+(?:cloud\s+)?drive)?"
POLITE = r"^(?:please\s+|(?:can|could|would) you\s+|i would like you to\s+)"
QUALIFIERS = r"\b(?:if|unless|except|only|provided|until|before|after|excluding|neither|nor)\b|rather than|instead of"
NEGATION = r"\b(?:not|never|without|cannot|must)\b|don['’]t|can['’]t"


@dataclass(frozen=True)
class TaskScope:
    kind: str = "unknown"
    target: str | None = None
    bans: frozenset[str] = frozenset()
    error: str | None = None


def _mask_literals(request):
    literals = []

    def mask(match):
        literals.append(match.group(2))
        return f"@f{len(literals) - 1}@"

    masked = re.sub(r"(?<!\w)(['\"])([^'\"\n]+)\1", mask, request)
    # Unmatched quotes and non-filename quotations remain unrecognized prose.
    return masked, literals


def _literal(slot, literals):
    index = int(slot[2:-1])
    if index >= len(literals):
        return None
    value = literals[index]
    if not value.strip() or any(c in value for c in "/\\:*?\n"):
        return None
    return value


def _intent(clause, literals):
    clause = re.sub(POLITE, "", clause)
    obj = r"(?:(?:the\s+)?(?:file|document)\s+)?(?:(?:named|called|titled)\s+)?(@f\d+@)"
    named = re.fullmatch(r"(?:read|open|inspect|review|examine|look at|take a look at)\s+" + obj + r"(.*)", clause)
    shown = re.fullmatch(r"(?:show|display)(?: me)? (?:the )?(?:contents|content|text|body) of " + obj, clause)
    if named or shown:
        match = named or shown
        if named and named.group(2).strip():
            tail = named.group(2).strip(" ,")
            followup = (r"(?:(?:and|then)\s+)?(?:suggest|propose|recommend)\s+"
                        r"[a-z0-9][a-z0-9 ,'-]*?\s*,?\s*(?:(?:and|then)\s+)?"
                        r"(?:add|append|write)\s+(?:them|it|the suggestions|the ideas)\s+"
                        r"to\s+(?:the|that|this)\s+(?:file|document)")
            if not re.fullmatch(followup, tail):
                return TaskScope(error="E_TASK_UNRECOGNIZED")
        name = _literal(match.group(1), literals)
        return TaskScope("named", name, error=None if name is not None else "E_SCOPE_UNRESOLVED")

    content_search = re.fullmatch(
        r"(?:find|locate|search for) (?:all |the )?(?:files|documents) "
        r"(?:containing|that contain|with the text) (@f\d+@)"
        r"(?:\s+(?:and|then) (?:read|show|display) (?:their|the) (?:contents|content|text|bodies))?", clause,
    )
    if content_search:
        index = int(content_search.group(1)[2:-1])
        if index >= len(literals) or not literals[index].strip():
            return TaskScope(error="E_SCOPE_UNRESOLVED")
        term = literals[index]
        has_contents = bool(re.search(r"\b(?:read|show|display)\b", clause))
        return TaskScope("content" if has_contents else "metadata", term)

    if any(re.fullmatch(pattern + DRIVE, clause) for pattern in (
        r"(?:show|display|read)(?: me)? (?:the )?(?:contents|text|bodies) of (?:all|every)(?: the)? (?:files|documents)",
        r"(?:show|display|read)(?: me)? all (?:files|documents) and their (?:contents|text|bodies)",
    )):
        return TaskScope("collection_contents")

    rank = r"(?:the )?(?:largest|biggest|smallest) (?:file|document)"
    if any(re.fullmatch(pattern + DRIVE, clause) for pattern in (
        r"(?:what|which) is (?:the )?(?:filename|file name|name) of " + rank,
        r"(?:give|tell|show)(?: me)? (?:the )?(?:filename|file name|name) of " + rank,
        r"(?:find|identify|locate)(?: and (?:delete|remove))? " + rank,
        r"(?:which|what) (?:file|document) (?:is|has) (?:the )?(?:largest|biggest|smallest)(?: size)?",
        r"(?:list|show|display)(?: me)? (?:all |the )?(?:files|documents|filenames|file names)",
    )):
        return TaskScope("metadata")
    if re.fullmatch(r"(?:create|append to|delete|remove|share) (?:files|documents)", clause):
        return TaskScope("mutation")
    return TaskScope(error="E_TASK_UNRECOGNIZED")


def analyze_request(request):
    if re.search(r"@f\d+@", request):
        return TaskScope(error="E_SCOPE_UNRESOLVED")
    masked, literals = _mask_literals(request)
    text = " ".join(masked.casefold().replace("\r\n", "\n").replace("\n", ";").split())
    if re.search(QUALIFIERS, text):
        return TaskScope(error="E_CONSTRAINT_UNRESOLVED")
    text = re.sub(
        r"\s+without (deleting|reading|sharing) (?:any )?(?:files|documents)(?=[.!?;]|$)",
        lambda m: ". do not " + {"deleting": "delete", "reading": "read", "sharing": "share"}[m.group(1)] + " files",
        text,
    )
    # Keep newlines as sentence boundaries while normalizing other whitespace.
    text = text.replace("\r", "")
    # Periods inside quoted literals have already been masked.
    clauses = [c.strip() for c in re.split(r"[.!?;]+|\s+(?:and|but)\s+(?=(?:please\s+)?(?:do not|don['’]t|never)\b)", text) if c.strip()]
    banned, intents = set(), []
    error = None
    synonyms = {"remove": "delete", "open": "read"}
    for clause in clauses:
        clause = re.sub(POLITE, "", clause)
        ban = re.fullmatch(r"(?:do not|don['’]t|never) (delete|remove|read|open|share|create|append to|list|search) "
                           r"(?:(?:any|all|my|the) )?(?:files|documents)" + DRIVE, clause)
        if ban:
            banned.add(synonyms.get(ban.group(1), ban.group(1)))
            continue
        if re.search(NEGATION, clause):
            return TaskScope(bans=frozenset(banned), error="E_CONSTRAINT_UNRESOLVED")
        intent = _intent(clause, literals)
        if intent.error:
            error = intent.error
        else:
            intents.append(intent)
    scopes = {(i.kind, i.target) for i in intents}
    if len(scopes) > 1 or len(literals) > 1:
        error = "E_SCOPE_UNRESOLVED"
    if error or not scopes:
        return TaskScope(bans=frozenset(banned), error=error or "E_TASK_UNRECOGNIZED")
    kind, target = next(iter(scopes))
    return TaskScope(kind, target, frozenset(banned))


def observed_files(history):
    """Read canonical tool envelopes and identity rows, never body instructions."""
    proposals, rows = {}, {}
    unreliable = False
    for message in history:
        if not isinstance(message, dict):
            return {}, True
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                if isinstance(call, dict):
                    if isinstance(call.get("id"), str):
                        proposals[call["id"]] = call
        if message.get("role") != "tool" or message.get("error") is not None:
            continue
        call = message.get("tool_call")
        if not isinstance(call, dict) or call.get("function") not in READ_TOOLS:
            continue
        prior = proposals.get(message.get("tool_call_id")) if isinstance(message.get("tool_call_id"), str) else None
        if (not prior or prior.get("function") != call.get("function")
                or prior.get("args") != call.get("args") or call.get("id") != message.get("tool_call_id")
                or call.get("id") is None):
            unreliable = True
            continue
        blocks = message.get("content")
        try:
            if not isinstance(blocks, list) or len(blocks) != 1 or blocks[0].get("type") != "text":
                raise ValueError("Unsupported tool-result representation")
            data = yaml.safe_load(blocks[0]["content"])
            data = data if isinstance(data, list) else [data]
            for row in data:
                if (not isinstance(row, dict) or not isinstance(row.get("id_"), str)
                        or not isinstance(row.get("filename"), str) or not isinstance(row.get("content"), str)):
                    raise ValueError("Missing canonical file identity")
                old = rows.get(row["id_"])
                if old and old["filename"] != row["filename"]:
                    raise ValueError("Conflicting file identity")
                rows[row["id_"]] = {k: row[k] for k in ("id_", "filename", "content")}
        except (ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError):
            unreliable = True
    return rows, unreliable


class CandidateFilePolicy:
    version = "file-rules-v0.2.0"

    def result(self, decision, code, explanation):
        return PolicyDecision(decision, f"{self.version}:{code}: {explanation}")

    def escalate(self, code, explanation):
        return self.result(Decision.ESCALATE, code, explanation)

    def decide(self, context):
        tool = context.tool_name
        if tool not in READ_TOOLS | WRITE_TOOLS:
            return self.escalate("E_NON_FILE_TOOL", "Tool is outside the classified file interface.")
        scope = analyze_request(context.task_request)
        if scope.error == "E_CONSTRAINT_UNRESOLVED":
            return self.escalate(scope.error, "Condition, exception, object restriction, or negation scope is unresolved.")
        for action in sorted(scope.bans):
            if tool in ACTION_TOOLS[action]:
                return self.result(Decision.DENY, "D_" + action.replace(" to", "").upper() + "_PROHIBITED",
                                   "Original user explicitly prohibits this global file operation.")
        if scope.error:
            return self.escalate(scope.error, "Task intent or object scope could not be resolved by the declared rules.")
        if tool in WRITE_TOOLS:
            return self.escalate("E_MUTATION_REVIEW", "File mutations and sharing require reviewer judgment.")
        try:
            args = json.loads(context.arguments_json)
            history = json.loads(context.observed_history_json)
        except (ValueError, TypeError):
            return self.escalate("E_ARGUMENTS_UNSUPPORTED", "Decision snapshot is not valid JSON.")
        fields = {"list_files": set(), "search_files_by_filename": {"filename"},
                  "get_file_by_id": {"file_id"}, "search_files": {"query"}}[tool]
        if not isinstance(args, dict) or set(args) != fields or any(not isinstance(v, str) or not v.strip() for v in args.values()):
            return self.escalate("E_ARGUMENTS_UNSUPPORTED", "Arguments must exactly match the supported query schema.")
        if scope.kind == "metadata":
            return self.escalate("E_CONTENT_OVERREACH", "Task needs names/sizes or discovery, but this tool returns file bodies.")
        if not isinstance(history, list):
            return self.escalate("E_HISTORY_UNRELIABLE", "Observed history is not a message list.")
        rows, unreliable = observed_files(history)
        if unreliable:
            return self.escalate("E_HISTORY_UNRELIABLE", "File identity evidence is malformed, uncorrelated, or conflicting.")
        if scope.kind == "named" and tool == "search_files_by_filename":
            if args["filename"].casefold() != scope.target.casefold():
                return self.escalate("E_TOOL_UNRELATED", "Lookup argument differs from the user's literal filename.")
            matches = [r for r in rows.values() if scope.target.casefold() in r["filename"].casefold()]
            if any(r["filename"].casefold() != scope.target.casefold() for r in matches) or len(matches) > 1:
                return self.escalate("E_NAME_LOOKUP_COLLATERAL", "Known substring/name collisions make this lookup ambiguous.")
            return self.result(Decision.APPROVE, "A_NAMED_LOOKUP", "Exact supplied-name lookup for explicitly requested file contents; substring collateral risk remains.")
        if scope.kind == "collection_contents" and tool == "list_files":
            return self.result(Decision.APPROVE, "A_COLLECTION_CONTENTS", "User explicitly requests contents across the drive.")
        if scope.kind == "content" and tool == "search_files":
            if args["query"].casefold() == scope.target.casefold():
                return self.result(Decision.APPROVE, "A_SCOPED_CONTENT_SEARCH", "Literal content query matches the requested content-reading scope.")
            return self.escalate("E_TOOL_UNRELATED", "Content query differs from the original literal scope.")
        if tool == "get_file_by_id" and scope.kind in ("named", "content", "collection_contents"):
            row = rows.get(args["file_id"])
            if row is None:
                return self.escalate("E_ID_UNOBSERVED", "No correlated file identity for this ID has been observed.")
            if scope.kind == "named":
                if row["filename"].casefold() != scope.target.casefold():
                    return self.escalate("E_ID_SCOPE_MISMATCH", "Observed ID is a different file from the requested name.")
                if sum(r["filename"].casefold() == scope.target.casefold() for r in rows.values()) != 1:
                    return self.escalate("E_SCOPE_UNRESOLVED", "Multiple observed IDs share the requested filename.")
            if scope.kind == "content" and scope.target.casefold() not in row["content"].casefold():
                return self.escalate("E_ID_SCOPE_MISMATCH", "Observed file does not match the user's content criterion.")
            return self.result(Decision.APPROVE, "A_SCOPED_READ", "Observed identity fits the original user's content-reading scope.")
        return self.escalate("E_TOOL_UNRELATED", "This query does not fit the recognized task and content scope.")


def reason_code(decision):
    return decision.reason.split(":", 2)[1]

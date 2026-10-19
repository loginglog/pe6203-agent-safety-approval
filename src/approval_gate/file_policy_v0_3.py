"""Bounded compositional file authorization; no task IDs or model-based parsing."""

from dataclasses import asdict, dataclass
import json
import re

import yaml

from .executor import Decision, PolicyDecision
from .file_policy_v0_2 import _mask_literals, _intent
from .tool_facts import load_file_facts

POLITE = r'^(?:(?:please|kindly)\s+|(?:can|could|would) you(?: please)?\s+|i would like you to\s+)'
CONTROL = r'\b(?:if|unless|except|only|before|after|until|excluding|neither|nor|not|never|without|cannot|must)\b|provided that|rather than|instead of|don[’\x27]t|can[’\x27]t'
OBJ = r'(?:(?:the |a )?(?:provided )?(?:file|document)(?: (?:named|called|titled))? )?(@f\d+@)'
IDOBJ = r'(?:the )?file (?:id|with id) (@f\d+@)'
BAN_VERBS = {'open': 'read', 'remove': 'delete', 'change': 'modify', 'append to': 'append'}


@dataclass(frozen=True)
class Ban:
    action: str
    target_kind: str = 'global'
    target: str | None = None


@dataclass(frozen=True)
class TaskScope:
    intent: str = 'unknown'
    target_kind: str | None = None
    target: str | None = None
    operations: tuple[str, ...] = ()
    bans: tuple[Ban, ...] = ()
    strict_isolation: bool = False
    parameters: tuple[tuple[str, str], ...] = ()
    unresolved: tuple[str, ...] = ()


def _literal(slot, literals):
    return literals[int(slot[2:-1])]


def _object(text, literals):
    text = re.sub(r'^(?:the )?(?:contents|content|text|body) of ', '', text)
    match = re.fullmatch(IDOBJ, text)
    if match:
        value = _literal(match[1], literals)
        return ('id', value) if value.strip() else None
    match = re.fullmatch(OBJ, text)
    if match:
        value = _literal(match[1], literals)
        if value.strip() and not any(c in value for c in '/\\\n:*?'):
            return 'name', value
    return None


def _positive(clause, literals):
    """Match an entire declared expression family, retaining all residual text."""
    strict = False
    if clause.startswith('only read '):
        clause = 'read ' + clause[len('only read '):]; strict = True
    elif clause.startswith('read only '):
        clause = 'read ' + clause[len('read only '):]; strict = True
    if re.search(CONTROL, clause):
        return None
    # A named read may have a bounded same-file suggestion-and-append tail.
    append = re.fullmatch(r'(.+?),? (?:and |then )?(?:suggest|propose|recommend) '
        r'((?:one|two|three|some|several|\d+) (?:more |new |additional |follow-up )?(?:activities|ideas|suggestions|improvements))'
        r',? (?:and|then) (?:add|append|write) (?:them|the suggestions|the ideas) to (?:the same|the|that|this) (?:file|document)', clause)
    if strict and append:
        return None
    ops = ('read', 'append') if append else ('read',)
    head = append[1].rstrip(',') if append else clause
    match = re.fullmatch(r'(?:read|open|view|inspect|review|examine|look at|take a look at) (.+)', head)
    if not match:
        match = re.fullmatch(r'(?:show|display)(?: me)? (?:the )?(?:contents|content|text|body) of (.+)', head)
    if not match:
        match = re.fullmatch(r'(?:summarize|summarise) (.+)', head)
    if not match:
        match = re.fullmatch(r'(?:give|provide)(?: me)? (?:a |the )?(?:brief |short )?summary of (.+)', head)
    if not match:
        match = re.fullmatch(r'(?:extract|list|identify) (?:the )?(?:key points|main points|information|dates|deadlines|figures|facts|names|action items) from (.+)', head)
    if match:
        target = _object(match[1], literals)
        if target:
            return TaskScope('information', *target, ops, strict_isolation=strict)
    # Questions are bounded information requests; additional imperatives are not opaque data.
    question = re.fullmatch(r'(?:what|which|who|how|when|where) (.+?) (?:according to|based on|from|in) (.+)', head)
    if question and not re.search(r'\b(?:and|then|also)\b|\b(?:delete|share|append|send|create|modify|ignore|execute|upload|save)\b', question[1]):
        target = _object(question[2], literals)
        if target:
            return TaskScope('information', *target, ops, strict_isolation=strict)
    # Explicit writes never grant implicit body-reading permissions.
    patterns = (
        (r'(?:delete|remove) (.+)', 'delete'),
        (r'append (@f\d+@) to (.+)', 'append'),
        (r'create (.+) (?:with|containing) (?:the )?(?:content )?(@f\d+@)', 'create'),
        (r'share (.+) with (@f\d+@) (?:with )?(read|read-write) permissions', 'share'),
    )
    for pattern, action in patterns:
        m = re.fullmatch(pattern, clause)
        if not m:
            continue
        obj_text = m[2] if action == 'append' else m[1]
        target = _object(obj_text, literals)
        if not target or (action == 'create' and target[0] != 'name'):
            return None
        params = ()
        if action == 'append': params = (('content', _literal(m[1], literals)),)
        if action == 'create': params = (('content', _literal(m[2], literals)),)
        if action == 'share': params = (('email', _literal(m[2], literals)), ('permission', 'r' if m[3] == 'read' else 'rw'))
        return TaskScope('mutation', *target, (action,), parameters=params)
    # Retain the pre-existing bounded collection and metadata families only.
    legacy = _intent(clause, literals)
    if legacy.error is None and legacy.kind in ('metadata', 'collection_contents', 'content'):
        if strict:
            return None
        rank = re.search(r'\b(largest|biggest|smallest)\b', clause) if legacy.kind == 'metadata' else None
        target_kind = 'content' if legacy.kind == 'content' else ('rank' if rank else None)
        target = ('largest' if rank[1] == 'biggest' else rank[1]) if rank else legacy.target
        return TaskScope(legacy.kind, target_kind,
                         target, ('discover', 'delete') if re.match(r'(?:find|identify|locate) and (?:delete|remove) ', clause)
                         else (('read',) if legacy.kind != 'metadata' else ('discover',)))
    return None


def analyze_request(request):
    if not isinstance(request, str) or re.search(r'@f\d+@', request):
        return TaskScope(unresolved=('Invalid or reserved-slot task text.',))
    masked, literals = _mask_literals(request)
    text = ' '.join(masked.casefold().replace('\n', ';').split())
    clauses = [re.sub(POLITE, '', c.strip()) for c in re.split(
        r'[.!?;]+|\s+(?:and|but)\s+(?=(?:please\s+)?(?:do not|don[’\x27]t|never)\b)', text) if c.strip()]
    positives, bans, unresolved = [], [], []
    strict_other = False
    for clause in clauses:
        if re.fullmatch(r'(?:do not|don[’\x27]t|never) (?:read|open) (?:any )?other (?:files|documents)', clause):
            strict_other = True; continue
        ban = re.fullmatch(r'(?:do not|don[’\x27]t|never) (modify|change|delete|remove|read|open|share|create|append to) (.+)', clause)
        if ban:
            action = BAN_VERBS.get(ban[1], ban[1]); obj = ban[2]
            if re.fullmatch(r'(?:(?:any|all|my|the) )?(?:files|documents)(?: in (?:the|my) (?:cloud )?drive)?', obj):
                bans.append(Ban(action)); continue
            target = _object(obj, literals)
            if target:
                bans.append(Ban(action, *target)); continue
            if obj in ('it', 'the file', 'that file', 'this file'):
                bans.append(Ban(action, 'anaphor')); continue
        positive = _positive(clause, literals)
        if positive is None: unresolved.append(clause)
        else: positives.append(positive)
    unique = {(p.intent, p.target_kind, p.target, p.operations, p.parameters, p.strict_isolation) for p in positives}
    if len(unique) != 1:
        unresolved.append('No unique, fully resolved task scope.')
        base = positives[0] if positives else TaskScope()
    else: base = positives[0]
    bound_bans = []
    for ban in bans:
        if ban.target_kind == 'anaphor':
            if base.target_kind in ('name', 'id') and len(unique) == 1:
                ban = Ban(ban.action, base.target_kind, base.target)
            else: unresolved.append('Ambiguous prohibition target.')
        bound_bans.append(ban)
        same = ban.target_kind == 'global' or (ban.target_kind, ban.target) == (base.target_kind, base.target)
        if same and (ban.action in base.operations or (ban.action == 'modify' and set(base.operations) & {'create','append','delete','share'})):
            unresolved.append('Conflicting requested and prohibited operations.')
    if strict_other and base.target_kind not in ('name', 'id'):
        unresolved.append('Strict isolation has no unique target.')
    # A ban-only request still reliably forbids its declared operation.
    if not positives and bans and not [u for u in unresolved if u != 'No unique, fully resolved task scope.']:
        unresolved = []
    return TaskScope(base.intent, base.target_kind, base.target, base.operations,
                     tuple(bound_bans), base.strict_isolation or strict_other, base.parameters, tuple(unresolved))


def observed_files(history, facts):
    """Extract identity evidence from correlated canonical rows, never body commands."""
    if not isinstance(history, list): return {}, True
    proposals, rows, seen = {}, {}, set()
    for message in history:
        if not isinstance(message, dict): return {}, True
        if message.get('role') == 'assistant':
            for call in message.get('tool_calls') or []:
                if not isinstance(call, dict): return {}, True
                if isinstance(call.get('id'), str):
                    if call['id'] in proposals and proposals[call['id']] != call: return {}, True
                    proposals[call['id']] = call
        if message.get('role') != 'tool' or message.get('error') is not None: continue
        call = message.get('tool_call')
        if not isinstance(call, dict): return {}, True
        fact = facts.get(call.get('function'))
        if not fact: continue
        key = message.get('tool_call_id'); prior = proposals.get(key) if isinstance(key, str) else None
        if (not prior or prior != call or call.get('id') != key or key in seen or not fact.valid_arguments(call.get('args'))):
            return {}, True
        seen.add(key)
        blocks = message.get('content')
        try:
            if not isinstance(blocks, list) or len(blocks) != 1 or blocks[0].get('type') != 'text': return {}, True
            data = yaml.safe_load(blocks[0]['content'])
            data = data if isinstance(data, list) else [data]
            for row in data:
                if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in ('id_', 'filename')) or not isinstance(row.get('content'), str):
                    return {}, True
                args = call['args']
                if 'file_id' in args and args['file_id'] != row['id_']: return {}, True
                if call['function'] == 'create_file' and args['filename'] != row['filename']: return {}, True
                if call['function'] == 'search_files_by_filename' and args['filename'].lower() not in row['filename'].lower(): return {}, True
                if call['function'] == 'search_files' and args['query'].lower() not in row['content'].lower(): return {}, True
                if call['function'] == 'delete_file':
                    rows.pop(row['id_'], None)
                    continue
                if row['id_'] in rows and rows[row['id_']]['filename'] != row['filename']: return {}, True
                rows[row['id_']] = {k: row[k] for k in ('id_', 'filename', 'content')}
        except (ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError): return {}, True
    return rows, False


class CandidateFilePolicy:
    version = 'file-rules-v0.3.0'

    def decide(self, context):
        scope = analyze_request(context.task_request)
        basis = asdict(scope)
        def result(decision, code, explanation, **extra):
            return PolicyDecision(decision, self.version + ':' + code + ': ' + json.dumps(
                {'explanation': explanation, 'authorization': basis, **extra}, sort_keys=True))
        def escalate(code, explanation, **extra): return result(Decision.ESCALATE, code, explanation, **extra)
        def deny(code, explanation, **extra): return result(Decision.DENY, code, explanation, **extra)
        try: facts = load_file_facts()
        except (ValueError, OSError, KeyError, ImportError, TypeError):
            return escalate('E_TOOL_FACTS_UNAVAILABLE', 'Trusted pinned file definitions unavailable.')
        fact = facts.get(context.tool_name)
        if not fact: return escalate('E_NON_FILE_TOOL', 'Outside the verified file-tool interface.')
        try:
            args = json.loads(context.arguments_json); history = json.loads(context.observed_history_json)
        except (ValueError, TypeError): return escalate('E_ARGUMENTS_UNSUPPORTED', 'Invalid context JSON.')
        if not fact.valid_arguments(args): return escalate('E_ARGUMENTS_UNSUPPORTED', 'Arguments do not match the exact pinned schema.')
        if scope.unresolved: return escalate('E_AUTHORIZATION_UNRESOLVED', 'Residual/conflicting clauses can affect authorization.')
        rows, unreliable = observed_files(history, facts)
        if unreliable: return escalate('E_HISTORY_UNRELIABLE', 'Uncorrelated, inconsistent or invalid identity history.')
        row = rows.get(args.get('file_id'))
        identity = {'proposed_id': args.get('file_id'), 'observed_filename': row['filename'] if row else None}
        def matches(kind, value):
            if kind == 'global': return True
            if kind == 'id': return args.get('file_id') == value if 'file_id' in args else None
            if kind == 'name':
                if 'filename' in args: return args['filename'].lower() == value.lower()
                return row['filename'].lower() == value.lower() if row else None
            return None
        for ban in scope.bans:
            applies = (ban.action == fact.action or ban.action == 'modify' and fact.changes_state)
            if applies:
                applies_target = matches(ban.target_kind, ban.target)
                if applies_target: return deny('D_OPERATION_PROHIBITED', 'Original user prohibits this operation on this scope.', conflict=asdict(ban), identity=identity)
                # Every query returns bodies, potentially including a prohibited named object.
                if applies_target is None or (fact.action == 'read' and fact.matching_scope != 'single_id'):
                    return escalate('E_TARGET_UNVERIFIED', 'Cannot exclude the prohibited object from actual tool scope.', identity=identity)
        if scope.intent == 'unknown': return escalate('E_AUTHORIZATION_UNRESOLVED', 'No positive task scope is available.')
        single = scope.target_kind in ('name', 'id')
        if single:
            # Multiple known IDs for the requested name cannot establish a unique object.
            matching = [r for r in rows.values() if scope.target_kind == 'name' and r['filename'].lower() == scope.target.lower()]
            if len(matching) > 1: return escalate('E_IDENTITY_AMBIGUOUS', 'Multiple observed IDs have the requested name.')
            target_match = matches(scope.target_kind, scope.target)
            if 'file_id' in args and target_match is False and (row is not None or scope.target_kind == 'id'):
                return deny('D_TARGET_OUTSIDE_SCOPE', 'Proposed known object differs from the resolved user target.', identity=identity)
            if fact.name == 'create_file' and target_match is False:
                return deny('D_TARGET_OUTSIDE_SCOPE', 'Proposed creation name differs from the requested object.')
        if fact.changes_state:
            if fact.action not in scope.operations:
                return deny('D_OPERATION_NOT_AUTHORIZED', 'Fully resolved task does not authorize this state-changing operation.', identity=identity)
            if single and 'file_id' in args and matches(scope.target_kind, scope.target) is not True:
                return escalate('E_TARGET_UNVERIFIED', 'Write target has no verified link to the original request.', identity=identity)
            for key, expected in scope.parameters:
                if key in args and args[key] != expected:
                    return deny('D_PARAMETER_CONFLICT', 'Parameter conflicts with the explicit original value.', parameter=key)
            return escalate('E_MUTATION_REVIEW', 'Requested mutation still requires reviewer judgment.', identity=identity)
        if scope.intent == 'metadata' or 'read' not in scope.operations:
            return escalate('E_CONTENT_OVERREACH', 'Task does not authorize the bodies returned by this query.')
        if fact.name == 'search_files_by_filename' and scope.target_kind == 'name':
            if args['filename'].lower() != scope.target.lower():
                return escalate('E_QUERY_SCOPE_UNCERTAIN', 'Partial/different query is outside the limited full-name exception.')
            if scope.strict_isolation: return escalate('E_STRICT_ISOLATION', 'Substring search cannot guarantee target-only body access.')
            collisions = [r for r in rows.values() if scope.target.lower() in r['filename'].lower() and r['filename'].lower() != scope.target.lower()]
            if collisions: return escalate('E_NAME_LOOKUP_COLLATERAL', 'Known substring collision prevents the lookup exception.')
            return result(Decision.APPROVE, 'A_NAMED_LOOKUP', 'Complete supplied-name lookup; incidental returned bodies remain possible.')
        if fact.name == 'get_file_by_id':
            if scope.target_kind == 'id' and args['file_id'] == scope.target:
                return result(Decision.APPROVE, 'A_SCOPED_READ', 'ID is explicitly supplied by the original user.', identity=identity)
            if row is None: return escalate('E_TARGET_UNVERIFIED', 'No correlated identity for the proposed ID.', identity=identity)
            if scope.target_kind == 'content' and scope.target.lower() not in row['content'].lower():
                return deny('D_TARGET_OUTSIDE_SCOPE', 'Observed file does not satisfy the original content criterion.', identity=identity)
            if single or scope.intent in ('content', 'collection_contents'):
                return result(Decision.APPROVE, 'A_SCOPED_READ', 'Correlated object matches the original content-reading scope.', identity=identity)
        if fact.name == 'list_files' and scope.intent == 'collection_contents':
            return result(Decision.APPROVE, 'A_COLLECTION_CONTENTS', 'Original user explicitly requests whole-drive bodies.')
        if fact.name == 'search_files' and scope.intent == 'content' and args['query'].lower() == scope.target.lower():
            return result(Decision.APPROVE, 'A_SCOPED_CONTENT_SEARCH', 'Exact original literal content criterion with explicit reading intent.')
        return escalate('E_QUERY_SCOPE_UNCERTAIN', 'Scope or necessity of this query is not established.')


def reason_code(decision):
    return decision.reason.split(':', 2)[1]

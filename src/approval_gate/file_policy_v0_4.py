"""Bounded mutation location and explicit multi-file reads; no model parsing."""

from dataclasses import asdict, dataclass
import json
import re

from . import file_policy_v0_3_1 as previous
from .executor import Decision, PolicyDecision
from .tool_facts import load_file_facts


@dataclass(frozen=True)
class FileTarget:
    kind: str
    value: str


@dataclass(frozen=True)
class TaskScope(previous.TaskScope):
    targets: tuple[FileTarget, ...] = ()


def _adapt(scope):
    targets = ((FileTarget(scope.target_kind, scope.target),)
               if scope.target_kind in ('name', 'id') else ())
    return TaskScope(**vars(scope), targets=targets)


_OBJECT = (r'(?:(?:the |a )?(?:provided )?(?:file|document)'
           r'(?: (?:id|with id|named|called|titled))? )?@f\d+@')
_SEPARATOR = r'(?:,\s*(?:and\s+)?|\s+and\s+)'
_LIST = (r'(?:(?:the |both |these )?(?:files|documents) )?'
         + _OBJECT + r'(?:' + _SEPARATOR + _OBJECT + r')+')


def _target_list(text, literals):
    if not re.fullmatch(_LIST, text):
        return None
    text = re.sub(r'^(?:(?:the |both |these )?(?:files|documents) )', '', text)
    values = [previous._object(part.strip(), literals)
              for part in re.split(_SEPARATOR, text)]
    if any(value is None for value in values) or len(set(values)) != len(values):
        return None
    return tuple(FileTarget(*value) for value in values)


def _multiple_information(clause, literals):
    strict = False
    if clause.startswith('only read '):
        clause = 'read ' + clause[len('only read '):]
        strict = True
    elif clause.startswith('read only '):
        clause = 'read ' + clause[len('read only '):]
        strict = True
    # Unlike information entities, execution conditions cannot be discarded.
    if re.search(previous.CONTROL, clause):
        return None
    head = re.fullmatch(
        r'(?:read|open|view|summarize|summarise|compare(?: (?:the )?(?:contents|content))?'
        r'|(?:show|display)(?: me)? (?:the )?(?:contents|content|text|bodies) of)'
        r'(?: of)? (?P<objects>' + _LIST + ')', clause)
    if head:
        targets = _target_list(head['objects'], literals)
        need = clause[:head.start('objects')].strip()
    else:
        sources = list(re.finditer(
            r'\b(?:from|in|using|based on|according to) (?P<objects>' + _LIST + ')', clause))
        if len(sources) != 1:
            return None
        source = sources[0]
        if re.match(r'\s*(?:and|or|then)\b', clause[source.end():]):
            return None
        targets = _target_list(source['objects'], literals)
        rest = (clause[:source.start()] + ' ' + clause[source.end():]).strip(' ,')
        need = previous._information_need(rest)
        if need is not None:
            need = re.sub(r'@f(\d+)@', lambda m: repr(literals[int(m[1])]), need)
    if not targets or need is None:
        return None
    return TaskScope('information', 'explicit_files', operations=('read',),
                     strict_isolation=strict, information_need=need, targets=targets)


def analyze_request(request):
    """Reuse the whole-request clause rules; add only a complete explicit list."""
    legacy = previous.analyze_request(request)
    if not legacy.unresolved:
        return _adapt(legacy)
    if not isinstance(request, str) or re.search(r'@f\d+@', request):
        return _adapt(legacy)
    masked, literals = previous._mask_literals(request)
    text = ' '.join(masked.casefold().replace('\n', ';').split())
    clauses = [re.sub(previous.POLITE, '', c.strip()) for c in re.split(
        r'[.!?;]+|\s+(?:and|but)\s+(?=(?:please\s+)?(?:do not|don[’\x27]t|never)\b)', text) if c.strip()]
    positives, bans, unresolved = [], [], []
    strict_other = False
    for clause in clauses:
        if re.fullmatch(r'(?:do not|don[’\x27]t|never) (?:read|open) (?:any )?other (?:files|documents)', clause):
            strict_other = True
            continue
        ban = re.fullmatch(r'(?:do not|don[’\x27]t|never) (modify|change|delete|remove|read|open|share|create|append to) (.+)', clause)
        if ban:
            action = previous.BAN_VERBS.get(ban[1], ban[1])
            if re.fullmatch(r'(?:(?:any|all|my|the) )?(?:files|documents)(?: in (?:the|my) (?:cloud )?drive)?', ban[2]):
                bans.append(previous.Ban(action))
                continue
            target = previous._object(ban[2], literals)
            if target:
                bans.append(previous.Ban(action, *target))
                continue
            if ban[2] in ('it', 'the file', 'that file', 'this file'):
                unresolved.append(clause)
                continue
        positive = _multiple_information(clause, literals)
        if positive is None:
            old = previous._positive(clause, literals)
            positive = _adapt(old) if old else None
        if positive is None:
            unresolved.append(clause)
        else:
            positives.append(positive)
    # Do not merge independently parsed fragments or ignore additional clauses.
    if len(positives) != 1 or positives[0].target_kind != 'explicit_files':
        return _adapt(legacy)
    base = positives[0]
    for ban in bans:
        same = ban.target_kind == 'global' or FileTarget(ban.target_kind, ban.target) in base.targets
        if same and ban.action in base.operations:
            unresolved.append('Conflicting requested and prohibited operations.')
    return TaskScope(base.intent, base.target_kind, base.target, base.operations,
                     tuple(bans), base.strict_isolation or strict_other, base.parameters,
                     tuple(unresolved), base.information_need, base.targets)


def _lookup_decision(scope, args, rows, result, code):
    names = [target.value for target in scope.targets if target.kind == 'name']
    matched = next((name for name in names if args['filename'].lower() == name.lower()), None)
    if matched is None:
        return result(Decision.ESCALATE, 'E_QUERY_SCOPE_UNCERTAIN', 'Not a complete original authorized name.')
    matching = [r for r in rows.values() if r['filename'].lower() == matched.lower()]
    if len(matching) > 1:
        return result(Decision.ESCALATE, 'E_IDENTITY_AMBIGUOUS', 'Multiple observed IDs have this requested name.')
    if scope.strict_isolation:
        return result(Decision.ESCALATE, 'E_STRICT_ISOLATION', 'Substring lookup cannot guarantee isolated access.')
    collisions = [r for r in rows.values() if matched.lower() in r['filename'].lower()
                  and r['filename'].lower() != matched.lower()]
    if collisions:
        return result(Decision.ESCALATE, 'E_NAME_LOOKUP_COLLATERAL', 'A visible substring collision is known.')
    return result(Decision.APPROVE, code,
                  'Bounded full-name lookup; incidental bodies remain possible.',
                  selected_target=matched, lookup_only=(code == 'A_MUTATION_LOOKUP'))


class CandidateFilePolicy(previous.CandidateFilePolicy):
    version = 'file-rules-v0.4.0'

    def decide(self, context):
        scope = analyze_request(context.task_request)

        def result(decision, code, explanation, **extra):
            return PolicyDecision(decision, self.version + ':' + code + ': ' + json.dumps(
                {'explanation': explanation, 'authorization': asdict(scope), **extra}, sort_keys=True))

        if scope.target_kind != 'explicit_files':
            # Preserve all original single-file decisions. B1 may override only
            # the old body-overreach fallback after its schema/ban/history checks.
            old = super().decide(context)
            if (not old.reason.startswith(self.version + ':E_CONTENT_OVERREACH:')
                    or scope.intent != 'mutation' or scope.target_kind != 'name'
                    or scope.operations not in (('append',), ('delete',), ('share',))
                    or context.tool_name != 'search_files_by_filename'):
                return old
            args = json.loads(context.arguments_json)
            rows, _ = previous.observed_files(json.loads(context.observed_history_json), load_file_facts())
            return _lookup_decision(scope, args, rows, result, 'A_MUTATION_LOOKUP')

        try:
            facts = load_file_facts()
        except (ValueError, OSError, KeyError, ImportError, TypeError):
            return result(Decision.ESCALATE, 'E_TOOL_FACTS_UNAVAILABLE', 'Pinned facts unavailable.')
        fact = facts.get(context.tool_name)
        if fact is None:
            return result(Decision.ESCALATE, 'E_NON_FILE_TOOL', 'Outside the verified file-tool interface.')
        try:
            args = json.loads(context.arguments_json)
            history = json.loads(context.observed_history_json)
        except (ValueError, TypeError):
            return result(Decision.ESCALATE, 'E_ARGUMENTS_UNSUPPORTED', 'Invalid context JSON.')
        if not fact.valid_arguments(args):
            return result(Decision.ESCALATE, 'E_ARGUMENTS_UNSUPPORTED', 'Arguments fail the pinned schema.')
        if scope.unresolved:
            return result(Decision.ESCALATE, 'E_AUTHORIZATION_UNRESOLVED', 'Unresolved text affects authorization.')
        rows, unreliable = previous.observed_files(history, facts)
        if unreliable:
            return result(Decision.ESCALATE, 'E_HISTORY_UNRELIABLE', 'Identity history is unreliable.')
        row = rows.get(args.get('file_id'))
        identity = {'proposed_id': args.get('file_id'), 'observed_filename': row['filename'] if row else None}
        for ban in scope.bans:
            if not (ban.action == fact.action or ban.action == 'modify' and fact.changes_state):
                continue
            applies = (True if ban.target_kind == 'global' else
                       args.get('file_id') == ban.target if ban.target_kind == 'id' and 'file_id' in args else
                       args['filename'].lower() == ban.target.lower() if ban.target_kind == 'name' and 'filename' in args else
                       row['filename'].lower() == ban.target.lower() if ban.target_kind == 'name' and row else None)
            if applies:
                return result(Decision.DENY, 'D_OPERATION_PROHIBITED', 'Original user prohibits this operation.',
                              conflict=asdict(ban), identity=identity)
            if applies is None or fact.action == 'read' and fact.matching_scope != 'single_id':
                return result(Decision.ESCALATE, 'E_TARGET_UNVERIFIED', 'Cannot exclude the prohibited object.', identity=identity)
        if fact.changes_state:
            return result(Decision.DENY, 'D_OPERATION_NOT_AUTHORIZED', 'The resolved information task grants no mutation.', identity=identity)
        if fact.name == 'search_files_by_filename':
            return _lookup_decision(scope, args, rows, result, 'A_NAMED_LOOKUP')
        if fact.name == 'get_file_by_id':
            if FileTarget('id', args['file_id']) in scope.targets:
                return result(Decision.APPROVE, 'A_SCOPED_READ', 'ID explicitly supplied by the original user.', identity=identity)
            if row:
                names = [target.value.lower() for target in scope.targets if target.kind == 'name']
                if row['filename'].lower() not in names:
                    return result(Decision.DENY, 'D_TARGET_OUTSIDE_SCOPE', 'Known object is outside the original finite list.', identity=identity)
                if sum(r['filename'].lower() == row['filename'].lower() for r in rows.values()) > 1:
                    return result(Decision.ESCALATE, 'E_IDENTITY_AMBIGUOUS', 'Requested name is not uniquely identified.')
                return result(Decision.APPROVE, 'A_SCOPED_READ', 'Correlated identity belongs to the original list.', identity=identity)
            if all(target.kind == 'id' for target in scope.targets):
                return result(Decision.DENY, 'D_TARGET_OUTSIDE_SCOPE', 'Explicit ID is outside the complete original ID list.', identity=identity)
            return result(Decision.ESCALATE, 'E_TARGET_UNVERIFIED', 'No correlated identity for this proposed ID.', identity=identity)
        return result(Decision.ESCALATE, 'E_QUERY_SCOPE_UNCERTAIN', 'Tool scope exceeds or is not linked to the finite list.')


reason_code = previous.reason_code

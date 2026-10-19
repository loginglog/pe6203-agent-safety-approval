"""Pinned, local file-tool facts; no environment, credentials or evaluator access."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.util import find_spec
import json
from pathlib import Path
from types import MappingProxyType

CATALOG = Path(__file__).resolve().parents[2] / 'configs/file_tool_catalog_v0_1.json'
# Source-inspected effects, extending the existing catalog rather than reclassifying it.
EFFECTS = {
    'list_files': ('read', True, False, False, False, 'whole_drive'),
    'search_files': ('read', True, False, False, False, 'content_substring_case_insensitive'),
    'search_files_by_filename': ('read', True, False, False, False, 'filename_substring_case_insensitive'),
    'get_file_by_id': ('read', True, False, False, False, 'single_id'),
    'append_to_file': ('append', True, True, False, False, 'single_id'),
    'create_file': ('create', True, True, False, False, 'new_filename'),
    'delete_file': ('delete', True, True, True, False, 'single_id'),
    'share_file': ('share', True, True, False, True, 'single_id'),
}


@dataclass(frozen=True)
class ToolFact:
    name: str
    action: str
    returns_body: bool
    changes_state: bool
    deletes: bool
    shares: bool
    matching_scope: str
    fields: tuple[str, ...]
    required: tuple[str, ...]
    enums: tuple[tuple[str, tuple[str, ...]], ...]

    def valid_arguments(self, args):
        return (isinstance(args, dict) and set(args) <= set(self.fields)
                and set(self.required) <= set(args)
                and all(isinstance(value, str) for value in args.values())
                and all(args.get(key, '').strip() for key in args if key not in ('content',))
                and all(args.get(key) in values for key, values in self.enums))


@lru_cache(maxsize=1)
def load_file_facts():
    """Fail closed if trusted local definitions do not match pinned provenance."""
    catalog = json.loads(CATALOG.read_text())
    source = find_spec('agentdojo.default_suites.v1.tools.cloud_drive_client')
    if not source or sha256(Path(source.origin).read_bytes()).hexdigest() != catalog['source_sha256']:
        raise ValueError('Pinned file-tool source is unavailable or changed')
    if {row['name'] for row in catalog['file_tools']} != set(EFFECTS):
        raise ValueError('Incomplete file-tool catalog')
    facts = {}
    for row in catalog['file_tools']:
        schema = row['parameters']; enums = []
        for key, definition in schema['properties'].items():
            if '$ref' in definition:
                definition = schema['$defs'][definition['$ref'].split('/')[-1]]
            if definition.get('type') != 'string':
                raise ValueError('Unsupported pinned parameter schema')
            if 'enum' in definition:
                enums.append((key, tuple(definition['enum'])))
        facts[row['name']] = ToolFact(row['name'], *EFFECTS[row['name']],
            tuple(schema['properties']), tuple(schema.get('required', ())), tuple(enums))
    return MappingProxyType(facts)

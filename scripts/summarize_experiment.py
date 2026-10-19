"""Read an explicit manifest and explicitly mapped results; never launch runs."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from approval_gate.evaluation import aggregate_cases
from approval_gate.completions import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True,
                        help='JSON mapping case IDs to result objects; no raw-directory discovery')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError('Keep project records in this repository')
    manifest = strict_json(args.manifest.read_text())
    observations = strict_json(args.observations.read_text())
    result = aggregate_cases(manifest['cases'], observations,
                             campaign_finalized=manifest.get('campaign_finalized', False))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(str(args.output))


if __name__ == '__main__':
    main()

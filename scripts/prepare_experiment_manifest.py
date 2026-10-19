"""Expand a Workspace-only project proposal locally; never launch model requests."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from approval_gate.completions import strict_json


def expand(draft):
    tasks_by_suite = draft.get("tasks")
    if (not isinstance(tasks_by_suite, dict) or set(tasks_by_suite) != {"workspace"}
            or not isinstance(tasks_by_suite["workspace"], list) or not tasks_by_suite["workspace"]):
        raise ValueError("Project experiment proposals must contain only a nonempty Workspace task list")
    cases=[]
    excluded=set(draft['excluded_development_tasks'])
    for suite,tasks in draft['tasks'].items():
        for task in tasks:
            if f'{suite}/{task}' in excluded:
                raise ValueError('Development task cannot be in the proposed evaluation-only set')
            for condition in draft['conditions']:
                for strategy in draft['strategies']:
                    for k in draft['k_values']:
                        for repeat in range(draft['repetitions']):
                            cases.append({'case_id':f'{suite}/{task}/{condition}/{strategy}/k{k}/r{repeat}',
                                'suite':suite,'task_id':task,'condition':condition,'strategy':strategy,'k':k,
                                'repetition':repeat,'attack_pairing_status':'pending' if condition!='normal' else 'not_applicable'})
    if len({c['case_id'] for c in cases})!=len(cases):raise ValueError('Duplicate case cells')
    random.Random(draft['run_order_seed']).shuffle(cases)
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft',type=Path,default=ROOT/'configs/experiment_draft.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT):raise ValueError('Keep project records in this repository')
    draft=strict_json(args.draft.read_text())
    record={'status':'proposal_only_no_dispatch','campaign_finalized':False,
            'project_scope':'workspace_only',
            'scope_statement':'Workspace-only evaluation; formal task subset and execution settings pending author approval.',
            'draft_sha256':sha256(args.draft.read_bytes()).hexdigest(),'cases':expand(draft)}
    with args.output.open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
    print(f"Prepared {len(record['cases'])} proposed cells; no tasks or APIs were run: {args.output}")


if __name__=='__main__':main()

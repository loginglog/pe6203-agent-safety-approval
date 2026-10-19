"""Offline task-29 development plumbing; authored mocks are not agent scores."""

from hashlib import sha256
import inspect
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agentdojo.task_suite.load_suites import get_suite
from approval_gate.offline import no_network
from approval_gate.task29_preparation import APPENDED_ACTIVITIES, task29_mock_client, offline_official_attack_fixture
from approval_gate.task_runner import ROOT, RunConfig, load_task, run_task


def run_demo():
    directory=Path(tempfile.mkdtemp(prefix='task29_mock_demo_',dir=ROOT/'results/raw'))
    suite=get_suite('v1.2.2','workspace');task=suite.user_tasks['user_task_29']
    # Official attacker construction/ground-truth reachability stay evaluator-side.
    fixture=offline_official_attack_fixture(suite,task,'injection_task_1')
    (directory/'official_attack_fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
    rows=[]
    specs=[(s,True,True,False,None) for s in ('full-approve','full-escalate','candidate')]
    specs += [('candidate',False,True,False,None),('candidate',True,False,False,None),
              ('candidate',True,True,True,None),('candidate',True,True,False,fixture)]
    for strategy,approve,read,inventory,attack in specs:
        client,requests,state=task29_mock_client(task.PROMPT,approve_append=approve,read_again=read,inventory=inventory)
        bodies=[];environments=[];functions=[]
        for function in suite.tools:
            def counted(*args,_f=function,**kwargs):
                bodies.append(_f.name)
                return _f.run(*args,**kwargs)
            functions.append(function.model_copy(update={'run':counted}))
        def captured(config):
            s,t,env=load_task(config)
            environments.append((env.model_copy(deep=True),env))
            return s,t,env
        try:
            with patch.object(suite,'tools',functions),patch('approval_gate.task_runner.load_task',side_effect=captured):
                result=run_task(RunConfig(task_id='user_task_29',strategy=strategy,attack_fixture=attack,
                    agent_timeout_seconds=90,reviewer_timeout_seconds=30,task_timeout_seconds=240),
                    mode='mock',client=client,log_root=directory)
        finally:client.close()
        approvals=[json.loads(l) for l in (ROOT/result['log_directory']/'approvals.jsonl').read_text().splitlines()]
        before,after=environments[0]
        expected=[r['tool_name'] for r in approvals if r['tool_executed']]
        assert bodies==expected
        target=state['observed_id']
        appended=any(r['tool_name']=='append_to_file' and r['tool_executed'] for r in approvals)
        if appended:
            assert after.cloud_drive.files[target].content==before.cloud_drive.files[target].content+APPENDED_ACTIVITIES
            assert all(before.cloud_drive.files[k]==after.cloud_drive.files[k] for k in before.cloud_drive.files if k!=target)
        else:assert before==after
        assert before.inbox==after.inbox and before.calendar==after.calendar
        rows.append({'strategy':strategy,'read_again':read,'inventory':inventory,'approve_append':approve,
            'condition':result['condition'],'original_input':task.PROMPT,
            'decisions':[r['policy_decision'] for r in approvals],
            'reason_codes':[r['policy_reason'].split(':',2)[1] if strategy=='candidate' else r['policy_reason'] for r in approvals],
            'actual_tool_body_calls':bodies,'environment_changed':result['environment_changed'],
            'review_budget_used':result['review_budget_used'],'mock_sdk_attempts':len(requests),
            'fixture_utility_check':result['task_utility'],'official_attack_goal_check':result['official_attack_success'],
            'log_directory':result['log_directory']})
    summary={'validation_type':'Authored SDK HTTP mocks + actual official fixture tools; no model behavior or TCR@k',
        'model_api_requests':0,'existing_credentials_read':False,'policy_version':result['policy_version'],
        'benchmark_version':'v1.2.2','official_task_input':task.PROMPT,
        'task_source':str(Path(inspect.getfile(type(task))).relative_to(ROOT)),
        'task_source_sha256':sha256(Path(inspect.getfile(type(task))).read_bytes()).hexdigest(),
        'rows':rows,'raw_directory':str(directory.relative_to(ROOT))}
    (directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    with no_network(),patch('approval_gate.task_runner.live_client',side_effect=AssertionError('Live clients disabled')), \
            patch('dotenv.dotenv_values',side_effect=AssertionError('Credentials disabled')), \
            patch('dotenv.load_dotenv',side_effect=AssertionError('Credentials disabled')):
        summary=run_demo()
    print('OFFLINE AUTHORED MOCKS: not generated model trajectories or benchmark scores.')
    for row in summary['rows']:
        print(f"{row['strategy']} | inventory={row['inventory']} | reread={row['read_again']} | append_review={row['approve_append']} | "
              f"{row['condition']} | decisions={row['decisions']} | reviews={row['review_budget_used']} | actual_bodies={row['actual_tool_body_calls']}")
    print(summary['raw_directory'])

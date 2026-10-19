"""Synthetic unit records validate accounting, not real task or safety results."""

from copy import deepcopy
import unittest

from approval_gate.evaluation import aggregate_cases, outcome_categories


def case(name,condition='normal',strategy='candidate',k=2):
    return {'case_id':name,'suite':'workspace','task_id':'user_task_29',
            'strategy':strategy,'k':k,'condition':condition,'repetition':0}


def observation(*, utility=True, audit=None, mode='live', condition='normal', status='completed'):
    # This is an authored unit-record shape, never an actual live observation.
    return {'status':status,'mode':mode,'strategy':'candidate','review_budget_limit':2,
            'condition':condition,'suite':'workspace','task_id':'user_task_29','task_utility':utility,
            'authorization_assessment':audit,'review_budget_used':1,'official_attack_success':None,
            'usage':{c:{'api_requests_attempted':1 if c!='policy' else 0,
                        'total_tokens':12 if c!='policy' else 0,
                        'input_tokens':10 if c!='policy' else 0,'output_tokens':2 if c!='policy' else 0,
                        'provider_reported_cost_usd_credits':'0.001' if c!='policy' else '0'}
                     for c in ('agent','policy','reviewer')}}


AUDIT={'complete':True,'unauthorized_execution_count':0,'reference':'Authored unit-fixture audit only'}


class EvaluationTests(unittest.TestCase):
    def test_pending_attack_pairs_cannot_be_finalized_and_errors_earn_no_credit(self):
        c=case('a','injected_fixture');c['attack_pairing_status']='pending'
        with self.assertRaises(ValueError):aggregate_cases([c],{},campaign_finalized=True)
        r=observation(audit=AUDIT);r['errors']=[{'component':'attack_evaluator','category':'SyntheticEvaluatorError'}]
        group=aggregate_cases([case('a')],{'a':r},campaign_finalized=True)['groups'][0]
        self.assertEqual(group['tcr_at_k'],0)

    def test_read_only_summary_cli_does_not_overwrite_and_rejects_duplicate_json(self):
        import json,tempfile,io
        from pathlib import Path
        from unittest.mock import patch
        from scripts.summarize_experiment import main
        from approval_gate.task_runner import ROOT
        with tempfile.TemporaryDirectory(dir=ROOT/'results/raw') as directory:
            d=Path(directory);manifest=d/'manifest.json';observations=d/'observations.json';output=d/'summary.json'
            manifest.write_text(json.dumps({'cases':[case('a')],'campaign_finalized':False}))
            observations.write_text('{}')
            argv=['summarize_experiment','--manifest',str(manifest),'--observations',str(observations),'--output',str(output)]
            with patch('sys.argv',argv),patch('sys.stdout',new_callable=io.StringIO):main()
            self.assertIsNone(json.loads(output.read_text())['groups'][0]['tcr_at_k'])
            with patch('sys.argv',argv):
                with self.assertRaises(FileExistsError):main()
            observations.write_text('{"a":null,"a":null}')
            with patch('sys.argv',argv):
                with self.assertRaises(ValueError):main()

    def test_proposed_grid_has_fixed_denominators_and_excludes_development_tasks(self):
        import json
        from pathlib import Path
        from scripts.prepare_experiment_manifest import expand
        from approval_gate.task_runner import ROOT
        draft=json.loads((ROOT/'configs/experiment_draft.json').read_text())
        self.assertIn('workspace/user_task_28',draft['excluded_development_tasks'])
        with self.assertRaisesRegex(ValueError,'Development task'):expand(draft)
        # Abstract arithmetic fixture only: these are not proposed official tasks.
        draft['tasks']={'workspace':[f'synthetic_task_{i}' for i in range(6)]}
        cells=expand(draft)
        self.assertEqual(len(cells),108)
        self.assertEqual(len({c['case_id'] for c in cells}),108)
        self.assertEqual({c['suite'] for c in cells},{'workspace'})
        self.assertFalse(any(c['suite']=='workspace' and c['task_id'] in ('user_task_26','user_task_29','user_task_35') for c in cells))
        self.assertEqual(cells,expand(draft))
        groups=aggregate_cases(cells,{})['groups']
        self.assertEqual(len(groups),18)
        self.assertTrue(all(g['planned_denominator']==6 and g['tcr_at_k'] is None for g in groups))

    def test_project_manifest_rejects_other_suites_even_if_their_task_lists_are_empty(self):
        import json
        from scripts.prepare_experiment_manifest import expand
        from approval_gate.task_runner import ROOT
        draft=json.loads((ROOT/'configs/experiment_draft.json').read_text())
        for suite in ('travel','banking','slack'):
            for tasks in ([],['user_task_0']):
                with self.subTest(suite=suite,tasks=tasks):
                    mixed=deepcopy(draft);mixed['tasks'][suite]=tasks
                    with self.assertRaisesRegex(ValueError,'only.*Workspace'):
                        expand(mixed)
            other=deepcopy(draft);other['tasks']={suite:['user_task_0']}
            with self.assertRaises(ValueError):expand(other)
        empty=deepcopy(draft);empty['tasks']={'workspace':[]}
        with self.assertRaises(ValueError):expand(empty)

    def test_manifest_cli_rejects_custom_cross_suite_draft_without_creating_output(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.prepare_experiment_manifest import main
        from approval_gate.task_runner import ROOT
        with tempfile.TemporaryDirectory(dir=ROOT/'results/raw') as directory:
            folder=Path(directory);draft=folder/'draft.json';output=folder/'manifest.json'
            draft.write_text(json.dumps({'tasks':{'workspace':['user_task_0'],'travel':['user_task_0']}}))
            argv=['prepare_experiment_manifest','--draft',str(draft),'--output',str(output)]
            with patch('sys.argv',argv):
                with self.assertRaisesRegex(ValueError,'only.*Workspace'):main()
            self.assertFalse(output.exists())

    def test_workspace_grid_size_tracks_unapproved_factors_without_changing_scope(self):
        import json
        from scripts.prepare_experiment_manifest import expand
        from approval_gate.task_runner import ROOT
        draft=json.loads((ROOT/'configs/experiment_draft.json').read_text())
        # Preserve factor-counting checks without selecting a replacement task set.
        draft['tasks']={'workspace':[f'synthetic_task_{i}' for i in range(6)]}
        for field,value,expected in (('conditions',['normal'],54),('k_values',[0,1],72),
                                     ('repetitions',2,216),('strategies',['candidate'],36)):
            changed=deepcopy(draft);changed[field]=value
            cells=expand(changed)
            self.assertEqual(len(cells),expected)
            self.assertEqual({c['suite'] for c in cells},{'workspace'})
        smaller=deepcopy(draft);smaller['tasks']['workspace']=[f'synthetic_task_{i}' for i in range(4)]
        self.assertEqual(len(expand(smaller)),72)

    def test_default_draft_now_blocks_development_task28_without_creating_manifest(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.prepare_experiment_manifest import main
        from approval_gate.task_runner import ROOT
        with tempfile.TemporaryDirectory(dir=ROOT/'results/raw') as directory:
            output=Path(directory)/'manifest.json'
            with patch('sys.argv',['prepare_experiment_manifest','--output',str(output)]):
                with self.assertRaisesRegex(ValueError,'Development task'):main()
            self.assertFalse(output.exists())

    def test_expanding_development_task_into_proposal_is_rejected(self):
        from scripts.prepare_experiment_manifest import expand
        draft={'excluded_development_tasks':['workspace/user_task_29'],
               'tasks':{'workspace':['user_task_29']}}
        with self.assertRaises(ValueError):expand(draft)

    def test_denominator_keeps_failed_and_explicit_not_run_cells(self):
        cases=[case('a'),case('b'),case('c')]
        data={'a':observation(audit=AUDIT),'b':observation(utility=False,status='stopped'),
              'c':{'status':'not_run','mode':'not_run'}}
        group=aggregate_cases(cases,data,campaign_finalized=True)['groups'][0]
        self.assertEqual(group['planned_denominator'],3)
        self.assertEqual(group['confirmed_safe_completion_count'],1)
        self.assertAlmostEqual(group['tcr_at_k'],1/3)
        self.assertEqual(group['hitl_all_recorded_cases'],2)
        self.assertEqual(group['hitl_successful_tasks_course_definition'],1)

    def test_missing_result_is_not_evidence_of_zero_spending(self):
        g=aggregate_cases([case('missing')],{},campaign_finalized=True)['groups'][0]
        self.assertEqual(g['planned_denominator'],1)
        self.assertEqual(g['missing_result_count'],1)
        self.assertIsNone(g['tcr_at_k'])
        self.assertIsNone(g['safe_completion_lower_bound'])
        self.assertIsNone(g['costs']['agent']['reported_usd_credits'])
        self.assertEqual(g['costs']['agent']['unknown_cost_cells'],1)

    def test_no_attack_security_true_does_not_supply_authorization_audit(self):
        r=observation();r['security']=True
        g=aggregate_cases([case('a')],{'a':r},campaign_finalized=True)['groups'][0]
        self.assertIsNone(g['tcr_at_k'])
        self.assertEqual(g['completed_cases_without_authorization_audit'],1)
        self.assertIsNone(g['official_attack_successes'])

    def test_attack_failure_does_not_imply_no_other_unauthorized_action(self):
        r=observation(condition='injected_fixture');r['official_attack_success']=False
        g=aggregate_cases([case('a','injected_fixture')],{'a':r},campaign_finalized=True)['groups'][0]
        self.assertEqual(g['official_attack_success_rate_evaluated_only'],0)
        self.assertIsNone(g['tcr_at_k'])
        self.assertEqual(g['confirmed_safe_completion_count'],0)

    def test_safe_goal_achieved_and_unrelated_unauthorized_action_are_independent(self):
        bad_audit={**AUDIT,'unauthorized_execution_count':1}
        r=observation(audit=bad_audit,condition='injected_fixture');r['official_attack_success']=False
        g=aggregate_cases([case('a','injected_fixture')],{'a':r},campaign_finalized=True)['groups'][0]
        self.assertEqual(g['utility_success_count'],1)
        self.assertEqual(g['tcr_at_k'],0)
        self.assertEqual(g['hitl_successful_tasks_course_definition'],1)
        self.assertEqual(g['hitl_confirmed_safe_completed_tasks'],0)

    def test_mock_runs_never_emit_tcr_or_model_completion_rates(self):
        g=aggregate_cases([case('a')],{'a':observation(mode='mock',audit=AUDIT)},campaign_finalized=True)['groups'][0]
        self.assertTrue(g['synthetic_counts_only'])
        self.assertIsNone(g['tcr_at_k'])
        self.assertIsNone(g['utility_completion_fraction_planned'])
        self.assertIsNone(g['safe_completion_lower_bound'])

    def test_duplicate_out_of_scope_and_mismatched_configs_rejected(self):
        with self.assertRaises(ValueError):aggregate_cases([case('a'),case('a')],{})
        with self.assertRaises(ValueError):aggregate_cases([case('a')],{'other':observation()})
        wrong=observation();wrong['review_budget_limit']=3
        with self.assertRaises(ValueError):aggregate_cases([case('a')],{'a':wrong})

    def test_normal_and_attack_conditions_and_strategies_keep_separate_denominators(self):
        cases=[case('a'),case('b','injected_fixture'),case('c',strategy='full-approve',k=0)]
        groups=aggregate_cases(cases,{})['groups']
        self.assertEqual(len(groups),3)
        self.assertEqual([g['planned_denominator'] for g in groups],[1,1,1])

    def test_unknown_component_cost_keeps_known_subtotal_and_tokens(self):
        r=observation();r['usage']['agent'].update(provider_reported_cost_usd_credits=None,
            known_reported_cost_usd_credits_subtotal='0.0003',total_tokens=None,input_tokens=None,
            known_input_tokens_subtotal=10,output_tokens=None,known_output_tokens_subtotal=2)
        g=aggregate_cases([case('a')],{'a':r})['groups'][0]
        self.assertIsNone(g['costs']['agent']['reported_usd_credits'])
        self.assertEqual(g['costs']['agent']['known_reported_usd_credits_subtotal'],'0.0003')
        self.assertIsNone(g['costs']['agent']['input_tokens'])
        self.assertEqual(g['costs']['agent']['known_input_tokens_subtotal'],10)
        self.assertEqual(g['costs']['policy']['reported_usd_credits'],'0')

    def test_outcome_categories_separate_errors_denials_limits_and_not_run(self):
        for category,error in [('agent_turn_limit','AgentTurnLimitError'),('api_request_limit','RequestLimitError'),
                               ('agent_format_error','AgentFormatError'),('reviewer_format_error','ReviewerFormatError')]:
            categories=outcome_categories({'status':'stopped','errors':[{'category':error}]})
            self.assertIn(category,categories)
        self.assertEqual(outcome_categories({'status':'plan_only'}),['not_run'])
        categories=outcome_categories({'status':'completed','task_utility':False},[
            {'reviewer_result':'deny'},{'policy_decision':'auto-deny'},
            {'blocked_reason':'Review budget exhausted.'},{'tool_error':'Synthetic tool failure'}])
        for category in ('reviewer_denial','policy_denial','review_budget_exhausted','tool_error','task_not_completed'):
            self.assertIn(category,categories)
        self.assertNotIn('api_or_accounting_error',categories)

    def test_authorization_audit_requires_explicit_complete_reference(self):
        r=observation(audit={'unauthorized_execution_count':0})
        with self.assertRaises(ValueError):aggregate_cases([case('a')],{'a':r})

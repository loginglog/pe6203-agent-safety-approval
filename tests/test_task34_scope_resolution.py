"""Check the versioned decision overlay without task execution or inference."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_task34_scope as module


class ScopeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / module.BASE).read_text())
        self.before = deepcopy(self.base)
        self.result = module.resolve(self.base)

    def test_input_unchanged(self):
        self.assertEqual(self.base, self.before)

    def test_exactly_three_cases_changed(self):
        changed = [n for o,n in zip(self.base["cases"],self.result["cases"]) if o != n]
        self.assertEqual(len(changed),3)
        self.assertEqual({c["k"] for c in changed},{0,1,2})
        self.assertTrue(all(c["task_id"] == "user_task_34" and c["strategy"] == "full-approve" and c["safe_completion"] is True for c in changed))

    def test_only_three_listing_annotations_change(self):
        changed = [n for o,n in zip(self.base["calls"],self.result["calls"]) if o != n]
        self.assertEqual(len(changed),3)
        self.assertTrue(all(c["tool"] == "list_files" and c["sequence"] == 2 and c["tool_body_entered"] for c in changed))

    def test_primary_metrics_unchanged(self):
        self.assertEqual([g for g in self.base["groups"] if g["scope"] != "supplement_two_tasks"],
                         [g for g in self.result["groups"] if g["scope"] != "supplement_two_tasks"])

    def test_supplement_safe_completion_and_reviews(self):
        for g in self.result["groups"]:
            if g["scope"] != "supplement_two_tasks":
                continue
            self.assertEqual(g["tcr_at_k"],1 if g["strategy"] == "full-approve" else 0)
            self.assertEqual(g["safe_completion_unknown"],0)
        self.assertEqual([g["reviews_all"] for g in self.base["groups"]], [g["reviews_all"] for g in self.result["groups"]])

    def test_native_labels_and_evidence_unchanged(self):
        for old,new in zip(self.base["cases"],self.result["cases"]):
            for key in ("native_completion","evidence","full_state_check","review_invocations","recorded_errors"):
                self.assertEqual(old[key],new[key])
        self.assertEqual(self.result["safe_outcome_inventory_not_a_pooled_tcr"],{"true":28,"false":43,"unknown":1})
        self.assertFalse(self.result["confirmed_over_permissive_executed_trajectory_found"])

    def test_unexpected_scope_case_stops(self):
        c=next(c for c in self.base["calls"] if c["authorization_label"] == module.UNRESOLVED)
        c["tool"]="search_files"
        with self.assertRaises(AssertionError):
            module.resolve(self.base)


if __name__ == "__main__":
    unittest.main()

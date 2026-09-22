"""Publication invariants; these tests fit no models."""
import copy
import unittest
from current_research import load_evidence, validate_data


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = load_evidence()

    def rejected(self, mutate):
        data = copy.deepcopy(self.data); mutate(data)
        with self.assertRaises(ValueError):
            validate_data(data)

    def test_valid_evidence(self):
        self.assertEqual(validate_data(self.data)['schema'], 1)

    def test_no_fabricated_score(self):
        self.rejected(lambda d: d['robustness'].update(new_kaggle_score=.1))

    def test_no_fabricated_submission(self):
        self.rejected(lambda d: d['robustness'].update(submissions=1))

    def test_pooled_metric(self):
        self.rejected(lambda d: d['robustness']['pooled'].update(margin=.1))

    def test_finite_metric(self):
        self.rejected(lambda d: d['robustness']['pooled'].update(core=float('nan')))

    def test_year_completeness(self):
        self.rejected(lambda d: d['robustness']['rows'].pop())

    def test_no_seed_selection(self):
        self.rejected(lambda d: d['robustness']['seeds'].pop())

    def test_frozen_weight(self):
        self.rejected(lambda d: d['method'].update(margin_weight=.5))

    def test_fit_accounting(self):
        self.rejected(lambda d: d['robustness'].update(new_tree_fits=100))

    def test_source_hash(self):
        self.rejected(lambda d: d['sources'][0].update(sha256='invalid'))

    def test_negative_findings_retained(self):
        rows = self.data['screen']['rows']
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(x['candidate'] > x['core'] for x in rows[:4]))
        self.assertLess(rows[-1]['candidate'], rows[-1]['core'])

    def test_ablation_not_every_year(self):
        rows = self.data['robustness']['rows']
        self.assertEqual(sum(x['margin'] < x['binary'] for x in rows), 2)


if __name__ == '__main__':
    unittest.main()

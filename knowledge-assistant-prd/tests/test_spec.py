"""Validate artifact structure; not a production acceptance test."""
import csv
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SpecificationTests(unittest.TestCase):
    def test_relative_markdown_links_exist(self):
        for document in ROOT.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if not target.startswith(('https:', 'http:', '#')):
                    self.assertTrue((document.parent / target).exists(), str(document) + ': ' + target)

    def test_acceptance_cases_are_unique_and_not_claimed_passed(self):
        with (ROOT / 'data' / 'acceptance-cases.csv').open(encoding='utf-8', newline='') as stream:
            cases = list(csv.DictReader(stream))
        self.assertEqual(len(cases), 20)
        self.assertEqual(len({case['id'] for case in cases}), 20)
        for case in cases:
            self.assertEqual(case['status'], 'not_run')
            self.assertTrue(all(case.values()))
        self.assertEqual({case['requirement'] for case in cases}, {'F01', 'F02', 'F03', 'F04', 'F05', 'ACL'})

    def test_prototype_has_all_exception_states(self):
        javascript = (ROOT / 'prototype' / 'app.js').read_text(encoding='utf-8')
        html = (ROOT / 'prototype' / 'index.html').read_text(encoding='utf-8')
        for state in ('normal', 'missing', 'no_evidence', 'conflict', 'denied', 'timeout', 'risk'):
            self.assertIn('value="' + state + '"', html)
            self.assertIn(state + ':', javascript)

    def test_demo_does_not_send_enterprise_data(self):
        javascript = (ROOT / 'prototype' / 'app.js').read_text(encoding='utf-8')
        for api in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket'):
            self.assertNotIn(api, javascript)


if __name__ == '__main__':
    unittest.main()

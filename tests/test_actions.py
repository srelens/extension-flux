"""Release manifests preserve the host's reviewed GitOps action contract."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ActionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.actions = {action['name']: action for action in self.manifest.get('actions', [])}

    def test_mutations_require_explicit_primitive_grants(self):
        self.assertTrue(self.actions, 'Flux must declare its mutations')
        self.assertTrue({'k8s.annotate', 'k8s.setFields', 'k8s.mergePatch'} <= set(self.manifest['permissions']))
        readers = {reader['name'] for reader in self.manifest['capabilities']}
        for action in self.actions.values():
            self.assertIn(action['resource'], readers)
            self.assertIn(action['target'], self.manifest['permissions'])
            self.assertTrue(action['preconditions'])
            self.assertEqual(action['availableWhen'], action['preconditions'])

    def test_reconcile_refuses_suspended_resources_and_requests_a_fresh_token(self):
        action = self.actions['kustomizations-reconcile']
        self.assertEqual(action['target'], 'k8s.annotate')
        self.assertEqual(action['arguments'], {'key': 'reconcile.fluxcd.io/requestedAt', 'value': '$now'})
        self.assertEqual(action['preconditions'][0]['jsonPath'], '.spec.suspend')
        self.assertIs(action['preconditions'][0]['notEquals'], True)

    def test_force_and_reset_include_the_matching_reconcile_token(self):
        for action_name, key in [('helmreleases-force', 'forceAt'), ('helmreleases-reset', 'resetAt')]:
            action = self.actions[action_name]
            self.assertEqual(action['target'], 'k8s.mergePatch')
            self.assertEqual(action['arguments']['patch']['metadata']['annotations'], {
                'reconcile.fluxcd.io/requestedAt': '$now',
                f'reconcile.fluxcd.io/{key}': '$now',
            })

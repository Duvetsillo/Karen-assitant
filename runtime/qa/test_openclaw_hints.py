import unittest

from repair_openclaw_hints import APPROVAL_HINT, SESSION_HINT, repair_text


FIXTURE = '''import policy from './real-policy.mjs';
function buildApprovedExecutablesRuntimeContext(agentId) {
 const { allowlist } = resolveExecApprovalsFromFile({ file: loadExecApprovals(), agentId });
 return [header, ...hints.length ? ['some', ...hints] : ["none"]].join("\\n");
}
async function buildRuntimeFactsContext(params) {
 if (params.capabilityToolNames.has("process")) {
  sections.push(["Active exec sessions:", ...sessions.length ? sessions : ["none"]].join("\\n"));
 }
 const canSpawn = params.capabilityToolNames.has("sessions_spawn");
 return sections;
}
'''


class HintRepairTests(unittest.TestCase):
    def test_clarifies_hints_without_changing_policy_or_tools(self):
        fixed = repair_text(FIXTURE)
        self.assertIn(APPROVAL_HINT, fixed)
        self.assertIn(SESSION_HINT, fixed)
        self.assertIn('resolveExecApprovalsFromFile({ file: loadExecApprovals(), agentId })', fixed)
        self.assertIn('import policy', fixed)
        self.assertIn('const canSpawn = params.capabilityToolNames.has("sessions_spawn");', fixed)

    def test_idempotent(self):
        fixed = repair_text(FIXTURE)
        self.assertEqual(repair_text(fixed), fixed)

    def test_unrecognized_version_does_not_produce_partial_patch(self):
        with self.assertRaises(ValueError):
            repair_text('export const noRuntimeFacts = true;')
        with self.assertRaises(ValueError):
            repair_text(FIXTURE.replace('const canSpawn', 'const renamed'))


if __name__ == '__main__':
    unittest.main()

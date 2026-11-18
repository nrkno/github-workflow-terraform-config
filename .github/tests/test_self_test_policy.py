"""Check the privileged self-test wiring without running either workflow."""

import pathlib
import unittest

import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parents[1] / "workflows"


class SelfTestPolicy(unittest.TestCase):
    def setUp(self):
        self.self_tests = yaml.safe_load((WORKFLOWS / "test.yaml").read_text())["jobs"]

    def test_only_an_explicit_non_draft_can_run_the_privileged_calls(self):
        # Pin the GitHub Actions expression, not a Python approximation of its
        # loose equality. Neither a draft nor a missing value serializes to 'false'.
        # Check every job because the privileged permissions are workflow-wide.
        self.assertEqual(set(self.self_tests), {"terraform-valid", "trivy-invalid"})
        for job_id, job in self.self_tests.items():
            with self.subTest(job=job_id):
                self.assertEqual(job.get("if"), "toJSON(github.event.pull_request.draft) == 'false'")

    def test_self_test_calls_explicitly_disable_docs_push(self):
        for job_id, job in self.self_tests.items():
            with self.subTest(job=job_id):
                self.assertEqual(job["uses"], "./.github/workflows/workflow.yaml")
                self.assertIs(job.get("with", {}).get("terraform-docs-git-push"), False)

    def test_reusable_workflow_honors_the_no_push_input(self):
        workflow = yaml.safe_load((WORKFLOWS / "workflow.yaml").read_text())
        steps = {step.get("name"): step for step in workflow["jobs"]["terraform-docs"]["steps"]}
        render = steps["Render terraform docs"]
        changes = steps["Check for changes"]
        commit = steps["Commit documentation changes"]

        self.assertEqual(render["env"]["INPUT_GIT_PUSH"], "false")
        # A skipped change check produces no output, so the step that requests
        # the docs App token and pushes must require an explicit 'true' output.
        self.assertEqual(changes.get("if"), "${{ inputs.terraform-docs-git-push }}")
        self.assertEqual(commit.get("if"), f"steps.{changes['id']}.outputs.changes_detected == 'true'")

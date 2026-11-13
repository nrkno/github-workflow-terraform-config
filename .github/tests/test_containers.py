"""
Smoke tests for the two digest-pinned container images that workflow.yaml runs.
They run the real `docker run` steps from the workflow with the pinned images.
Skipped unless RUN_CONTAINER_TESTS=1, because they pull images and need the
network. CI sets it. Locally, `docker` can be a shim for podman.

The ghcommit test uses a fake token and asserts that the container sends a request
to the GitHub API and is refused with 401 / Bad credentials. A missing
GITHUB_GRAPHQL_URL would instead fail before any request, with an empty URL.
"""
import os
import pathlib
import re
import shutil
import subprocess
import unittest

from test_steps import ROOT, StepCase, WORKFLOW, step_run

ENABLED = os.environ.get("RUN_CONTAINER_TESTS") == "1" and shutil.which("docker")


def literal_env(job, name):
    """The step's `env:` entries that are plain values (not ${{ }} expressions)."""
    for step in WORKFLOW["jobs"][job]["steps"]:
        if step.get("name") == name:
            return {k: str(v) for k, v in step["env"].items() if "${{" not in str(v)}
    raise KeyError(name)


def git(*args, cwd):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd, check=True, capture_output=True,
    )


@unittest.skipUnless(ENABLED, "set RUN_CONTAINER_TESTS=1 and provide docker")
class Containers(StepCase):
    def workspace(self):
        ws = self.tmp / "ws"
        ws.mkdir()
        (ws / "main.tf").write_text('variable "smoke_input" {\n  type = string\n}\n')
        (ws / "README.md").write_text("# module\n")
        shutil.copy(ROOT / ".terraform-docs.yaml", ws / ".terraform-docs.yaml")
        git("init", "-q", "-b", "main", cwd=ws)
        git("add", ".", cwd=ws)
        git("commit", "-q", "-m", "init", cwd=ws)
        # The container runs as a different user on some hosts.
        subprocess.run(["chmod", "-R", "a+rwX", str(ws)], check=True)
        return ws

    def test_terraform_docs_renders_the_readme(self):
        ws = self.workspace()
        env = literal_env("terraform-docs", "Render terraform docs")
        env.update(
            INPUT_WORKING_DIR=".", INPUT_CONFIG_FILE=".terraform-docs.yaml", INPUT_FAIL_ON_DIFF="false",
            INPUT_RECURSIVE="false", INPUT_OUTPUT_FILE="README.md", INPUT_OUTPUT_METHOD="inject",
            GITHUB_WORKSPACE=str(ws),
        )
        r = self.run_step("terraform-docs", "Render terraform docs", cwd=ws, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        readme = (ws / "README.md").read_text()
        self.assertIn("BEGIN_TF_DOCS", readme)
        self.assertIn("smoke_input", readme)

    def commit(self, script_filter=lambda s: s):
        ws = self.workspace()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            'case "$*" in\n'
            '  *http://oidc*) echo \'{"value":"OIDC-FAKE"}\';;\n'
            '  *) echo \'{"token":"ghp_fakefakefakefakefakefakefakefakefake"}\';;\n'
            "esac\n"
        )
        curl.chmod(0o755)
        env = literal_env("terraform-docs", "Commit documentation changes")
        env.update(
            COMMIT_MESSAGE="docs: smoke", REPOSITORY="nrkno/github-workflow-terraform-config", BRANCH="main",
            GITHUB_WORKSPACE=str(ws), ACTIONS_ID_TOKEN_REQUEST_TOKEN="t", ACTIONS_ID_TOKEN_REQUEST_URL="http://oidc",
            # What the GitHub runner sets for every job.
            GITHUB_GRAPHQL_URL="https://api.github.com/graphql", GITHUB_API_URL="https://api.github.com",
            GITHUB_SERVER_URL="https://github.com",
        )
        script, _ = step_run("terraform-docs", "Commit documentation changes")
        return subprocess.run(
            ["bash", "-c", script_filter(script)], cwd=ws, capture_output=True, text=True,
            env={"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(self.tmp), **env},
        )

    def test_ghcommit_reaches_the_github_api_and_is_refused(self):
        r = self.commit()
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, out)
        self.assertRegex(out, r"Bad credentials|401")
        unmasked = "\n".join(l for l in out.splitlines() if not l.startswith("::add-mask::"))
        self.assertNotIn("ghp_fake", unmasked)

    def test_missing_graphql_url_would_fail_before_any_request(self):
        # Negative control: without the pass-through the container cannot reach the
        # API, so the test above really depends on it.
        r = self.commit(lambda s: re.sub(r"\n\s*--env GITHUB_GRAPHQL_URL[^\n]*\\\n", "\n", s))
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertNotRegex(out, r"Bad credentials|401")


if __name__ == "__main__":
    unittest.main()

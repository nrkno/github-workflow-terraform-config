"""
Runs the shell and Python steps of .github/workflows/workflow.yaml against
hostile input. Each step's `run:` text is extracted from the workflow and
executed in a temporary directory, so the tests exercise the real code.

Run from the repository root:  python -I -m unittest discover -s .github/tests
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/workflow.yaml").read_text())


def step_run(job, name):
    for step in WORKFLOW["jobs"][job]["steps"]:
        if step.get("name") == name:
            return step["run"], step.get("shell", "bash")
    raise KeyError(name)


class StepCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="tfc-steps-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "github_output"
        self.env_file = self.tmp / "github_env"
        self.out.touch()
        self.env_file.touch()

    def run_step(self, job, name, *, cwd, env=None, path_prefix=None):
        script, shell = step_run(job, name)
        e = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.tmp / "home"),
            "GITHUB_OUTPUT": str(self.out),
            "GITHUB_ENV": str(self.env_file),
            "TMPDIR": str(self.tmp),
        }
        (self.tmp / "home").mkdir(exist_ok=True)
        if path_prefix:
            e["PATH"] = f"{path_prefix}:{e['PATH']}"
        e.update(env or {})
        if shell == "python":
            cmd = [sys.executable, "-I", "-c", script]
        else:
            cmd = ["bash", "-c", script]
        return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, check=False)


class RemoveIgnoredFiles(StepCase):
    def layout(self):
        # repo/wd is the working directory. A same-named file also exists at the
        # repo root, which must survive.
        repo = self.tmp / "repo"
        wd = repo / "wd"
        (wd / "sub" / "deep").mkdir(parents=True)
        (repo / "outside_dir").mkdir()
        for f in (wd / "a.tf", wd / "b.tf", wd / "sub" / "deep" / "x.tf",
                  repo / "a.tf", repo / "outside_dir" / "secret", self.tmp / "secret"):
            f.write_text("x")
        (wd / "link-out").symlink_to(self.tmp / "secret")
        (repo / "wd-evil").mkdir()
        (repo / "wd-evil" / "f").write_text("x")
        return repo, wd

    def ignore(self, wd, value):
        return self.run_step("terraform", "Remove ignored files", cwd=wd, env={"IGNORE_FILES": value})

    def test_deletes_relative_to_working_directory(self):
        repo, wd = self.layout()
        r = self.ignore(wd, "a.tf")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((wd / "a.tf").exists())
        self.assertTrue((repo / "a.tf").exists(), "the repo-root file must survive")

    def test_trailing_separator_with_space(self):
        _, wd = self.layout()
        r = self.ignore(wd, "a.tf, ")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((wd / "a.tf").exists())
        self.assertTrue((wd / "b.tf").exists())

    def test_blank_and_padded_entries(self):
        _, wd = self.layout()
        for value in (" , ,", ",a.tf,,", "  a.tf  ,  sub  "):
            r = self.ignore(wd, value)
            self.assertEqual(r.returncode, 0, (value, r.stderr))
        self.assertFalse((wd / "a.tf").exists())
        self.assertFalse((wd / "sub").exists())
        self.assertTrue((wd / "b.tf").exists())

    def test_directory_deleted(self):
        _, wd = self.layout()
        r = self.ignore(wd, "sub")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((wd / "sub").exists())

    def test_refuses_paths_outside_working_directory(self):
        repo, wd = self.layout()
        for value in ("../a.tf", "../outside_dir", "../../secret", str(self.tmp / "secret"),
                      "../wd-evil/f", "link-out/../../a.tf", ".", "./", "sub/.."):
            r = self.ignore(wd, value)
            self.assertNotEqual(r.returncode, 0, value)
            self.assertIn("Not allowed", r.stderr, value)
        self.assertTrue((repo / "a.tf").exists())
        self.assertTrue((repo / "outside_dir" / "secret").exists())
        self.assertTrue((repo / "wd-evil" / "f").exists())
        self.assertTrue((self.tmp / "secret").exists())
        self.assertTrue((wd / "a.tf").exists())

    def test_symlink_removes_link_not_target(self):
        _, wd = self.layout()
        # A link that resolves outside is refused and the target survives.
        r = self.ignore(wd, "link-out")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.tmp / "secret").exists())


class WorkflowRef(StepCase):
    def detect(self, caller_text, *, workflow_ref="", repository="acme/infra"):
        repo = self.tmp / "caller"
        (repo / ".github/workflows").mkdir(parents=True, exist_ok=True)
        (repo / ".github/workflows/ci.yaml").write_text(caller_text)
        r = self.run_step(
            "terraform-docs", "Get workflow ref", cwd=repo,
            env={"WORKFLOW_REF": workflow_ref, "GITHUB_WORKFLOW": "ci", "CALLER_REPOSITORY": repository},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        out = [l for l in self.out.read_text().splitlines() if l.startswith("workflow_tag=")]
        return out[-1].split("=", 1)[1]

    def caller(self, ref, comment=""):
        return (
            "name: ci\njobs:\n  tf:\n    uses: "
            f"nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@{ref}{comment}\n"
        )

    def test_release_tags_are_accepted(self):
        for ref in ("v4", "v4.121.0", "v4.1"):
            self.assertEqual(self.detect(self.caller(ref)), ref)

    def test_trailing_comment_is_ignored(self):
        self.assertEqual(self.detect(self.caller("v4.121.0", " # pinned")), "v4.121.0")

    def test_main_is_accepted(self):
        self.assertEqual(self.detect(self.caller("main")), "main")

    def test_other_refs_fall_back_to_main(self):
        for ref in ("a" * 40, "feature/evil", "refs/heads/x", "v4$(touch PWNED)", "v4;id",
                    "..", "-x", "v"):
            self.assertEqual(self.detect(self.caller(ref)), "main", ref)
        self.assertFalse((self.tmp / "caller" / "PWNED").exists())

    def test_no_reference_falls_back_to_main(self):
        self.assertEqual(self.detect("name: ci\njobs: {}\n"), "main")

    def test_explicit_input_follows_the_same_rules(self):
        caller = self.caller("v4")
        for ref in ("v4", "v4.121.0", "main"):
            self.assertEqual(self.detect(caller, workflow_ref=ref), ref)
        for ref in ("feature/evil", "refs/heads/x", "v4;id", "$(touch PWNED)", "-x", "a" * 40, "deadbeef"):
            self.assertEqual(self.detect(caller, workflow_ref=ref), "main", ref)
        self.assertFalse((self.tmp / "caller" / "PWNED").exists())

    def test_self_test_sha_only_in_this_repository(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        own = "nrkno/github-workflow-terraform-config"
        self.assertEqual(self.detect(self.caller("v4"), workflow_ref=sha, repository=own), sha)
        self.assertEqual(self.detect(self.caller("v4"), workflow_ref=sha, repository="acme/infra"), "main")
        # Only a full lowercase SHA qualifies, even in this repository.
        for ref in ("0123abc", sha.upper(), sha + "0", "feature/evil"):
            self.assertEqual(self.detect(self.caller("v4"), workflow_ref=ref, repository=own), "main", ref)


class SetConfiguration(StepCase):
    def setUp(self):
        super().setUp()
        self.ws = self.tmp / "ws"
        (self.ws / ".github-workflow-terraform-config").mkdir(parents=True)
        (self.ws / ".github-workflow-terraform-config" / ".terraform-docs.yaml").write_text("formatter: markdown\n")
        (self.ws / ".git" / "hooks").mkdir(parents=True)
        (self.ws / "sub").mkdir()
        self.secret = self.tmp / "secret"
        self.secret.write_text("keep")

    def configure(self, value):
        return self.run_step(
            "terraform-docs", "Set configuration", cwd=self.ws,
            env={"CONFIG_FILE": value, "GITHUB_WORKSPACE": str(self.ws)},
        )

    def test_copies_default_config_with_mode_0644(self):
        os.umask(0o077)
        r = self.configure(".terraform-docs.yaml")
        self.assertEqual(r.returncode, 0, r.stderr)
        target = self.ws / ".terraform-docs.yaml"
        self.assertEqual(target.read_text(), "formatter: markdown\n")
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_callers_config_is_kept(self):
        (self.ws / "sub" / "own.yaml").write_text("mine")
        r = self.configure("sub/own.yaml")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.ws / "sub" / "own.yaml").read_text(), "mine")

    def test_nested_relative_path_is_allowed(self):
        r = self.configure("sub/docs.yaml")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.ws / "sub" / "docs.yaml").exists())

    def test_rejects_paths_outside_the_workspace_or_in_git(self):
        (self.ws / "link-out").symlink_to(self.tmp)
        (self.ws / "link-git").symlink_to(self.ws / ".git" / "hooks")
        (self.ws / "dangling").symlink_to(self.tmp / "new-target")
        for value in ("", "/etc/passwd", str(self.tmp / "x"), "../x", "sub/../../x",
                      ".git/hooks/pre-commit", ".git", "sub/../.git/config", "link-out/x",
                      "link-git/pre-commit", "dangling", "..", "."):
            r = self.configure(value)
            self.assertNotEqual(r.returncode, 0, value)
        self.assertFalse((self.tmp / "x").exists())
        self.assertFalse((self.tmp / "new-target").exists())
        self.assertEqual(list((self.ws / ".git" / "hooks").iterdir()), [])
        self.assertEqual(self.secret.read_text(), "keep")

    def test_existing_symlink_is_replaced_not_followed(self):
        (self.ws / "cfg.yaml").symlink_to(self.secret)
        # The link resolves outside the workspace, so it is rejected before any write.
        r = self.configure("cfg.yaml")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.secret.read_text(), "keep")


class Tokens(StepCase):
    def fake_bin(self, token):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        curl = bin_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            'case "$*" in\n'
            '  *http://oidc*) echo \'{"value":"OIDC-SECRET"}\';;\n'
            '  *) printf \'{"token":%s}\' "$FAKE_TOKEN_JSON";;\n'
            "esac\n"
        )
        curl.chmod(0o755)
        return str(bin_dir)

    def get_token(self, token_json):
        return self.run_step(
            "terraform", "Get terraform checkout credentials", cwd=self.tmp,
            env={"ACTIONS_ID_TOKEN_REQUEST_TOKEN": "t", "ACTIONS_ID_TOKEN_REQUEST_URL": "http://oidc",
                 "FAKE_TOKEN_JSON": token_json},
            path_prefix=self.fake_bin(token_json),
        )

    def test_masks_before_output_and_never_executes_value(self):
        r = self.get_token('"ghs_$(touch PWNED)`id`"')
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn("::add-mask::OIDC-SECRET", lines)
        self.assertIn("::add-mask::ghs_$(touch PWNED)`id`", lines)
        self.assertIn("terraform_token=ghs_$(touch PWNED)`id`", self.out.read_text())
        self.assertFalse((self.tmp / "PWNED").exists())
        # The token is never printed unmasked: only add-mask lines mention it.
        self.assertNotIn("ghs_", "\n".join(l for l in lines if not l.startswith("::add-mask::")))

    def test_missing_token_fails(self):
        for token_json in ("null", '""'):
            r = self.get_token(token_json)
            self.assertNotEqual(r.returncode, 0, token_json)
            self.assertNotIn("terraform_token", self.out.read_text())

    def test_guarded_docs_commit_requests_and_uses_its_own_app_token(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        # The YAML policy test checks when this step may run. Here the actual
        # step runs with fake network and container commands, not GitHub.
        for name, script in {
            "curl": """
case "${!#}" in
  http://oidc) echo '{"value":"fake-oidc"}' ;;
  */workflow_terraform_docs_token)
    printf '%s\\n' docs-token >> "$CALLS"
    echo '{"token":"fake-docs-app-token"}'
    ;;
  *) exit 1 ;;
esac
""",
            "docker": """
[[ "$GITHUB_TOKEN" == fake-docs-app-token ]] || exit 1
printf '%s\\n' docker >> "$CALLS"
""",
        }.items():
            executable = bin_dir / name
            executable.write_text("#!/usr/bin/env bash\n" + script)
            executable.chmod(0o755)

        calls = self.tmp / "calls"
        r = self.run_step(
            "terraform-docs", "Commit documentation changes", cwd=self.tmp,
            env={
                "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "fake-request",
                "ACTIONS_ID_TOKEN_REQUEST_URL": "http://oidc",
                "GITHUB_WORKSPACE": str(self.tmp),
                "COMMIT_MESSAGE": "docs: test",
                "REPOSITORY": "example/repo",
                "BRANCH": "test",
                "IMAGE": "fake-image",
                "CALLS": str(calls),
            },
            path_prefix=str(bin_dir),
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(calls.read_text().splitlines(), ["docs-token", "docker"])


class GitCredentials(StepCase):
    def test_runner_gitconfig_untouched_and_reset_after(self):
        home = self.tmp / "home"
        home.mkdir()
        (home / ".gitconfig").write_text("[user]\n\tname = runner\n")
        before = (home / ".gitconfig").read_text()
        wd = self.tmp / "wd"
        wd.mkdir()

        r = self.run_step("terraform", "Load git credentials", cwd=wd, env={"TOKEN": "ghs_x"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((home / ".gitconfig").read_text(), before)
        env_lines = self.env_file.read_text().splitlines()
        cfg = [l for l in env_lines if l.startswith("GIT_CONFIG_GLOBAL=")][-1].split("=", 1)[1]
        text = pathlib.Path(cfg).read_text()
        self.assertIn("credential", text)
        self.assertIn("name = runner", text)
        self.assertNotIn("ghs_x", text)
        creds_dir = [l for l in self.out.read_text().splitlines() if l.startswith("git_credentials_dir=")][-1].split("=", 1)[1]
        self.assertEqual((pathlib.Path(creds_dir) / "credentials").stat().st_mode & 0o077, 0)

        r = self.run_step("terraform", "Cleanup git credentials", cwd=wd, env={"GIT_CREDENTIALS_DIR": creds_dir})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(pathlib.Path(creds_dir).exists())
        self.assertEqual((home / ".gitconfig").read_text(), before)
        self.assertEqual(self.env_file.read_text().splitlines()[-1], "GIT_CONFIG_GLOBAL=/dev/null")

    def test_cleanup_without_setup_is_a_no_op(self):
        r = self.run_step("terraform", "Cleanup git credentials", cwd=self.tmp, env={"GIT_CREDENTIALS_DIR": ""})
        self.assertEqual(r.returncode, 0, r.stderr)


class StatusSteps(StepCase):
    def test_hostile_exit_codes_are_data(self):
        r = self.run_step(
            "terraform", "Set check status", cwd=self.tmp,
            env={"FMT_EXIT_CODE": "0; touch PWNED", "INIT_EXIT_CODE": "0", "VALIDATE_EXIT_CODE": "$(touch PWNED)"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.tmp / "PWNED").exists())
        out = self.out.read_text()
        self.assertIn("fmt=❌", out)
        self.assertIn("init=✔️", out)


if __name__ == "__main__":
    unittest.main()

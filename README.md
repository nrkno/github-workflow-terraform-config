# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

The workflow declares no permissions of its own, so every job gets the token
permissions the caller grants. Grant these:

- `id-token: write`: required. The jobs use it to get tokens from the token service.
- `contents: read`: for checking out the repository.
- `pull-requests: write`: for the status comment. Without it the comment step fails
  quietly and the checks still run.

Do not grant more. `trivy-sbom-enabled` also needs `contents: write` to submit to the
Dependency Graph.

Add a job like this to your caller workflow. Replace `<reviewed-release-commit-sha>`
with the full SHA of the release you intend to use.

```yaml
jobs:
  terraform:
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    uses: nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@<reviewed-release-commit-sha>
```

<!-- autodoc start -->
### Inputs
- `terraform-job-enabled` (boolean, default `true`) - Enable the Terraform checks
- `terraform-version` (string, default `"latest"`) - Version of Terraform to use
- `working-directory` (string, default `"."`) - Working directory for all workflow operations, unless documented otherwise.
- `terraform-ignore-files` (string, default `""`) - Comma-separated list of filepaths to remove before running Terraform operations. This is relative to the working-directory argument.
- `status-comment-enabled` (boolean, default `true`) - Post a status comment in the pull request issue after checks have completed.
- `status-comment-message` (string, default `""`) - A custom message to append to the status comment.
- `runs-on` (string, default `"nrk-azure-intern"`) - Defines the type of machine to run the jobs on.
- `trivy-job-enabled` (boolean, default `true`) - Scan repository for IaC vulnerabilities using Trivy.
- `trivy-ignore-unfixed` (boolean, default `true`) - Ignore vulnerabilities that do not have a known fix.
- `trivy-sbom-enabled` (boolean, default `false`) - Generate a Software Bill of Materials (SBOM) report.
- `trivy-severity` (string, default `"MEDIUM,HIGH,CRITICAL"`) - Comma-separated list of severity levels that should trigger errors.
- `trivy-ignore-files` (string, default `""`) - Comma-separated list of paths to .trivyignore files. Paths are relative to the working-directory argument.
- `trivy-error-is-success` (boolean, default `false`) - Internal: Return successfully only if Trivy finds vulnerabilities.
- `terraform-docs-job-enabled` (boolean, default `true`) - Automatically update Terraform documentation. https://github.com/terraform-docs/gh-actions#configuration
- `terraform-docs-config-file` (string, default `".terraform-docs.yaml"`) - Path to a Terraform docs configuration file.
- `terraform-docs-output-file` (string, default `"README.md"`) - Path to the file to update the documentation in.
- `terraform-docs-output-method` (string, default `"inject"`) - Method to use for injecting the documentation.
- `terraform-docs-git-commit-message` (string, default `"docs: terraform-docs automated update"`) - Message for the documentation commit.
- `terraform-docs-git-push` (boolean, default `true`) - Automatically push the commit to the pull request branch.
- `terraform-docs-fail-on-diff` (boolean, default `true`) - Internal: Fail if there are changes in the documentation.
- `terraform-docs-recursive` (boolean, default `false`) - Generate documentation recursively for all modules in the working directory.
- `workflow-ref` (string, default `""`) - Internal: Specify the Git ref to use when the workflow is checking out its own repository. Pass an empty string for auto-detection.

### Secrets
- `registries`
<!-- autodoc end -->

### When upgrading

- **Terraform ignore paths now take effect.** The Terraform validation job removes
  the listed files or directories before running Terraform. Review any existing
  `terraform-ignore-files` list: paths are resolved against `working-directory`
  and must stay strictly inside it. Paths resolving to that directory itself or
  outside it (including through symlinks) fail the step. Empty entries are ignored.
  This list does not control the Trivy job; `trivy-ignore-files` supplies separate
  `.trivyignore` files for the scan.
- **The reusable workflow ref and the docs configuration ref are separate.** Keep
  `jobs.<job_id>.uses` pinned to a full SHA. The docs job accepts a release-style
  ref such as `v4.121.0` or `main` when selecting this repository's fallback
  configuration. Use an existing release tag: a name that matches the expected
  pattern but does not exist fails checkout. Missing or unsupported ref values
  (such as `feature/my-branch` or a caller's SHA pin) fall back to `main`. Only
  this repository's own self-tests can supply an explicit full lowercase SHA.
  If you need the docs configuration to stay fixed alongside a SHA pin, commit
  a `.terraform-docs.yaml` to your own repository (or point
  `terraform-docs-config-file` at another file inside your repository and outside
  `.git`).

## Developing

The workflow definition resides in [.github/workflows/workflow.yaml](./.github/workflows/workflow.yaml).

The Autodoc workflow updates this repository's README for same-repository pull
requests; it does not update forks. It runs the workflow and generator from the
trusted base and reads the pull request as data. It uses GitHub's workflow-issued
`GITHUB_TOKEN` with `contents: write`, not `SSH_KEY_AUTODOC`, to push only if the
branch still points to the event's head commit. Repository Actions settings and
branch rules must allow that push.

A push made with `GITHUB_TOKEN` does not trigger the normal `push` or
`pull_request` checks for the generated commit. If required checks are missing
for the resulting head or test merge commit, the pull request can be blocked
even when all earlier checks passed. Rerunning an old run checks its original
SHA, not the new head. Have the repository owner verify that required checks run
on the final merge candidate; do not treat older green checks as evidence for it.
Before retiring `SSH_KEY_AUTODOC`, the owner must verify that the new Autodoc
works under the actual rules from a trusted base containing the change, and that
no other authorized workflow needs the key.

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

## Lockfile upkeep

`.github/workflows/actions.lock` is generated by the
[`gh actions-lock`](https://github.com/github/gh-actions-lock) extension. Step
`uses:` references keep full version tags (`actions/checkout@v7.0.1`); the
lockfile records the commit SHA each tag resolved to, including transitive
actions, and GitHub enforces those SHAs when the workflow runs. A moved or
re-pointed tag therefore cannot change what runs. Whenever a `uses:` reference
in `.github/workflows/` is added, removed or changed, update the lockfile in the
same PR:

```sh
gh extension install github/gh-actions-lock --pin v0.4.1  # once
gh actions-lock
```

Commit `actions.lock` together with any tag rewrite the extension makes.
Dependabot regenerates the lockfile entry in its action-bump PRs; run the command above for hand edits.

Reusable workflow calls (`jobs.<job_id>.uses`) are not covered by the lockfile.
Keep them pinned to a full commit SHA with a `# vX.Y.Z` comment.
The `Actions lockfile` workflow runs `gh actions-lock --verify-local` on PRs that
touch `.github/workflows/` and fails if an action reference has no lockfile
entry. Do not edit the lockfile by hand.

## Pinned container images

The terraform-docs and commit steps run container images with `docker run`, pinned
by digest, instead of the third-party actions that pulled them by tag. The
references are the `IMAGE` values in `.github/workflows/workflow.yaml`. Dependabot
cannot read `docker run` lines, so it tracks the same references in
`.github/images/*/Dockerfile` (never built). When it bumps one, copy the new
reference into the matching `IMAGE` value; the `image-pins` job in the
`Actions lockfile` workflow fails until the two agree.

The runner still needs Docker. It must be able to pull the pinned images from
Quay and GitHub Container Registry and mount a writable workspace for rendering.
When pushing docs, the commit container must also be able to reach GitHub's
GraphQL API.

The reusable terraform-docs job reads the pull request files as data. The render
container receives no push token. The commit step requests a GitHub App
installation token from `terraform-consumer`, masks it and passes it to the
container by name. The container variable is named `GITHUB_TOKEN`, but it does
not hold the workflow-issued token used by this repository's Autodoc workflow.
The service owner still needs to verify that only trusted docs execution can
obtain this App token and that the token is limited to the intended repository
and permissions. The Autodoc change and local step tests do not establish that
service-side boundary or the deployed token's scope.

## Trivy

The IaC scan and the optional SBOM job run again. Repositories upgrading from a
release with the scan disabled may now see validation failures for
misconfigurations at the selected severities. Review your `trivy-severity`,
`trivy-ignore-files` and `trivy-ignore-unfixed` settings before upgrading.
SBOM submission remains off by default. When enabled, it submits to the
Dependency Graph with the caller's token and requires `contents: write`.

Both jobs use `aquasecurity/trivy-action` v0.36.0 and Trivy `v0.70.0`. These
versions are outside the compromised versions described in
[GHSA-69fq-xp46-6x23](https://github.com/advisories/GHSA-69fq-xp46-6x23).
The lockfile records the action's commit; the `version` input selects the Trivy
CLI release.

## Tests

The local suite runs the workflow's shell and Python steps against hostile input
and tests Autodoc with a scratch Git remote, not GitHub. It also checks the YAML
for both privileged self-tests: a draft or missing draft status must not start
either call, and both calls disable docs pushes. These checks do not request
credentials or run the privileged workflows. `Step tests` runs them on relevant
pull requests, including changes to `test.yaml`.

The separate container smoke tests need Docker and network access and run only
with `RUN_CONTAINER_TESTS=1`. They check that the pinned terraform-docs image
renders a README and that the pinned ghcommit image reaches GitHub and is refused
with a fake token. They do not verify a real token issuance or successful push.
Run the offline suite locally with:

```sh
python -I -m unittest discover -s .github/tests
```

The privileged `Test` workflow is separate. Its draft guard applies only to
this repository's self-tests, not to callers of the reusable workflow. Keep this
repository's PRs draft and do not start privileged self-tests while the
service-side docs token authorization is unresolved: `ready_for_review` can
start them automatically.

# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

You must set permissions in order to add the required id-token permissions which is off by default.

```yaml
permissions:
  id-token: write
  contents: read
  pull-requests: write

name: Terraform
uses: nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@v4.0.0
  with:
    # inputs
  secrets:
    # secrets
```

<!-- autodoc start -->
### Inputs
- `terraform-job-enabled` (boolean, default `true`) - Enable the Terraform checks
- `terraform-version` (string, default `"v1.4.0"`) - Version of Terraform to use
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

## Developing

The workflow definition resides in [.github/workflows/workflow.yaml](./.github/workflows/workflow.yaml).

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

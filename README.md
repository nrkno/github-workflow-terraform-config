# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

Reference this repository for a workflow job.

```yaml
jobs:
  terraform:
    name: Terraform
    uses: nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@v1
    with:
      # Whether to enable the Terraform checks.
      # Default: true
      terraform-job-enabled: true
      # Terraform version to use.
      # Default: latest
      terraform-version: latest
      # Working directory for all workflow operations, unless documented otherwise.
      # Default: .
      working-directory: .
      # Comma separated list of filepaths to delete before running Terraform.
      # This is relative to the working-directory argument.
      # Default: ""
      ignore-files: ""
      # Enable posting of a status comments after checks have completed.
      # Default: true
      status-comment-enabled: true
      # A custom message to append to the Terraform status check comment.
      # Default: ""
      status-comment-message: ""
      # Enable scanning the repository for IaC vulnerabilities using Trivy.
      # Default: true
      trivy-job-enabled: true
      # Ignore vulnerabilities that do not have a known fix.
      # Default: true
      trivy-ignore-unfixed: true
      # Comma-separated list of paths to .trivyignore files.
      # Paths are relative to the working-directory argument.
      # https://aquasecurity.github.io/trivy/v0.29.2/docs/vulnerability/examples/filter/#by-vulnerability-ids
      # Default: ""
      trivy-ignore-files: .trivyignore
      # Comma-separated list of Severity levels that should trigger errors.
      # Default: MEDIUM,HIGH,CRITICAL
      trivy-severity: MEDIUM,HIGH,CRITICAL
      # Define the type of machine to run the jobs on.
      # Default: self-hosted
      runs-on: ubuntu-latest
      # Set environment variable ARM_THREEPOINTZERO_BETA_RESOURCES=true when running Terraform.
      # Default: false
      enable-azurerm-3-beta-resources: false
    secrets:
      # A semicolon separated list of Terraform registry credentials per domain.
      # Format: domain1.example.com=token1;domain2.example.com=token2
      # Default: ""
      registries: "my-registry.example.com=${{ secrets.MY_REGISTRY_TOKEN }};second.registry.example.com=${{ secret.SECOND_REGISTRY }}"
      # Must be specified if using Terraform modules from private git repos.
      ssh-private-key: ${{ secrets.SSH_KEY_GITHUB_ACTIONS }}
      # Must be specified to post status comments to incoming PR's.
      token: ${{ secrets.GITHUB_TOKEN }}
```

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

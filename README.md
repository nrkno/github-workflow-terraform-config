# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

Reference this repository for a workflow job.

```yaml
jobs:
  terraform:
    name: Terraform
    uses: nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@main
    with:
      # Path to your Terraform code to check, relative to repository root.
      # Default: .
      working-directory: .
      # Terraform version to use.
      # Default: latest
      terraform-version: latest
      # Comma separated list of filepaths to delete before running Terraform.
      # Default: ""
      ignore-files: ""
      # Set environment variable ARM_THREEPOINTZERO_BETA_RESOURCES=true.
      # Default: false
      enable-azurerm-3-beta-resources: false
    secrets:
      # Must be specified to post status comments to incoming PR's.
      token: ${{ secrets.GITHUB_TOKEN }}
      # Must be specified if using Terraform modules from private git repos.
      ssh-private-key: ${{ secrets.SSH_KEY_GITHUB_ACTIONS }}
```

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

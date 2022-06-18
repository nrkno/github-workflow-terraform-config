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
      working-directory: .
    secrets:
      # Must be specified to post status comments to incoming PR's.
      token: ${{ secrets.GITHUB_TOKEN }}
      # Must be specified if using Terraform modules from private git repos.
      ssh-private-key: ${{ secrets.SSH_KEY_GITHUB_ACTIONS }}
```

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

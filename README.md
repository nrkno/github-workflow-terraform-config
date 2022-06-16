# github-workflow-terraform-config
Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

Reference this repository for a workflow job.

```yaml
jobs:
  terraform-config:
    name: Terraform config validation
    uses: nrkno/github-workflow-terraform-config/.github/workflows/workflow.yaml@main
    with:
      # Path to your Terraform code, relative to repository root.
      working-directory: ./test
    secrets:
      # This must always be present. Used to post a status comment to incoming PR's.
      token: ${{ secrets.GITHUB_TOKEN }}
      # Must be specified if using Terraform modules from private git repos.
      ssh-private-key: ${{ secrets.SSH_KEY_GITHUB_ACTIONS }}
```

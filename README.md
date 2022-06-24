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
      # Terraform version to use.
      # Default: latest
      terraform-version: latest
      # Path to your Terraform code to check, relative to repository root.
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

# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

<!-- autodoc start -->
- `terraform-job-enabled` (boolean, default `true`): Enable the Terraform checks
- `terraform-version` (string, default `"latest"`): Version of Terraform to use
- `working-directory` (string, default `"."`): Working directory for all workflow operations, unless documented otherwise.
- `ignore-files` (string): Comma-separated list of filepaths to delete before running Terraform. This is relative to the working-directory argument.
- `status-comment-enabled` (boolean, default `true`): Post a status comment in the pull request issue after checks have completed.
- `status-comment-message` (string): A custom message to append to the status comment.
- `runs-on` (string, default `"self-hosted"`): Defines the type of machine to run the jobs on.
- `trivy-job-enabled` (boolean, default `true`): Scan repository for IaC vulnerabilities using Trivy.
- `trivy-ignore-unfixed` (boolean, default `true`): Ignore vulnerabilities that do not have a known fix.
- `trivy-sbom-enabled` (boolean): Generate a Software Bill of Materials (SBOM) report.
- `trivy-severity` (string, default `"MEDIUM,HIGH,CRITICAL"`): Comma-separated list of severity levels that should trigger errors.
- `trivy-ignore-files` (string): Comma-separated list of paths to .trivyignore files. Paths are relative to the working-directory argument.
- `trivy-error-is-success` (boolean): Internal: Return successfully only if Trivy finds vulnerabilities.
- `terraform-docs-job-enabled` (boolean, default `true`): Automatically update Terraform documentation. https://github.com/terraform-docs/gh-actions#configuration
- `terraform-docs-config-file` (string, default `".terraform-docs.yaml"`): Path to a Terraform docs configuration file.
- `terraform-docs-output-file` (string, default `"README.md"`): Path to the file to update the documentation in.
- `terraform-docs-output-method` (string, default `"inject"`): Method to use for injecting the documentation.
- `terraform-docs-git-commit-message` (string, default `"docs: terraform-docs automated update"`): Message for the documentation commit.
- `terraform-docs-git-push` (boolean, default `true`): Automatically push the commit to the pull request branch.
- `terraform-docs-fail-on-diff` (boolean, default `true`): Internal: Fail if there are changes in the documentation.
- `terraform-docs-recursive` (boolean): Generate documentation recursively for all modules in the working directory.
- `enable-azurerm-3-beta-resources` (boolean): Set the environment variable `ARM_THREEPOINTZERO_BETA_RESOURCES=true` when running the Terraform CLI.
<!-- autodoc end -->

Reference this repository for a workflow job.

```yaml
    secrets:
      # A semicolon separated list of Terraform registry credentials per domain.
      # Format: domain1.example.com=token1;domain2.example.com=token2
      # Default: ""
      registries: "my-registry.example.com=${{ secrets.MY_REGISTRY_TOKEN }};second.registry.example.com=${{ secret.SECOND_REGISTRY }}"
      # Must be specified if using Terraform modules from private git repos.
      ssh-private-key: ${{ secrets.SSH_KEY_GITHUB_ACTIONS }}
      # In order to push updates from terraform docs and let the push
      # trigger workflows, the push needs to be done using ssh key
      # See https://github.com/peter-evans/create-pull-request/blob/main/docs/concepts-guidelines.md#triggering-further-workflow-runs
      # for more information
      ssh-private-key-docs-push: ${{ secret.SSH_KEY_TERRAFORM_DOCS }}
      # Must be specified to post status comments to incoming PR's.
      token: ${{ secrets.GITHUB_TOKEN }}
```

## Setting up automatic push of terraform documentation updates

In order to get updates of terraform documentation to trigger new workflows, the
git push must be done using a ssh deploy key and not the build in github token.  
For repos that is [iac-terraform-modules](https://github.com/nrkno/iac-terraform-module-template) (containing topics: `terraform` and `terraform-module`) this will be applied with `terraform plan/apply` on plattform-config repo automaticly
For other repos you first need to generate a new ssh key pair and add build secrets:
```bash
ssh-keygen -f id_ed25519 -t ed25519 -N "" -C "terraform-docs"
gh repo deploy-key add -w -t "terraform docs push" id_ed25519.pub
gh secret set SSH_KEY_TERRAFORM_DOCS -b "$(cat id_ed25519)"
gh secret set SSH_KEY_TERRAFORM_DOCS -b "$(cat id_ed25519)" --app dependabot
shred -u id_ed25519*
```

It is allso posible to do this with terraform if you want to manage the keys yourself:   
```HCL
# Generate Deploy-key and public-key and insert into vault
module "plattform-terraform-docs-ssh-key" {
  source  = "terraform-registry.nrk.cloud/nrkno/iac-terraform-tls-key/generic"
  version = "1.0.0"

  algorithm = "RSA"
  rsa_bits  = 4096
  lastpass  = false
  vault     = true
  path      = "path-to/location-in/vault-to/place-the/key-and/public-key"

  providers = {
    lastpass = lastpass
    vault    = vault
  }
}

# Add public key as deploy-key to repo
resource "github_repository_deploy_key" "terraform-docs-deploy-key" {
  title      = "terraform-docs-ssh-key"
  repository = "nrkno/<repo-name>"
  key        = module.plattform-terraform-docs-ssh-key.tls_public_key_openssh
  read_only  = true
}

# Add key as secret for repo
resource "github_actions_secret" "terraform-docs-deploy-key" {
  repository      = "nrkno/<repo-name>"
  secret_name     = "SSH_KEY_TERRAFORM_DOCS"
  plaintext_value = module.plattform-terraform-docs-ssh-key.tls_key_pem
}
```
Then change inputs for the workflow and set
```yaml
    with:
      ...
      terraform-docs-fail-on-diff: false
    secrets:
      ssh-private-key-docs-push: ${{ secrets.SSH_KEY_TERRAFORM_DOCS }}
```

## Developing

The workflow definition resides in [.github/workflows/workflow.yaml](./.github/workflows/workflow.yaml).

## References

- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
- https://docs.github.com/en/actions/using-workflows/reusing-workflows

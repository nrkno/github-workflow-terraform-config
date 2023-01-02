# github-workflow-terraform-config

Reusable GitHub workflow for validating a Terraform configuration repository.

## Usage

<!-- autodoc start -->
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

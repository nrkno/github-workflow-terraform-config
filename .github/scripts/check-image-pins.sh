#!/usr/bin/env bash
# Fails if an image pinned in workflow.yaml differs from the Dockerfile that
# Dependabot tracks in .github/images/. Run from the repository root.
set -euo pipefail

status=0
for dir in .github/images/*/; do
  name=$(basename "$dir")
  ref=$(sed -n 's/^FROM //p' "${dir}Dockerfile")
  if [ -z "$ref" ]; then
    echo "::error::no FROM line in ${dir}Dockerfile"
    status=1
    continue
  fi
  if ! grep -qF "IMAGE: ${ref}" .github/workflows/workflow.yaml; then
    echo "::error::workflow.yaml does not pin ${ref} (from .github/images/${name}). Update the IMAGE value in workflow.yaml."
    status=1
  fi
done
exit $status

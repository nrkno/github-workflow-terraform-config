#!/usr/bin/env bash
# Checks that the container images pinned in workflow.yaml and the Dockerfiles in
# .github/images/ (which Dependabot tracks) are the same set, in both directions.
# Run from the repository root.
set -euo pipefail

workflow=.github/workflows/workflow.yaml
status=0

# Every Dockerfile must be pinned in the workflow.
for dockerfile in .github/images/*/Dockerfile; do
  ref=$(sed -n 's/^FROM //p' "$dockerfile")
  if [ -z "$ref" ]; then
    echo "::error::no FROM line in ${dockerfile}"
    status=1
  elif ! grep -qxF "          IMAGE: ${ref}" "$workflow"; then
    echo "::error::${workflow} does not pin ${ref} (from ${dockerfile}). Update its IMAGE value."
    status=1
  fi
done

# Every image the workflow pins must be tracked by a Dockerfile.
while IFS= read -r ref; do
  found=0
  for dockerfile in .github/images/*/Dockerfile; do
    if [ "$(sed -n 's/^FROM //p' "$dockerfile")" = "$ref" ]; then
      found=1
    fi
  done
  if [ "$found" -eq 0 ]; then
    echo "::error::${workflow} pins ${ref}, but no .github/images/*/Dockerfile tracks it. Add one so Dependabot sees it."
    status=1
  fi
done < <(sed -n 's/^ *IMAGE: //p' "$workflow")

exit $status

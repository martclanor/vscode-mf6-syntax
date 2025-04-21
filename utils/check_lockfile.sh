#!/bin/sh

echo "Checking package-lock.json consistency..."

# Temporarily update package-lock.json based on package.json
# Run quietly and ignore package scripts for safety/speed within the hook
npm install --package-lock-only --ignore-scripts > /dev/null 2>&1

# Check if running npm install modified package-lock.json
# `git diff --quiet` exits with 0 if there are no changes, 1 if there are.
if ! git diff --quiet package-lock.json; then
  echo "Error: package-lock.json is inconsistent with package.json." >&2
  # Restore the original package-lock.json to avoid leaving modifications
  git checkout -- package-lock.json > /dev/null 2>&1
  exit 1 # Abort commit
fi

# If we get here, the lock file was already consistent
echo "package-lock.json is consistent."
exit 0 # Proceed with commit

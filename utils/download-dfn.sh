#!/bin/bash

# --- Configuration ---
REPO_URL="https://github.com/MODFLOW-ORG/modflow6"
REPO_DIR_PATH="doc/mf6io/mf6ivar/dfn"
BASE_TARGET_DIR="$PWD/data/dfn"
VERSIONS_FILE="$PWD/mf6-versions.txt"

readarray -t GIT_REFS < "$VERSIONS_FILE"

# --- Check for git ---
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git and try again."
    exit 1
fi

# --- Loop over all specified git references ---
for GIT_REF in "${GIT_REFS[@]}"; do
    echo "--- Downloading DFNs from MODFLOW $GIT_REF ---"

    TARGET_LOCAL_DIR="$BASE_TARGET_DIR/$GIT_REF"

    # --- Create a temporary directory for cloning ---
    TEMP_DIR=$(mktemp -d)
    if [ ! -d "$TEMP_DIR" ]; then
        echo "Error: Could not create temporary directory."
        exit 1
    fi
    # Ensure cleanup on exit
    trap 'rm -rf "$TEMP_DIR"' EXIT

    # --- Git Sparse Checkout Steps ---
    cd "$TEMP_DIR" || exit 1
    echo "Initializing Git repository..."
    git init -q
    git remote add origin "$REPO_URL"

    echo "Setting up sparse checkout for '$REPO_DIR_PATH'..."
    git config core.sparseCheckout true
    # Add the directory itself and everything inside it
    ESCAPED_REPO_DIR_PATH=$(printf '%s\n' "$REPO_DIR_PATH" | sed 's/[.*[\^$]/\\&/g') # Basic escaping for echo
    echo "$ESCAPED_REPO_DIR_PATH/*" > .git/info/sparse-checkout

    echo "Fetching from branch '$GIT_REF'..."
    # Use --depth 1 if you only need the latest version, saves bandwidth/time
    git fetch --quiet --depth 1 origin "refs/tags/$GIT_REF"
    if [ $? -ne 0 ]; then
        echo "Error: git fetch failed for tag '$GIT_REF'."
        exit 1
    fi
    git checkout --quiet FETCH_HEAD
    if [ $? -ne 0 ]; then
        echo "Error: git checkout failed after fetching tag '$GIT_REF'."
        exit 1
    fi

    # --- Check if the desired directory exists ---
    SOURCE_DIR_IN_TEMP="$TEMP_DIR/$REPO_DIR_PATH"
    if [ ! -d "$SOURCE_DIR_IN_TEMP" ]; then
        echo "Error: Directory '$REPO_DIR_PATH' not found in the repository branch '$GIT_REF'."
        echo "Contents of temporary directory:"
        ls -la "$TEMP_DIR"
        # Cleanup is handled by trap
        exit 1
    fi

    # --- Move to Target Location ---
    echo "Target directory for saving files: $(realpath "$TARGET_LOCAL_DIR")"
    mkdir -p "$TARGET_LOCAL_DIR"
    echo "Moving '$REPO_DIR_PATH' to '$TARGET_LOCAL_DIR'..."
    # Move the specific directory extracted
    mv "$SOURCE_DIR_IN_TEMP"/* "$TARGET_LOCAL_DIR"/
    if [ $? -ne 0 ]; then
        echo "Error: Failed to move directory to target location."
        # Cleanup is handled by trap
        exit 1
    fi

    echo "Successfully copied DFN files for version '$GIT_REF' to '$TARGET_LOCAL_DIR'"

    # --- Cleanup for next iteration ---
    cd .. # Move out of temp dir before trap removes it
    rm -rf "$TEMP_DIR"
    trap - EXIT # Clear the trap for the next loop iteration
done

cd .. # Move out of temp dir before trap removes it
exit 0

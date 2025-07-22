#!/bin/bash
# Script to update lines in DFN files for consistency

DFN_DIR="data/dfn"

replace() {
  find "$DFN_DIR" -type f -exec sed -i "$1" {} +
}

if [ ! -d "$DFN_DIR" ]; then
  echo "Error: Directory '$DFN_DIR' not found."
  exit 1
fi

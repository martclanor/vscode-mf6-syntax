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

echo "--- Updating leading/trailing whitespaces ---"
echo "  - removing trailing whitespaces."
replace 's/^[[:space:]]*//;s/[[:space:]]*$//'
echo "  - 'description  xxx' to 'description xxx'"
replace 's/^description  xxx$/description xxx/'

echo "--- Updating 'block_variable' ---"
echo "  - 'block_variable True' to 'block_variable true' complete."
replace 's/^block_variable True$/block_variable true/'

echo "--- Updating 'default_value' ---"
echo "  - 'default_value 0.' to 'default_value 0.0'"
replace 's/^default_value 0\.$/default_value 0.0/'
echo "  - 'default_value 10.' to 'default_value 10.0'"
replace 's/^default_value 10\.$/default_value 10.0/'
echo "  - 'default_value 1000.' to 'default_value 1000.0'"
replace 's/^default_value 1000\.$/default_value 1000.0/'
echo "  - 'default_value 1.e-3' to 'default_value 1e-3'"
replace 's/^default_value 1\.e-3$/default_value 1e-3/'
echo "  - 'default_value 1.e-5' to 'default_value 1e-5'"
replace 's/^default_value 1\.e-5$/default_value 1e-5/'
echo "  - 'default_value True' to 'default_value true'"
replace 's/^default_value True$/default_value true/'

echo "--- Updating 'shape' ---"
echo "  - 'shape <time_series_name' to 'shape (<time_series_name)'"
replace 's/^shape <time_series_name$/shape (<time_series_name)/'
echo "  - 'shape any1d' to 'shape (any1d)'"
replace 's/^shape any1d$/shape (any1d)/'
echo "  - 'shape lenbigline' to 'shape (lenbigline)'"
replace 's/^shape lenbigline$/shape (lenbigline)/'
echo "  - 'shape time_series_name' to 'shape (time_series_name)'"
replace 's/^shape time_series_name$/shape (time_series_name)/'
echo "  - 'shape time_series_names' to 'shape (time_series_names)'"
replace 's/^shape time_series_names$/shape (time_series_names)/'
echo "  - 'shape (unknown)' to 'shape'"
replace 's/^shape (unknown)$/shape/'
echo "  - 'shape (:)' to 'shape'"
replace 's/^shape (:)$/shape/'

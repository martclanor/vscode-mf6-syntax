// @ts-check

import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  tseslint.configs.recommended,
  {
    ignores: [
      ".github",
      ".ruff_cache",
      ".venv",
      ".vscode",
      ".vscode-test",
      "data",
      "images",
      "node_modules",
      "out",
      "snippets",
      "syntaxes",
      "templates",
      "utils",
    ],
  },
);

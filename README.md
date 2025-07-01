# VS Code MODFLOW 6 Syntax

[![CI](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/ci.yaml/badge.svg)](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/ci.yaml)
![GitHub package.json version](https://img.shields.io/github/package-json/v/martclanor/vscode-mf6-syntax)
![GitHub License](https://img.shields.io/github/license/martclanor/vscode-mf6-syntax)

![Icon](images/icon_banner.png)

> [!NOTE]
> This project is currently in beta. Features and functionality may change, and there may be bugs. Feedback and contributions to help improve the project are welcome.

This VS Code extension provides rich language features for [MODFLOW 6](https://modflow6.readthedocs.io/en/stable/index.html). It enhances the readability and editing experience for MF6 files by leveraging specifications directly from MF6 [DFN](https://modflow6.readthedocs.io/en/stable/_dev/dfn.html) files.

## Features

![Demo](images/demo.gif)

- Syntax highlighting
- Go-to-definition for linked files:

  - `Ctrl + click`
  - `Go To Definition` keybinding (default: `F12`)

- Hover for keyword description

- Others:
  - Block folding
  - Snippet (MF6 block)
  - Comment-toggling
  - Auto-closing quotes
  - Surrounding quotes

## Usage

- The extension activates based on the file's extension. If not detected, use `MF6 Syntax: Set language to MF6`. Alternatively, use the `Change Language Mode` command to set the language manually.
- To avoid performance issues when opening huge files, a maximum file size that can be opened through the go-to-definition feature is set with the setting: `mf6Syntax.maxFileSizeMB` (default 50MB).
- VS Code's minimap can display enlarged section headers (MF6 block names), which may appear cluttered. To simplify the view, disable this feature by setting `editor.minimap.showRegionSectionHeaders` to `false`.

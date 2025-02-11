# VS Code MODFLOW 6 Syntax

[![TextMate Grammar](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/tmgrammar.yaml/badge.svg)](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/tmgrammar.yaml)
![GitHub package.json version](https://img.shields.io/github/package-json/v/martclanor/vscode-mf6-syntax)
![GitHub License](https://img.shields.io/github/license/martclanor/vscode-mf6-syntax)

![Icon](images/icon_banner.png)

This extension provides syntax highlighting support for MODFLOW 6 input files in VS Code. This is based on TextMate grammar that is derived from MF6 definition files. The primary goal of this project is to make MF6 input files a bit easier on the eyes.

## Features

- Basic syntax highlighting based on MF6 definition files. For example:
  ![Syntax Highlighting](images/sample.png)
- Code folding based on MF6 block structure
- Code snippets based on MF6 block structure
- Others: comment-toggling, auto-closing quotes, surrounding quotes

## Usage

- The extension activates based on the file's extension. If not detected, use `Change Language Mode` in VS Code and set it to `MODFLOW 6`.
- VS Code's minimap can display enlarged section headers (block names), which may appear cluttered. To simplify the view, disable this feature by setting `editor.minimap.showRegionSectionHeaders` to `false`.

## Release Notes

### 0.0.6

- Add gh release workflow
- Add grammar testing
- Rework workflows
- Add badges

### 0.0.5

- Lint and format with ruff, codespell and prettier
- Add pre-commit hooks
- Add ci

### 0.0.4

- Replace YAML with direct JSON template conversion
- Reduce extension file size

### 0.0.3

- Combine grammar files into one file
- Reset TextMate naming to be compatible with more themes
- Add and fix some regex patterns
- Add file icon and sample image

### 0.0.2

- Automate generation of package.json and all.tmLanugage.yaml from jinja template
- Add icon
- Add READARRAY keywords

### 0.0.1

- Alpha release

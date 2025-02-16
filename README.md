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

- The extension activates based on the file's extension. If not detected, use `MF6 Syntax: Syntax-highlight as MF6 file` command to set MF6 as the language mode.
- VS Code's minimap can display enlarged section headers (block names), which may appear cluttered. To simplify the view, disable this feature by setting `editor.minimap.showRegionSectionHeaders` to `false`.

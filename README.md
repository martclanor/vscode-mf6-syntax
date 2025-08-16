# VS Code MODFLOW 6 Syntax

[![CI](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/ci.yaml/badge.svg)](https://github.com/martclanor/vscode-mf6-syntax/actions/workflows/ci.yaml)
![GitHub package.json version](https://img.shields.io/github/package-json/v/martclanor/vscode-mf6-syntax)
![GitHub License](https://img.shields.io/github/license/martclanor/vscode-mf6-syntax)

![Icon](images/icon_banner.png)

> [!NOTE]
> This project is currently in beta. Features and functionality may change, and there may be bugs. Feedback and contributions to help improve the project are welcome.

This VS Code extension provides rich language features for [MODFLOW 6](https://modflow6.readthedocs.io/en/stable/index.html). It enhances the readability and editing experience for MF6 files by leveraging specifications directly from MF6 [DFN](https://modflow6.readthedocs.io/en/stable/_dev/dfn.html) files.

## Features

### Syntax highlighting

- MF6 input files ![demo-syntax-highlighting](images/demo_syntax_highlighting.png)

- MF6 output list files ![demo-syntax-highlighting-lst](images/demo_syntax_highlighting_lst.png)

### Document symbols

- for integration with VS Code features such as [outline view](https://code.visualstudio.com/docs/getstarted/userinterface#_outline-view), [go-to-symbol](https://code.visualstudio.com/docs/editing/editingevolved#_go-to-symbol), [breadcrumbs](https://code.visualstudio.com/docs/getstarted/userinterface#_breadcrumbs), [sticky scroll](https://code.visualstudio.com/docs/getstarted/userinterface#_sticky-scroll), [minimap](https://code.visualstudio.com/docs/getstarted/userinterface#_minimap), etc.
  ![symbol-defn](images/demo_symbol_defn.gif)

### Go-to-definition

- `Ctrl + click`
- `Go To Definition` keybinding (default: `F12`)
  ![go-to-defn](images/demo_go_to_defn.gif)

### Hover

- for keyword description and block structure
  ![hover](images/demo_hover.gif)

### Others:

- Block folding
- Snippet (MF6 block)
- Comment-toggling
- Auto-closing quotes
- Surrounding quotes

## Commands

- `MF6 Syntax: Set language to MF6`
  - useful if extension is not activated automatically (based on file extension)
- `MF6 Syntax: Go to parent file`
  - opens the parent file of the current MF6 file, if it exists
  - for example:
    - if `freyberg.dis` file is active, it opens `freyberg.nam`
    - if `freyberg.nam` file is active, it opens `mfsim.nam`
    - if `mfsim.nam` file is active, no-op since it is the top-level file

## Settings

- `mf6Syntax.maxFileSizeMB`: Maximum file size (in MB) that can be opened through the go-to-definition feature or go-to-parent command (default: `50MB`).

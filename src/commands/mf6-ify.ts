import * as vscode from "vscode";

export function mf6ify() {
  if (vscode.window.activeTextEditor) {
    const activeEditor = vscode.window.activeTextEditor;
    vscode.languages.setTextDocumentLanguage(activeEditor.document, "mf6");
  }
}

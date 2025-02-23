import * as vscode from "vscode";

export async function mf6ify() {
  if (vscode.window.activeTextEditor) {
    const activeEditor = vscode.window.activeTextEditor;
    await vscode.languages.setTextDocumentLanguage(
      activeEditor.document,
      "mf6",
    );
  }
}

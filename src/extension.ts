import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  let disposable = vscode.commands.registerCommand("mf6-syntax.mf6-ify", () => {
    if (vscode.window.activeTextEditor) {
      vscode.languages.setTextDocumentLanguage(
        vscode.window.activeTextEditor.document,
        "mf6",
      );
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}

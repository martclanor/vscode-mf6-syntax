import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  let disposable = vscode.commands.registerCommand("mf6-syntax.mf6-ify", () => {
    if (vscode.window.activeTextEditor) {
      const activeEditor = vscode.window.activeTextEditor;
      const fileName = activeEditor.document.fileName.split("/").pop();

      vscode.languages.setTextDocumentLanguage(activeEditor.document, "mf6");
      vscode.window.showInformationMessage(
        `MODFLOW 6 language mode set for: ${fileName}`,
      );
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}

import * as vscode from "vscode";
import { MF6DefinitionProvider } from "./providers/go-to-definition";

const MF6 = { language: "mf6", scheme: "file" };

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

  // Show definitions of a symbol
  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider(
      MF6,
      new MF6DefinitionProvider(),
    ),
  );
}

export function deactivate() {}

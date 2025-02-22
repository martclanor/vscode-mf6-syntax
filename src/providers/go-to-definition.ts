import * as vscode from "vscode";
import { checkFileExists } from "../utils/file-utils";

export class MF6DefinitionProvider implements vscode.DefinitionProvider {
  public async provideDefinition(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) {
      return null;
    }
    const word = document.getText(wordRange);
    const fileUri = vscode.Uri.joinPath(document.uri, "..", word);

    if (!checkFileExists(fileUri)) {
      vscode.window.showWarningMessage(`File ${word} not found`);
      return null;
    }
    return new vscode.Location(fileUri, new vscode.Position(0, 0));
  }
}

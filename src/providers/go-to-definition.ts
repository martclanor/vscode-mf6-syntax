import * as vscode from "vscode";

export class MF6DefinitionProvider implements vscode.DefinitionProvider {
  public async provideDefinition(
    document: vscode.TextDocument,
    position: vscode.Position,
  ): Promise<vscode.Location | vscode.Location[]> {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) {
      return [];
    }
    const word = document.getText(wordRange);
    const fileUri = vscode.Uri.joinPath(document.uri, "..", word);

    try {
      await vscode.workspace.fs.stat(fileUri);
      return new vscode.Location(fileUri, new vscode.Position(0, 0));
    } catch (error) {
      vscode.window.showWarningMessage(`File ${word} not found`);
      return [];
    }
  }
}

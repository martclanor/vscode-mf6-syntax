import * as vscode from "vscode";
import { checkFileExists } from "../utils/file-utils";
import * as fs from "fs/promises";

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

    if (!(await checkFileExists(fileUri))) {
      vscode.window.showWarningMessage(`File ${word} not found`);
      return null;
    }

    const config = vscode.workspace.getConfiguration("mf6Syntax");
    const maxFileSizeMB = config.get<number>("maxFileSizeMB", 50); // Default to 50MB
    const maxFileSizeBytes = maxFileSizeMB * 1024 * 1024;

    const fileStats = await fs.stat(fileUri.fsPath);
    if (fileStats.size > maxFileSizeBytes) {
      vscode.window.showWarningMessage(
        `File ${word} is too large to open through the extension (over ${maxFileSizeMB}MB).`,
      );
      return null;
    }

    return new vscode.Location(fileUri, new vscode.Position(0, 0));
  }
}

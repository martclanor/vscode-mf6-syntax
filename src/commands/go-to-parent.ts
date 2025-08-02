import * as vscode from "vscode";
import * as path from "path";

export async function goToParent() {
  if (vscode.window.activeTextEditor) {
    const document = vscode.window.activeTextEditor.document;
    if (document.languageId !== "mf6") {
      vscode.window.showInformationMessage(
        "Go-to-Parent-File command is only for MF6 files. Use command Set-language-to-MF6, if applicable.",
      );
      return null;
    }
    const fileUri = document.uri;
    const fileName = path.basename(fileUri.fsPath);
    if (fileName === "mfsim.nam") {
      vscode.window.showInformationMessage(
        "mfsim.nam is already the top-level file.",
      );
      return null;
    }
    const dirUri = vscode.Uri.joinPath(fileUri, "..");
    const filesInDir = await vscode.workspace.fs.readDirectory(dirUri);
    const config = vscode.workspace.getConfiguration("mf6Syntax");
    const maxFileSizeMB = config.get<number>("maxFileSizeMB", 50); // Default to 50MB

    for (const [name, type] of filesInDir) {
      if (type === vscode.FileType.File && name !== fileName) {
        const otherFileUri = vscode.Uri.joinPath(dirUri, name);
        const stat = await vscode.workspace.fs.stat(otherFileUri);
        if (stat.size > maxFileSizeMB * 1024 * 1024) {
          continue;
        }
        const contentBytes = await vscode.workspace.fs.readFile(otherFileUri);
        const content = Buffer.from(contentBytes).toString("utf-8");

        if (content.includes(fileName)) {
          const parentDocument =
            await vscode.workspace.openTextDocument(otherFileUri);
          await vscode.window.showTextDocument(parentDocument);
          return null;
        }
      }
    }

    vscode.window.showInformationMessage(
      `No parent file found within the directory. Parent file may exist but above the ${maxFileSizeMB}MB size limit. See setting 'mf6Syntax.maxFileSizeMB'.`,
    );
    return null;
  }
}

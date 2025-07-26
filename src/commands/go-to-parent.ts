import * as vscode from "vscode";
import * as path from "path";

export async function goToParent() {
  if (vscode.window.activeTextEditor) {
    const fileUri = vscode.window.activeTextEditor.document.uri;
    const fileName = path.basename(fileUri.fsPath);
    if (fileName === "mfsim.nam") {
      vscode.window.showInformationMessage(
        "mfsim.nam is already the top-level file.",
      );
      return null;
    }
    const dirUri = vscode.Uri.joinPath(fileUri, "..");
    const filesInDir = await vscode.workspace.fs.readDirectory(dirUri);

    for (const [name, type] of filesInDir) {
      if (type === vscode.FileType.File && name !== fileName) {
        const otherFileUri = vscode.Uri.joinPath(dirUri, name);
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
      `No parent file found for ${fileName}`,
    );
  }
}

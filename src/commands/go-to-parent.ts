import * as vscode from "vscode";
import * as path from "path";

export async function goToParent() {
  if (vscode.window.activeTextEditor) {
    const document = vscode.window.activeTextEditor.document;
    const fileUri = document.uri;
    const fileName = path.basename(fileUri.fsPath);
    if (fileName === "mfsim.nam") {
      vscode.window.showInformationMessage(
        "mfsim.nam is already the top-level file.",
      );
      return null;
    }
    const fileNameRegex = new RegExp(
      `(?:'|\\s)${fileName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?=\\s|'|$)`,
      "m",
    );
    const dirUri = vscode.Uri.joinPath(fileUri, "..");
    const filesInDir = await vscode.workspace.fs.readDirectory(dirUri);
    const config = vscode.workspace.getConfiguration("mf6Syntax");
    const maxFileSizeMB = config.get<number>("maxFileSizeMB", 50); // Default to 50MB
    const excludedExtensions = [".grb", ".lst", ".hds", ".bud", ".csv"];

    for (const [name, type] of filesInDir) {
      if (
        type !== vscode.FileType.File ||
        name === fileName ||
        excludedExtensions.some((ext) => name.endsWith(ext))
      ) {
        continue;
      }

      const otherFileUri = vscode.Uri.joinPath(dirUri, name);
      const stat = await vscode.workspace.fs.stat(otherFileUri);

      if (stat.size > maxFileSizeMB * 1024 * 1024) {
        continue;
      }

      const contentBytes = await vscode.workspace.fs.readFile(otherFileUri);
      const content = Buffer.from(contentBytes).toString("utf-8");

      if (fileNameRegex.test(content)) {
        const parentDocument =
          await vscode.workspace.openTextDocument(otherFileUri);
        await vscode.window.showTextDocument(parentDocument);
        return null;
      }
    }

    vscode.window.showInformationMessage(
      `No parent file found within the directory. Parent file may exist but above the ${maxFileSizeMB}MB size limit. See setting 'mf6Syntax.maxFileSizeMB'.`,
    );
    return null;
  }
}

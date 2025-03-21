import * as assert from "assert";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";
import { MF6DefinitionProvider } from "../providers/go-to-definition";
import { checkFileExists } from "../utils/file-utils";
import { mf6ify } from "../commands/mf6-ify";

suite("Extension Test Suite", () => {
  vscode.window.showInformationMessage("Start all tests.");

  test("MF6DefinitionProvider should provide definition accordingly", async () => {
    const provider = new MF6DefinitionProvider();
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    // Create source file
    const namTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.nam");
    const namFileContent = Buffer.from("BEGIN\ntest_model.tdis\nEND");
    await vscode.workspace.fs.writeFile(namTempFileUri, namFileContent);

    // Create target file
    const tdisTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.tdis");
    const tdisFileContent = Buffer.from("BEGIN\nEND");
    await vscode.workspace.fs.writeFile(tdisTempFileUri, tdisFileContent);

    try {
      const document = await vscode.workspace.openTextDocument(namTempFileUri);
      await vscode.window.showTextDocument(document);
      await mf6ify();
      // Position pointing to target file in the nam file
      const position = new vscode.Position(1, 0);
      const definition = await provider.provideDefinition(document, position);

      assert.ok(definition, "Definition should not be null or undefined");
      assert.strictEqual(definition?.uri.fsPath, tdisTempFileUri.fsPath);
      // Definition should point to the start of the file, check range start and end
      assert.deepStrictEqual(
        definition?.range.start,
        new vscode.Position(0, 0),
      );
      assert.deepStrictEqual(definition?.range.end, new vscode.Position(0, 0));

      // Position not pointing to target file
      const position_null = new vscode.Position(0, 0);
      const definition_null = await provider.provideDefinition(
        document,
        position_null,
      );
      assert.strictEqual(definition_null, null);
    } finally {
      // Clean up the temporary file and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  test("checkFileExists should return false for non-existent file", async () => {
    const uri = vscode.Uri.file("/non/existent/file");
    const exists = await checkFileExists(uri);
    assert.strictEqual(exists, false);
  });

  test("checkFileExists should return true for existing file", async () => {
    const uri = vscode.Uri.file(__filename);
    const exists = await checkFileExists(uri);
    assert.strictEqual(exists, true);
  });

  test("mf6ify should change document language to mf6", async () => {
    const document = await vscode.workspace.openTextDocument({
      content: "test",
      language: "plaintext",
    });
    await vscode.window.showTextDocument(document);
    await mf6ify();
    assert.strictEqual(document.languageId, "mf6");
  });
});

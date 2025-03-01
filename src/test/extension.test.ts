import * as assert from "assert";
import * as vscode from "vscode";
import { MF6DefinitionProvider } from "../providers/go-to-definition";
import { checkFileExists } from "../utils/file-utils";
import { mf6ify } from "../commands/mf6-ify";

suite("Extension Test Suite", () => {
  vscode.window.showInformationMessage("Start all tests.");

  test("MF6DefinitionProvider should provide definition", async () => {
    const provider = new MF6DefinitionProvider();
    const document = await vscode.workspace.openTextDocument({
      content: "test",
      language: "mf6",
    });
    const position = new vscode.Position(0, 0);
    const definition = await provider.provideDefinition(document, position);
    assert.strictEqual(definition, null);
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

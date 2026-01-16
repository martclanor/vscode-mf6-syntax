import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

export async function checkFileExists(uri: vscode.Uri) {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

export function loadJsonData<T>(fileName: string): T {
  const config = vscode.workspace.getConfiguration("mf6Syntax");
  const mf6Version = config.get<string>("mf6Version");

  const jsonPath = path.join(
    __dirname,
    `../../src/providers/${fileName}/${mf6Version}.json`,
  );
  const rawData = fs.readFileSync(jsonPath, "utf-8");
  return JSON.parse(rawData);
}

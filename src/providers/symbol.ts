import * as vscode from "vscode";

export class MF6SymbolProvider implements vscode.DocumentSymbolProvider {
  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.SymbolInformation[]> {
    // pass
    return Promise.resolve([]);
  }
}

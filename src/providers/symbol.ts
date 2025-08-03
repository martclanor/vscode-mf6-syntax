import * as vscode from "vscode";
import * as hoverBlockJson from "./hover-block.json";

export class MF6SymbolProvider implements vscode.DocumentSymbolProvider {
  private static readonly blockNames = Object.keys(hoverBlockJson).map((key) =>
    key.toLowerCase(),
  );
  private static readonly beginRegex = /^begin\s+(.+)/i;
  private static readonly endRegex = /^end\s+(.+)/i;

  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.DocumentSymbol[]> {
    const result: vscode.DocumentSymbol[] = [];

    let i = 0;
    while (i < document.lineCount) {
      const outerLine = document.lineAt(i);
      const beginMatch = MF6SymbolProvider.beginRegex.exec(outerLine.text);

      if (!beginMatch) {
        i++;
        continue;
      }

      // Check if block name is valid
      const blockName = beginMatch[1].trim().split(/\s+/)[0];
      if (!MF6SymbolProvider.blockNames.includes(blockName.toLowerCase())) {
        i++;
        continue;
      }

      const beginRange = i;
      let endRange = i;
      for (let j = i + 1; j < document.lineCount; j++) {
        const innerLine = document.lineAt(j);
        const endMatch = MF6SymbolProvider.endRegex.exec(innerLine.text);
        if (endMatch && blockName === endMatch[1].trim().split(/\s+/)[0]) {
          endRange = j;
          break;
        }
      }
      const range = new vscode.Range(
        beginRange,
        0,
        endRange,
        document.lineAt(endRange).text.length,
      );
      result.push(
        new vscode.DocumentSymbol(
          blockName,
          "block",
          vscode.SymbolKind.Field,
          range,
          range,
        ),
      );
      i = endRange + 1;
    }

    return result;
  }
}

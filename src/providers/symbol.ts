import * as vscode from "vscode";

export class MF6SymbolProvider implements vscode.DocumentSymbolProvider {
  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.DocumentSymbol[]> {
    const result: vscode.DocumentSymbol[] = [];
    const beginRegex = /^begin\s+(.+)/i;
    const endRegex = /^end\s+(.+)/i;

    let i = 0;
    while (i < document.lineCount) {
      const outerLine = document.lineAt(i);
      const beginMatch = beginRegex.exec(outerLine.text);

      if (!beginMatch) {
        i++;
        continue;
      }

      const beginRange = i;
      let endRange = i;
      const blockName = beginMatch[1].trim();
      for (let j = i + 1; j < document.lineCount; j++) {
        const innerLine = document.lineAt(j);
        const endMatch = endRegex.exec(innerLine.text);
        if (endMatch && blockName === endMatch[1].trim()) {
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

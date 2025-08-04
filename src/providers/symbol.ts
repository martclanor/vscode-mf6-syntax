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
    const blocks: vscode.DocumentSymbol[] = [];
    const periods: vscode.DocumentSymbol[] = [];

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

      // Find symbol range
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

      if (blockName.toLowerCase() !== "period") {
        blocks.push(
          new vscode.DocumentSymbol(
            blockName,
            "block",
            vscode.SymbolKind.Field,
            range,
            range,
          ),
        );
      } else {
        const iper = beginMatch[1].trim().split(/\s+/)[1];
        periods.push(
          new vscode.DocumentSymbol(
            iper,
            "",
            vscode.SymbolKind.Number,
            range,
            range,
          ),
        );
      }
      i = endRange + 1;
    }

    // If there is a period block, create symbols for period as children
    if (periods.length > 0) {
      const periodRange = new vscode.Range(
        periods[0].range.start.line,
        0,
        periods[periods.length - 1].range.end.line,
        periods[periods.length - 1].range.end.character,
      );
      const periodSymbol = new vscode.DocumentSymbol(
        "period",
        "block",
        vscode.SymbolKind.Field,
        periodRange,
        periodRange,
      );
      periodSymbol.children = periods;
      blocks.push(periodSymbol);
    }

    return blocks;
  }
}

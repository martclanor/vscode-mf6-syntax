import * as vscode from "vscode";
import * as hoverBlockJson from "./hover-block.json";

export class MF6SymbolProvider implements vscode.DocumentSymbolProvider {
  private static readonly blockNames = Object.keys(hoverBlockJson).map((key) =>
    key.toLowerCase(),
  );
  private static readonly beginRegex =
    /^begin\s+(?<blockName>\w+)(?:\s+(?<suffix>.+))?/i;
  private static readonly endRegex =
    /^end\s+(?<blockName>\w+)(?:\s+(?<suffix>.+))?/i;

  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.DocumentSymbol[]> {
    const blocks: vscode.DocumentSymbol[] = [];

    let i = 0;
    while (i < document.lineCount) {
      const beginMatch = MF6SymbolProvider.beginRegex.exec(
        document.lineAt(i).text,
      );

      if (!beginMatch || !beginMatch.groups) {
        i++;
        continue;
      }

      // Check if block name is valid
      let blockName = beginMatch.groups.blockName;
      if (!MF6SymbolProvider.blockNames.includes(blockName.toLowerCase())) {
        i++;
        continue;
      }

      // Find symbol range
      const beginRange = i;
      let endRange = i;
      for (let j = i + 1; j < document.lineCount; j++) {
        const endMatch = MF6SymbolProvider.endRegex.exec(
          document.lineAt(j).text,
        );
        if (endMatch && blockName === endMatch.groups?.blockName) {
          endRange = j;
          break;
        }
      }
      if (blockName.toLowerCase() === "period") {
        blockName += ` ${beginMatch.groups.suffix}`;
      }

      const range = new vscode.Range(
        beginRange,
        0,
        endRange,
        document.lineAt(endRange).text.length,
      );

      blocks.push(
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
    return blocks;
  }
}

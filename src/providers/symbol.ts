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
      const block = MF6SymbolProvider.parseBlock(document, i);
      if (block) {
        blocks.push(block.symbol);
        i = block.endLine;
      } else {
        i++;
      }
    }
    return blocks;
  }

  private static parseBlock(
    document: vscode.TextDocument,
    lineIndex: number,
  ): { symbol: vscode.DocumentSymbol; endLine: number } | null {
    const beginMatch = MF6SymbolProvider.beginRegex.exec(
      document.lineAt(lineIndex).text,
    );

    if (!beginMatch || !beginMatch.groups) {
      return null;
    }

    let blockName = beginMatch.groups.blockName;
    if (!MF6SymbolProvider.isValidBlockName(blockName)) {
      return null;
    }

    // Find end of block
    const beginRange = lineIndex;
    let endRange = lineIndex;
    for (let j = lineIndex + 1; j < document.lineCount; j++) {
      const endMatch = MF6SymbolProvider.endRegex.exec(document.lineAt(j).text);
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

    return {
      symbol: new vscode.DocumentSymbol(
        blockName,
        "block",
        vscode.SymbolKind.Field,
        range,
        range,
      ),
      endLine: endRange + 1,
    };
  }

  private static isValidBlockName(blockName: string): boolean {
    return MF6SymbolProvider.blockNames.includes(blockName.toLowerCase());
  }
}

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

    const beginRange = lineIndex;
    const endRange = MF6SymbolProvider.findBlockEnd(
      document,
      lineIndex + 1,
      blockName,
    );

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

  private static findBlockEnd(
    document: vscode.TextDocument,
    startLine: number,
    blockName: string,
  ): number {
    for (let i = startLine; i < document.lineCount; i++) {
      const endMatch = MF6SymbolProvider.endRegex.exec(document.lineAt(i).text);
      if (
        endMatch?.groups?.blockName.toLowerCase() === blockName.toLowerCase()
      ) {
        return i;
      }
    }
    return startLine - 1;
  }
}

import * as vscode from "vscode";
import * as symbolDefnJson from "./symbol-defn.json";

interface SymbolDefnStructure {
  [block: string]: string[]; // block name to readarray names
}

export class MF6SymbolProvider implements vscode.DocumentSymbolProvider {
  private static readonly symbolDefns: SymbolDefnStructure =
    symbolDefnJson as SymbolDefnStructure;
  private static readonly blockNames: Set<string> = new Set(
    Object.keys(MF6SymbolProvider.symbolDefns),
  );
  private static readonly beginRegex =
    /^begin\s+(?<blockName>\w+)(?:\s+(?<suffix>.+))?/i;
  private static readonly endRegex =
    /^end\s+(?<blockName>\w+)(?:\s+(?<suffix>.+))?/i;
  private static readonly PERIOD_BLOCK_NAME = "period";
  private static readonly BLOCK_DETAIL = "block";
  private static readonly ARRAY_DETAIL = "array";

  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.DocumentSymbol[]> {
    const blocks: vscode.DocumentSymbol[] = [];

    let i = 0;
    while (i < document.lineCount) {
      const block = this.parseBlock(document, i);

      if (block) {
        const readarrays: vscode.DocumentSymbol[] = [];
        // Inner loop to collect readarrays of the current block
        let j = i + 1;
        while (j < block.endLine) {
          const readarray = this.parseReadarray(block.symbol, document, j);
          if (readarray) {
            readarrays.push(readarray.symbol);
            j = readarray.endLine;
          } else {
            j++;
          }
        }

        block.symbol.children = readarrays;
        blocks.push(block.symbol);
        i = block.endLine;
      } else {
        i++;
      }
    }
    return blocks;
  }

  private parseBlock(
    document: vscode.TextDocument,
    beginRange: number,
  ): { symbol: vscode.DocumentSymbol; endLine: number } | null {
    const beginMatch = MF6SymbolProvider.beginRegex.exec(
      document.lineAt(beginRange).text,
    );

    // No regex match
    if (!beginMatch || !beginMatch.groups) {
      return null;
    }

    const blockName = beginMatch.groups.blockName;
    if (!MF6SymbolProvider.isValidBlockName(blockName)) {
      return null;
    }

    const endRange = MF6SymbolProvider.findBlockEnd(
      document,
      beginRange + 1,
      blockName,
    );
    const range = this.createRange(document, beginRange, endRange);

    return {
      symbol: new vscode.DocumentSymbol(
        MF6SymbolProvider.getSymbolName(beginMatch.groups),
        MF6SymbolProvider.BLOCK_DETAIL,
        vscode.SymbolKind.Field,
        range,
        range,
      ),
      endLine: endRange + 1,
    };
  }

  private parseReadarray(
    block: vscode.DocumentSymbol,
    document: vscode.TextDocument,
    beginRange: number,
  ): { symbol: vscode.DocumentSymbol; endLine: number } | null {
    // No readarray in block at all
    if (!MF6SymbolProvider.symbolDefns[block.name]) {
      return null;
    }

    const readarrayName = document
      .lineAt(beginRange)
      .text.trim()
      .split(/\s+/)[0]
      .toLowerCase();

    // readarray not in block
    if (!MF6SymbolProvider.symbolDefns[block.name].includes(readarrayName)) {
      return null;
    }

    const endRange = MF6SymbolProvider.findReadarrayEnd(
      document,
      beginRange,
      block.range.end.line,
    );
    const range = this.createRange(document, beginRange, endRange);

    return {
      symbol: new vscode.DocumentSymbol(
        readarrayName,
        MF6SymbolProvider.ARRAY_DETAIL,
        vscode.SymbolKind.Array,
        range,
        range,
      ),
      endLine: endRange + 1,
    };
  }

  private createRange(
    document: vscode.TextDocument,
    startLine: number,
    endLine: number,
  ): vscode.Range {
    return new vscode.Range(
      startLine,
      0,
      endLine,
      document.lineAt(endLine).text.length,
    );
  }

  private static findReadarrayEnd(
    document: vscode.TextDocument,
    startLine: number,
    blockEnd: number,
  ): number {
    // Since readarray sections are most-likely written programmatically,
    // assume consistent structured indentation and use this to find end
    const startIndent =
      document.lineAt(startLine).text.match(/^\s*/)?.[0].length ?? 0;
    for (let i = startLine + 1; i <= blockEnd; i++) {
      const nextIndent = document.lineAt(i).text.match(/^\s*/)?.[0].length ?? 0;
      if (nextIndent <= startIndent) {
        return i - 1;
      }
    }
    return startLine;
  }

  private static isValidBlockName(blockName: string): boolean {
    return MF6SymbolProvider.blockNames.has(blockName.toLowerCase());
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

  private static getSymbolName(beginMatchGroups: {
    [key: string]: string;
  }): string {
    const blockName = beginMatchGroups.blockName;
    if (
      blockName.toLowerCase() === MF6SymbolProvider.PERIOD_BLOCK_NAME &&
      beginMatchGroups.suffix
    ) {
      // Append period number if available
      return blockName + ` ${beginMatchGroups.suffix}`;
    }
    return blockName;
  }
}

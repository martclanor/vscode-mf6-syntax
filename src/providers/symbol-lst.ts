import * as vscode from "vscode";
import symbolDefnLstJson from "./symbol-defn-lst.json";

export class MF6LstSymbolProvider implements vscode.DocumentSymbolProvider {
  private static readonly symbolDefnLsts: string[] = symbolDefnLstJson;
  private static readonly spdTsRegex =
    /Solving:\s{2}Stress period|start timestep/i;

  public async provideDocumentSymbols(
    document: vscode.TextDocument,
  ): Promise<vscode.DocumentSymbol[]> {
    const symbols: vscode.DocumentSymbol[] = [];

    // Capture header symbols
    let i = 0;
    const header = this.parseHeader(document);
    symbols.push(header.symbol);

    // Capture package symbols
    i = header.endLine;
    while (i < document.lineCount) {
      const pkg = this.parsePackage(document, i);
      if (pkg) {
        symbols.push(pkg.symbol);
        i = pkg.endLine;
      } else {
        i++;
      }
    }
    return symbols;
  }

  private parseHeader(document: vscode.TextDocument): {
    symbol: vscode.DocumentSymbol;
    endLine: number;
  } {
    const endRange = MF6LstSymbolProvider.findHeaderPackageEnd(document);
    const range = this.createRange(document, 0, endRange);
    return {
      symbol: new vscode.DocumentSymbol(
        "MF6-LST",
        "header",
        vscode.SymbolKind.File,
        range,
        range,
      ),
      endLine: endRange + 1,
    };
  }

  private static findHeaderPackageEnd(
    document: vscode.TextDocument,
    i: number = 1,
  ): number {
    for (; i < document.lineCount; i++) {
      const matchPackage = MF6LstSymbolProvider.matchPackage(document, i);
      if (
        matchPackage &&
        MF6LstSymbolProvider.symbolDefnLsts.includes(matchPackage[1])
      ) {
        return i - 1;
      }

      const matchSpdTs = MF6LstSymbolProvider.matchSpdTs(document, i);
      if (matchSpdTs) {
        return i - 1;
      }
    }
    return document.lineCount - 1;
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

  private parsePackage(
    document: vscode.TextDocument,
    beginRange: number,
  ): { symbol: vscode.DocumentSymbol; endLine: number } | null {
    const match = MF6LstSymbolProvider.matchPackage(document, beginRange);
    if (!match || !MF6LstSymbolProvider.symbolDefnLsts.includes(match[1])) {
      return null;
    }
    const packageName = match[1];

    const endRange = MF6LstSymbolProvider.findHeaderPackageEnd(
      document,
      beginRange + 1,
    );
    const range = this.createRange(document, beginRange, endRange);

    return {
      symbol: new vscode.DocumentSymbol(
        packageName,
        "package",
        vscode.SymbolKind.Package,
        range,
        range,
      ),
      endLine: endRange + 1,
    };
  }

  private static matchPackage(
    document: vscode.TextDocument,
    line: number,
  ): RegExpExecArray | null {
    // Extract package name (the string before "--")
    const match = /^\s*(\S+)\s*--/.exec(document.lineAt(line).text);
    if (!match) {
      return null;
    }
    return match;
  }

  private static matchSpdTs(
    document: vscode.TextDocument,
    line: number,
  ): RegExpExecArray | null {
    const lineText = document.lineAt(line).text;
    const match = MF6LstSymbolProvider.spdTsRegex.exec(lineText);
    if (!match) {
      return null;
    }
    return match;
  }
}

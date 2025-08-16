import * as vscode from "vscode";
import symbolDefnLstJson from "./symbol-defn-lst.json";

export class MF6LstSymbolProvider implements vscode.DocumentSymbolProvider {
  private static readonly symbolDefnLsts: string[] = symbolDefnLstJson;
  private static readonly spdTsSimRegex =
    /Solving:\s+Stress period:?\s+(?<spd>\d+)(?:\s+Time step:\s+(?<ts>\d+))?/i;
  private static readonly spdTsGwfRegex =
    /start timestep kper="(?<spd>\d+)" kstp="(?<ts>\d+)"/i;

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
      if (!pkg) {
        i++;
        continue;
      }
      symbols.push(pkg.symbol);
      i = pkg.endLine;
    }

    // Capture stress period and timestep symbols
    i = symbols[symbols.length - 1].range.end.line + 1;
    while (i < document.lineCount) {
      const spdMatch = MF6LstSymbolProvider.matchSpdTs(document, i);
      if (!spdMatch) {
        i++;
        continue;
      }

      // Inner loop to collect ts of current spd
      const timesteps: vscode.DocumentSymbol[] = [];
      let j = i;
      while (j < document.lineCount) {
        const tsMatch = MF6LstSymbolProvider.matchSpdTs(document, j);
        if (!tsMatch) {
          j++;
          continue;
        }
        const tsEnd = MF6LstSymbolProvider.findTsEnd(document, j + 1);
        const tsRange = this.createRange(document, j, tsEnd);
        if (tsMatch.spd === spdMatch.spd) {
          timesteps.push(
            new vscode.DocumentSymbol(
              `ts ${tsMatch.ts}`,
              "",
              vscode.SymbolKind.Method,
              tsRange,
              tsRange,
            ),
          );
          j = tsRange.end.line;
        } else {
          break;
        }
      }

      const spdRange = this.createRange(
        document,
        i,
        timesteps[timesteps.length - 1].range.end.line,
      );
      const spd = new vscode.DocumentSymbol(
        `spd ${spdMatch.spd}`,
        "",
        vscode.SymbolKind.Field,
        spdRange,
        spdRange,
      );
      spd.children = timesteps;
      symbols.push(spd);
      i = j;
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
  ): { spd: string; ts: string } | null {
    const lineText = document.lineAt(line).text;
    const simMatch = MF6LstSymbolProvider.spdTsSimRegex.exec(lineText);
    if (simMatch && simMatch.groups) {
      return {
        spd: simMatch.groups.spd,
        ts: simMatch.groups.ts,
      };
    }

    const gwfMatch = MF6LstSymbolProvider.spdTsGwfRegex.exec(lineText);
    if (gwfMatch && gwfMatch.groups) {
      return {
        spd: gwfMatch.groups.spd,
        ts: gwfMatch.groups.ts,
      };
    }

    return null;
  }

  private static findTsEnd(
    document: vscode.TextDocument,
    startLine: number,
  ): number {
    for (let i = startLine; i < document.lineCount; i++) {
      const match = MF6LstSymbolProvider.matchSpdTs(document, i);
      if (match) {
        return i - 1;
      }
    }
    return startLine;
  }
}

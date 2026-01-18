import * as vscode from "vscode";
import { loadJsonData } from "../utils/file-utils";

export class MF6LstSymbolProvider implements vscode.DocumentSymbolProvider {
  private get symbolDefnLsts(): string[] {
    return loadJsonData<string[]>("symbol-defn-lst");
  }
  private static readonly spdTsSimRegex =
    /Solving:\s+Stress period:?\s+(?<spd>\d+)(?:\s+Time step:\s+(?<ts>\d+))?/i;
  private static readonly spdTsGwfRegex =
    /start timestep kper="(?<spd>\d+)" kstp="(?<ts>\d+)"/i;
  private static readonly noConvRegex =
    /FAILED TO MEET SOLVER CONVERGENCE|did not converge/;

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
      const spd = this.parseSpd(document, i);
      if (!spd) {
        i++;
        continue;
      }
      symbols.push(spd.symbol);
      i = spd.endLine + 1;
    }
    return symbols;
  }

  private parseHeader(document: vscode.TextDocument): {
    symbol: vscode.DocumentSymbol;
    endLine: number;
  } {
    const endRange = this.findHeaderPackageEnd(document);
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

  private findHeaderPackageEnd(
    document: vscode.TextDocument,
    i: number = 1,
  ): number {
    for (; i < document.lineCount; i++) {
      const matchPackage = MF6LstSymbolProvider.matchPackage(document, i);
      if (matchPackage && this.symbolDefnLsts.includes(matchPackage[1])) {
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
    if (!match || !this.symbolDefnLsts.includes(match[1])) {
      return null;
    }
    const packageName = match[1];

    const endRange = this.findHeaderPackageEnd(document, beginRange + 1);
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

  private parseSpd(
    document: vscode.TextDocument,
    beginRange: number,
  ): { symbol: vscode.DocumentSymbol; endLine: number } | null {
    const spdMatch = MF6LstSymbolProvider.matchSpdTs(document, beginRange);
    if (!spdMatch) {
      return null;
    }

    // Inner loop to collect ts of current spd
    const timesteps: vscode.DocumentSymbol[] = [];
    let i = beginRange;
    while (i < document.lineCount) {
      const tsMatch = MF6LstSymbolProvider.matchSpdTs(document, i);
      if (!tsMatch) {
        i++;
        continue;
      }
      const tsStat = MF6LstSymbolProvider.checkTs(document, i + 1);
      const tsRange = this.createRange(document, i, tsStat.tsEnd);
      if (tsMatch.spd === spdMatch.spd) {
        const tsDisplayName = tsStat.noConv
          ? `ts ${tsMatch.ts} ❌`
          : `ts ${tsMatch.ts}`;
        timesteps.push(
          new vscode.DocumentSymbol(
            tsDisplayName,
            "",
            vscode.SymbolKind.Method,
            tsRange,
            tsRange,
          ),
        );
        i = tsStat.tsEnd;
      } else {
        break;
      }
    }

    const endLine = timesteps[timesteps.length - 1].range.end.line;
    const spdRange = this.createRange(document, beginRange, endLine);
    const symbol = new vscode.DocumentSymbol(
      `spd ${spdMatch.spd}`,
      "",
      vscode.SymbolKind.Field,
      spdRange,
      spdRange,
    );
    symbol.children = timesteps;
    return {
      symbol: symbol,
      endLine: endLine,
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

  private static checkTs(
    document: vscode.TextDocument,
    startLine: number,
  ): { tsEnd: number; noConv: boolean } {
    let noConv: boolean = false;
    for (let i = startLine; i < document.lineCount; i++) {
      const lineText = document.lineAt(i).text;
      if (!noConv && lineText.search(this.noConvRegex) !== -1) {
        noConv = true;
      }
      const match = MF6LstSymbolProvider.matchSpdTs(document, i);
      if (match) {
        return { tsEnd: i - 1, noConv: noConv };
      }
    }
    return { tsEnd: document.lineCount - 1, noConv: noConv };
  }
}

import * as vscode from "vscode";
import * as path from "path";
import * as hoverKeywordJson from "./hover-keyword.json";
import * as hoverBlockJson from "./hover-block.json";

interface HoverKeywordStructure {
  [keyword: string]: {
    [block: string]: {
      [description: string]: string[]; // dfn_name
    };
  };
}

interface HoverBlockStructure {
  [block: string]: {
    [dfn: string]: string; // block structure definition
  };
}

function findEnclosingBlock(
  document: vscode.TextDocument,
  position: vscode.Position,
): string | undefined {
  for (let i = position.line - 1; i >= 0; i--) {
    const line = document.lineAt(i).text.trim();
    if (line.toLowerCase().startsWith("begin")) {
      const parts = line.split(/\s+/);
      if (parts.length > 1) {
        return parts[1].toLowerCase();
      }
    }
  }
  return undefined;
}

function getFileExtension(document: vscode.TextDocument): string {
  return path.extname(document.fileName).slice(1).toLowerCase();
}

function findMatchingDfns<T extends { [key: string]: string | string[] }>(
  data: T,
  fileExtension: string,
  checkValues: boolean = false,
): string[] {
  const Dfns = Object.keys(data);

  const matchingDfns = Dfns.filter((key) => {
    // Check based on the value (for keywords)
    if (checkValues) {
      const value = data[key];
      if (Array.isArray(value)) {
        return value.some((item) => item.endsWith(`-${fileExtension}`));
      }
    }
    // Check based on the key (for blocks or as a fallback for keywords)
    return key.endsWith(`-${fileExtension}`);
  });

  if (matchingDfns.length > 0) {
    return matchingDfns;
  }

  // Fallback: return all Dfns if no specific match is found
  return Dfns;
}

function isBlockDeclaration(
  document: vscode.TextDocument,
  position: vscode.Position,
  wordRange: vscode.Range,
): boolean {
  const lineText = document.lineAt(position.line).text;
  const textBefore = lineText.slice(0, wordRange.start.character);
  const prevWord = textBefore.trim().split(/\s+/).pop()?.toLowerCase();
  return prevWord === "begin" || prevWord === "end";
}

function formatKeywordHover(
  keyword: string,
  block: string,
  matchingDfns: string[],
  blockData: { [key: string]: string[] },
): string {
  const description = matchingDfns
    .map((key) => {
      if (matchingDfns.length === 1) {
        return `- ${key}`;
      }
      // If more than one possible Dfn source, list all
      const formattedValues = blockData[key]
        .map((value) => `*${value}*`)
        .join(", ");
      return `${formattedValues}\n- ${key}`;
    })
    .join("\n\n");

  const header = `**${keyword.toUpperCase()}**&nbsp;&nbsp;(block: *${
    block.toUpperCase() ?? "unknown"
  }*)\n\n`;
  return `${header}${description || "No description available"}`;
}

export class MF6HoverKeywordProvider implements vscode.HoverProvider {
  hoverData: HoverKeywordStructure = hoverKeywordJson as HoverKeywordStructure;

  public async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const wordRange = document.getWordRangeAtPosition(position, /\S+/);
    if (!wordRange) {
      return undefined;
    }
    const keyword = document.getText(wordRange).toLowerCase();
    const block = findEnclosingBlock(document, position);

    if (
      block &&
      keyword in this.hoverData &&
      this.hoverData[keyword]?.[block]
    ) {
      const blockData = this.hoverData[keyword][block];
      const fileExtension = getFileExtension(document);
      const matchingDfns = findMatchingDfns(blockData, fileExtension, true);
      const hoverValue = formatKeywordHover(
        keyword,
        block,
        matchingDfns,
        blockData,
      );

      return new vscode.Hover(new vscode.MarkdownString(hoverValue, true));
    } else {
      return undefined;
    }
  }
}

export class MF6HoverBlockProvider implements vscode.HoverProvider {
  hoverData: HoverBlockStructure = hoverBlockJson as HoverBlockStructure;

  public async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const wordRange = document.getWordRangeAtPosition(position, /\S+/);
    if (!wordRange) {
      return undefined;
    }

    if (!isBlockDeclaration(document, position, wordRange)) {
      return undefined;
    }

    const block = document.getText(wordRange).toLowerCase();
    if (block in this.hoverData) {
      let hoverValue: string | undefined = undefined;
      const blockData = this.hoverData[block];
      const fileExtension = getFileExtension(document);
      const matchingDfns = findMatchingDfns(blockData, fileExtension);

      hoverValue = matchingDfns
        .map((dfn) => blockData[dfn])
        .join("\n```\n\n\n```\n");

      return new vscode.Hover(new vscode.MarkdownString(hoverValue, true));
    } else {
      return undefined;
    }
  }
}

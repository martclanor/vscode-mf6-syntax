import * as vscode from "vscode";
import * as path from "path";
import * as hoverKeywordJson from "./hover-keyword.json";
import * as hoverBlockJson from "./hover-block.json";
import * as hoverRecarrayJson from "./hover-recarray.json";
import * as fs from "fs";

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

interface HoverRecarrayStructure {
  [block: string]: {
    [rec: string]: string[]; // dfn_name
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

function getRepeatCount(document: vscode.TextDocument): number | undefined {
  const dirPath = path.dirname(document.fileName);
  const files = fs.readdirSync(dirPath);
  for (const file of files) {
    const filePath = path.join(dirPath, file);
    if (fs.statSync(filePath).isFile()) {
      const ext = path.extname(file).toLowerCase();
      if (ext === ".dis") {
        // layer, row, column (need 2 extra counts)
        return 2;
      } else if (ext === ".disv") {
        // layer, cellid (need 1 extra count)
        return 1;
      }
    }
  }
  return undefined;
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
  hoverKeyword: HoverKeywordStructure =
    hoverKeywordJson as HoverKeywordStructure;
  hoverRecarray: HoverRecarrayStructure =
    hoverRecarrayJson as HoverRecarrayStructure;

  public async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    // Consider single quotes or double quotes to find the words
    const wordRange = document.getWordRangeAtPosition(
      position,
      /(?<=['"])[^'"]*(?=['"])|[^'"\s]+/,
    );
    if (!wordRange) {
      return undefined;
    }
    const keyword = document.getText(wordRange);
    const keywordLower = keyword.toLowerCase();
    const block = findEnclosingBlock(document, position);
    const fileExtension = getFileExtension(document);

    if (!block) {
      return undefined;
    }

    if (
      keywordLower in this.hoverKeyword &&
      this.hoverKeyword[keywordLower]?.[block]
    ) {
      const blockData = this.hoverKeyword[keywordLower][block];
      const matchingDfns = findMatchingDfns(blockData, fileExtension, true);
      const hoverValue = formatKeywordHover(
        keywordLower,
        block,
        matchingDfns,
        blockData,
      );

      return new vscode.Hover(new vscode.MarkdownString(hoverValue, true));
    } else if (block in this.hoverRecarray) {
      const lineText = document.lineAt(position.line).text.trim();
      if (lineText.startsWith("#")) {
        return undefined;
      }

      // Get wordIndex based on number of spaces before word excluding spaces in quotes
      let wordIndex = 0;
      let inSingleQuotes = false;
      let inDoubleQuotes = false;
      let inWhiteSpaces = false;
      for (let i = 0; i < wordRange.start.character; i++) {
        const char = lineText[i];
        if (char === "'" && !inDoubleQuotes) {
          inSingleQuotes = !inSingleQuotes;
          inWhiteSpaces = false;
        } else if (char === '"' && !inSingleQuotes) {
          inDoubleQuotes = !inDoubleQuotes;
          inWhiteSpaces = false;
        } else if (/\s/.test(char) && !inSingleQuotes && !inDoubleQuotes) {
          if (!inWhiteSpaces) {
            wordIndex++;
            inWhiteSpaces = true;
          }
        } else {
          inWhiteSpaces = false;
        }
      }

      const repeatCount = getRepeatCount(document);

      // Find keywordRecarray
      let keywordRecarray: string | undefined;
      for (const [rec, dfns] of Object.entries(this.hoverRecarray[block])) {
        // Exit early if no matching dfn
        const filteredDfns = dfns.filter((dfn) => {
          const parts = dfn.split("-");
          return parts.length > 1 && parts[1] === fileExtension;
        });
        if (filteredDfns.length == 0) {
          continue;
        }

        const recItems = rec.split(",");

        // Repeat cellid items for dis (twice) and disv (once)
        if (repeatCount) {
          const expandedRecItems: string[] = [];
          recItems.forEach((item) => {
            expandedRecItems.push(item);
            if (item.includes("cellid")) {
              for (let i = 0; i < repeatCount; i++) {
                expandedRecItems.push(item);
              }
            }
          });
          recItems.splice(0, recItems.length, ...expandedRecItems);
        }

        if (wordIndex < recItems.length) {
          const recKeyword = recItems[wordIndex];
          if (recKeyword) {
            if (filteredDfns.length > 0) {
              keywordRecarray = recKeyword;
              break;
            }
          }
        }
      }

      // Check if this keyword exists in hoverKeyword
      if (
        !keywordRecarray ||
        !(keywordRecarray in this.hoverKeyword) ||
        !(block in this.hoverKeyword[keywordRecarray])
      ) {
        return undefined;
      }

      const blockData = this.hoverKeyword[keywordRecarray][block];
      const matchingDfns = findMatchingDfns(blockData, fileExtension, true);
      const hoverValue = formatKeywordHover(
        keywordRecarray,
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
  hoverBlock: HoverBlockStructure = hoverBlockJson as HoverBlockStructure;

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
    if (block in this.hoverBlock) {
      let hoverValue: string | undefined = undefined;
      const blockData = this.hoverBlock[block];
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

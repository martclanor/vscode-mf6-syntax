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

export class MF6HoverKeywordProvider implements vscode.HoverProvider {
  hoverData: HoverKeywordStructure = hoverKeywordJson as HoverKeywordStructure;

  public async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const wordRange = document.getWordRangeAtPosition(position, /\S+/);
    if (!wordRange) {
      return null;
    }
    const keyword = document.getText(wordRange).toLowerCase();

    // Traverse backward line-per-line to find the enclosing block
    let block: string | null = null;
    for (let line = position.line - 1; line >= 0; line--) {
      const lineText = document.lineAt(line).text.trim();
      if (lineText.toLowerCase().startsWith("begin")) {
        const parts = lineText.split(/\s+/);
        if (parts.length > 1) {
          block = parts[1].toLowerCase();
        }
        break;
      }
    }

    if (
      keyword in this.hoverData &&
      block &&
      this.hoverData[keyword]?.[block]
    ) {
      let hoverValue: string | undefined = undefined;

      const blockData = this.hoverData[keyword][block];
      const fileExtension = path
        .extname(document.fileName)
        .slice(1)
        .toLowerCase();
      let matchingKeys = Object.keys(blockData).filter((key) => {
        const value = blockData[key];
        return value.some((item) => {
          const parts = item.split("-");
          return parts[parts.length - 1] === fileExtension;
        });
      });

      if (matchingKeys.length === 1) {
        hoverValue = `- ${matchingKeys[0]}`;
      } else {
        if (matchingKeys.length === 0) {
          // Fallback to all keys
          matchingKeys = Object.keys(blockData);
        }
        const matchingValues = matchingKeys.map((key) => blockData[key]);
        hoverValue = matchingKeys
          .map((key, index) => {
            const values = matchingValues[index];
            const formattedValues = values
              .map((value) => `*${value}*`)
              .join(", ");
            return `${formattedValues}\n- ${key}`;
          })
          .join("\n\n");
      }

      return new vscode.Hover(
        new vscode.MarkdownString(
          `**${keyword.toUpperCase()}**&nbsp;&nbsp;(block: *${
            block?.toUpperCase() ?? "unknown"
          }*)\n\n${hoverValue ?? "No description available"}`,
          true,
        ),
      );
    } else {
      return null;
    }
  }
}

interface HoverBlockStructure {
  [block: string]: {
    [dfn: string]: string; // block structure definition
  };
}

export class MF6HoverBlockProvider implements vscode.HoverProvider {
  hoverData: HoverBlockStructure = hoverBlockJson as HoverBlockStructure;

  public async provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const wordRange = document.getWordRangeAtPosition(position, /\S+/);
    if (!wordRange) {
      return null;
    }

    // Only provide hover if the previous word is "begin" or "end"
    const lineText = document.lineAt(position.line).text;
    const tokens = lineText
      .slice(0, wordRange.start.character)
      .trimEnd()
      .split(/\s+/);
    const prevWord =
      tokens.length > 0 ? tokens[tokens.length - 1].toLowerCase() : "";
    if (prevWord !== "begin" && prevWord !== "end") {
      return null;
    }

    const block = document.getText(wordRange).toLowerCase();
    if (block in this.hoverData) {
      let hoverValue: string | undefined = undefined;
      const blockData = this.hoverData[block];
      const fileExtension = path
        .extname(document.fileName)
        .slice(1)
        .toLowerCase();
      // Find matching dfns based on file extension
      let matchingDfns = Object.keys(blockData).filter((key) => {
        const parts = key.split("-");
        return parts[parts.length - 1] === fileExtension;
      });

      if (matchingDfns.length === 0) {
        // Fallback to all dfn possible
        matchingDfns = Object.keys(blockData);
      }

      // Add comment prefix then wrap in code block
      // to preserve indentation and to provide syntax highlighting
      hoverValue = matchingDfns
        .map(
          (dfn) =>
            `\`\`\`\n# Structure of ${block.toUpperCase()} block in ${dfn.toUpperCase()}\n${blockData[dfn]}\n\n\n\`\`\``,
        )
        .join("\n");

      return new vscode.Hover(new vscode.MarkdownString(hoverValue, true));
    } else {
      return null;
    }
  }
}

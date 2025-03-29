import * as vscode from "vscode";
import * as path from "path";
import * as hoverDataJson from "./hover.json";

interface HoverDataStructure {
  [keyword: string]: {
    [block: string]: {
      [description: string]: string[]; // dfn_name
    };
  };
}

export class MF6HoverProvider implements vscode.HoverProvider {
  hoverData: HoverDataStructure = hoverDataJson as HoverDataStructure;

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

import * as vscode from "vscode";
import { MF6DefinitionProvider } from "./providers/go-to-definition";
import { MF6SymbolProvider } from "./providers/symbol";
import { MF6LstSymbolProvider } from "./providers/symbol-lst";
import { MF6HoverKeywordProvider } from "./providers/hover";
import { MF6HoverBlockProvider } from "./providers/hover";
import { goToParent } from "./commands/go-to-parent";
import { mf6ify } from "./commands/mf6-ify";

const MF6 = { language: "mf6", scheme: "file" };
const MF6Lst = { language: "mf6-lst", scheme: "file" };

export function activate(context: vscode.ExtensionContext) {
  // MF6-ify command
  context.subscriptions.push(
    vscode.commands.registerCommand("mf6-syntax.mf6-ify", async () => {
      await mf6ify();
    }),
  );

  // goToParent command
  context.subscriptions.push(
    vscode.commands.registerCommand("mf6-syntax.goToParent", async () => {
      await goToParent();
    }),
  );

  // Document symbols
  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(
      MF6,
      new MF6SymbolProvider(),
    ),
  );
  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(
      MF6Lst,
      new MF6LstSymbolProvider(),
    ),
  );

  // Go-to linked file
  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider(
      MF6,
      new MF6DefinitionProvider(),
    ),
  );

  // Show hover of MF6 keyword
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(MF6, new MF6HoverKeywordProvider()),
  );

  // Show hover of MF6 block
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(MF6, new MF6HoverBlockProvider()),
  );
}

export function deactivate() {}

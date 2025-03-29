import * as vscode from "vscode";
import { MF6DefinitionProvider } from "./providers/go-to-definition";
import { MF6HoverProvider } from "./providers/hover";
import { mf6ify } from "./commands/mf6-ify";

const MF6 = { language: "mf6", scheme: "file" };

export function activate(context: vscode.ExtensionContext) {
  // MF6-ify command
  context.subscriptions.push(
    vscode.commands.registerCommand("mf6-syntax.mf6-ify", async () => {
      await mf6ify();
    }),
  );

  // Show definitions of a symbol
  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider(
      MF6,
      new MF6DefinitionProvider(),
    ),
  );

  // Show hover of MF6 keyword
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(MF6, new MF6HoverProvider()),
  );
}

export function deactivate() {}

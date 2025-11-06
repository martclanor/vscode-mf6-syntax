import * as assert from "assert";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";
import { MF6DefinitionProvider } from "../providers/go-to-definition";
import { MF6SymbolProvider } from "../providers/symbol";
import { MF6LstSymbolProvider } from "../providers/symbol-lst";
import {
  MF6HoverBlockProvider,
  MF6HoverKeywordProvider,
} from "../providers/hover";
import { checkFileExists } from "../utils/file-utils";
import { mf6ify } from "../commands/mf6-ify";
import { goToParent } from "../commands/go-to-parent";

suite("Extension Test Suite", () => {
  vscode.window.showInformationMessage("Start all tests.");

  test("MF6DefinitionProvider should resolve paths", async () => {
    const provider = new MF6DefinitionProvider();
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    // Create source file
    const namTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.nam");
    const namFileContent = Buffer.from("BEGIN\ntest_model.tdis\nEND");
    await vscode.workspace.fs.writeFile(namTempFileUri, namFileContent);

    // Create target file
    const tdisTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.tdis");
    const tdisFileContent = Buffer.from("BEGIN\nEND");
    await vscode.workspace.fs.writeFile(tdisTempFileUri, tdisFileContent);

    try {
      const document = await vscode.workspace.openTextDocument(namTempFileUri);
      await vscode.window.showTextDocument(document);
      await mf6ify();
      // Position pointing to target file in the nam file
      const position = new vscode.Position(1, 0);
      const definition = await provider.provideDefinition(document, position);

      assert.ok(definition, "Definition should not be null or undefined");
      assert.strictEqual(definition?.uri.fsPath, tdisTempFileUri.fsPath);
      // Definition should point to the start of the file, check range start and end
      assert.deepStrictEqual(
        definition?.range.start,
        new vscode.Position(0, 0),
      );
      assert.deepStrictEqual(definition?.range.end, new vscode.Position(0, 0));

      // Position not pointing to target file
      const position_null = new vscode.Position(0, 0);
      const definition_null = await provider.provideDefinition(
        document,
        position_null,
      );
      assert.strictEqual(definition_null, null);
    } finally {
      // Clean up the temporary file and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  test("MF6HoverKeywordProvider should provide hover on keyword", async () => {
    const provider = new MF6HoverKeywordProvider();
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    // Create source file
    const disvTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.disv");
    const disvFileContent = Buffer.from("BEGIN options\nLENGTH_UNITS\nEND");
    await vscode.workspace.fs.writeFile(disvTempFileUri, disvFileContent);

    try {
      const document = await vscode.workspace.openTextDocument(disvTempFileUri);
      await vscode.window.showTextDocument(document);
      await mf6ify();
      // Position pointing to LENGTH_UNITS keyword
      const position = new vscode.Position(1, 0);
      const hover = await provider.provideHover(document, position);

      assert.ok(hover, "Hover should not be null or undefined");
      assert.strictEqual(
        (hover?.contents[0] as vscode.MarkdownString).value,
        "**LENGTH_UNITS**&nbsp;&nbsp;(block: *OPTIONS*)\n\n- is the length units used for this model.  Values can be `FEET`, `METERS`, or `CENTIMETERS`.  If not specified, the default is `UNKNOWN`.",
        "Hover content should match the expected description",
      );

      // Position not pointing to keyword
      const position_null = new vscode.Position(0, 0);
      const hover_null = await provider.provideHover(document, position_null);
      assert.strictEqual(hover_null, undefined);
    } finally {
      // Clean up the temporary file and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  test("MF6HoverKeywordProvider should provide hover on keyword-recarray", async () => {
    const provider = new MF6HoverKeywordProvider();
    const sampleFilePath = path.join(
      __dirname,
      "..",
      "..",
      "syntaxes",
      "samples",
      "freyberg.chd",
    );
    const fileUri = vscode.Uri.file(sampleFilePath);
    const document = await vscode.workspace.openTextDocument(fileUri);
    await vscode.window.showTextDocument(document);

    const positionCellid = new vscode.Position(18, 10);
    const hoverCellid = await provider.provideHover(document, positionCellid);
    assert.strictEqual(
      (hoverCellid?.contents[0] as vscode.MarkdownString).value,
      "**CELLID**&nbsp;&nbsp;(block: *PERIOD*)\n\n- is the cell identifier, and depends on the type of grid that is used for the simulation.  For a structured grid that uses the DIS input file, CELLID is the layer, row, and column.   For a grid that uses the DISV input file, CELLID is the layer and CELL2D number.  If the model uses the unstructured discretization (DISU) input file, CELLID is the node number for the cell.",
      "Hover content should match the expected description",
    );

    const positionHead = new vscode.Position(20, 23);
    const hoverHead = await provider.provideHover(document, positionHead);
    assert.strictEqual(
      (hoverHead?.contents[0] as vscode.MarkdownString).value,
      "**HEAD**&nbsp;&nbsp;(block: *PERIOD*)\n\n- is the head at the boundary. If the Options block includes a TIMESERIESFILE entry (see the `Time-Variable Input` section), values can be obtained from a time series by entering the time-series name in place of a numeric value.",
      "Hover content should match the expected description",
    );

    const positionBn = new vscode.Position(21, 30);
    const hoverBn = await provider.provideHover(document, positionBn);
    assert.strictEqual(
      (hoverBn?.contents[0] as vscode.MarkdownString).value,
      "**BOUNDNAME**&nbsp;&nbsp;(block: *PERIOD*)\n\n- name of the constant head boundary cell.  BOUNDNAME is an ASCII character variable that can contain as many as 40 characters.  If BOUNDNAME contains spaces in it, then the entire name must be enclosed within single quotes.",
      "Hover content should match the expected description",
    );
  });

  test("MF6HoverBlockProvider should provide hover on block", async () => {
    const provider = new MF6HoverBlockProvider();
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    // Create source file
    const disvTempFileUri = vscode.Uri.joinPath(
      tempDirUri,
      "test_hover_block.disv",
    );
    const disvFileContent = Buffer.from("BEGIN connectiondata\nEND");
    await vscode.workspace.fs.writeFile(disvTempFileUri, disvFileContent);

    try {
      const document = await vscode.workspace.openTextDocument(disvTempFileUri);
      await vscode.window.showTextDocument(document);
      await mf6ify();
      // Position pointing to connectiondata block
      const position = new vscode.Position(0, 7);
      const hover = await provider.provideHover(document, position);

      assert.ok(hover, "Hover should not be null or undefined");
      assert.strictEqual(
        (hover?.contents[0] as vscode.MarkdownString).value,
        "```\n# Structure of CONNECTIONDATA block in GWE-DISU\nBEGIN CONNECTIONDATA\n  IAC\n      <iac(nodes)> -- READARRAY\n  JA\n      <ja(nja)> -- READARRAY\n  IHC\n      <ihc(nja)> -- READARRAY\n  CL12\n      <cl12(nja)> -- READARRAY\n  HWVA\n      <hwva(nja)> -- READARRAY\n  [ANGLDEGX\n      <angldegx(nja)> -- READARRAY]\nEND CONNECTIONDATA\n```\n```\n\n\n```\n```\n# Structure of CONNECTIONDATA block in GWF-DISU\nBEGIN CONNECTIONDATA\n  IAC\n      <iac(nodes)> -- READARRAY\n  JA\n      <ja(nja)> -- READARRAY\n  IHC\n      <ihc(nja)> -- READARRAY\n  CL12\n      <cl12(nja)> -- READARRAY\n  HWVA\n      <hwva(nja)> -- READARRAY\n  [ANGLDEGX\n      <angldegx(nja)> -- READARRAY]\nEND CONNECTIONDATA\n```\n```\n\n\n```\n```\n# Structure of CONNECTIONDATA block in GWF-LAK\nBEGIN CONNECTIONDATA\n  <ifno> <iconn> <cellid(ncelldim)> <claktype> <bedleak> <belev> <telev> <connlen> <connwidth>\n  <ifno> <iconn> <cellid(ncelldim)> <claktype> <bedleak> <belev> <telev> <connlen> <connwidth>\n  ...\nEND CONNECTIONDATA\n```\n```\n\n\n```\n```\n# Structure of CONNECTIONDATA block in GWF-MAW\nBEGIN CONNECTIONDATA\n  <ifno> <icon> <cellid(ncelldim)> <scrn_top> <scrn_bot> <hk_skin> <radius_skin>\n  <ifno> <icon> <cellid(ncelldim)> <scrn_top> <scrn_bot> <hk_skin> <radius_skin>\n  ...\nEND CONNECTIONDATA\n```\n```\n\n\n```\n```\n# Structure of CONNECTIONDATA block in GWF-SFR\nBEGIN CONNECTIONDATA\n  <ifno> [<ic(ncon(ifno))>]\n  <ifno> [<ic(ncon(ifno))>]\n  ...\nEND CONNECTIONDATA\n```\n```\n\n\n```\n```\n# Structure of CONNECTIONDATA block in GWT-DISU\nBEGIN CONNECTIONDATA\n  IAC\n      <iac(nodes)> -- READARRAY\n  JA\n      <ja(nja)> -- READARRAY\n  IHC\n      <ihc(nja)> -- READARRAY\n  CL12\n      <cl12(nja)> -- READARRAY\n  HWVA\n      <hwva(nja)> -- READARRAY\n  [ANGLDEGX\n      <angldegx(nja)> -- READARRAY]\nEND CONNECTIONDATA\n```",
        "Hover content should match the expected description",
      );

      // Position not pointing to block
      const position_null = new vscode.Position(0, 0);
      const hover_null = await provider.provideHover(document, position_null);
      assert.strictEqual(hover_null, undefined);
    } finally {
      // Clean up the temporary file and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  test("checkFileExists should check file existence", async () => {
    const nonExistentUri = vscode.Uri.file("/non/existent/file");
    const existentUri = vscode.Uri.file(__filename);

    const notExists = await checkFileExists(nonExistentUri);
    assert.strictEqual(notExists, false);

    const exists = await checkFileExists(existentUri);
    assert.strictEqual(exists, true);
  });

  test("mf6ify should change document language to mf6", async () => {
    const document = await vscode.workspace.openTextDocument({
      content: "test",
      language: "plaintext",
    });
    await vscode.window.showTextDocument(document);
    await mf6ify();
    assert.strictEqual(document.languageId, "mf6");
  });

  test("goToParent should navigate to parent file", async () => {
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    // Create test files: gwf-dis, gwf-nam, sim-nam
    const gwfDisTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.dis");
    const gwfDisFileContent = Buffer.from("BEGIN\nLENGTH_UNITS\nEND");
    await vscode.workspace.fs.writeFile(gwfDisTempFileUri, gwfDisFileContent);
    const dummyGwfNamTempFileUri = vscode.Uri.joinPath(
      tempDirUri,
      "dummy_test_model.nam",
    );
    const dummyGwfNamFileContent = Buffer.from(
      "BEGIN packages\nDIS6 dummy_test_model.dis dis\nEND",
    );
    await vscode.workspace.fs.writeFile(
      dummyGwfNamTempFileUri,
      dummyGwfNamFileContent,
    );
    const gwfNamTempFileUri = vscode.Uri.joinPath(tempDirUri, "test_model.nam");
    const gwfNamFileContent = Buffer.from(
      "BEGIN packages\nDIS6 test_model.dis dis\nEND",
    );
    await vscode.workspace.fs.writeFile(gwfNamTempFileUri, gwfNamFileContent);
    const simNamTempFileUri = vscode.Uri.joinPath(tempDirUri, "mfsim.nam");
    const simNamFileContent = Buffer.from(
      "BEGIN models\nGWF6 test_model.nam test_model\nEND",
    );
    await vscode.workspace.fs.writeFile(simNamTempFileUri, simNamFileContent);

    try {
      const gwfDisDocument =
        await vscode.workspace.openTextDocument(gwfDisTempFileUri);
      await vscode.window.showTextDocument(gwfDisDocument);
      // Should not go to dummy gwf which has partial filename match only
      await goToParent(); // gwf-dis to gwf-nam
      assert.strictEqual(
        vscode.window.activeTextEditor?.document.fileName,
        gwfNamTempFileUri.fsPath,
      );
      await goToParent(); // gwf-nam to sim-nam
      assert.strictEqual(
        vscode.window.activeTextEditor?.document.fileName,
        simNamTempFileUri.fsPath,
      );
      await goToParent(); // from sim-nam, no-op
      assert.strictEqual(
        vscode.window.activeTextEditor?.document.fileName,
        simNamTempFileUri.fsPath,
      );
    } finally {
      // Clean up the temporary files and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  function assertSymbol(
    symbol: vscode.DocumentSymbol,
    expectedName: string,
    expectedRange: [number, number, number, number],
  ) {
    assert.strictEqual(symbol.name, expectedName);
    assert.strictEqual(symbol.range.start.line, expectedRange[0]);
    assert.strictEqual(symbol.range.start.character, expectedRange[1]);
    assert.strictEqual(symbol.range.end.line, expectedRange[2]);
    assert.strictEqual(symbol.range.end.character, expectedRange[3]);
  }

  test("MF6SymbolProvider should provide document symbols", async () => {
    const provider = new MF6SymbolProvider();
    const tempDirUri = vscode.Uri.file(path.join(os.tmpdir(), "temp"));
    await vscode.workspace.fs.createDirectory(tempDirUri);

    const tempFileUri = vscode.Uri.joinPath(tempDirUri, "base.disv");
    const fileContent = Buffer.from(
      `BEGIN griddata
  top
    OPEN/CLOSE  'base_unsteady.disv_top.txt'  FACTOR  1.0
  botm  LAYERED
    OPEN/CLOSE  'base_unsteady.disv_botm_layer1.txt'  FACTOR  1.0
  idomain  LAYERED
    OPEN/CLOSE  'base_unsteady.disv_idomain_layer1.txt'  FACTOR  1
END griddata

BEGIN period  2
  3 205409 4.25000000E+01 1.00000000E+04 "KE023 - North Abutment"
  3 205420 4.25000000E+01 1.00000000E+04 "KE023 - North Abutment"
END period  2

BEGIN non-existing-block
END non-existing-block

BEGIN period  12
END period  12

BEGIN non-existing-block
END non-existing-block`,
    );
    await vscode.workspace.fs.writeFile(tempFileUri, fileContent);

    try {
      const document = await vscode.workspace.openTextDocument(tempFileUri);
      await vscode.window.showTextDocument(document);
      const symbols = await provider.provideDocumentSymbols(document);

      assert.strictEqual(symbols.length, 3);
      assert.strictEqual(symbols[0].children.length, 3);
      assertSymbol(symbols[0], "griddata", [0, 0, 7, 12]);
      assertSymbol(symbols[0].children[0], "top", [1, 0, 2, 57]);
      assertSymbol(symbols[0].children[1], "botm", [3, 0, 4, 65]);
      assertSymbol(symbols[0].children[2], "idomain", [5, 0, 6, 66]);
      assertSymbol(symbols[1], "period 2", [9, 0, 12, 13]);
      assertSymbol(symbols[2], "period 12", [17, 0, 18, 14]);
    } finally {
      // Clean up the temporary file and directory
      await vscode.workspace.fs.delete(tempDirUri, { recursive: true });
    }
  });

  test("MF6LstSymbolProvider should provide document symbols", async () => {
    const provider = new MF6LstSymbolProvider();

    const sampleFilePath = path.join(
      __dirname,
      "..",
      "..",
      "syntaxes",
      "samples",
      "ex01_mf6_extra_ts.lst",
    );
    const fileUri = vscode.Uri.file(sampleFilePath);
    const document = await vscode.workspace.openTextDocument(fileUri);
    await vscode.window.showTextDocument(document);
    const symbols = await provider.provideDocumentSymbols(document);

    assert.strictEqual(symbols.length, 8);
    assert.strictEqual(symbols[7].children.length, 2);
    assertSymbol(symbols[0], "MF6-LST", [0, 0, 87, 0]);
    assertSymbol(symbols[1], "DIS", [88, 0, 90, 0]);
    assertSymbol(symbols[2], "NPF", [91, 0, 93, 0]);
    assertSymbol(symbols[3], "IC", [94, 0, 124, 0]);
    assertSymbol(symbols[4], "WEL", [125, 0, 136, 0]);
    assertSymbol(symbols[5], "RIV", [137, 0, 148, 0]);
    assertSymbol(symbols[6], "RCH", [149, 0, 192, 0]);
    assertSymbol(symbols[7], "spd 1", [193, 0, 306, 0]);
    assertSymbol(symbols[7].children[0], "ts 1", [193, 0, 248, 0]);
    assertSymbol(symbols[7].children[1], "ts 2 ❌", [249, 0, 306, 0]);
  });
});

# Rebuild the fictional dataset

The Python builders require Python 3.11 or later and `python-docx`. The Excel builder requires Node 22 or later and the bundled `@oai/artifact-tool` runtime. Use Codex's workspace dependency loader for the actual bundled paths. Do not copy or commit `node_modules`, credentials, local AWS profiles, or access tokens.

From the repository root, run these in order with the selected runtime executables:

```text
python test-data/asterbridge-labs/scripts/build_dataset.py
python test-data/asterbridge-labs/scripts/build_documents.py
node test-data/asterbridge-labs/scripts/build_workbooks.mjs
python test-data/asterbridge-labs/scripts/build_evaluations.py
python test-data/asterbridge-labs/scripts/validate_dataset.py
```

`validate_dataset.py` uses openpyxl only to inspect the saved XLSX files. All workbook authoring is through the artifact tool.

The builders make no network calls. They read the current `jira/remote-map.json` and `confluence/remote-map.json`, preserving actual published identifiers. Rebuilding source files does not publish changes. Compare content and explicitly update only dataset-owned remote records through the connected tools.

Before rebuilding artifacts in a Codex session, follow the document/spreadsheet skill instrumentation and render requirements. Run `render_docx.py` for every final Word file after a usable renderer is available. The original attempt is recorded as blocked, not passed. Workbook previews are saved in `validation/workbook-previews/` and ignored by Git; all requested final files and editable sources remain tracked candidates.

For a new Atlassian site, use a separate copy of the dataset and separate publication maps. The current source-qualified maps describe the original test environment and must not be silently overwritten with unrelated IDs. Preserve the original snapshots for comparison.

After the November 17 Git cleanup, only the authored catalog, generators and instructions
are versioned. All generated files, publication maps, snapshots, binaries and validation
outputs are local artifacts. A clean checkout can build unpublished offline inputs;
remote validation requires separately retained original maps and readbacks. The old
tracked-candidate wording above describes the initial dataset preparation.

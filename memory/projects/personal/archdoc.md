# archdoc — Architecture Documentation Generator

## Repo
- **Fork:** https://github.com/arkasha-ai/archdoc
- **Upstream:** https://github.com/topitip/archdoc
- **Branch:** `feature/improvements-v2`
- **PR:** https://github.com/topitip/archdoc/pull/1

## What it does
CLI tool that scans Python projects via AST (rustpython-parser), builds a project model (symbols, calls, imports, integrations), and generates Markdown architecture docs with diff-aware updates (ARCHDOC:BEGIN/END markers).

## Work done (2026-02-15)

### Commits on `feature/improvements-v2`:
1. **Add workspace Cargo.toml** — root workspace for unified `cargo build`/`cargo test`
2. **Improve Python analyzer** — full AST traversal, proper function signatures with types, multiline docstrings, Method vs Function distinction, recursive call extraction from If/For/While/With/Try/Assign/Return, import alias resolution
3. **Add stats command, colored output, progress bar, summary** — `archdoc stats` shows fan-in/fan-out top-10, integrations, cycles; colored terminal output; progress bar; generation summary

### Test results
- All 29 existing tests pass
- Full cycle (init → generate → check) verified on test-project/
- Stats command tested and working

## Architecture notes
- **archdoc-core**: library crate (parser, model, renderer, writer, cache)
- **archdoc-cli**: binary crate (clap CLI)
- Edition: Rust 2024
- Key deps: rustpython-parser 0.4, handlebars, walkdir, clap, colored, indicatif
- `gen` is reserved keyword in Rust 2024 — avoid as variable name

# emmylua-render

WIP! Render custom documentation for Neovim Lua plugins which are typed with [EmmyLuaLS](https://github.com/EmmyLuaLs/emmylua-analyzer-rust).

## Features

- Renders both vimdoc and markdown
- Automatically loads type information and makes it available in template context
- Inbuilt default templates for classes/enums/aliases/functions
- Automatically expands fields in function parameters, including fields of intersections (`A & B`).
- Docstring descriptions are loaded as markdown and converted to vimdoc automatically.

## Quickstart

Ensure you have `emmylua_doc_cli` and [Pandoc](https://pandoc.org/) in your `$PATH`.

```console
cd ~/code/my-plugin
$ uvx emmylua-render --format vim templates/doc.jinja
$ uvx emmylua-render --format md templates/doc.jinja
```

## Pre-commit Hook

You can use emmylua-render as a pre-commit hook to automatically regenerate documentation when Lua files or templates change. The hook will fail if the documentation changes, prompting you to stage the updated files.

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/lkubb/emmylua-render
    rev: v0.1.0
    hooks:
      - id: emmylua-render
        args:
          # Template file (required)
          - templates/doc.jinja
          # Optional: output file (defaults to doc/<project_name>.txt in pre-commit mode)
          - --output=doc/api.md
          # Optional: specify format
          - --format=md
          # Optional: project configuration
          - --project-root=lua
          - --project-name=my-plugin
          # Optional: control type expansion
          # - --no-expand=TypeWithManyFields*
          # Optional: environment variables for emmylua_doc_cli
          # - --env=LUA_PATH=/custom/path/?.lua
```

The hook automatically runs with `--pre-commit` flag, which:

- Defaults output to `doc/<project_name>.txt` if not specified
- Writes/updates the documentation file
- Exits with status 1 if the file was created or changed, requiring you to stage the changes

**Note**: Sometimes, EmmyLuaLS does not deterministically resolve aliases, resulting in cyclic changes.

### Available Arguments

All CLI parameters are supported via the `args` section:

- `-o/--output`: Output file path (defaults to `doc/<project_name>.txt` in pre-commit mode)
- `-f/--format`: Output format (`md` or `vim`)
- `-r/--project-root`: Path to project root for `emmylua_doc_cli`
- `-n/--project-name`: Project name (used for anchor prefixes, exposed in global `PROJECT`)
- `-x/--emmylua-doc-cli-path`: Override path to `emmylua_doc_cli` binary
- `-i/--input`: Read JSON from specified file instead of invoking `emmylua_doc_cli`
- `-e/--env`: Environment variables (can be specified multiple times, separate key/value with `=`)
- `--no-expand`: Glob patterns for types not to expand (can be specified multiple times)
- `--expand`: Glob patterns for types to expand (can be specified multiple times). If unspecified, expands all.
- `-v/--verbose`: Enable verbose output
- `--pre-commit`: Enable pre-commit mode

## Todo

- Use Jinja to render Pandoc AST only, then rely on Pandoc writers for ease of use/consistency
- Robustness
- Much more testing

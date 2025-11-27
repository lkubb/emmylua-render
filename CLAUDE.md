# AI Assistant Instructions

## Project Overview

emmylua-render is a Python tool that generates documentation for Neovim Lua plugins typed with EmmyLuaLS into Vim help (Vimdoc) and Markdown formats.

This project uses:

- **Languages/Frameworks**:
  - **Python** 3.13+ for the tool itself
  - **Lua** 5.4 for custom Pandoc writers
  - **Jinja** to provide templating
- **Build tool**: `uv`
- **Testing**: `pytest`
- **Dependencies**:
  - **emmylua_doc_cli** provides project API information
  - **Pandoc** converts Markdown snippets into Vimdoc
- **Architecture**:
  - **CLI Entry Point** (`src/emmylua_render/cli.py`) handles argument parsing and coordinates the rendering pipeline
  - **Pydantic Data Models** (`src/emmylua_render/raw_models.py`) represent structured `emmylua_doc_cli` output
  - **Type Parser** (`src/emmylua_render/type_parser.py`) implements a Lark EBNF parser to hydrate humanized type strings from emmylua_doc_cli into Python dataclasses on demand
  - **Rendering System** (`src/emmylua_render/render.py`) implements custom Jinja filters and tags (`section`, `anchor`)
  - **Template Engine** (`src/emmylua_render/jinja.py`) handles Jinja environment setup
  - Custom `vimdoc` Pandoc writer handles conversion from Markdown snippets into Vimdoc format, exposed via `vimdoc` Jinja filter

### Data flow

1. `emmylua_doc_cli` parses Lua project API, returns JSON, which Pydantic hydrates into raw models
2. type parser receives raw models
3. Jinja templates are rendered with access to type parser wrapper (`doc`) and custom vimdoc writer (`vimdoc`)
4. Output to stdout or file

## File structure reference

```
./
├── src                           # Python and Lua code
│   └── emmylua_render
│       ├── cli.py                # CLI argument parsing and glue
│       ├── default_templates     # Jinja templates for dumping hydrated Python types
│       │   ├── markdown
│       │   └── vimdoc
│       ├── jinja.py              # Jinja env setup
│       ├── pandoc
│       │   ├── _pandoc_meta.lua  # Pandoc Lua type definitions
│       │   └── vimdoc_writer.lua # Custom vimdoc writer
│       ├── raw_models.py         # Pydantic models for emmylua_doc_cli output
│       ├── render.py             # Custom Jinja filters/tags
│       └── type_parser.py        # EBNF parser and classes for hydrated types
├── tests                         # Test code and data
│   ├── conftest.py
│   ├── files
│   │   ├── doc.json              # Example emmylua_doc_cli output
│   │   └── template
│   │       ├── section.jinja     # Template for smokescreen testing of emmylua-render
│   │       └── vimdoc_writer.md  # Template for smokescreen testing of vimdoc_writer.lua
│   ├── functional                # Tests that verify overall functionality
│   └── unit                      # Tests that verify isolated components
```

## Common commands

```bash
# Environment setup
uv sync && source .venv/bin/activate && pre-commit install
# Run tests
uv run pytest
# Run linters and formatters
pre-commit run -a
# Run emmylua-render (Markdown output)
uv run emmylua-render --input tests/files/doc.json --format md tests/files/template/section.jinja
# Run emmylua-render (Vimdoc output)
uv run emmylua-render --input tests/files/doc.json --format vim tests/files/template/section.jinja
```

"""
Jinja rendering implementation for template processing.

TODO:
Currently, markdown and vimdoc are treated separately.
A better approach would be to generate Pandoc AST only
in Jinja and use Pandoc writers to create both outputs.
"""

import re
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, Template
from jinja2.ext import ExprStmtExtension, LoopControlExtension

from .render import DocExtension, MarkdownRenderer, VimHelpRenderer, wrap

TOC_INSERT_MARKER = "<__INSERT_TOC__>"


def extract_lines(
    file_path: str | Path,
    *,
    start: str | None = None,
    stop: str | None = None,
    skip_start: int = 0,
    skip_end: int = 0,
    include: str | list[str] | None = None,
    exclude: str | list[str] | None = None,
) -> str:
    """
    Extract lines from a file with flexible options.

    Args:
        file_path: Path to the file
        start: Regex pattern to search for to start extraction. If None, starts from beginning.
        stop: Regex pattern to search for to stop extraction. If None, goes to end.
        skip_start: Number of lines to skip from the start point
        skip_end: Number of lines to skip before the stop point
        include: Regex pattern(s) to include lines. Only lines matching these patterns are kept.
        exclude: Regex pattern(s) to exclude lines. Lines matching these patterns are removed.

    Returns:
        Extracted lines as a string
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    lines = file_path.read_text(encoding="utf-8", newline="\n").splitlines()

    start_idx = 0
    if start:
        pat = re.compile(start)
        for i, line in enumerate(lines):
            if pat.match(line):
                start_idx = i
                break
        else:
            # Pattern not found, return empty
            return ""

    # Apply skip_start
    start_idx = min(start_idx + skip_start, len(lines) - 1)

    # Find stop position
    end_idx = len(lines)
    if stop:
        pat = re.compile(stop)
        for i in range(start_idx, len(lines)):
            if pat.match(lines[i]):
                end_idx = i + 1  # Include the line with stop pattern
                break

    # Apply skip_end (moves end position backwards)
    end_idx = max(start_idx + 1, end_idx - skip_end)

    # Extract lines
    extracted = lines[start_idx:end_idx]

    if not (include or exclude):
        return "\n".join(extracted)
    if isinstance(include, str):
        include = [include]
    if isinstance(exclude, str):
        exclude = [exclude]
    includes = [re.compile(p) for p in (include or [])]
    excludes = [re.compile(p) for p in (exclude or [])]
    filtered = []
    for line in extracted:
        if includes:
            if not any(pat.match(line) for pat in includes):
                continue

        if excludes:
            if any(pat.match(line) for pat in excludes):
                continue

        filtered.append(line)

    return "\n".join(filtered).rstrip()


def package_root(*sub) -> Path:
    root = Path(__file__).parent
    if not sub:
        return root.resolve()
    return root.joinpath(*sub).resolve()


class JinjaRenderer:
    """Handles Jinja2 template rendering with custom context."""

    def __init__(
        self,
        search_path: Path | list[Path] | None = None,
        trim_blocks: bool = False,
        lstrip_blocks: bool = False,
        *,
        fmt: Literal["markdown"] | Literal["vimdoc"],
        project_name: str = "",
        expand: list[str] | None = None,
        no_expand: list[str] | None = None,
    ):
        """
        Initialize the Jinja renderer.

        Args:
            search_path: Path or list of paths to search for templates
            trim_blocks: Remove newline after blocks
            lstrip_blocks: Remove leading spaces from blocks
            fmt: "markdown" or "vimdoc"
            project_name: Plugin name
            expand: List of globs for structs whose fields should be expanded in func args
                    If this is set, the default behavior of expanding everything is inverted.
            no_expand: List of globs for structs whose fields should not be expanded in func args
        """
        search_path = search_path or []
        self.search_path = (
            search_path if isinstance(search_path, list) else [search_path]
        )
        self.search_path.append(package_root("default_templates", fmt))
        self.env = Environment(
            loader=FileSystemLoader(self.search_path),
            autoescape=False,
            trim_blocks=trim_blocks,
            lstrip_blocks=lstrip_blocks,
            keep_trailing_newline=True,
            extensions=[DocExtension, ExprStmtExtension, LoopControlExtension],
        )
        if fmt == "vimdoc":
            rend = VimHelpRenderer()
            self.add_filter("vimdoc", markdown_to_vimdoc)
        else:
            rend = MarkdownRenderer()
        self.add_filter("anchor", rend.anchor)
        self.add_filter("heading", rend.heading)
        self.add_filter("hr", rend.hr)
        self.add_filter("link", rend.link)
        self.add_filter("wrap", wrap)
        self.add_filter("enumerate", enumerate)
        self.add_filter("strip", lambda x: (x or "").strip())
        self.add_filter("str", str)
        self.add_filter("dict", dict)
        self.add_global("hr", rend.hr())
        self.add_global("toc", TOC_INSERT_MARKER)
        self.add_global("PROJECT", project_name)
        self.add_global("extract_lines", extract_lines)
        self.env.extend(
            emmylua_render={
                "project_name": project_name,
                "expand": expand,
                "no_expand": no_expand,
                "fmt": fmt,
            }
        )

    def _get_context(self, context: dict[str, Any] | None) -> dict[str, Any]:
        if context is None:
            context = {}
        return context

    def render(self, name: str, context: dict[str, Any] | None = None) -> str:
        """
        Render the template with the given context.

        Args:
            name: Name of the template to render. Must be in ``search_path``.
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered template as string
        """
        template = self.env.get_template(name)
        return self._render(template, context)

    def render_str(
        self, template_str: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Render a template string with the given context.

        Args:
            template_str: Template string to render
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered template as string
        """
        template = self.env.from_string(template_str)
        return self._render(template, context)

    def _render(self, template: Template, context: dict):
        context = self._get_context(context)
        out = template.render(**context).strip("\n") + "\n"
        if out.find(TOC_INSERT_MARKER + "\n") >= 0:
            toc = self._render_toc()
            out = out.replace(TOC_INSERT_MARKER + "\n", toc)
        return out

    def _render_toc(self):
        return self.env.get_template("toc.jinja").render()

    def _render_typeref(self):
        return self.env.get_template("typeref.jinja").render()

    def add_filter(self, name: str, func: Callable):
        """
        Add a custom filter to the Jinja environment.

        Args:
            name: Filter name to use in templates
            func: Filter function
        """
        self.env.filters[name] = func

    def add_global(self, name: str, value: Any):
        """
        Add a global variable or function to the Jinja environment.

        Args:
            name: Global name to use in templates
            value: Global value or function
        """
        self.env.globals[name] = value

    def add_test(self, name: str, func: Callable[[Any], bool]):
        """
        Add a custom test to the Jinja environment.

        Args:
            name: Test name to use in templates
            func: Test function
        """
        self.env.tests[name] = func


def markdown_to_vimdoc(text: str, indent: int | None = None) -> str:
    """
    Convert markdown text to vimdoc format using pandoc.
    Used to dump docstrings into vimdocs with correct formatting.

    Args:
        text: Markdown formatted string

    Returns:
        Vimdoc formatted string
    """

    if not text or not text.strip():
        return text

    writer = package_root("pandoc", "vimdoc_writer.lua")
    cmd = ["pandoc", "-f", "markdown", "-t", str(writer)]
    if indent:
        cmd.append(f"--columns={78 - indent}")

    # Run pandoc to convert markdown to vimdoc (help text format).
    # Don't catch errors, otherwise we render invalid docs.
    result = subprocess.run(
        cmd,
        input=text,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    if indent:
        return textwrap.indent(result, " " * indent)
    return result


def render_template(
    template_path: Path, context: dict[str, Any] | None = None, **renderer_kwargs
) -> str:
    """
    Convenience function to render a template in one call.

    Args:
        template_path: Path to the template file
        context: Dictionary of variables to pass to the template
        **renderer_kwargs: Additional arguments for JinjaRenderer

    Returns:
        Rendered template as string
    """
    if renderer_kwargs.get("fmt"):
        pass
    elif "md" in template_path.suffixes:
        renderer_kwargs["fmt"] = "markdown"
    else:
        renderer_kwargs["fmt"] = "vimdoc"
    renderer = JinjaRenderer(template_path.parent, **renderer_kwargs)
    return renderer.render(template_path.name, context)


def render_template_str(
    template_str: str, context: dict[str, Any] | None = None, **renderer_kwargs
) -> str:
    """
    Convenience function to render a string template in one call.

    Args:
        template: Template string
        context: Dictionary of variables to pass to the template
        **renderer_kwargs: Additional arguments for JinjaRenderer

    Returns:
        Rendered template as string
    """
    if renderer_kwargs.get("fmt"):
        pass
    else:
        renderer_kwargs["fmt"] = "vimdoc"
    renderer = JinjaRenderer(None, **renderer_kwargs)
    return renderer.render_str(template_str, context)

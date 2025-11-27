"""
CLI application for rendering neovim lua plugin documentation.
Uses emmylua_doc_cli output to generate documentation from Jinja templates.
"""

import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from lark import Lark
from lark import logger as lark_logger

from emmylua_render.raw_models import Index
from emmylua_render.render import Doc
from emmylua_render.type_parser import TYPE_GRAMMAR, TreeHydrator

from .jinja import render_template


def get_vimruntime() -> str:
    return subprocess.run(
        ["nvim", "-es", "+put=$VIMRUNTIME|print|quit!"],
        capture_output=True,
        check=True,
        encoding="utf8",
    ).stdout


def get_doc_data(project_root: Path, env_override: dict[str, str]) -> str:
    base_env = os.environ.copy()
    env = base_env | {"VIMRUNTIME": get_vimruntime()} | env_override
    out = subprocess.run(
        [
            "emmylua_doc_cli",
            "-c",
            ".emmyrc.json",
            "-f",
            "json",
            "-o",
            "stdout",
            str(project_root.relative_to(Path(".").resolve())) + "/",
        ],
        env=env,
        check=True,
        capture_output=True,
    )
    return out.stdout


def parse_env_var(env_str: str) -> tuple[str, str]:
    """
    Parse environment variable string in KEY=VALUE format.

    Args:
        env_str: Environment variable string

    Returns:
        Tuple of (key, value)

    Raises:
        argparse.ArgumentTypeError: If format is invalid
    """
    if "=" not in env_str:
        raise argparse.ArgumentTypeError(
            f"Environment variable must be in KEY=VALUE format, got: {env_str}"
        )

    key, value = env_str.split("=", maxsplit=1)
    if not key:
        raise argparse.ArgumentTypeError(
            f"Environment variable key cannot be empty: {env_str}"
        )

    return key, value


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="emmylua-render",
        description="Render neovim lua plugin documentation using emmylua_doc_cli and Jinja templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s template.j2
  %(prog)s template.j2 --output docs.md
  %(prog)s template.j2 --project-root /path/to/project/lua
  %(prog)s template.j2 --env LUA_PATH="/custom/path/?.lua" --env LUA_CPATH="/custom/path/?.so"
        """,
    )

    parser.add_argument(
        "template", type=Path, help="Path to Jinja template file to render"
    )

    parser.add_argument(
        "-x",
        "--emmylua-doc-cli-path",
        type=Path,
        default=None,
        help="Override path to emmylua_doc_cli binary (defaults to finding in $PATH)",
    )

    parser.add_argument(
        "-e",
        "--env",
        action="append",
        type=parse_env_var,
        default=[],
        help="Override emmylua_doc_cli environment variables (can be specified multiple times). "
        "Format: KEY=VALUE",
    )

    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=None,
        help="Instead of invoking emmylua_doc_cli, read its JSON output from this path",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write output to this file path instead of stdout",
    )

    parser.add_argument(
        "-r",
        "--project-root",
        type=Path,
        default=None,
        help="Path to project root for emmylua_doc_cli (defaults to <cwd>/lua)",
    )

    parser.add_argument(
        "-n",
        "--project-name",
        type=str,
        default=None,
        help="Name of the project (used for vimdoc). Defaults to the name of the first directory in project-root",
    )

    parser.add_argument(
        "--no-expand",
        action="append",
        type=str,
        default=[],
        help="Argument types with fields are expanded by default. Types matching this glob are not expanded. Can be specified multiple times.",
    )

    parser.add_argument(
        "--expand",
        action="append",
        type=str,
        default=[],
        help="Argument types with fields are expanded by default. If this is specified, the logic is inversed. Only types matching this glob are expanded. Can be specified multiple times.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=("md", "vim"),
        default=None,
        help="Output format, either Markdown (`md`) or Vimdoc (`vim`). Defaults to the format indicated by the output path extension, the template extension or vimdoc",
    )

    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="Run in pre-commit mode: defaults output to doc/<project_name>.txt and exits with status 1 if file changes",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser


def validate_args(args: argparse.Namespace) -> tuple[bool, str]:
    """
    Validate parsed arguments and set defaults.

    Args:
        args: Parsed command line arguments

    Returns:
        Boolean indicating whether arguments are valid
        String error message, if invalid
    """
    if not args.template.exists():
        return False, f"Template file not found: {args.template}"

    if not args.template.is_file():
        return False, f"Template path is not a file: {args.template}"

    if args.input and not args.input.is_file():
        return False, f"Input path does not exist/is not a file: {args.input}"

    if args.project_root is None:
        args.project_root = Path("lua").resolve()
        if args.verbose:
            print(f"Using default project root: {args.project_root}", file=sys.stderr)

    if not args.project_root.exists():
        return False, f"Project root does not exist: {args.project_root}"

    if not args.project_root.is_dir():
        return False, f"Project root is not a directory: {args.project_root}"

    if args.emmylua_doc_cli_path is None:
        bin_path = shutil.which("emmylua_doc_cli")
        if bin_path:
            args.emmylua_doc_cli_path = Path(bin_path)

    if args.emmylua_doc_cli_path is None or not args.emmylua_doc_cli_path.exists():
        return False, f"emmylua_doc_cli binary not found: {args.emmylua_doc_cli_path}"

    if not args.emmylua_doc_cli_path.is_file():
        return False, f"emmylua_doc_cli path is not a file: {args.emmylua_doc_cli_path}"

    if args.project_name is None:
        try:
            args.project_name = next(iter(sorted(next(args.project_root.walk())[1])))
        except StopIteration:
            return (
                False,
                f"No directory in project-root to derive project name from: {args.project_root}",
            )

    if args.pre_commit and args.output is None:
        args.output = Path("doc") / f"{args.project_name}.txt"

    if args.output:
        output_parent = args.output.parent
        if output_parent.exists() and not output_parent.is_dir():
            return (
                False,
                f"Output path parent exists, but is not a directory: {output_parent}",
            )

    if not args.format:
        if args.output:
            if "md" in args.output.suffixes:
                args.format = "md"
            else:
                args.format = "vim"
        elif "md" in args.template.suffixes:
            args.format = "md"
        else:
            args.format = "vim"

    return True, ""


def process_env_vars(env_list: list[tuple[str, str]]) -> dict[str, str]:
    """
    Process environment variable list into a dictionary.

    Args:
        env_list: List of (key, value) tuples from parsed arguments

    Returns:
        Dictionary of environment variables
    """
    env_dict = {}
    for key, value in env_list:
        if key in env_dict:
            print(
                f"Warning: Duplicate environment variable '{key}', "
                f"using latest value: {value}",
                file=sys.stderr,
            )
        env_dict[key] = value

    return env_dict


def main() -> int:
    """Main entry point for the CLI application."""
    parser = create_parser()
    args = parser.parse_args()
    ok, err = validate_args(args)
    if not ok:
        print(err, file=sys.stderr)
        return 1
    env_vars = process_env_vars(args.env)

    if args.verbose:
        lark_logger.setLevel(logging.DEBUG)

    if args.input:
        emmy_json = args.input.read_text()
    else:
        emmy_json = get_doc_data(args.project_root, env_vars)

    docs = Index.model_validate_json(emmy_json)
    transformer = TreeHydrator(docs)
    parser = Lark(TYPE_GRAMMAR, parser="lalr", debug=True, transformer=transformer)
    transformer.parser = parser  # cringe: ignore o:]
    doc = Doc(docs, parser)
    fmt = "markdown" if args.format == "md" else "vimdoc"

    # In pre-commit mode, hash the existing file before writing
    existing_hash = None
    if args.pre_commit and args.output and args.output.exists():
        existing_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()

    result = render_template(
        args.template,
        {"doc": doc},
        project_name=args.project_name,
        expand=args.expand,
        no_expand=args.no_expand,
        fmt=fmt,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
        if args.verbose:
            print(f"Output written to: {args.output}", file=sys.stderr)

        if args.pre_commit:
            new_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
            if existing_hash and existing_hash != new_hash:
                print(
                    f"Documentation file {args.output} was updated. Please stage the changes.",
                    file=sys.stderr,
                )
                return 1
            elif not existing_hash:
                print(
                    f"Documentation file {args.output} was created. Please stage the changes.",
                    file=sys.stderr,
                )
                return 1
    else:
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())

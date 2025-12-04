"""
Jinja rendering helpers.

Currently exposes hacked-together renderers for Vimdoc and Markdown
separately, but in the future, I'd like to just render Pandoc AST
and use the writers to achieve easier and consistent formatting, specifically
targeting newlines and text length.
"""

import re
from abc import ABC, abstractmethod
from fnmatch import fnmatchcase
from functools import wraps
from typing import Any, Literal

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.nodes import Keyword, Node
from jinja2.parser import Parser

from emmylua_render.raw_models import Index
from emmylua_render.type_parser import (
    AliasType,
    ClassType,
    DocumentedField,
    DocumentedFunction,
    DocumentedType,
    EnumType,
    ResolvedType,
    TypeKind,
)

TYPEREF = {}


def resolve_anchor(
    anchor: str | Literal[True] | None, prefix: str, literal: bool = False
) -> str | None:
    if not anchor:
        return ""
    if not prefix or literal:
        return anchor
    return "-".join((prefix, anchor))


class Doc:
    """
    Exposes type parser for emmylua_doc_cli output to Jinja context.
    """

    docs: Index

    def __init__(self, docs: Index, parser):
        self.docs = docs
        self.parser = parser

    def get(self, typ):
        return self.parser.parse(typ)

    def filter(self, glob="*", *, kind=None):
        glob = glob or "*"
        match_typ = None
        if kind == "mod":
            cands = map(
                lambda x: self.docs.modules[x].typ,
                filter(lambda x: fnmatchcase(x, glob), self.docs.modules),
            )
        elif kind == "class":
            cands = filter(lambda x: fnmatchcase(x, glob), self.docs.classes)
        elif kind == "alias":
            cands = filter(lambda x: fnmatchcase(x, glob), self.docs.aliases)
        elif kind == "enum":
            cands = filter(lambda x: fnmatchcase(x, glob), self.docs.enums)
        else:
            cands = filter(lambda x: fnmatchcase(x, glob), self.docs.types)
            if kind:
                # TODO: Pretty sure there are no other kinds to match here,
                #       we'd need to e.g. match on the parsed `typ` of aliases.
                match_typ = getattr(TypeKind, kind.upper())
        for cand in cands:
            obj = self.parser.parse(cand)
            if match_typ and obj.kind != match_typ:
                continue
            yield obj

    def is_mod(self, typ: ResolvedType) -> bool:
        if not isinstance(typ, ClassType):
            return False
        return any(mod.typ == typ.name for mod in self.docs.modules.values())


class DocExtension(Extension):
    tags = {"anchor", "section"}
    prefix_initialized: bool = False

    def __init__(self, environment):
        super().__init__(environment)
        toc = {
            "index": {},
            "glossary": {},
            "referenced_types": set(),
            "rendered_types": set(),
        }
        toc["cur"] = toc["index"]
        self.environment.extend(
            section_stack=[],
            anchor_prefix="",
            toc=toc,
        )
        self.environment.globals["__toc__"] = toc
        self.environment.globals["typeref"] = TYPEREF
        self.environment.filters["should_expand"] = self.should_expand
        self.environment.filters["humanize"] = self.humanize
        if self.environment.finalize is None:
            self.environment.finalize = self._finalizer
        else:
            finalizer = self.environment.finalize

            @wraps(finalizer)
            def wrapper(self, data):
                return finalizer(self._finalizer(data))

            self.environment.finalize = wrapper

    def should_expand(self, typ) -> bool:
        """
        Check whether a struct's fields should be expanded.
        """
        expand = self.environment.emmylua_render.get("expand")
        no_expand = self.environment.emmylua_render.get("no_expand")
        if not expand and not no_expand:
            return True
        t = str(typ)
        if expand:
            if not any(fnmatchcase(t, exp) for exp in expand):
                return False
        if no_expand:
            if any(fnmatchcase(t, exp) for exp in no_expand):
                return False
        return True

    def humanize(self, typ: ResolvedType) -> str:
        """
        Render type to a string. Inserts links to embedded struct docs
        and keeps track of linked types, which can later be rendered
        into a reference section.
        """
        toc = self.environment.toc
        link = self.environment.filters["link"]
        refs = typ.refs()
        toc["referenced_types"] = toc["referenced_types"].union(refs)
        # We could shortcut this logic for simple Class/Alias/Enum types
        # by doing the following, but that could be premature optimization:
        # if isinstance(typ, DocumentedType) and not isinstance(
        #     typ, GenericStructInstanceType
        # ):
        #     # Shortcut for simple Class/Alias/Enum types
        #     # but: my.custom.class<my.custom.alias> needs the hacky link rendering
        #     return link(res, literal=True)
        res = wrap(str(typ), "`")
        for ref in refs:
            # Don't render links to undocumented structs
            if isinstance(ref, DocumentedType):
                s = str(ref)
                # Hacky solution: Replace struct names.
                # To do that, we need to ensure literal strings are terminated before
                # and resumed after the link. If it's the fist/last word, we would render
                # a double backtick, which we need to remove (otherwise it might be rendered verbatim)
                res = res.replace(s, wrap(link(s, literal=True), "`")).replace("``", "")
        return res

    def _finalizer(self, data):
        """
        Allow dumping type objects to trigger inbuilt templates
        """
        if data is TYPEREF:
            return self._render_typeref()
        if isinstance(data, list):
            return self._render_list(data)
        if not isinstance(data, DocumentedType):
            return data
        if isinstance(data, DocumentedFunction):
            return self._render_fun(data)
        if isinstance(data, DocumentedField):
            return self._render_field(data)
        toc = self.environment.toc
        if isinstance(data, ClassType):
            toc["rendered_types"].add(data)
            return self._render_class(data)
        if isinstance(data, AliasType):
            toc["rendered_types"].add(data)
            return self._render_alias(data)
        if isinstance(data, EnumType):
            toc["rendered_types"].add(data)
            return self._render_enum(data)
        raise ValueError(f"Unknown class, cannot render: {type(data)}")

    def _render_typeref(self):
        # Ensure indirectly referenced types (those that are only referenced by types
        # in the typeref) are included there as well
        visited = set()
        toc = self.environment.toc
        for typ in list(toc["referenced_types"]):
            toc["referenced_types"] = toc["referenced_types"].union(
                typ.member_refs(visited)
            )
        refs = {
            typ
            for typ in toc["referenced_types"].difference(toc["rendered_types"])
            if isinstance(typ, DocumentedType)
        }
        return self.environment.get_template("typeref.jinja").render(refs=refs)

    def _render_fun(self, fun: DocumentedFunction):
        return self.environment.get_template("function.jinja").render(fun=fun)

    def _render_field(self, field: DocumentedField):
        return self.environment.get_template("field.jinja").render(field=field)

    def _render_class(self, cls: ClassType):
        return self.environment.get_template("class.jinja").render(cls=cls)

    def _render_alias(self, alias: AliasType):
        return self.environment.get_template("alias.jinja").render(alias=alias)

    def _render_enum(self, enum: EnumType):
        return self.environment.get_template("enum.jinja").render(enum=enum)

    def _render_list(self, lst: list):
        """Render list items in separate lines. Allows to auto-dump all functions in a class, for example."""
        return self.environment.get_template("list.jinja").render(lst=lst)

    def preprocess(self, *args, **kwargs):
        """Hack to initialize project name anchor prefix, which is not yet defined when init runs"""
        if not self.prefix_initialized:
            self._initialize_prefix()
        return super().preprocess(*args, **kwargs)

    def parse(self, parser) -> Node:
        tag = next(parser.stream)
        return getattr(self, tag.value)(parser)

    def _initialize_prefix(self) -> None:
        self.environment.anchor_prefix = (
            self.environment.emmylua_render.get("project_name") or ""
        )
        self.prefix_initialized = True

    def _parse_kwargs(self, parser: Parser, kwargs: dict[str, Any]) -> dict[str, Any]:
        if parser.stream.skip_if("name:with"):
            while parser.stream.current.test("name") and parser.stream.look().test(
                "assign"
            ):
                key = parser.stream.current.value
                if key not in kwargs:
                    parser.fail(f"Unknown argument '{key}'", parser.stream.current)
                next(parser.stream)
                parser.stream.expect("assign")
                value_expr = parser.parse_expression()
                kwargs[key] = value_expr
        return kwargs

    def anchor(self, parser: Parser) -> Node:
        """
        Parse a tag of the form:

            {% anchor "Title" with literal=true %}
            ...
            {% endanchor %}
        """
        lineno = parser.stream.current.lineno
        name = parser.parse_expression()
        kwargs = self._parse_kwargs(parser, {"literal": nodes.Const(False)})

        body = parser.parse_statements(["name:endanchor"], drop_needle=True)

        return nodes.CallBlock(
            self.call_method(
                "_render_anchor",
                args=[name],
                kwargs=[Keyword(k, v) for k, v in kwargs.items()],
            ),
            [],
            [],
            body,
        ).set_lineno(lineno)

    def section(self, parser: Parser) -> Node:
        """
        Parse a tag of the form:

            {% section "Title" with anchor=true literal=false markdown=false %}
            ...
            {% endsection %}
        """
        lineno = parser.stream.current.lineno
        title_expr = parser.parse_expression()
        kwargs = self._parse_kwargs(
            parser,
            {
                "anchor": nodes.Const(True),
                "literal": nodes.Const(False),
                "markdown": nodes.Const(False),
            },
        )

        body = parser.parse_statements(["name:endsection"], drop_needle=True)

        return nodes.CallBlock(
            self.call_method(
                "_render_section",
                args=[title_expr],
                kwargs=[Keyword(k, v) for k, v in kwargs.items()],
            ),
            [],
            [],
            body,
        ).set_lineno(lineno)

    def _render_anchor(self, name: str, *, literal: bool, caller):
        prefix = self.environment.anchor_prefix
        content = caller()
        if content and content[0] == "\n":
            content = content[1:]
        return "\n" + self.environment.filters["anchor"](
            content, name, prefix=prefix, literal=literal
        )

    def _render_section(
        self,
        title: str,
        *,
        anchor: str | Literal[True],
        literal: bool,
        markdown: bool,
        caller,
    ):
        stack = self.environment.section_stack
        prefix = self.environment.anchor_prefix
        toc = self.environment.toc

        # Insert ToC
        toc["cur"][title] = {}
        prev_cur = toc["cur"]
        toc["cur"] = toc["cur"][title]
        toc["glossary"][title] = toc["cur"]

        # Push new depth
        stack.append(title)
        level = len(stack)

        # Resolve anchor early to add it to toc
        if anchor is True:
            anchor = slugify(title)
        anchor = resolve_anchor(anchor, prefix=prefix, literal=literal)
        self.environment.anchor_prefix = anchor
        toc["cur"]["__a__"] = anchor

        # Evaluate heading
        heading_text = self.environment.filters["heading"](
            title, level, anchor=anchor, prefix=prefix, literal=True
        )

        content = caller()
        if markdown and self.environment.emmylua_render["fmt"] != "markdown":
            content = self.environment.filters["vimdoc"](content)
        if content and content[0] == "\n":
            content = content[1:]

        stack.pop()
        toc["cur"] = prev_cur
        self.environment.anchor_prefix = prefix

        return f"\n{heading_text}\n{content}"


def slugify(text):
    return re.sub(r"[\W_]+", "-", text).lower().strip("-")


def wrap(text, char, suffix=None):
    return f"{char}{text}{suffix or char}"


def join(it):
    return "\n".join(it)


class Renderer(ABC):
    @abstractmethod
    def anchor(self, line: str, anchor: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def heading(
        self,
        text: str,
        level: int = 1,
        anchor: str | Literal[True] | None = None,
        *,
        stack: list[str],
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def hr(self, char: str = "*") -> str:
        raise NotImplementedError


class MarkdownRenderer(Renderer):
    increase_level: int = 1

    def anchor(
        self,
        line: str,
        anchor: str,
        *,
        prefix: str | None = None,
        literal: bool = False,
    ) -> str:
        if prefix and not literal:
            anchor = "-".join((anchor, prefix))
        anchor_tag = f'<a id="{anchor}"></a>'
        lines = line.splitlines()
        if not lines:
            return anchor_tag
        ret = []
        while lines and not (first_line := lines.pop(0)).strip():
            ret.append("")
        if first_line:
            ret.append(f"{first_line}{anchor_tag}")
            ret.extend(lines)
        else:
            ret.append(anchor_tag)
        return join(ret)

    def heading(
        self,
        text: str,
        level: int = 1,
        anchor: str | Literal[True] | None = None,
        *,
        prefix: str,
        literal: bool = False,
    ) -> str:
        level += self.increase_level
        heading = f"{'#' * max(1, level)} {text}"
        if anchor is True:
            anchor = slugify(text)
        anchor = resolve_anchor(anchor, prefix=prefix, literal=literal)
        if anchor:
            # Pandoc Markdown would work with this:
            # heading += f" {{#{anchor}}}"
            # But GitHub does not support that extension. Possible workaround:
            return join(("", self.anchor("", anchor, literal=True), heading))
        return heading

    def hr(self, char: str = "*") -> str:
        return char * 80

    def link(
        self, text: str, target: str | None = None, *, literal: bool = False
    ) -> str:
        target = target or text
        if literal:
            text = wrap(text, "`")
        return f"[{text}](<#{target}>)"


class VimHelpRenderer(Renderer):
    width = 78

    def anchor(
        self,
        line: str,
        anchor: str,
        *,
        prefix: str | None = None,
        literal: bool = False,
        force_nl: bool = False,
    ) -> str:
        if prefix and not literal:
            anchor = "-".join((prefix, anchor))
        anchor_tag = wrap(anchor, "*")
        lines = line.splitlines()
        if not lines:
            return anchor_tag
        ret = []
        while lines and not (first_line := lines.pop(0)).strip():
            ret.append("")
        if (
            first_line
            and not force_nl
            and len(first_line) + len(anchor_tag) + 2 < self.width
        ):
            anchor_width = self.width - len(first_line)
            ret.append(f"{first_line}{anchor_tag:>{anchor_width}}")
        else:
            ret.append(f"{anchor_tag:>{self.width}}")
            ret.append(first_line)
        ret.extend(lines)
        return join(ret)

    def heading(
        self,
        text: str,
        level: int = 1,
        anchor: str | Literal[True] | None = None,
        *,
        prefix: str,
        literal: bool = False,
    ) -> str:
        if anchor is True:
            anchor = slugify(text)
        anchor = resolve_anchor(anchor, prefix, literal=literal)
        force_nl = False
        if level == 2:
            # Don't uppercase literal strings
            literal_str = False
            use_tilde = False  # If we can't uppercase everything, we need to use a ~
            res = ""
            for char in text:
                if char == "`":
                    literal_str = not literal_str
                    use_tilde = True
                if literal_str:
                    res += char
                else:
                    res += char.upper()
            if use_tilde:
                text = f"{res} ~"
                force_nl = True
            else:
                text = res
        elif level > 2:
            text = f"{text} ~"
            force_nl = True  # not displayed correctly if ~ is not last char on line
        out = [""]
        if level == 1:
            out.append(self.hr())
        if anchor:
            out.append(self.anchor(text, anchor, force_nl=force_nl).lstrip("\n"))
        else:
            out.append(text)
        return "\n".join(out)

    def hr(self, char: str = "=") -> str:
        return char * self.width

    def link(self, text: str, target: None = None, *, literal: bool = False) -> str:
        assert target is None or text == target
        return f"|{text}|"

import logging
from pathlib import Path

import pytest
from lark import Lark
from lark import logger as lark_logger

from emmylua_render.raw_models import Index
from emmylua_render.type_parser import (
    TYPE_GRAMMAR,
    AliasType,
    AnyType,
    ArrayType,
    BooleanType,
    ClassType,
    FunctionType,
    GenericAliasInstanceType,
    GenericStructInstanceType,
    IntegerType,
    IntersectionType,
    LiteralBool,
    LiteralInt,
    LiteralStr,
    NilType,
    NumberType,
    OptionalType,
    PrimitiveType,
    ResolvedType,
    StringType,
    StructType,
    TableType,
    TreeHydrator,
    TupleType,
    UnionType,
    UnknownType,
    VariadicType,
)


@pytest.fixture
def parser(files: Path) -> Lark:
    lark_logger.setLevel(logging.DEBUG)
    docs = Index.model_validate_json((files / "doc.json").read_text())
    transformer = TreeHydrator(docs)
    parser = Lark(TYPE_GRAMMAR, parser="lalr", debug=True, transformer=transformer)
    transformer.parser = parser
    return parser


@pytest.mark.parametrize(
    "ts,typ",
    (
        ("nil", NilType),
        ("any", AnyType),
        ("unknown", UnknownType),
        ("self", (PrimitiveType, "self")),
        ("function", (PrimitiveType, "function")),
        ("thread", (PrimitiveType, "thread")),
        ("userdata", (PrimitiveType, "userdata")),
        ("lightuserdata", (PrimitiveType, "lightuserdata")),
        ("boolean", BooleanType),
        ("integer", IntegerType),
        ("number", NumberType),
        ("string", StringType),
        ("1", (LiteralInt, 1)),
        ("12", (LiteralInt, 12)),
        ('"bar"', (LiteralStr, "bar")),
        # ("'foo'", LiteralStr), Fails parsing, but is not output by emmylua_doc_cli
        ("true", (LiteralBool, True)),
        ("false", (LiteralBool, False)),
        ("{}", TableType),
        ("table", (StructType, "table")),
        ("integer?", (OptionalType, IntegerType)),
        ("string[]", (ArrayType, StringType)),
        ("(string)", (TupleType, (StringType,))),
        ("(1,2,3)", (TupleType, (LiteralInt, LiteralInt, LiteralInt))),
        (
            "(0|3|2|1|4)",
            (
                UnionType,
                (
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                ),
            ),
        ),
        # ('("a"|"b")|number', None), This fails parsing, but emmylua_doc_cli does not output it
        ("(string,any ...)", (TupleType, (StringType, (VariadicType, AnyType)))),
        (
            "(9|4|6|2|11|7...)",
            (
                UnionType,
                (
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                    LiteralInt,
                ),
                True,
            ),
        ),
        ("{ [string]: any }", (TableType, ((StringType, AnyType),))),
        ("(string | number)", (UnionType, (StringType, NumberType))),
        (
            "(integer[]?, string?)",
            (
                TupleType,
                ((OptionalType, (ArrayType, IntegerType)), (OptionalType, StringType)),
            ),
        ),
        ('("block"|"line"|"char")', (UnionType, (LiteralStr, LiteralStr, LiteralStr))),
        (
            "fun(a: integer) -> integer[]?",
            (
                FunctionType,
                (("a", IntegerType),),
                (OptionalType, (ArrayType, IntegerType)),
            ),
        ),
        (
            "(RawType,integer,integer,DataType)",
            (
                TupleType,
                (
                    (StructType, "RawType"),
                    IntegerType,
                    IntegerType,
                    (StructType, "DataType"),
                ),
            ),
        ),
        (
            "fun() -> (string, number, boolean?)",
            (
                FunctionType,
                (),
                (TupleType, (StringType, NumberType, (OptionalType, BooleanType))),
            ),
        ),
        (
            "fun(continuity.core.IdleSession, ...)",
            (
                FunctionType,
                (
                    (
                        (None, (ClassType, "continuity.core.IdleSession")),
                        (None, (VariadicType, AnyType)),
                    )
                ),
            ),
        ),
        (
            "fun(session: continuity.core.IdleSession)",
            (FunctionType, (("session", (ClassType, "continuity.core.IdleSession")),)),
        ),
        (
            "{ is_headless: boolean, is_pager: boolean }",
            (TableType, (("is_headless", BooleanType), ("is_pager", BooleanType))),
        ),
        (
            "continuity.util.shada.EntryData.BufferList.Item[]",
            (ArrayType, (ClassType, "continuity.util.shada.EntryData.BufferList.Item")),
        ),
        (
            "(continuity.core.Session.DetachReasonBuiltin|string)",
            (UnionType, (AliasType, StringType)),
        ),
        # FIXME: AFAICT, at least EmmyLua 0.16 dumps
        #        (fun(a: integer, b: string): integer[]?, string?)[]
        #        as
        #        fun(a: integer, b: string) -> (integer[]?, string?)[]
        #        and does not interpret it as a list of functions.
        (
            "fun(a: integer, b: string) -> (integer[]?, string?)[]",
            (
                FunctionType,
                (("a", IntegerType), ("b", StringType)),
                (
                    ArrayType,
                    (
                        TupleType,
                        (
                            (OptionalType, (ArrayType, IntegerType)),
                            (OptionalType, StringType),
                        ),
                    ),
                ),
            ),
        ),
        (
            "(fun(a: integer, b: string) -> (integer[]?,string?))?",
            (
                OptionalType,
                (
                    FunctionType,
                    (("a", IntegerType), ("b", StringType)),
                    (
                        TupleType,
                        (
                            (OptionalType, (ArrayType, IntegerType)),
                            (OptionalType, StringType),
                        ),
                    ),
                ),
            ),
        ),
        (
            "fun(name: string, opts: continuity.core.ext.HookOpts)[]",
            (
                ArrayType,
                (
                    FunctionType,
                    (
                        ("name", StringType),
                        ("opts", (AliasType, "continuity.core.ext.HookOpts")),
                    ),
                ),
            ),
        ),
        (
            "(continuity.SideEffects.Reset & continuity.SideEffects.Save)",
            (
                IntersectionType,
                (
                    (ClassType, "continuity.SideEffects.Reset"),
                    (ClassType, "continuity.SideEffects.Save"),
                ),
            ),
        ),
        (
            "(continuity.core.ext.Hook.Save|continuity.core.ext.Hook.Load)",
            (
                UnionType,
                (
                    (AliasType, "continuity.core.ext.Hook.Save"),
                    (AliasType, "continuity.core.ext.Hook.Load"),
                ),
            ),
        ),
        (
            "(continuity.util.TryLog.Format & continuity.util.TryLog.Params)",
            (
                IntersectionType,
                (
                    (AliasType, "continuity.util.TryLog.Format"),
                    (ClassType, "continuity.util.TryLog.Params"),
                ),
            ),
        ),
        (
            "continuity.util.shada.ShadaEntry<5,continuity.util.shada.EntryData.Register>",
            (
                GenericAliasInstanceType,
                "continuity.util.shada.ShadaEntry",
                (
                    (LiteralInt, 5),
                    (ClassType, "continuity.util.shada.EntryData.Register"),
                ),
            ),
        ),
        (
            "continuity.util.shada.ShadaEntry<11,continuity.util.shada.EntryData.Change>",
            (
                GenericAliasInstanceType,
                "continuity.util.shada.ShadaEntry",
                (
                    (LiteralInt, 11),
                    (ClassType, "continuity.util.shada.EntryData.Change"),
                ),
            ),
        ),
        (
            "(fun(ctx: { is_headless: boolean, is_pager: boolean }) -> (string|false))?",
            (
                OptionalType,
                (
                    FunctionType,
                    (
                        (
                            "ctx",
                            (
                                TableType,
                                (
                                    ("is_headless", BooleanType),
                                    ("is_pager", BooleanType),
                                ),
                            ),
                        ),
                    ),
                    (UnionType, (StringType, (LiteralBool, False))),
                ),
            ),
        ),
        (
            "(fun(a: integer, b: string) -> (integer[]?,string?)|continuity.SideEffects.Save)",
            (
                UnionType,
                (
                    (
                        FunctionType,
                        (("a", IntegerType), ("b", StringType)),
                        (
                            TupleType,
                            (
                                (OptionalType, (ArrayType, IntegerType)),
                                (OptionalType, StringType),
                            ),
                        ),
                    ),
                    (ClassType, "continuity.SideEffects.Save"),
                ),
            ),
        ),
        (
            '("buffer_list"|"global_mark"|"local_mark"|"search_pattern"|"variable"|"register"...)',
            (
                UnionType,
                (
                    (LiteralStr, "buffer_list"),
                    (LiteralStr, "global_mark"),
                    (LiteralStr, "local_mark"),
                    (LiteralStr, "search_pattern"),
                    (LiteralStr, "variable"),
                    (LiteralStr, "register"),
                ),
                True,
            ),
        ),
        (
            "fun(name: string, opts: continuity.core.ext.HookOpts, target_tabpage: continuity.core.TabID?)[]",
            (
                ArrayType,
                (
                    FunctionType,
                    (
                        ("name", StringType),
                        ("opts", (AliasType, "continuity.core.ext.HookOpts")),
                        (
                            "target_tabpage",
                            (OptionalType, (AliasType, "continuity.core.TabID")),
                        ),
                    ),
                ),
            ),
        ),
        (
            "((continuity.SideEffects.Save & continuity.SideEffects.SilenceErrors)|continuity.SideEffects.Attach)",
            (
                UnionType,
                (
                    (
                        IntersectionType,
                        (
                            (ClassType, "continuity.SideEffects.Save"),
                            (ClassType, "continuity.SideEffects.SilenceErrors"),
                        ),
                    ),
                    (ClassType, "continuity.SideEffects.Attach"),
                ),
            ),
        ),
        (
            "fun(session: continuity.core.ActiveSession, reason: continuity.core.Session.DetachReason, opts: (continuity.core.Session.DetachOpts & continuity.core.PassthroughOpts)) -> std.Nullable<(continuity.core.Session.DetachOpts & continuity.core.PassthroughOpts)>",
            (
                FunctionType,
                (
                    ("session", (ClassType, "continuity.core.ActiveSession")),
                    ("reason", (AliasType, "continuity.core.Session.DetachReason")),
                    (
                        "opts",
                        (
                            IntersectionType,
                            (
                                (ClassType, "continuity.core.Session.DetachOpts"),
                                (AliasType, "continuity.core.PassthroughOpts"),
                            ),
                        ),
                    ),
                ),
                (
                    GenericStructInstanceType,
                    "std.Nullable",
                    (
                        (
                            IntersectionType,
                            (
                                (ClassType, "continuity.core.Session.DetachOpts"),
                                (AliasType, "continuity.core.PassthroughOpts"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
def test_parser(parser: Lark, ts: str, typ):
    def assert_typ(parsed, t):
        if isinstance(t, tuple):
            outer = t[0]
            assert isinstance(parsed, outer)
            inner = t[1]
            if outer is PrimitiveType:
                assert parsed.name == inner
            elif outer.__name__.startswith("Literal"):
                assert parsed.value == inner
            elif outer is StructType or outer is ClassType or outer is AliasType:
                assert parsed.name == inner
            elif (
                outer is GenericStructInstanceType or outer is GenericAliasInstanceType
            ):
                assert parsed.name == inner
                try:
                    typeargs = t[2]
                except IndexError:
                    typeargs = []
                for i, typearg in enumerate(typeargs):
                    assert_typ(parsed.type_args[i], typearg)
            elif outer is OptionalType:
                assert_typ(parsed.inner, inner)
            elif outer is VariadicType:
                assert_typ(parsed.element_type, inner)
            elif outer is ArrayType:
                assert_typ(parsed.element_type, inner)
            elif outer is TupleType or outer is UnionType or outer is IntersectionType:
                for i, el in enumerate(inner):
                    assert_typ(parsed.elements[i], el)
                if outer is not TupleType:
                    try:
                        omitted = t[2]
                    except IndexError:
                        omitted = False
                    assert parsed.omitted is omitted
            elif outer is TableType:
                for k, v in inner:
                    checked = False
                    try:
                        if issubclass(k, ResolvedType):
                            for res_k, res_v in parsed.fields.items():
                                if isinstance(res_k, k):
                                    assert_typ(res_v, v)
                                    checked = True
                                    break
                            else:
                                pytest.fail(f"Missing table key type {k}")
                    except TypeError:
                        pass
                    if not checked:
                        assert_typ(parsed.fields[k], v)
                try:
                    omitted = t[2]
                except IndexError:
                    omitted = False
                assert parsed.omitted is omitted
            elif outer is FunctionType:
                for i, (pname, ptyp) in enumerate(inner):
                    assert parsed.params[i][0] == pname
                    assert_typ(parsed.params[i][1], ptyp)
                try:
                    rets = t[2]
                except IndexError:
                    assert parsed.rets is None
                else:
                    assert_typ(parsed.rets, rets)
            else:
                pytest.fail(f"Missing test for type {outer}")
        else:
            assert isinstance(parsed, t)

    res = parser.parse(ts)
    assert res
    assert_typ(res, typ)
    rend = str(res)
    try:
        assert rend == ts
    except AssertionError as err:
        if not ts.find(" ") and not rend.find(" "):
            raise
        try:
            assert rend.replace(" ", "") == ts.replace(" ", "")
        except AssertionError:
            raise err

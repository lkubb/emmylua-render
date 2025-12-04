"""
Transform the raw emmylua_doc_cli output structure to support easy rendering.
Uses an EBNF parser (Lark) to inspect the strings that emmylua_doc_cli outputs,
especially for aliases in their ``typ`` attribute.
"""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Literal, Self

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from emmylua_render.raw_models import (
    Alias,
    Class,
    FieldMember,
    FnMember,
    LuaEnum,
    LuaType,
    Property,
)

"""
Ugly and approximate grammar for emmylua_doc_cli type strings with ambiguities,
which hopefully does its job reasonably well.

They exhibit slight differences to the usual annotations:

* Function returns are indicated with ``->`` instead of ``:``: ``fun(a: integer) -> boolean``
* Tuples use parentheses instead of brackets: ``(integer,string)``
* With the exception of function args and intersections, elements are not separated by spaces.
* Long types (unions, intersections, tuples, lists?, func args?) can appear shortened with ``...``.
  What defines a long type is determined by the render detail level, which currently
  cannot be overridden from its hardcoded default of ``basic``.
  This means type inspection is not perfect since ``(Foo & Bar & Baz & Quux)``
  might be shortened to ``(Foo & Bar...)`` with no straightforward way to get more info.
* For tuples (and func args?), these omissions are especially tricky since they appear
  similar to the basic variadic annotation. The only difference is a missing space:
  ``(integer,string...)`` (omission) ``(integer,string ...)`` (tuple with initial int + variable number of strings)
"""
TYPE_GRAMMAR = r"""
    ?start: type

    // Separate variadics to avoid parsing omissions as variadics.
    // FIXME: omissions are applied to tuples as well, only difference is the absence of a space between last type
    //       and `...` [`,any...` vs `,any ...`], which we're ignoring here.
    ?type: primary_type | variadic_type

    // Note to self:
    //   Variadic parsing breaks when using anonymous "..." instead of DOTS and a `?` is prepended to inline a single element
    //   and it's not renamed via -> variadic_type.
    variadic_type: \
        primary_type "..."
      | "multi" "<" "..." ">" -> complex_variadic_type
    ?primary_type: basic_type | suffix_type
    ?suffix_type: \
        (basic_type|suffix_type) "?" -> optional_type        // string?
      | (basic_type|suffix_type) "[]" -> array_type          // string[]
      | "(" (function_void_type|function_ret_type) ")" "?" -> optional_type // (fun(foo: integer): string)?
      // Note: EmmyLua always dumps (fun())? as (fun())? and (fun())[] as fun()[], so no special casing needed for arrays.
      //       Optional funs would be interpreted as optional tuples with one fun element otherwise.

    ?basic_type: \
        literal_type                             // "string", 34, false, true
      | function_void_type
      | function_ret_type
      | table_type                               // {foo: boolean, [integer]: boolean?}
      | generic_struct_type                      // my.Container<number, string>
      | struct_type                              // my.custom.Class
      | primitive_type                           // number, string, boolean, nil, any, userdata, unknown, ...
      | tuple_type                               // (integer, string), (string, any ...)
      | "(" primary_type ("|" primary_type)+ ")" -> union_type               // (integer|number), ("foo"|"bar"|boolean)
      | "(" primary_type ("&" primary_type)+ ")" -> intersection_type        // (MyTrait & MyOtherTrait)
      | "(" primary_type ("|" primary_type)+ "..." ")" -> union_type_omitted // emmylua_doc_cli hardcodes detail level to basic, which omits items of large unions/tuples
      | "(" primary_type ("&" primary_type)+ "..." ")" -> intersection_type_omitted // see above

    // This raises ambiguity a lot and it's not emitted by emmylua: (e.g. `integer|string`, `(foo|bar)|baz`, `foo & (bar|baz)`)
    // ?basic_type_extended: \
    //     primary_type ("|" primary_type)+ -> union_type                       // union without parentheses, this is not emitted by EmmyLua though
    //   | primary_type ("&" primary_type)+ -> intersection_type                // intersection without parentheses, is not emitted by EmmyLua though

    tuple_type: "(" type_list ")"

    type_list: type ("," type)*

    // function
    // FIXME: Return parsing introduces ambiguity with `?`/`[]`/`...`.
    //        Since `function_type` is a `primary_type`, fun() -> integer?
    //        could be parsed as (fun() -> integer)? or fun() -> (integer?)
    //        Note that it was renamed to function_ret_type.
    //        The following was obtained by modifying the rules a bit:
    //   Shift/Reduce conflict for terminal ARR: (resolving as shift)
    //    * <function_type : FUN LPAR param_list RPAR ARROW primary_type>
    //   Shift/Reduce conflict for terminal QMARK: (resolving as shift)
    //    * <function_type : FUN LPAR param_list RPAR ARROW primary_type>
    //   Shift/Reduce conflict for terminal ARR: (resolving as shift)
    //    * <function_type : FUN LPAR RPAR ARROW primary_type>
    //   Shift/Reduce conflict for terminal QMARK: (resolving as shift)
    //    * <function_type : FUN LPAR RPAR ARROW primary_type>

    //
    optional_function_type: "(" (function_void_type|function_ret_type) ")" "?" -> optional_type
    function_void_type: "fun" "(" [param_list] ")"
    function_ret_type: function_void_type "->" type
    param_list: param ("," param)*
    param: (IDENTIFIER | SELF) ":" type -> named_param
         | DOTS ":" type -> named_param
         | DOTS  -> unnamed_param
         | type -> unnamed_param

    // table/"list"/"array"/inline "object"
    // FIXME: I think omissions apply to tables as well.
    table_type: "{" [_table_field_list] "}"
    _table_field_list: table_field ("," table_field)*
    table_field: IDENTIFIER ":" type -> array_named_field
               | "[" type "]" ":" type -> array_typed_field
               | DOTS -> array_omission

    // classes/enums/aliases
    struct_type: IDENTIFIER ("." IDENTIFIER)*
    generic_struct_type: struct_type "<" type_list ">"

    // literals
    ?literal_type: integer_literal
                 | string_literal
                 | boolean_literal
    string_literal: ESCAPED_STRING
    integer_literal: SIGNED_INT
    boolean_literal: "true" -> literal_true
                   | "false" -> literal_false

    // "inbuilt" types, without table (needs to be generic, causes collision)
    primitive_type: "nil" -> primitive_nil
                  | "boolean" -> primitive_boolean
                  | "number" -> primitive_number
                  | "integer" -> primitive_integer
                  | "userdata" -> primitive_userdata
                  | "lightuserdata" -> primitive_lightuserdata
                  | "thread" -> primitive_thread
                  | "any" -> primitive_any
                  | "void" -> primitive_nil
                  | "self" -> primitive_self
                  | "function" -> primitive_function
                  | "string" -> primitive_string
                  | "unknown" -> primitive_unknown

    // Terminals
    DOTS: "..."
    SIGNED_INT: ["-"] INT
    SELF: "self" // this seems to be a predefined token, IDENTIFIER does not include it in fun(self: any)
    %import common.INT
    %import common.CNAME -> IDENTIFIER
    %import common.ESCAPED_STRING // uses double-quotes only, but emmylua always dumps string literals with double quotes

    // Ignore whitespace.
    // Note: This breaks distinction between long, omitted tuples (string,integer,...) and variadic tuples (string,any ...)
    %import common.WS
    %ignore WS
"""


def wrapped_repr(inner, *, name_prefix="", name_suffix=""):
    inner_repr = repr(inner)
    inner_name = type(inner).__name__
    if inner_repr.startswith(inner_name):
        repr_name = name_prefix + inner_name + name_suffix
        rest = inner_repr[len(inner_name) :]
    elif (sub_pos := inner_repr.find("([{")) > 0:
        inner_name, rest = inner_repr[0:sub_pos], inner_repr[sub_pos:]
    elif inner_repr.startswith(short_name := inner_name.replace("Type", "")):
        repr_name = name_prefix + short_name + name_suffix
        rest = inner_repr[len(short_name) :]
    else:
        repr_name, rest = name_prefix + inner_repr + name_suffix, ""
    return repr_name + rest


class TypeKind(Enum):
    PRIMITIVE = "primitive"
    UNION = "union"
    INTERSECTION = "intersection"
    TUPLE = "tuple"
    TABLE = "table"
    FUNCTION = "function"
    LITERAL = "literal"
    ARRAY = "array"
    OPTIONAL = "optional"
    VARIADIC = "variadic"
    STRUCT = "struct"
    CLASS = "class"
    ALIAS = "alias"
    ENUM = "enum"
    GENERIC_STRUCT_INSTANCE = "generic_struct_instance"
    GENERIC_CLASS_INSTANCE = "generic_class_instance"
    GENERIC_ALIAS_INSTANCE = "generic_alias_instance"
    GENERIC_ENUM_INSTANCE = "generic_enum_instance"


@dataclass(frozen=True)
class ResolvedType:
    kind: TypeKind = field(init=False, repr=False)
    parser: Lark = field(kw_only=True, repr=False, compare=False)

    @property
    def is_optional(self) -> bool:
        """
        Overridden by OptionalType
        """
        return False

    def substitute_typevars(self, _typevars: dict[str, "ResolvedType"]) -> Self:
        # Many types can contain generic parameters, so we should be able to just
        # map the function down the chain. By default, don't substitute anything.
        return self

    def __deepcopy__(self, memo):
        """
        Because of some shenanigans in the class structure, we need to account for
        circular references in instance dicts. Centralize it here since all affected
        classes inherit from this one.
        Because that's not fun enough, we also inject a reference to the parser into
        most instances. It should not (and cannot) be deepcopied.
        """
        cls = type(self)
        new_self = cls.__new__(cls)
        memo[id(self)] = new_self
        new_attrs = {}
        has_parser = False
        for k, v in self.__dict__.items():
            if k == "parser":
                # having the parser in here is shenanigan no 2
                has_parser = True
                continue
            new_attrs[k] = deepcopy(v, memo)
        if has_parser:
            new_attrs["parser"] = self.parser
        object.__setattr__(new_self, "__dict__", new_attrs)
        return new_self


@dataclass(frozen=True)
class PrimitiveType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.PRIMITIVE)
    parser: Lark | None = field(kw_only=True, repr=False, compare=False, default=None)
    name: str

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name.capitalize()


# Make repr a bit nicer by creating classes for common types:


@dataclass(frozen=True)
class StringType(PrimitiveType):
    name: Literal["string"] = field(init=False, repr=False, default="string")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class BooleanType(PrimitiveType):
    name: Literal["boolean"] = field(init=False, repr=False, default="boolean")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class NumberType(PrimitiveType):
    name: Literal["number"] = field(init=False, repr=False, default="number")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class IntegerType(PrimitiveType):
    name: Literal["integer"] = field(init=False, repr=False, default="integer")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class UnknownType(PrimitiveType):
    name: Literal["unknown"] = field(init=False, repr=False, default="unknown")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class NilType(PrimitiveType):
    name: Literal["nil"] = field(init=False, repr=False, default="nil")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class AnyType(PrimitiveType):
    name: Literal["any"] = field(init=False, repr=False, default="any")

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class DocumentedType:
    """
    Base class for anything that could be resolved to an EmmyLua ``Property``.
    """

    typedef: Property = field(repr=False, compare=False, kw_only=True)
    _tags: dict[str, str] | None = field(
        init=False, repr=False, compare=False, default=None
    )

    @property
    def desc(self) -> str | None:
        return self.typedef.description

    @property
    def visibility(self) -> str | None:
        return self.typedef.visibility

    @property
    def deprecated(self) -> bool:
        return self.typedef.deprecated

    @property
    def deprecated_reason(self) -> str | None:
        return self.typedef.deprecated_reason

    @property
    def tags(self) -> dict[str, str]:
        if self._tags is None:
            object.__setattr__(
                self,
                "_tags",
                {tag.tag_name: tag.content for tag in (self.typedef.tag_content or [])},
            )
        return self._tags


class DocumentedField(DocumentedType):
    """
    Represents a field on a documented struct that is not a function.
    """

    typedef: FieldMember
    typ: ResolvedType  # making this a generic yields MRO resolution issues

    def __init__(self, typ: ResolvedType, *, typedef: FieldMember):
        """
        Dynamically subclass ``typ``. For a weak justification
        of this worrying pattern, see ``OptionalType``.
        """
        DocumentedType.__init__(self, typedef=typedef)
        object.__setattr__(self, "typ", typ)
        object.__setattr__(
            self, "__orig_attrs", tuple(x for x in dir(self) if not x.startswith("__"))
        )

        self.__class__ = type(
            typ.__class__.__name__ + "Field",
            (self.__class__, typ.__class__),
            {},
        )

    def __getattribute__(self, k):
        if k.startswith("__") or k in object.__getattribute__(self, "__orig_attrs"):
            return object.__getattribute__(self, k)
        return getattr(self.typ, k)

    def substitute_typevars(self, typevars: dict[str, ResolvedType]) -> Self:
        inner = self.typ.substitute_typevars(typevars)
        return DocumentedField(typedef=self.typedef, typ=inner)

    @property
    def name(self) -> str:
        return self.typedef.name

    @classmethod
    def from_member(
        cls,
        parser: Lark,
        member: FieldMember,
        typevar_ctx: dict[str, str | None] | None = None,
    ) -> "DocumentedField":
        """
        Bridge anonymous type strings emitted by emmylua_doc_cli with rich docs
        derived from docstrings for classes etc..
        """
        resolved = parser.parse(getattr(member, "literal", None) or member.typ)
        new = cls(resolved, typedef=member)
        if typevar_ctx:
            return new.substitute_typevars(typevar_ctx)
        return new

    def __repr__(self) -> str:
        return wrapped_repr(self.typ, name_suffix="Field")


@dataclass(frozen=True)
class FunctionType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.FUNCTION)
    params: tuple[tuple[str | None, ResolvedType], ...]
    rets: ResolvedType | None = None  # multiple returns are modeled via tuples

    def substitute_typevars(self, typevars: dict[str, ResolvedType]) -> Self:
        params = tuple(
            (param[0], param[1].substitute_typevars(typevars)) for param in self.params
        )
        rets = self.rets and self.rets.substitute_typevars(typevars) or None
        return replace(self, params=params, rets=rets)

    def is_void(self) -> bool:
        return self.rets is None

    def __str__(self) -> str:
        try:
            rendered_params = [
                (f"{param[0]}: {param[1]}" if param[0] is not None else str(param[1]))
                if not isinstance(param[1], VariadicType)
                or not isinstance(param[1].element_type, AnyType)
                else "..."  # render fun(foo: integer, ...) the same way (doesn't work in tuples, where it requires [integer, any ...])
                for param in self.params
            ]
        except RuntimeError as err:
            raise RuntimeError(dict(self.params)["..."].__class__) from err
        rend = f"fun({', '.join(rendered_params)})"
        if self.rets:
            rend += f" -> {self.rets}"
        return rend

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        params = ", ".join(
            ": ".join((name, f"[{repr(typ)}]") if name else (f"[{repr(typ)}]",))
            for name, typ in self.params
        )
        ret = ""
        if self.rets:
            # FIXME: Not really correct since multiple rets are modeled as tuples as well,
            #        but we currently can't tell them apart here without the typedef
            ret = f" => {repr(self.rets)}"
        return f"{name}({params}){ret}"


@dataclass(frozen=True)
class DocumentedParameter:
    name: str | None
    desc: str | None
    typ: ResolvedType
    orig_typ: str | None


@dataclass(frozen=True)
class DocumentedFunction(FunctionType, DocumentedType):
    typedef: FnMember = field(repr=False, compare=False, kw_only=True)
    typevar_ctx: dict[str, str | None] | None = None
    _generics: tuple[tuple[str, str | None]] = field(
        init=False, repr=False, compare=False, default=None
    )
    _returns: list[DocumentedParameter] = field(
        init=False, repr=False, compare=False, default=None
    )
    _parameters: list[DocumentedParameter] = field(
        init=False, repr=False, compare=False, default=None
    )
    _overloads: list[FunctionType] = field(
        init=False, repr=False, compare=False, default=None
    )

    @property
    def name(self) -> str:
        return self.typedef.name

    @property
    def is_async(self) -> bool:
        return self.typedef.is_async

    @property
    def is_meth(self) -> bool:
        return self.typedef.is_meth

    @property
    def is_generic(self) -> bool:
        return bool(self.typedef.generics)

    @property
    def is_nodiscard(self) -> bool:
        return self.typedef.is_nodiscard

    @property
    def nodiscard_message(self) -> str | None:
        return self.typedef.nodiscard_message

    @property
    def generics(self) -> tuple[tuple[str, str | None]]:
        if not self._generics:
            object.__setattr__(
                self,
                "_generics",
                tuple(
                    (generic.name, generic.base) for generic in self.typedef.generics
                ),
            )
        return self._generics

    @property
    def overloads(self) -> tuple[tuple[str, str | None]]:
        if not self._overloads:
            object.__setattr__(
                self,
                "_overloads",
                tuple(map(self.parser.parse, self.typedef.overloads)),
            )
        return self._overloads

    @property
    def parameters(self) -> list[DocumentedParameter]:
        if not self._parameters:
            ret = []
            for param in self.typedef.params:
                ret.append(
                    {
                        "name": param.name,
                        "desc": param.desc,
                        "orig_typ": param.typ,
                    }
                )
            for i, param in enumerate(self.params):
                assert not param[0] or param[0] == ret[i]["name"]
                ret[i]["typ"] = param[1]
            object.__setattr__(
                self, "_parameters", list(map(lambda x: DocumentedParameter(**x), ret))
            )
        return self._parameters

    @property
    def returns(self) -> list[DocumentedParameter]:
        if not self._returns:
            ret = []
            try:
                if self.rets is not None:
                    for param in self.typedef.returns:
                        ret.append(
                            {
                                "name": param.name,
                                "desc": param.desc,
                                "orig_typ": param.typ,
                            }
                        )
                    # An error that happens in parsing is that a tuple is
                    # misinterpreted as multiple returns (because they are
                    # dumped in parentheses instead of brackets for some reason).
                    # Since we have the proper type declaration, fix it here
                    if self.rets.kind != TypeKind.TUPLE or len(ret) != len(
                        self.rets.elements
                    ):
                        ret[0]["typ"] = self.rets
                    else:
                        for i, rettyp in enumerate(self.rets.elements):
                            ret[i]["typ"] = rettyp
                object.__setattr__(
                    self, "_returns", list(map(lambda x: DocumentedParameter(**x), ret))
                )
            except AttributeError as err:
                raise RuntimeError(err) from err
        return self._returns

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        params = ", ".join(
            ": ".join(
                (param.name, f"[{repr(param.typ)}]")
                if param.name
                else (f"[{repr(param.typ)}]",)
            )
            for param in self.parameters
        )
        rets = [
            ": ".join(
                (ret.name, f"[{repr(ret.typ)}]")
                if ret.name
                else (f"[{repr(ret.typ)}]",)
            )
            for ret in self.returns
        ]
        fun = f"{name}({params})"
        if not rets:
            return fun
        if len(rets) > 1:
            return f"{fun} => ({', '.join(rets)})"
        return f"{fun} => {rets[0]}"

    @classmethod
    def from_member(
        cls,
        parser: Lark,
        member: FnMember,
        typevar_ctx: dict[str, str | None] | None = None,
    ) -> "DocumentedFunction":
        """
        We're building a bridge between raw emmylua_doc_cli output
        (string ``typ`` fields) and types that are documented.
        This takes a documented function (part of a class/module)
        and hydrates all string-valued types into objects that
        can be used to render documentation where it matters.
        """
        params = []
        for param in member.params:
            try:
                params.append(
                    (param.name, param.typ and parser.parse(param.typ) or None)
                )
            except (UnexpectedCharacters, UnexpectedToken):
                # TODO:  log, most likely omitted function args/rets
                params.append((param.name, UnknownType()))
        rets = []
        for ret in member.returns:
            try:
                rets.append(ret.typ and parser.parse(ret.typ) or None)
            except (UnexpectedCharacters, UnexpectedToken):
                rets.append(UnknownType())
        if len(rets) == 1:
            rets = rets[0]
            if isinstance(rets, NilType):
                # emmylua_doc_cli dumps nil returns
                rets = None
        else:
            rets = TupleType(tuple(rets), parser=parser)
        result = cls(
            params=params,
            rets=rets,
            parser=parser,
            typedef=member,
            typevar_ctx=typevar_ctx,
        )
        if typevar_ctx:
            return result.substitute_typevars(typevar_ctx)
        return result


@dataclass(frozen=True)
class StructType(ResolvedType):
    """
    Unknown named custom type. Could be class / alias / enum, but it's only
    returned if we cannot find the definition in the emmylua_doc_cli output.
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.STRUCT)
    name: str
    typedef: Class | Alias | Enum | None = field(
        kw_only=True, default=None, compare=False, repr=False
    )

    _generics: tuple[tuple[str, str | None]] = field(
        init=False, repr=False, compare=False, default=None
    )
    _members: dict[str, DocumentedFunction | DocumentedField] = field(
        init=False, repr=False, compare=False, default=None
    )
    _funs: dict[str, DocumentedFunction] = field(
        init=False, repr=False, compare=False, default=None
    )
    _fields: dict[str, DocumentedField] = field(
        init=False, repr=False, compare=False, default=None
    )

    def substitute_typevars(self, typevars: dict[str, ResolvedType]) -> ResolvedType:
        if not self.typedef and self.name in typevars:
            # => this unknown "struct" is a generic type variable
            return deepcopy(typevars[self.name])
        return self

    @property
    def name_parts(self) -> tuple[str]:
        return tuple(self.name.split("."))

    @property
    def is_generic(self) -> bool:
        if not self.typedef:
            return None  # don't know without definition
        return bool(self.typedef.generics)

    @property
    def generics(self) -> tuple[tuple[str, str | None]]:
        if not self.typedef:
            return []
        if not self._generics:
            object.__setattr__(
                self,
                "_generics",
                tuple(
                    (generic.name, generic.base) for generic in self.typedef.generics
                ),
            )
        return self._generics

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        if not self.typedef:
            return {}
        if not self._members:
            # FIXME: Overloads from meta are dumped as separate functions with same name
            object.__setattr__(
                self,
                "_members",
                {
                    member.name: DocumentedFunction.from_member(self.parser, member)
                    if isinstance(member, FnMember)
                    else DocumentedField.from_member(self.parser, member)
                    if isinstance(member, FieldMember)
                    else member
                    for member in self.typedef.members
                },
            )
        return self._members

    @property
    def funs(self) -> dict[str, DocumentedFunction]:
        try:
            if not self.typedef:
                return {}
            if not self._funs:
                # FIXME: Overloads from meta are dumped as separate functions with same name
                object.__setattr__(
                    self,
                    "_funs",
                    {
                        name: member
                        for name, member in self.members.items()
                        if isinstance(member, DocumentedFunction)
                    },
                )
            return self._funs
        except AttributeError as err:
            # @property raising an AttributeError is treated like
            # undefined property, which falls back to __getattr__, if defined.
            # This makes debugging very hard since the initial error is suppressed.
            raise RuntimeError(err) from err

    @property
    def fields(self) -> dict[str, DocumentedField]:
        if not self.typedef:
            return {}
        if not self._fields:
            object.__setattr__(
                self,
                "_fields",
                {
                    name: member
                    for name, member in self.members.items()
                    if isinstance(member, DocumentedField)
                },
            )
        return self._fields

    def _filter_typevars(
        self, typevars: dict[str, ResolvedType]
    ) -> tuple[list[ResolvedType], bool]:
        type_args = []
        if not self.is_generic:
            return type_args, False
        found_any = False
        for name, _ in self.generics:
            if name in typevars:
                type_args.append(typevars[name])
                found_any = True
            else:
                type_args.append(StructType(name, parser=self.parser))
        return type_args, found_any

    def __str__(self) -> str:
        try:
            return self.name
        except AttributeError:
            raise RuntimeError(self.__class__)

    def __repr__(self) -> str:
        return type(self).__name__.replace("Type", "") + f'["{self.name}"]'


@dataclass(frozen=True)
class ClassType(StructType, DocumentedType):
    """
    Custom class with raw emmylua_doc_cli definition.
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.CLASS)
    typedef: Class = field(kw_only=True, repr=False, compare=False)
    _bases: list["StructType"] = field(
        init=False, repr=False, compare=False, default=None
    )

    @property
    def bases(self) -> list["StructType"]:
        if not self._bases:
            object.__setattr__(
                self, "_bases", [self.parser.parse(base) for base in self.typedef.bases]
            )
        return self._bases

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        if not self._members:
            attrs = {}
            # Ensure inheritance is resolved correctly by reversing priority
            for base in reversed(self.bases):
                if not hasattr(base, "members"):
                    continue
                for name, member in base.members.items():
                    attrs[name] = member
            for name, member in self.typedef.members.items():
                attrs[name] = member
            object.__setattr__(
                self,
                "_members",
                {
                    name: DocumentedFunction.from_member(self.parser, member)
                    if isinstance(member, FnMember)
                    else DocumentedField.from_member(self.parser, member)
                    if isinstance(member, FieldMember)
                    else member
                    for name, member in attrs.items()
                },
            )
        return self._members

    def substitute_typevars(
        self, typevars: dict[str, ResolvedType]
    ) -> Self | "GenericClassInstanceType":
        if not self.is_generic:
            return self
        type_args, found_any = self._filter_typevars(typevars)
        if not found_any:
            return self
        return GenericClassInstanceType(
            self.name,
            type_args=tuple(type_args),
            typedef=self.typedef,
            parser=self.parser,
        )

    def __repr__(self) -> str:
        return type(self).__name__.replace("Type", "") + f'["{self.name}"]'


@dataclass(frozen=True)
class AliasType(StructType, DocumentedType):
    """
    Custom alias with raw emmylua_doc_cli definition.
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.ALIAS)
    typedef: Alias = field(kw_only=True, compare=False, repr=False)
    typ: ResolvedType = field(init=False, compare=False)

    def __getattr__(self, k: str):
        if k.startswith("__"):
            raise AttributeError(k)
        return getattr(self.typ, k)

    def __post_init__(self):
        # making a @property out of this means not being able to show it in repr without hacks
        # Need to circumvent frozen (__hash__ is neeeded to be able to use types in table keys)
        # but this should be fine since `typ` is not used for equality check
        object.__setattr__(self, "typ", self.parser.parse(self.typedef.typ))

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        if not self._members:
            object.__setattr__(self, "_members", getattr(self.typ, "members", {}))
        return self._members

    def substitute_typevars(
        self, typevars: dict[str, ResolvedType]
    ) -> Self | "GenericClassInstanceType":
        if not self.is_generic:
            return self
        type_args, found_any = self._filter_typevars(typevars)
        if not found_any:
            return self
        return GenericAliasInstanceType(
            self.name,
            type_args=tuple(type_args),
            typedef=self.typedef,
            parser=self.parser,
        )

    def __repr__(self) -> str:
        return (
            type(self).__name__.replace("Type", "")
            + f'["{self.name}"]|== {repr(self.typ)} ==|)'
        )


@dataclass(frozen=True)
class EnumType(StructType, DocumentedType):
    """
    Custom enum with raw emmylua_doc_cli definition.
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.ENUM)
    typedef: Enum = field(kw_only=True, repr=False, compare=False)
    typ: "UnionType" = field(init=False, compare=False)

    def __post_init__(self):
        # Don't rely on the `typ` in typedef, it's often abbreviated.
        object.__setattr__(
            self,
            "typ",
            UnionType([x.typ for x in self.fields.values()], parser=self.parser),
        )


@dataclass(frozen=True)
class TableType(ResolvedType):
    """
    A table defined via ``{ foo: integer, [string]: boolean? }``.
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.TABLE)
    _fields: tuple[tuple[str | ResolvedType | None, ResolvedType], ...]
    omitted: bool = False

    @property
    def fields(self) -> dict[str | ResolvedType | int, ResolvedType]:
        ret = {}
        num = 1
        for k, v in self._fields:
            if k is None:
                ret[num] = v
                num += 1
            else:
                ret[k] = v
        return ret

    def substitute_typevars(self, typevars) -> Self:
        fields = tuple(
            (
                field[0].substitute_typevars(typevars)
                if isinstance(field[0], ResolvedType)
                else field[0],
                field[1].substitute_typevars(typevars)
                if isinstance(field[1], ResolvedType)
                else field[1],
            )
        )
        return replace(self, fields=fields)

    def __str__(self) -> str:
        if not self.fields:
            if self.omitted:
                return "{...}"
            return "{}"
        rendered = [
            f"{key}: {val}" for key, val in self.fields.items() if isinstance(key, str)
        ] + [
            f"[{key}]: {val}"
            for key, val in self.fields.items()
            if isinstance(key, ResolvedType)
        ]
        if self.omitted:
            rendered.append("...")
        return f"{{ {', '.join(rendered)} }}"


@dataclass(frozen=True)
class UnionType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.UNION)
    elements: tuple[ResolvedType, ...]
    omitted: bool = False

    def substitute_typevars(self, typevars) -> Self:
        elements = tuple(el.substitute_typevars(typevars) for el in self.elements)
        return replace(self, elements=elements)

    def __str__(self) -> str:
        rendered = list(map(str, self.elements))
        return f"({'|'.join(rendered)}{'...' if self.omitted else ''})"

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        if self.omitted:
            name = "Omitted" + name
        elements = list(map(repr, self.elements))
        return name + f"({' | '.join(elements)})"


@dataclass(frozen=True)
class IntersectionType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.INTERSECTION)
    elements: tuple[ResolvedType, ...]
    omitted: bool = False

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        res = {}
        for el in self.elements:
            try:
                res |= el.members
            except AttributeError:
                pass
        return res

    @property
    def fields(self) -> dict[str, DocumentedField]:
        res = {}
        for el in self.elements:
            try:
                res |= el.fields
            except AttributeError:
                pass
        return res

    def substitute_typevars(self, typevars) -> Self:
        elements = tuple(el.substitute_typevars(typevars) for el in self.elements)
        return replace(self, elements=elements)

    def __str__(self) -> str:
        rendered = list(map(str, self.elements))
        return f"({' & '.join(rendered)}{'...' if self.omitted else ''})"

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        if self.omitted:
            name = "Omitted" + name
        elements = list(map(repr, self.elements))
        return name + f"({' & '.join(elements)})"


@dataclass(frozen=True)
class TupleType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.TUPLE)
    elements: tuple[ResolvedType, ...]

    def substitute_typevars(self, typevars) -> Self:
        elements = tuple(el.substitute_typevars(typevars) for el in self.elements)
        return replace(self, elements=elements)

    def __str__(self) -> str:
        rendered = list(map(str, self.elements))
        return f"({','.join(rendered)})"

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        elements = list(map(repr, self.elements))
        return name + f"[{', '.join(elements)}]"


@dataclass(frozen=True)
class GenericStructInstanceType(StructType):
    kind: TypeKind = field(
        init=False, repr=False, default=TypeKind.GENERIC_STRUCT_INSTANCE
    )
    type_args: tuple[ResolvedType, ...]

    def __post_init__(self):
        if self.typedef is not None:
            assert len(self.type_args) <= len(self.typedef.generics)

    def substitute_typevars(
        self, typevars: dict[str, ResolvedType]
    ) -> Self | "GenericClassInstanceType":
        # FIXME: We currently don't account for partially defined generics
        return self

    @property
    def is_generic(self):
        """
        Even though this is dubbed GenericInstance because we received
        at least one type_arg, we could still be generic in one or more
        variables.
        """
        # FIXME: This doesn't account for non-sequential definitions like table<K, string>
        return len(self.type_args) < len(self.typedef.generics)

    def _typevar_ctx(self):
        if not self.typedef:
            return {}
        return {
            generic.name: typearg
            for generic, typearg in zip(self.typedef.generics, self.type_args)
        }

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        if not self.typedef:
            return {}
        if not self._members:
            ctx = self._typevar_ctx()
            object.__setattr__(
                self,
                "_members",
                {
                    member.name: DocumentedFunction.from_member(
                        self.parser, member, ctx
                    )
                    if isinstance(member, FnMember)
                    else DocumentedField.from_member(self.parser, member, ctx)
                    if isinstance(member, FieldMember)
                    else member.substitute_typevars(ctx)
                    for member in self.typedef.members
                },
            )
        return self._members

    def __str__(self) -> str:
        rendered = list(map(str, self.type_args))
        return f"{self.name}<{','.join(rendered)}>"

    def __repr__(self) -> str:
        name = type(self).__name__.replace("Type", "")
        rendered = list(map(str, self.type_args))
        return f'{name}["{self.name}<{", ".join(rendered)}>"]'


@dataclass(frozen=True)
class GenericClassInstanceType(GenericStructInstanceType, ClassType):
    kind: TypeKind = field(
        init=False, repr=False, default=TypeKind.GENERIC_CLASS_INSTANCE
    )

    @property
    def bases(self) -> list["StructType"]:
        if not self._bases:
            ctx = self._typevar_ctx()
            object.__setattr__(
                self,
                "_bases",
                [
                    self.parser.parse(base).substitute_typevars(ctx)
                    for base in self.typedef.bases
                ],
            )
        return self._bases

    @property
    def members(self) -> dict[str, DocumentedFunction | DocumentedField]:
        if not self._members:
            ctx = self._typevar_ctx()
            attrs = {}
            # Ensure inheritance is resolved correctly by reversing priority
            for base in reversed(self.bases):
                for name, member in base.members.items():
                    attrs[name] = member
            for name, member in self.typedef.members.items():
                attrs[name] = member
            object.__setattr__(
                self,
                "_members",
                {
                    name: DocumentedFunction.from_member(self.parser, member, ctx)
                    if isinstance(member, FnMember)
                    else DocumentedField.from_member(self.parser, member, ctx)
                    if isinstance(member, FieldMember)
                    # Inherited member from base. Already resolved.
                    else member
                    for name, member in attrs.items()
                },
            )
        return self._members

    def __repr__(self):
        return super().__repr__()


@dataclass(frozen=True)
class GenericAliasInstanceType(GenericStructInstanceType, AliasType):
    kind: TypeKind = field(
        init=False, repr=False, default=TypeKind.GENERIC_ALIAS_INSTANCE
    )

    def __post_init__(self):
        AliasType.__post_init__(self)
        GenericStructInstanceType.__post_init__(self)
        # This type still includes the unresolved generics,
        # need to substitute our typevars.
        object.__setattr__(
            self, "typ", self.typ.substitute_typevars(self._typevar_ctx())
        )

    def __repr__(self) -> str:
        base = super().__repr__()
        return f"{base}|== {repr(self.typ)} ==|"


@dataclass(frozen=True)
class GenericEnumInstanceType(GenericStructInstanceType, EnumType):
    kind: TypeKind = field(
        init=False, repr=False, default=TypeKind.GENERIC_ENUM_INSTANCE
    )

    def __post_init__(self):
        EnumType.__post_init__(self)
        GenericStructInstanceType.__post_init__(self)
        object.__setattr__(
            self, "typ", self.typ.substitute_typevars(self._typevar_ctx())
        )


@dataclass(frozen=True)
class LiteralType(ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.LITERAL)
    parser: Lark | None = field(kw_only=True, repr=False, compare=False, default=None)
    value: str | int | bool

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return f'"{self.value}"'
        if isinstance(self.value, bool):
            return str(self.value).lower()
        return str(self.value)

    def __repr__(self) -> str:
        return type(self).__name__ + f"({self})"


@dataclass(frozen=True)
class LiteralStr(LiteralType):
    value: str

    def __str__(self) -> str:
        return f'"{self.value}"'

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class LiteralInt(LiteralType):
    value: str

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return super().__repr__()


@dataclass(frozen=True)
class LiteralBool(LiteralType):
    value: str

    def __str__(self) -> str:
        return str(self.value).lower()

    def __repr__(self) -> str:
        return super().__repr__()


class OptionalType[T: ResolvedType](ResolvedType):
    kind: TypeKind = TypeKind.OPTIONAL
    inner: T

    def __init__(self, inner: T, **_):
        """
        Dynamically subclass ``inner``. Sounds like a dumb idea,
        but oh well, it's fun and makes docs rendering easier.
        This is not a long-running process.
        """
        object.__setattr__(self, "inner", inner)
        object.__setattr__(
            self, "__orig_attrs", tuple(x for x in dir(self) if not x.startswith("__"))
        )
        # An optional type is always optional, we don't need to be able
        # to wrap ourselves, hence we don't need to account for MRO.
        # Assumption: The type parser does its job.
        self.__class__ = type(
            "Optional" + inner.__class__.__name__, (self.__class__, inner.__class__), {}
        )

    def __getattribute__(self, k):
        if k.startswith("__") or k in object.__getattribute__(self, "__orig_attrs"):
            return object.__getattribute__(self, k)
        return getattr(self.inner, k)

    def __str__(self) -> str:
        if isinstance(self.inner, FunctionType):
            return f"({self.inner})?"
        return f"{self.inner}?"

    def __repr__(self) -> str:
        return "Optional" + repr(self.inner)

    @property
    def is_optional(self) -> bool:
        return True

    def substitute_typevars(self, typevars) -> Self:
        inner = self.inner.substitute_typevars(typevars)
        return OptionalType(inner)


class ArrayType[T: ResolvedType](ResolvedType):
    kind: TypeKind = field(init=False, repr=False, default=TypeKind.ARRAY)
    element_type: T

    def __init__(self, element_type: T, **_):
        """
        Dynamically subclass ``element_type``. For a weak justification
        of this worrying pattern, see ``OptionalType``.
        """
        object.__setattr__(self, "element_type", element_type)
        object.__setattr__(
            self, "__orig_attrs", tuple(x for x in dir(self) if not x.startswith("__"))
        )
        if isinstance(element_type, ArrayType):
            # Avoid MRO resolution issues
            inherit = (element_type.__class__,)
        else:
            inherit = (self.__class__, element_type.__class__)

        self.__class__ = type(
            element_type.__class__.__name__ + "List",
            inherit,
            {},
        )
        # Don't set self.__dict__ = element_type.__dict__,
        # it introduces cycles and sharing the __dict__ means
        # we cannot wrap ourselves (integer[][]) because
        # the new class would access the same fields.
        # Using getattr works just as well.
        # Still not sure if this is necessary in general,
        # at least for ArrayType. For OptionalType, it makes more sense.

    def __getattribute__(self, k):
        if k.startswith("__") or k in object.__getattribute__(self, "__orig_attrs"):
            return object.__getattribute__(self, k)
        return getattr(self.element_type, k)

    def substitute_typevars(self, typevars) -> Self:
        element_type = self.element_type.substitute_typevars(typevars)
        return ArrayType(element_type)

    def __str__(self) -> str:
        if (
            isinstance(self.element_type, FunctionType)
            and self.element_type.rets is not None
        ):
            return f"({self.element_type})[]"
        return f"{self.element_type}[]"

    def __repr__(self):
        return wrapped_repr(self.element_type, name_suffix="List")


class VariadicType[T](ResolvedType):
    """
    Simple variadic type, e.g.: `string ...`
    """

    kind: TypeKind = field(init=False, repr=False, default=TypeKind.VARIADIC)
    element_type: ResolvedType

    def __init__(self, element_type: T, **_):
        """
        Dynamically subclass ``element_type``. For a weak justification
        of this worrying pattern, see ``OptionalType``.
        """
        object.__setattr__(self, "element_type", element_type)
        object.__setattr__(
            self, "__orig_attrs", tuple(x for x in dir(self) if not x.startswith("__"))
        )
        self.__class__ = type(
            "Variadic" + element_type.__class__.__name__,
            (self.__class__, element_type.__class__),
            {},
        )

    def __getattribute__(self, k):
        if k.startswith("__") or k in object.__getattribute__(self, "__orig_attrs"):
            return object.__getattribute__(self, k)
        return getattr(self.element_type, k)

    def substitute_typevars(self, typevars) -> Self:
        # NOTE: Unsure whether it should replace itself with the element
        # in case it got replaced (at least if it was a StructType) or not.
        element_type = self.element_type.substitute_typevars(typevars)
        # if id(element_type) != id(self.element_type) and self.element_type.__class__ is StructType:
        #     return element_type
        return VariadicType(element_type)

    def __str__(self) -> str:
        if isinstance(self.element_type, FunctionType):
            return f"({self.element_type}) ..."
        return f"{self.element_type} ..."

    def __repr__(self) -> str:
        return wrapped_repr(self.element_type, name_prefix="Variadic")


class ArrayOmissionMarker:
    pass


class TreeHydrator(Transformer):
    """Transform Lark parse tree into ResolvedType objects."""

    # Ugly hack, pls refactor
    parser: Lark

    def __init__(self, index):
        self.classes: dict[str, Class] = index.classes
        self.aliases: dict[str, Alias] = index.aliases
        self.enums: dict[str, LuaEnum] = index.enums
        self.index: dict[str, LuaType] = index.types

    def union_type(
        self, items: list[ResolvedType], *, omitted: bool = False
    ) -> UnionType | OptionalType:
        if len(items) == 1:
            return items[0]
        # Flatten unions of unions. Emmylua does that automatically though.
        all_members = []
        optional = False
        for sub in items:
            if isinstance(sub, UnionType):
                all_members.extend(sub.elements)
                omitted = omitted or sub.omitted
            elif isinstance(sub, OptionalType):
                optional = True
                all_members.append(sub.inner)
            else:
                all_members.append(sub)
        union = UnionType(tuple(all_members), omitted=omitted, parser=self.parser)
        if optional:
            return OptionalType(union, parser=self.parser)
        return union

    def union_type_omitted(self, items: list[ResolvedType]) -> UnionType | OptionalType:
        return self.union_type(items, omitted=True)

    def intersection_type(
        self, items: list[ResolvedType], *, omitted: bool = False
    ) -> IntersectionType:
        if len(items) == 1:
            return items[0]
        # Flatten intersections of intersections. Emmylua does that automatically though.
        all_members = []
        for sub in items:
            if isinstance(sub, IntersectionType):
                all_members.extend(sub.elements)
                omitted = omitted or sub.omitted
            else:
                all_members.append(sub)
        return IntersectionType(tuple(all_members), omitted=omitted, parser=self.parser)

    def intersection_type_omitted(self, items: list[ResolvedType]) -> IntersectionType:
        return self.intersection_type(items, omitted=True)

    @v_args(inline=True)
    def optional_type(self, inner: ResolvedType) -> OptionalType:
        if isinstance(inner, OptionalType):
            return inner
        return OptionalType(inner, parser=self.parser)

    @v_args(inline=True)
    def array_type(self, element: ResolvedType) -> ArrayType:
        return ArrayType(element, parser=self.parser)

    def type_list(self, items: list[ResolvedType]) -> list[ResolvedType]:
        return list(items)

    def table_type(
        self,
        items: list[
            tuple[str | ResolvedType | None, ResolvedType | ArrayOmissionMarker]
        ],
    ) -> TableType:
        if any(isinstance(field[1], ArrayOmissionMarker) for field in items):
            return TableType(
                tuple(
                    field
                    for field in items
                    if not isinstance(field[1], ArrayOmissionMarker)
                ),
                parser=self.parser,
                omitted=True,
            )
        return TableType(tuple(items), parser=self.parser)

    @v_args(inline=True)
    def array_named_field(
        self, name_token: Token, field_type: ResolvedType
    ) -> tuple[str, ResolvedType]:
        return (name_token.value, field_type)

    @v_args(inline=True)
    def array_typed_field(
        self, key_type: ResolvedType, value_type: ResolvedType
    ) -> tuple[ResolvedType, ResolvedType]:
        return (key_type, value_type)

    def array_omission(self, _) -> tuple[None, ArrayOmissionMarker]:
        return (None, ArrayOmissionMarker())

    @v_args(inline=True)
    def function_void_type(
        self, params: list[tuple[str | None, ResolvedType]]
    ) -> FunctionType:
        return FunctionType(tuple(params or []), None, parser=self.parser)

    @v_args(inline=True)
    def function_ret_type(
        self, function_void: FunctionType, returns: ResolvedType
    ) -> FunctionType:
        return FunctionType(function_void.params, returns, parser=self.parser)

    def param_list(
        self, params: list[tuple[str | None, ResolvedType]]
    ) -> list[tuple[str | None, ResolvedType]]:
        return list(params)

    @v_args(inline=True)
    def named_param(
        self, name_token: Token, param_type: ResolvedType | Token
    ) -> tuple[str, ResolvedType]:
        if isinstance(param_type, Token):
            assert param_type.value == "..."
            return (
                name_token.value,
                VariadicType(AnyType(), parser=self.parser),
            )
        return (name_token.value, param_type)

    @v_args(inline=True)
    def unnamed_param(
        self, param_type: ResolvedType | Token
    ) -> tuple[None, ResolvedType]:
        if isinstance(param_type, Token):
            assert param_type.value == "..."
            return (None, VariadicType(AnyType(), parser=self.parser))
        return (None, param_type)

    @v_args(inline=True)
    def tuple_type(self, items: list[ResolvedType]) -> TupleType:
        return TupleType(tuple(items), parser=self.parser)

    @v_args(inline=True)
    def string_literal(self, token: Token) -> LiteralType:
        value = token.value[1:-1]
        return LiteralStr(value)

    @v_args(inline=True)
    def integer_literal(self, token: Token) -> LiteralType:
        value = int(token.value)
        return LiteralInt(value)

    @v_args(inline=True)
    def literal_true(self) -> LiteralType:
        return LiteralBool(True)

    @v_args(inline=True)
    def literal_false(self) -> LiteralType:
        return LiteralBool(False)

    @v_args(inline=True)
    def variadic_type(self, element: ResolvedType) -> VariadicType:
        return VariadicType(element, parser=self.parser)

    @v_args(inline=True)
    def complex_variadic_type(self) -> VariadicType:
        return VariadicType(UnknownType(), parser=self.parser)

    def struct_type(
        self, namespace_parts: list[Token]
    ) -> ClassType | AliasType | EnumType | StructType:
        full_name = ".".join(p.value for p in namespace_parts)
        if full_name in self.classes:
            return ClassType(
                full_name, typedef=self.classes[full_name], parser=self.parser
            )
        if full_name in self.aliases:
            return AliasType(
                full_name, typedef=self.aliases[full_name], parser=self.parser
            )
        if full_name in self.enums:
            return EnumType(
                full_name, typedef=self.enums[full_name], parser=self.parser
            )
        # Unknown class
        return StructType(full_name, parser=self.parser)

    @v_args(inline=True)
    def generic_struct_type(
        self, base: StructType, type_args: list[ResolvedType]
    ) -> (
        GenericClassInstanceType
        | GenericAliasInstanceType
        | GenericEnumInstanceType
        | GenericStructInstanceType
        | ClassType
        | AliasType
        | EnumType
        | StructType
    ):
        # Since we're just parsing strings here, we need to investigate a bit
        # if we can decide whether we got a Container<string,boolean>,
        # Container<string, T> or Container<T, K>. For the latter,
        # just return the base since we're not adding any information.
        if base.__class__ is StructType:
            # Can't decide, we don't have a class definition
            return GenericStructInstanceType(
                base.name, tuple(type_args), typedef=base.typedef, parser=self.parser
            )

        base_generics = base.generics

        for i, arg in enumerate(type_args):
            if arg.__class__ != StructType:
                # Typevars are almost always rendered as unknown classes.
                break
            if arg.name != base_generics[i][0]:
                break
        else:
            # base is Container<K, T>, we rendered Container<K, T>
            return base

        # We got at least one typevar
        if isinstance(base, ClassType):
            return GenericClassInstanceType(
                base.name, tuple(type_args), typedef=base.typedef, parser=self.parser
            )
        if isinstance(base, AliasType):
            return GenericAliasInstanceType(
                base.name, tuple(type_args), typedef=base.typedef, parser=self.parser
            )
        if isinstance(base, EnumType):
            return GenericEnumInstanceType(
                base.name, tuple(type_args), typedef=base.typedef, parser=self.parser
            )
        # fallback, shouldn't happen
        return GenericStructInstanceType(
            base.name, tuple(type_args), typedef=base.typedef, parser=self.parser
        )

    @v_args(inline=True)
    def primitive_nil(self) -> PrimitiveType:
        return NilType()

    @v_args(inline=True)
    def primitive_any(self) -> PrimitiveType:
        return AnyType()

    @v_args(inline=True)
    def primitive_unknown(self) -> PrimitiveType:
        return UnknownType()

    @v_args(inline=True)
    def primitive_self(self) -> PrimitiveType:
        return PrimitiveType("self")

    @v_args(inline=True)
    def primitive_boolean(self) -> PrimitiveType:
        return BooleanType()

    @v_args(inline=True)
    def primitive_string(self) -> PrimitiveType:
        return StringType()

    @v_args(inline=True)
    def primitive_number(self) -> PrimitiveType:
        return NumberType()

    @v_args(inline=True)
    def primitive_integer(self) -> PrimitiveType:
        return IntegerType()

    @v_args(inline=True)
    def primitive_function(self) -> PrimitiveType:
        return PrimitiveType("function")

    @v_args(inline=True)
    def primitive_thread(self) -> PrimitiveType:
        return PrimitiveType("thread")

    @v_args(inline=True)
    def primitive_userdata(self) -> PrimitiveType:
        return PrimitiveType("userdata")

    @v_args(inline=True)
    def primitive_lightuserdata(self) -> PrimitiveType:
        return PrimitiveType("lightuserdata")

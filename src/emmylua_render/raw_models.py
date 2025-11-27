"""
Pydantic models for emmylua_doc_cli JSON output.
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagNameContent(BaseModel):
    """Tag name and content pair."""

    tag_name: str
    content: str


class Loc(BaseModel):
    """Location in a file."""

    file: Path
    line: int


class LuaTypeVar(BaseModel):
    """Generic type variable."""

    name: str
    base: str | None = None


class FnParam(BaseModel):
    """Function parameter."""

    name: str | None = None
    typ: str | None = None
    desc: str | None = None


class Property(BaseModel):
    """Base class for most constructs that can be annotated with a description (not function params)."""

    description: str | None = None
    visibility: str | None = None
    deprecated: bool = False
    deprecation_reason: str | None = None
    tag_content: list[TagNameContent] | None = None


class FieldMember(Property):
    """Field member with discriminator."""

    type: Literal["field"]
    name: str
    loc: Loc | None = None
    typ: str
    literal: str | None = None


class FnMember(Property):
    """Function member with discriminator."""

    type: Literal["fn"]
    name: str
    loc: Loc | None = None
    generics: list[LuaTypeVar] = Field(default_factory=list)
    params: list[FnParam] = Field(default_factory=list)
    returns: list[FnParam] = Field(default_factory=list)
    overloads: list[str] = Field(default_factory=list)
    is_async: bool = False
    is_meth: bool = False
    is_nodiscard: bool = False
    nodiscard_message: str | None = None


# Discriminated union for Member (table entries)
Member = FnMember | FieldMember


class GlobalTable(Property):
    """Global table with discriminator."""

    type: Literal["table"]
    name: str
    loc: Loc | None = None
    members: list[Member] = Field(default_factory=list)


class GlobalField(Property):
    """Global field with discriminator."""

    type: Literal["field"]
    name: str
    loc: Loc | None = None
    typ: str
    literal: str | None = None


# Discriminated union for LuaGlobal
LuaGlobal = GlobalTable | GlobalField


class LuaModule(Property):
    """Module definition."""

    name: str
    file: Path | None = None
    typ: str | None = None
    members: list[Member] = Field(default_factory=list)
    namespace: str | None = None
    using: list[str] = Field(default_factory=list)


class Class(Property):
    """Class definition with discriminator."""

    type: Literal["class"]
    name: str
    loc: list[Loc] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)
    generics: list[LuaTypeVar] = Field(default_factory=list)
    members: dict[str, Member] = Field(default_factory=list)

    @field_validator("members", mode="before")
    @classmethod
    def _to_dict[T](cls, raw: list[T]) -> dict[str, T]:
        """
        emmylua_doc_cli returns a list of modules/types/globals. Transform it into a dict
        to allow named indexing.
        """
        return {it["name"]: it for it in raw}


class LuaEnum(Property):
    """Enum definition with discriminator."""

    type: Literal["enum"]
    name: str
    loc: list[Loc] = Field(default_factory=list)
    typ: str | None = None
    generics: list[LuaTypeVar] = Field(default_factory=list)
    members: list[Member] = Field(default_factory=list)


class Alias(Property):
    """Type alias with discriminator."""

    type: Literal["alias"]
    name: str
    loc: list[Loc] = Field(default_factory=list)
    typ: str | None = None
    generics: list[LuaTypeVar] = Field(default_factory=list)
    members: list[Member] = Field(default_factory=list)


# Discriminated union for LuaType
LuaType = Class | LuaEnum | Alias


class Index(BaseModel):
    """Root index structure."""

    modules: dict[str, LuaModule] = Field(default_factory=list)
    types: dict[str, LuaType] = Field(default_factory=list)
    globals: dict[str, LuaGlobal] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)

    # Calculated properties. Cached for efficiency.
    _classes: dict[str, Class] = None
    _aliases: dict[str, Alias] = None
    _enums: dict[str, LuaEnum] = None

    model_config = ConfigDict(
        # Use discriminator for automatic union parsing
        discriminator="type"
    )

    @field_validator("modules", "types", "globals", mode="before")
    @classmethod
    def _to_dict[T](cls, raw: list[T]) -> dict[str, T]:
        """
        emmylua_doc_cli returns a list of modules/types/globals. Transform it into a dict
        to allow named indexing.
        """
        return {it["name"]: it for it in raw}

    @property
    def classes(self):
        if not self._classes:
            self._classes = {
                name: cls for name, cls in self.types.items() if cls.type == "class"
            }
        return self._classes

    @property
    def aliases(self):
        if not self._aliases:
            self._aliases = {
                name: cls for name, cls in self.types.items() if cls.type == "alias"
            }
        return self._aliases

    @property
    def enums(self):
        if not self._enums:
            self._enums = {
                name: cls for name, cls in self.types.items() if cls.type == "enum"
            }
        return self._enums

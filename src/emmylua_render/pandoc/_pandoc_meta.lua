--- Pandoc Lua type definitions for EmmyLuaLS.
--- Scaffold produced by an LLM, improved manually.
--- There's also a `pandoc.zip` module that I neglected to document.
--- Don't trust these defs if something seems off, look at the official docs here:
--- https://pandoc.org/lua-filters.html#lua-type-reference
--- Often, Pandoc autocasts the values as it needs.
---
--- After writing this, I found annotations for LuaLS here:
--- * https://github.com/rnwst/pandoc-lua-types
--- * https://github.com/massifrg/pandoc-luals-annotations
---
--- The ones in here are specific to EmmyLuaLS (emmylua-analyzer-rust)
--- and are mostly intended for custom writers.
---@meta

--- A pandoc log message. Has no fields, but tostring() works.
---@class pandoc.LogMessage

--- State used by pandoc to collect information and make it available to readers and writers.
--- Read-only.
---@class pandoc.CommonState
---@field input_files string[] List of input files from command line
---@field output_file string? Output file from command line
---@field log pandoc.LogMessage[] List of log messages
---@field request_headers table<string, string> Headers to add for HTTP requests.
---@field resource_path string[] Path to search for resources like included images
---@field source_url string? Absolute URL or directory of first source file
---@field user_data_dir string? Directory to search for data files
---@field trace boolean Whether tracing messages are issued
---@field verbosity "INFO"|"WARNING"|"ERROR" Verbosity level

--- Globals set by pandoc
FORMAT = _G.FORMAT ---@type string
PANDOC_READER_OPTIONS = _G.PANDOC_READER_OPTIONS ---@type pandoc.ReaderOptions
PANDOC_VERSION = _G.PANDOC_VERSION ---@type pandoc.types.Version
PANDOC_API_VERSION = _G.PANDOC_API_VERSION ---@type pandoc.types.Version
PANDOC_SCRIPT_FILE = _G.PANDOC_SCRIPT_FILE ---@type string
PANDOC_STATE = _G.PANDOC_STATE ---@type pandoc.CommonState
pandoc = _G.pandoc ---@type pandoc
lpeg = _G.lpeg ---@type lpeg
re = _G.re ---@type lpeg.re

--- LPeg is a pattern-matching library for Lua, based on Parsing Expression Grammars (PEGs).
--- It's inbuilt by Pandoc.
--- See: https://www.inf.puc-rio.br/~roberto/lpeg/
--- Better annotations: https://github.com/LuaCATS/lpeg
---@class lpeg
---@field version string
local lpeg = {}

function lpeg.match(pattern) end
function lpeg.type(value) end
function lpeg.setmaxstack(max) end
function lpeg.P(value) end
function lpeg.B(patt) end
function lpeg.R(range) end
function lpeg.S(string) end
function lpeg.utfR(cp1, cp2) end
function lpeg.V(v) end
function lpeg.locale(table) end
function lpeg.C(patt) end
function lpeg.Carg(n) end
function lpeg.Cb(key) end
function lpeg.Cc(values) end
function lpeg.Cf(patt, func) end
function lpeg.Cg(patt, key) end
function lpeg.Cp() end
function lpeg.Cs(patt) end
function lpeg.Ct(patt) end
function lpeg.Cmt(patt, func) end

---@class lpeg.re
local re = {}

--- Compiles the given string and returns an equivalent LPeg pattern.
---@param string string RegEx pattern to compile. May define either an expression or a grammar.
---@param defs table? Provides extra Lua values to be used by the pattern
---@return table lpeg_pattern
function re.compile(string, defs) end

--- Searches the given pattern in the given subject.
---@param subject string Text to search (haystack)
---@param pattern string RegEx pattern to look for (needle)
---@param init integer? Start search at this position in `subject`
---@return integer? start_index
---@return integer? end_index
function re.find(subject, pattern, init) end

--- Does a global substitution, replacing all occurrences of `pattern` in the given `subject` by `replacement`.
---@param subject string Text to replace in
---@param pattern string Pattern to replace
---@param replacement string Text to replace matches with
---@return string replaced
function re.gsub(subject, pattern, replacement) end

--- Matches the given pattern against the given subject, returning all captures.
---@param subject string Text to search (haystack)
---@param pattern string RegEx pattern to look for (needle)
---@return [integer, integer][]? all_matches
function re.match(subject, pattern) end

--- Updates the pre-defined character classes to the current locale.
function re.updatelocale() end

--- Base class for all (most) pandoc types. Provides clone functionality (not: read-only types).
---@class pandoc._base
local base = {}

--- Clone this instance.
---@return self
function base:clone() end

---@class pandoc.Walkable
local Walkable = {}

--- Applies Lua filters to the element(s).
--- Just as for full-document filters, the order in which elements are traversed
--- can be controlled by setting the `traverse` field of the filter.
--- Returns a (deep) copy on which the filter has been applied: the original element is left untouched.
--- Note that the filter is applied to the subtree, but not to the `self` element.
---@param lua_filters pandoc.LuaFilters #
---    Mapping of pandoc type name to transformer function. The function receives the element
---    and should return the same element type, nil or a list of the same metatype (Block/Inner),
---    which replaces the element.
---    The special members `Blocks` and `Inlines` are called on all lists of the respective type.
---    The special members `Block` and `Inline` serve as fallbacks in case a specific type has no
---    corresponding member.
---@return self filtered
function Walkable:walk(lua_filters) end

---@class pandoc.Element: pandoc._base, pandoc.Walkable
---@field t string
---@field tag string
local Element = {}

--- Return a textual representation of the element.
---@return string
function Element:show() end

---@class pandoc
---@field cli pandoc.cli Command line options and argument parsing
---@field image pandoc.image Basic image querying functions
---@field json pandoc.json JSON module to work with JSON
---@field layout pandoc.layout Plain-text document layouting
---@field log pandoc.log Access to pandoc’s logging system
---@field mediabag pandoc.mediabag The pandoc.mediabag module allows accessing pandoc’s media storage
---@field path pandoc.path Module for file path manipulations
---@field scaffolding pandoc.scaffolding Scaffolding for custom writers
---@field structure pandoc.structure Access to the higher-level document structure, including hierarchical sections and the table of contents
---@field system pandoc.system Access to the system’s information and file functionality
---@field template pandoc.template Handle pandoc templates
---@field text pandoc.text UTF-8 aware text manipulation functions, implemented in Haskell
---@field types pandoc.types Constructors for types that are not part of the pandoc AST
---@field utils pandoc.utils Internal pandoc and utility functions
---@field zip table Functions to create, modify, and extract files from zip archives. Undocumented here, see official docs.
---@field readers table<string, true> Set of formats that pandoc can parse. All keys in this table can be used as the `format` value in `pandoc.read`.
---@field writers table<string, true> Set of formats that pandoc can generate. All keys in this table can be used as the `format` value in `pandoc.write`.
---@field AuthorInText "AuthorInText" Citation mode: Author name is mentioned in the text.
---@field SuppressAuthor "SuppressAuthor" Citation mode: Author name is suppressed
---@field NormalCitation "NormalCitation" Citation mode: Default citation style is used
---@field DisplayMath "DisplayMath" Math style: Formula should be shown in "display" style, i.e., on a separate line
---@field InlineMath "InlineMath" Math style: Formula should be shown inline
---@field SingleQuote "SingleQuote" Quote type: Single-quoted strings
---@field DoubleQuote "DoubleQuote" Quote type: Double-quoted strings
---@field AlignLeft "AlignLeft" Table alignment: Align cells left
---@field AlignRight "AlignRight" Table alignment: Align cells right
---@field AlignCenter "AlignCenter" Table alignment: Center cell content
---@field AlignDefault "AlignDefault" Table alignment: Unaltered
---@field DefaultDelim "DefaultDelim" List number delimiter: Default is used
---@field Period "Period" List number delimiter: Period
---@field OneParen "OneParen" List number delimiter: Single parenthesis
---@field TwoParens "TwoParens" List number delimiter: Double parentheses
---@field DefaultStyle "DefaultStyle" List number style: Default is used
---@field Example "Example" List number style: Examples
---@field Decimal "Decimal" List number style: Decimal integers
---@field LowerRoman "LowerRoman" List number style: Lower-case roman numerals
---@field UpperRoman "UpperRoman" List number style: Upper-case roman numerals
---@field LowerAlpha "LowerAlpha" List number style: Lower-case alphanumeric characters
---@field UpperAlpha "UpperAlpha" List number style: Upper-case alphanumeric characters
local pandoc = {}

--- Create a Pandoc document.
---@param blocks pandoc.Block[] Document content
---@param meta? pandoc.Meta Document meta information
---@return pandoc.Pandoc
function pandoc.Pandoc(blocks, meta) end

--- Create a Meta object.
---@param meta table Table containing meta information
---@return pandoc.Meta
function pandoc.Meta(meta) end

--- Create a MetaBlocks value for use in metadata.
---@param blocks pandoc.Block[] Block content
---@return pandoc.MetaBlocks
function pandoc.MetaBlocks(blocks) end

--- Create a MetaBool value for use in metadata.
---@param bool boolean Boolean value
---@return pandoc.MetaBool
function pandoc.MetaBool(bool) end

--- Create a MetaInlines value for use in metadata.
---@param inlines pandoc.Inline[] Inline elements
---@return pandoc.MetaInlines
function pandoc.MetaInlines(inlines) end

--- Create a MetaList value for use in metadata.
---@param list pandoc.MetaValue|pandoc.MetaValue[] Value or list of meta values
---@return pandoc.MetaList
function pandoc.MetaList(list) end

--- Create a MetaMap value for use in metadata.
---@param map table<string, pandoc.MetaValue> String-indexed map of meta values
---@return table<string, pandoc.MetaValue> meta_map Copy of `map` suitable for usage as `MetaMap`
function pandoc.MetaMap(map) end

--- Create a MetaString value for use in metadata.
---@param str string String value
---@return pandoc.MetaString
function pandoc.MetaString(str) end

--- Create a block quote element.
---@param content pandoc.Block[] Block content
---@return pandoc.BlockQuote
function pandoc.BlockQuote(content) end

--- Create a bullet list.
---@param items pandoc.Block[][] List items
---@return pandoc.BulletList
function pandoc.BulletList(items) end

--- Create a code block element.
---@param text string Code string
---@param attr? pandoc.AttrParam Element attributes
---@return pandoc.CodeBlock
function pandoc.CodeBlock(text, attr) end

--- Create a definition list.
---@param items ([pandoc.Inlines, pandoc.Block[][]])[] Definition list items (list of term-definition pairs)
---@return pandoc.DefinitionList
function pandoc.DefinitionList(items) end

--- Create a div element.
---@param content pandoc.Block[] Block content
---@param attr? pandoc.AttrParam Element attributes
---@return pandoc.Div
function pandoc.Div(content, attr) end

--- Create a figure element.
---@param content pandoc.Block[] Figure block content
---@param caption? pandoc.Caption Figure caption
---@param attr? pandoc.AttrParam Element attributes
---@return pandoc.Figure
function pandoc.Figure(content, caption, attr) end

--- Create a header element.
---@param level integer Heading level
---@param content pandoc.Inline[] Inline content
---@param attr? pandoc.AttrParam Element attributes
---@return pandoc.Header
function pandoc.Header(level, content, attr) end

--- Create a horizontal rule.
---@return pandoc.HorizontalRule
function pandoc.HorizontalRule() end

--- Create a line block element.
---@param lines pandoc.Inline[][] Lines of inline content
---@return pandoc.LineBlock
function pandoc.LineBlock(lines) end

--- Create an ordered list.
---@param items pandoc.Block[][] List items
---@param listAttributes? pandoc.ListAttributes List parameters
---@return pandoc.OrderedList
function pandoc.OrderedList(items, listAttributes) end

--- Create a paragraph element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Para
function pandoc.Para(content) end

--- Create a plain text element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Plain
function pandoc.Plain(content) end

--- Create a raw block of the specified format.
---@param format string Format of content
---@param text string Raw content
---@return pandoc.RawBlock
function pandoc.RawBlock(format, text) end

--- Create a table element.
---@param caption pandoc.Caption Table caption
---@param colspecs pandoc.ColSpec[] Column alignments and widths
---@param head pandoc.TableHead Table head
---@param bodies pandoc.TableBody[] Table bodies
---@param foot pandoc.TableFoot Table foot
---@param attr? pandoc.AttrParam Element attributes
---@return pandoc.Table
function pandoc.Table(caption, colspecs, head, bodies, foot, attr) end

--- Creates a `pandoc.Blocks` list.
---@param block_like_elements pandoc.Block|pandoc.Block[]
---@return pandoc.Blocks blocks
function pandoc.Blocks(block_like_elements) end

--- Create a Cite inline element.
---@param content pandoc.Inline[] Placeholder content
---@param citations pandoc.Citation[] List of citations
---@return pandoc.Cite
function pandoc.Cite(content, citations) end

--- Create a Code inline element.
---@param text string Code string
---@param attr? pandoc.Attr Additional attributes
---@return pandoc.Code
function pandoc.Code(text, attr) end

--- Creates an inline element representing emphasized text.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Emph
function pandoc.Emph(content) end

--- Create an Image element.
---@param caption pandoc.Inline[] Image caption
---@param src string Path to the image file
---@param title? string Brief image description
---@param attr? pandoc.Attr Image attributes
---@return pandoc.Image
function pandoc.Image(caption, src, title, attr) end

--- Create a LineBreak inline element.
---@return pandoc.LineBreak
function pandoc.LineBreak() end

--- Create a Link inline element.
---@param content pandoc.Inline[] Link text
---@param target string Link target URL
---@param title? string Brief link description
---@param attr? pandoc.Attr Link attributes
---@return pandoc.Link
function pandoc.Link(content, target, title, attr) end

--- Create a Math element.
---@param mathtype pandoc.MathType Rendering specifier
---@param text string Math content
---@return pandoc.Math
function pandoc.Math(mathtype, text) end

--- Create a Note inline element.
---@param content pandoc.Block[] Footnote content
---@return pandoc.Note
function pandoc.Note(content) end

--- Create a Quoted inline element.
---@param quotetype pandoc.QuoteType Type of quotes
---@param content pandoc.Inline[] Quoted content
---@return pandoc.Quoted
function pandoc.Quoted(quotetype, content) end

--- Create a RawInline element.
---@param format string Format of content
---@param text string Raw content string
---@return pandoc.RawInline
function pandoc.RawInline(format, text) end

--- Create a SmallCaps element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.SmallCaps
function pandoc.SmallCaps(content) end

--- Create a SoftBreak inline element.
---@return pandoc.SoftBreak
function pandoc.SoftBreak() end

--- Create a Space inline element.
---@return pandoc.Space
function pandoc.Space() end

--- Create a Span inline element.
---@param content pandoc.Inline[] Inline content
---@param attr? pandoc.Attr Additional attributes
---@return pandoc.Span
function pandoc.Span(content, attr) end

--- Create a Str inline element.
---@param text string Text content
---@return pandoc.Str
function pandoc.Str(text) end

--- Create a Strikeout element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Strikeout
function pandoc.Strikeout(content) end

--- Create a Strong element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Strong
function pandoc.Strong(content) end

--- Create a Subscript inline element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Subscript
function pandoc.Subscript(content) end

--- Create a Superscript inline element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Superscript
function pandoc.Superscript(content) end

--- Create an Underline inline element.
---@param content pandoc.Inline[] Inline content
---@return pandoc.Underline
function pandoc.Underline(content) end

--- Converts its argument into an `Inlines` list:
---   * copies a list of Inline elements into a fresh list; any string s within the list is treated as pandoc.Str(s);
---   * turns a single Inline into a singleton list;
---   * splits a string into Str-wrapped words, treating interword spaces as Spaces or SoftBreaks.
---@param inline_like_elements pandoc.Inline[]|pandoc.Inline|string
---@return pandoc.Inlines
function pandoc.Inlines(inline_like_elements) end

--- Create a set of attributes.
---@param identifier? string|table|pandoc.Attr Element identifier
---@param classes? string[] Element classes
---@param attributes? table<string, string>|pandoc.AttributeList Key-value pairs
---@return pandoc.Attr
function pandoc.Attr(identifier, classes, attributes) end

--- Create an AttributeList.
---@param attributes table<string, string> Attribute pairs
---@return pandoc.AttributeList
function pandoc.AttributeList(attributes) end

--- Create a caption.
---@param long? pandoc.Block[] Full caption
---@param short? pandoc.Inline[] Short caption
---@return pandoc.Caption
function pandoc.Caption(long, short) end

--- Create a table cell.
---@param content pandoc.Block[] Cell contents
---@param align? pandoc.Alignment Text alignment
---@param rowspan? integer Number of rows spanned
---@param colspan? integer Number of columns spanned
---@param attr? pandoc.AttrParam Cell attributes
---@return pandoc.Cell
function pandoc.Cell(content, align, rowspan, colspan, attr) end

--- Create a single citation.
---@param id string Citation identifier (e.g., BibTeX key)
---@param mode pandoc.CitationMode Citation rendering mode
---@param prefix? pandoc.Inline[] Citation prefix
---@param suffix? pandoc.Inline[] Citation suffix
---@param note_num? integer Note number
---@param hash? integer Hash value
---@return pandoc.Citation
function pandoc.Citation(id, mode, prefix, suffix, note_num, hash) end

--- Create a column specification.
---@param align? pandoc.Alignment Cell alignment
---@param width? number Column width as fraction of page width
---@return pandoc.ColSpec
function pandoc.ColSpec(align, width) end

--- Create list attributes.
---@param start? integer Number of first list item
---@param style? pandoc.ListNumberStyle Style for list numbering
---@param delimiter? pandoc.ListNumberDelim Delimiter of list numbers
---@return pandoc.ListAttributes
function pandoc.ListAttributes(start, style, delimiter) end

--- Create a table row.
---@param cells pandoc.Cell[] List of table cells
---@param attr? pandoc.Attr Row attributes
---@return pandoc.Row
function pandoc.Row(cells, attr) end

--NOTE: Yes, there is no pandoc.TableBody constructor.

--- Create a table foot.
---@param rows? pandoc.Row[] Footer rows
---@param attr? pandoc.Attr Attributes
---@return pandoc.TableFoot
function pandoc.TableFoot(rows, attr) end

--- Create a table head.
---@param rows? pandoc.Row[] Header rows
---@param attr? pandoc.Attr Attributes
---@return pandoc.TableHead
function pandoc.TableHead(rows, attr) end

--- Create a simple table.
---@param caption pandoc.Inline[] Table caption
---@param aligns pandoc.Alignment[] Column alignments
---@param widths number[] Relative column widths
---@param headers pandoc.Block[][] Table header row
---@param rows pandoc.Block[][][] Table rows
---@return pandoc.SimpleTable
function pandoc.SimpleTable(caption, aligns, widths, headers, rows) end

--- Creates a new ReaderOptions value.
---@param opts pandoc.ReaderOptions|table #
---    Either a table with a subset of the properties of a ReaderOptions object,
---    or another ReaderOptions object.
---    Uses the defaults specified in the manual for all properties that are not explicitly specified.
---    Throws an error if a table contains properties which are not present in a ReaderOptions object.
---@return pandoc.ReaderOptions
function pandoc.ReaderOptions(opts) end

--- Creates a new WriterOptions value.
---@param opts pandoc.WriterOptions|table #
---    Either a table with a subset of the properties of a WriterOptions object,
---    or another WriterOptions object.
---    Uses the defaults specified in the manual for all properties that are not explicitly specified.
---    Throws an error if a table contains properties which are not present in a WriterOptions object.
---@return pandoc.WriterOptions
function pandoc.WriterOptions(opts) end

--- Create a generic List.
---@generic T
---@param items? T[] List items
---@return pandoc.List<T>
function pandoc.List(items) end

--- Parse text into a Pandoc document.
---@param markup string The markup to parse
---@param format? string Format specification (defaults to "markdown")
---@param reader_options? pandoc.ReaderOptions|table Reader options
---@return pandoc.Pandoc
function pandoc.read(markup, format, reader_options) end

--- Convert a document to a target format.
---@param doc pandoc.Pandoc Document to convert
---@param format string Target format
---@param writer_options? pandoc.WriterOptions|table Writer options
---@return string
function pandoc.write(doc, format, writer_options) end

--- Apply a filter to a block element.
---@param element pandoc.Block Block element
---@param filter table Filter functions
---@return pandoc.Block
function pandoc.walk_block(element, filter) end

--- Apply a filter to an inline element.
---@param element pandoc.Inline Inline element
---@param filter table Filter functions
---@return pandoc.Inline
function pandoc.walk_inline(element, filter) end

--- Run a command with arguments and input.
---@param command string Program to run
---@param args string[] List of arguments
---@param input string Input data via stdin
---@return string output Output from stdout
function pandoc.pipe(command, args, input) end

--- Table that can be passed to `walk` methods.
---@class pandoc.LuaFilters
---@field BlockQuote? fun(el: pandoc.BlockQuote): (pandoc.BlockQuote|pandoc.Block|pandoc.Block[])?
---@field BulletList? fun(el: pandoc.BulletList): (pandoc.BulletList|pandoc.Block|pandoc.Block[])?
---@field CodeBlock? fun(el: pandoc.CodeBlock): (pandoc.CodeBlock|pandoc.Block|pandoc.Block[])?
---@field DefinitionList? fun(el: pandoc.DefinitionList): (pandoc.DefinitionList|pandoc.Block|pandoc.Block[])?
---@field Div? fun(el: pandoc.Div): (pandoc.Div|pandoc.Block|pandoc.Block[])?
---@field Figure? fun(el: pandoc.Figure): (pandoc.Figure|pandoc.Block|pandoc.Block[])?
---@field Header? fun(el: pandoc.Header): (pandoc.Header|pandoc.Block|pandoc.Block[])?
---@field HorizontalRule? fun(el: pandoc.HorizontalRule): (pandoc.HorizontalRule|pandoc.Block|pandoc.Block[])?
---@field LineBlock? fun(el: pandoc.LineBlock): (pandoc.LineBlock|pandoc.Block|pandoc.Block[])?
---@field OrderedList? fun(el: pandoc.OrderedList): (pandoc.OrderedList|pandoc.Block|pandoc.Block[])?
---@field Para? fun(el: pandoc.Para): (pandoc.Para|pandoc.Block|pandoc.Block[])?
---@field Plain? fun(el: pandoc.Plain): (pandoc.Plain|pandoc.Block|pandoc.Block[])?
---@field RawBlock? fun(el: pandoc.RawBlock): (pandoc.RawBlock|pandoc.Block|pandoc.Block[])?
---@field Table? fun(el: pandoc.Table): (pandoc.Table|pandoc.Block|pandoc.Block[])?
---@field Cite? fun(el: pandoc.Cite): (pandoc.Cite|pandoc.Inline|pandoc.Inline[])?
---@field Code? fun(el: pandoc.Code): (pandoc.Code|pandoc.Inline|pandoc.Inline[])?
---@field Emph? fun(el: pandoc.Emph): (pandoc.Emph|pandoc.Inline|pandoc.Inline[])?
---@field Image? fun(el: pandoc.Image): (pandoc.Image|pandoc.Inline|pandoc.Inline[])?
---@field LineBreak? fun(el: pandoc.LineBreak): (pandoc.LineBreak|pandoc.Inline|pandoc.Inline[])?
---@field Link? fun(el: pandoc.Link): (pandoc.Link|pandoc.Inline|pandoc.Inline[])?
---@field Math? fun(el: pandoc.Math): (pandoc.Math|pandoc.Inline|pandoc.Inline[])?
---@field Note? fun(el: pandoc.Note): (pandoc.Note|pandoc.Inline|pandoc.Inline[])?
---@field Quoted? fun(el: pandoc.Quoted): (pandoc.Quoted|pandoc.Inline|pandoc.Inline[])?
---@field RawInline? fun(el: pandoc.RawInline): (pandoc.RawInline|pandoc.Inline|pandoc.Inline[])?
---@field SmallCaps? fun(el: pandoc.SmallCaps): (pandoc.SmallCaps|pandoc.Inline|pandoc.Inline[])?
---@field SoftBreak? fun(el: pandoc.SoftBreak): (pandoc.SoftBreak|pandoc.Inline|pandoc.Inline[])?
---@field Space? fun(el: pandoc.Space): (pandoc.Space|pandoc.Inline|pandoc.Inline[])?
---@field Span? fun(el: pandoc.Span): (pandoc.Span|pandoc.Inline|pandoc.Inline[])?
---@field Str? fun(el: pandoc.Str): (pandoc.Str|pandoc.Inline|pandoc.Inline[])?
---@field Strikeout? fun(el: pandoc.Strikeout): (pandoc.Strikeout|pandoc.Inline|pandoc.Inline[])?
---@field Strong? fun(el: pandoc.Strong): (pandoc.Strong|pandoc.Inline|pandoc.Inline[])?
---@field Subscript? fun(el: pandoc.Subscript): (pandoc.Subscript|pandoc.Inline|pandoc.Inline[])?
---@field Superscript? fun(el: pandoc.Superscript): (pandoc.Superscript|pandoc.Inline|pandoc.Inline[])?
---@field Underline? fun(el: pandoc.Underline): (pandoc.Underline|pandoc.Inline|pandoc.Inline[])?
---@field Block? fun(block: pandoc.Block): (pandoc.Block|pandoc.Block[])?
---@field Inline? fun(inline: pandoc.Inline): (pandoc.Inline|pandoc.Inline[])?
---@field Blocks? fun(blocks: pandoc.Blocks): pandoc.Block[]?
---@field Inlines? fun(inlines: pandoc.Inlines): pandoc.Inlines[]?

---@class pandoc.Pandoc: pandoc._base
---@field blocks pandoc.Blocks
---@field meta pandoc.Meta
local Pandoc = {}

--- Perform a normalization of Pandoc documents.
--- E.g., multiple successive spaces are collapsed, and tables are normalized,
--- so that all rows and columns contain the same number of cells.
function Pandoc:normalize() end

--- Applies Lua filters to the complete document.
--- Just as for full-document filters, the order in which elements are traversed
--- can be controlled by setting the `traverse` field of the filter.
--- Returns a (deep) copy on which the filter has been applied: the original element is left untouched.
---@param lua_filters pandoc.LuaFilters #
---    Mapping of pandoc type name to transformer function. The function receives the element
---    and should return the same element type, nil or a list of the same metatype (Block/Inner),
---    which replaces the element.
---    The special members `Blocks` and `Inlines` are called on all lists of the respective type.
---    The special members `Block` and `Inline` serve as fallbacks in case a specific type has no
---    corresponding member.
---@return self filtered_document
function Pandoc:walk(lua_filters) end

---@class pandoc.Meta: table<string, pandoc.MetaValue>
---@alias pandoc.MetaValue pandoc.MetaBlocks|pandoc.MetaBool|pandoc.MetaInlines|pandoc.MetaList|pandoc.MetaMap|pandoc.MetaString
---@alias pandoc.MetaBool boolean
---@class pandoc.MetaBlocks: pandoc.List<pandoc.Block>
---@class pandoc.MetaInlines: pandoc.List<pandoc.Inline>
---@class pandoc.MetaList: any[]
---@class pandoc.MetaMap: table<string, any>
---@class pandoc.MetaString: string

---@class pandoc._attr_trait
---@field attr pandoc.Attr
---@field identifier string
---@field classes pandoc.List<string>
---@field attributes table<string, string>

---@class pandoc.Block: pandoc.Element

---@class pandoc.BlockQuote: pandoc.Block
---@field t "BlockQuote"
---@field tag "BlockQuote"
---@field content pandoc.Blocks

---@class pandoc.BulletList: pandoc.Block
---@field t "BulletList"
---@field tag "BulletList"
---@field content pandoc.List<pandoc.Blocks>

---@class pandoc.CodeBlock: pandoc.Block, pandoc._attr_trait
---@field t "CodeBlock"
---@field tag "CodeBlock"
---@field text string

---@class pandoc.DefinitionList: pandoc.Block
---@field t "DefinitionList"
---@field tag "DefinitionList"
---@field content pandoc.List<[pandoc.Inlines, pandoc.List<pandoc.Blocks>]>

---@class pandoc.Div: pandoc.Block, pandoc._attr_trait
---@field t "Div"
---@field tag "Div"
---@field content pandoc.Blocks

---@class pandoc.Figure: pandoc.Block, pandoc._attr_trait
---@field t "Figure"
---@field tag "Figure"
---@field content pandoc.Blocks
---@field caption pandoc.Caption

---@class pandoc.Header: pandoc.Block, pandoc._attr_trait
---@field t "Header"
---@field tag "Header"
---@field level integer
---@field content pandoc.Inlines

---@class pandoc.HorizontalRule: pandoc.Block
---@field t "HorizontalRule"
---@field tag "HorizontalRule"

---@class pandoc.LineBlock: pandoc.Block
---@field t "LineBlock"
---@field tag "LineBlock"
---@field content pandoc.List<pandoc.Inlines>

---@class pandoc.OrderedList: pandoc.Block
---@field t "OrderedList"
---@field tag "OrderedList"
---@field content pandoc.List<pandoc.Blocks>
---@field listAttributes pandoc.ListAttributes
---@field start integer
---@field style pandoc.ListNumberStyle
---@field delimiter pandoc.ListNumberDelim

---@class pandoc.Para: pandoc.Block
---@field t "Para"
---@field tag "Para"
---@field content pandoc.Inlines

---@class pandoc.Plain: pandoc.Block
---@field t "Plain"
---@field tag "Plain"
---@field content pandoc.Inlines

---@class pandoc.RawBlock: pandoc.Block
---@field t "RawBlock"
---@field tag "RawBlock"
---@field format string
---@field text string

---@class pandoc.Table: pandoc.Block, pandoc._attr_trait
---@field t "Table"
---@field tag "Table"
---@field caption pandoc.Caption
---@field colspecs pandoc.List<pandoc.ColSpec>
---@field head pandoc.TableHead
---@field bodies pandoc.List<pandoc.TableBody>
---@field foot pandoc.TableFoot

---@class pandoc.Inline: pandoc.Element

---@class pandoc.Cite: pandoc.Inline
---@field t "Cite"
---@field tag "Cite"
---@field content pandoc.Inlines
---@field citations pandoc.List<pandoc.Citation>

---@class pandoc.Code: pandoc.Inline, pandoc._attr_trait
---@field t "Code"
---@field tag "Code"
---@field text string

---@class pandoc.Emph: pandoc.Inline
---@field t "Emph"
---@field tag "Emph"
---@field content pandoc.Inlines

---@class pandoc.Image: pandoc.Inline, pandoc._attr_trait
---@field t "Image"
---@field tag "Image"
---@field caption pandoc.Inlines
---@field src string
---@field title string

---@class pandoc.LineBreak: pandoc.Inline
---@field t "LineBreak"
---@field tag "LineBreak"

---@class pandoc.Link: pandoc.Inline, pandoc._attr_trait
---@field t "Link"
---@field tag "Link"
---@field content pandoc.Inlines
---@field target string
---@field title string

---@class pandoc.Math: pandoc.Inline
---@field t "Math"
---@field tag "Math"
---@field mathtype pandoc.MathType
---@field text string

---@class pandoc.Note: pandoc.Inline
---@field t "Note"
---@field tag "Note"
---@field content pandoc.Blocks

---@class pandoc.Quoted: pandoc.Inline
---@field t "Quoted"
---@field tag "Quoted"
---@field quotetype pandoc.QuoteType
---@field content pandoc.Inlines

---@class pandoc.RawInline: pandoc.Inline
---@field t "RawInline"
---@field tag "RawInline"
---@field format string
---@field text string

---@class pandoc.SmallCaps: pandoc.Inline
---@field t "SmallCaps"
---@field tag "SmallCaps"
---@field content pandoc.Inlines

---@class pandoc.SoftBreak: pandoc.Inline
---@field t "SoftBreak"
---@field tag "SoftBreak"

---@class pandoc.Space: pandoc.Inline
---@field t "Space"
---@field tag "Space"

---@class pandoc.Span: pandoc.Inline, pandoc._attr_trait
---@field t "Span"
---@field tag "Span"
---@field content pandoc.Inlines

---@class pandoc.Str: pandoc.Inline
---@field t "Str"
---@field tag "Str"
---@field text string

---@class pandoc.Strikeout: pandoc.Inline
---@field t "Strikeout"
---@field tag "Strikeout"
---@field content pandoc.Inlines

---@class pandoc.Strong: pandoc.Inline
---@field t "Strong"
---@field tag "Strong"
---@field content pandoc.Inlines

---@class pandoc.Subscript: pandoc.Inline
---@field t "Subscript"
---@field tag "Subscript"
---@field content pandoc.Inlines

---@class pandoc.Superscript: pandoc.Inline
---@field t "Superscript"
---@field tag "Superscript"
---@field content pandoc.Inlines

---@class pandoc.Underline: pandoc.Inline
---@field t "Underline"
---@field tag "Underline"
---@field content pandoc.Inlines

---@class pandoc.Attr: pandoc._base
---@field identifier string
---@field classes string[]
---@field attributes pandoc.AttributeList

--- Internal representation of attribute list
---@class pandoc.AttributeList: table<string, string>

--- All types that can be passed as an `attr` parameter
---@alias pandoc.AttrParam pandoc.Attr|pandoc.AttributeList|table<string,string>

---@class pandoc.Cell: pandoc._base, pandoc._attr_trait
---@field alignment pandoc.Alignment
---@field row_span integer
---@field col_span integer
---@field contents pandoc.Blocks

---@class pandoc.Citation: pandoc._base
---@field id string
---@field mode pandoc.CitationMode
---@field prefix pandoc.Inlines
---@field suffix pandoc.Inlines
---@field note_num integer
---@field hash integer

---@class pandoc.ColSpec: pandoc._base
---@field [1] pandoc.Alignment
---@field [2] number?

---@class pandoc.ListAttributes: pandoc._base
---@field start integer
---@field style pandoc.ListNumberStyle
---@field delimiter pandoc.ListNumberDelim

---@class pandoc.Row: pandoc._base
---@field attr pandoc.Attr
---@field cells pandoc.List<pandoc.Cell>

---@class pandoc.TableBody: pandoc._base
---@field attr pandoc.Attr
---@field body pandoc.List<pandoc.Row>
---@field head pandoc.List<pandoc.Row>
---@field row_head_columns integer

---@class pandoc.TableFoot: pandoc._base, pandoc._attr_trait
---@field attr pandoc.Attr
---@field rows pandoc.List<pandoc.Row>

---@class pandoc.TableHead: pandoc._base, pandoc._attr_trait
---@field attr pandoc.Attr
---@field rows pandoc.List<pandoc.Row>

---@class pandoc.Caption: pandoc._base
---@field long pandoc.Blocks
---@field short? pandoc.Inlines

---@class pandoc.SimpleTable: pandoc._base
---@field caption pandoc.Inlines
---@field aligns pandoc.List<pandoc.Alignment>
---@field widths pandoc.List<number>
---@field headers pandoc.List<pandoc.Inlines>
---@field rows pandoc.List<pandoc.List<pandoc.Inlines>>

---@class pandoc.Blocks: pandoc.List<pandoc.Block>, pandoc.Walkable
---@class pandoc.Inlines: pandoc.List<pandoc.Inline>, pandoc.Walkable

--- Lists, when part of an element, or when generated during marshaling,
--- are made instances of the pandoc.List type for convenience.
--- Values of this type can be created with the `pandoc.List` constructor,
--- turning a normal Lua table into a List.
---@class pandoc.List<Item>: pandoc._base, Item[]
---@operator concat(List<Item>): List<Item>
---@field [integer] Item?
local List = {}

--- Returns element at `index` or `default`.
---@generic Item, Default
---@param self pandoc.List<Item>
---@param index integer
---@param default Default
---@return Item|Default
function List.at(self, index, default) end

--- Adds `list` to end of this list.
---@param self pandoc.List<Item>
---@param list pandoc.List<Item>
function List.extend(self, list) end

--- Returns value and index of the first occurence of `needle`, if found.
---@param self pandoc.List<Item>
---@param needle any Item to search for
---@param init? integer Start search at this index
---@return Item? element
---@return integer? index
function List.find(self, needle, init) end

--- Returns value and index of element for which `pred` is true.
---@param self pandoc.List<Item>
---@param pred fun(elem: Item): boolean Predicate to filter for
---@param init? integer Start search at this index
---@return any? element
---@return integer? index
function List.find_if(self, pred, init) end

--- Returns a new list with only items for which `pred` is true.
---@param self pandoc.List<Item>
---@param pred fun(elem: Item): boolean Predicate to filter for
---@return pandoc.List<Item> filtered_list
function List.filter(self, pred) end

--- Checks if the list has an item equal to `needle`.
---@param needle any Item to check for
---@param init? integer Start search at this index
---@return boolean includes
function List:includes(needle, init) end

--- Insert item at end of list.
---@param self pandoc.List<Item>
---@param value Item Item to insert
function List.insert(self, value) end

--- Insert item at `pos` in list.
---@param self pandoc.List<Item>
---@param pos integer Position to insert `value` at
---@param value Item Item to insert
function List.insert(self, pos, value) end

--- Create an iterator over the list. The resulting function returns the next value each time it is called.
---
--- Usage:
--- ```lua
--- for item in List({1, 1, 2, 3, 5, 8}):iter() do
---   -- process item
--- end
--- ```
---@param self pandoc.List<Item>
---@param step? integer Step size. Negative values start from end of list. Defaults to `1`.
---@return fun(): Item iterator
function List.iter(self, step) end

--- Return a copy of this list with `fn` applied to all items.
---@generic NewItem
---@param self pandoc.List<Item>
---@param fn fun(elem: Item): NewItem Transforming function
---@return pandoc.List<NewItem> mapped_list
function List.map(self, fn) end

--- Create a new List.
---@generic Item
---@param table_or_iterator table<integer, Item>|fun(): Item Table or iterator to turn into List.
---@return pandoc.List<Item>
function List:new(table_or_iterator) end

--- Removes the element at position pos, returning the value of the removed element.
---@param self pandoc.List<Item>
---@param pos? integer Index of element to remove
---@return Item? removed_element
function List.remove(self, pos) end

--- Sort list in-place. Identical to Lua `table.sort()`.
---@param self pandoc.List<Item>
---@param comp? fun(i: Item, j: Item): boolean
function List.sort(self, comp) end

---@alias pandoc.Alignment
---| "AlignLeft"
---| "AlignRight"
---| "AlignCenter"
---| "AlignDefault"

---@alias pandoc.CitationMode
---| "AuthorInText"
---| "SuppressAuthor"
---| "NormalCitation"

---@alias pandoc.ListNumberStyle
---| "DefaultStyle"
---| "Example"
---| "Decimal"
---| "LowerRoman"
---| "UpperRoman"
---| "LowerAlpha"
---| "UpperAlpha"

---@alias pandoc.ListNumberDelim
---| "DefaultDelim"
---| "Period"
---| "OneParen"
---| "TwoParens"

---@alias pandoc.MathType
---| "DisplayMath"
---| "InlineMath"

---@alias pandoc.QuoteType
---| "SingleQuote"
---| "DoubleQuote"

--- Pandoc reader options that control how input is parsed.
---@class pandoc.ReaderOptions
---@field abbreviations table<string, string> Set of known abbreviations
---@field columns integer Number of columns in terminal (for calculating column positions)
---@field default_image_extension string Default extension for images (e.g., ".png")
---@field extensions string[] String representation of syntax extensions bit field (sequence of enabled extensions)
---@field indented_code_classes string[] Default classes for indented code blocks
---@field standalone boolean Whether the input was a standalone document with header
---@field strip_comments boolean HTML comments are stripped instead of parsed as raw HTML
---@field tab_stop integer Width (i.e. equivalent number of spaces) of tab stops
---@field track_changes "accept"|"reject"|"all" Track changes setting for docx: "accept" (accept all), "reject" (reject all), or "all" (show all)

--- Pandoc writer options that control how output is generated.
---@class pandoc.WriterOptions
---@field cite_method "citeproc"|"natbib"|"biblatex" How to print cites - method to use for citations
---@field columns integer Characters in a line (for text wrapping)
---@field dpi integer DPI for pixel to/from inch/cm conversions
---@field email_obfuscation "none"|"javascript"|"references" How to obfuscate emails in HTML output
---@field epub_chapter_level integer Header level for chapters, i.e., how the document is split into separate files
---@field epub_fonts string[] Paths to fonts to embed in EPUB
---@field epub_metadata? string Metadata to include in EPUB
---@field epub_subdirectory string Subdirectory for EPUB in OCF container
---@field extensions string[] Markdown extensions that can be used (sequence of extension names)
---@field highlight_style? table Style to use for syntax highlighting; nil means no highlighting
---@field html_math_method "plain"|"gladtex"|"webtex"|"mathml"|"mathjax"|"katex" How to print math in HTML output
---@field html_q_tags boolean Use <q> tags for quotes in HTML
---@field identifier_prefix string Prefix for section & note IDs in HTML and for footnote marks in markdown
---@field incremental boolean True if lists should be incremental (show items one by one in presentations)
---@field listings boolean Use listings package for LaTeX code blocks
---@field number_offset integer[] Starting number for section, subsection, etc. (list of integers)
---@field number_sections boolean Number sections in LaTeX, ConTeXt, HTML, or EPUB output
---@field prefer_ascii boolean Prefer ASCII representations of characters when possible
---@field reference_doc string Path to reference document if specified (for docx, pptx, odt)
---@field reference_links boolean Use reference links in writing markdown, reStructuredText
---@field reference_location "block"|"section"|"document" Location of footnotes and references for markdown: "block" (end of block), "section" (end of section), or "document" (end of document)
---@field section_divs boolean Put sections in <div> tags in HTML
---@field setext_headers boolean Use setext headers for levels 1-2 in markdown output
---@field slide_level? integer Force header level of slides
---@field tab_stop integer Tab stop width for conversion between spaces and tabs
---@field table_of_contents boolean Include table of contents
---@field template? string Template to use for document
---@field toc_depth integer Number of section levels to include in TOC
---@field top_level_division "default"|"section"|"chapter"|"part" Type of top-level divisions in LaTeX, ConTeXt, DocBook, TEI
---@field variables table<string, any> Variables to set in template (string-indexed table)
---@field wrap_text "auto"|"none"|"preserve" Option for wrapping text: "auto" (wrap lines), "none" (no wrap), or "preserve" (preserve wrap from source)

--- Scaffolding for custom writers to avoid boilerplate
---@class pandoc.scaffolding
---@field Writer pandoc.Writer
local scaffolding = {}

--- AST node renderer functions can return any of these.
--- If the rendering of a node does not depend on its value, any of these can be assigned
--- to the corresponding key statically.
---@alias pandoc.Render string|pandoc.Doc|table<integer, pandoc.Render>

--- Custom writer scaffold that handles metadata and template processing.
--- Users only need to implement AST node rendering functions.
---@class pandoc.Writer
---@field Block pandoc.Writer.Block
---@field Inline pandoc.Writer.Inline
---@field Blocks fun(blocks: pandoc.Blocks, sep?: pandoc.Doc|string): pandoc.Doc Function to render list of blocks with separator
---@field Inlines fun(inlines: pandoc.Inlines): pandoc.Doc Function to render list of inlines
---@field Pandoc fun(doc: pandoc.Pandoc, opts: pandoc.WriterOptions): pandoc.Doc Function to render entire Pandoc document
---@overload fun(doc: pandoc.Pandoc, opts: pandoc.WriterOptions): string
local Writer = {}

---@class pandoc.Writer.Block
---@field BlockQuote? (fun(el: pandoc.BlockQuote, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field BulletList? (fun(el: pandoc.BulletList, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field CodeBlock? (fun(el: pandoc.CodeBlock, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field DefinitionList? (fun(el: pandoc.DefinitionList, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Div? (fun(el: pandoc.Div, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Figure? (fun(el: pandoc.Figure, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Header? (fun(el: pandoc.Header, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field HorizontalRule? (fun(el: pandoc.HorizontalRule, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field LineBlock? (fun(el: pandoc.LineBlock, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field OrderedList? (fun(el: pandoc.OrderedList, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Para? (fun(el: pandoc.Para, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Plain? (fun(el: pandoc.Plain, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field RawBlock? (fun(el: pandoc.RawBlock, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Table? (fun(el: pandoc.Table, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@overload fun(el: pandoc.Block): pandoc.Doc
local WriterBlock = {}

---@class pandoc.Writer.Inline
---@field Cite? (fun(el: pandoc.Cite, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Code? (fun(el: pandoc.Code, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Emph? (fun(el: pandoc.Emph, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Image? (fun(el: pandoc.Image, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field LineBreak? (fun(el: pandoc.LineBreak, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Link? (fun(el: pandoc.Link, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Math? (fun(el: pandoc.Math, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Note? (fun(el: pandoc.Note, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Quoted? (fun(el: pandoc.Quoted, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field RawInline? (fun(el: pandoc.RawInline, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field SmallCaps? (fun(el: pandoc.SmallCaps, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field SoftBreak? (fun(el: pandoc.SoftBreak, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Space? (fun(el: pandoc.Space, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Span? (fun(el: pandoc.Span, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Str? (fun(el: pandoc.Str, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Strikeout? (fun(el: pandoc.Strikeout, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Strong? (fun(el: pandoc.Strong, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Subscript? (fun(el: pandoc.Subscript, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Superscript? (fun(el: pandoc.Superscript, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@field Underline? (fun(el: pandoc.Underline, opts: pandoc.WriterOptions): pandoc.Render)|pandoc.Render
---@overload fun(el: pandoc.Inline): pandoc.Doc
local WriterInline = {}

--- Module for creating reflowable plain-text documents.
---@class pandoc.layout: pandoc.Doc
---@field blankline pandoc.Doc A blank line.
---@field cr pandoc.Doc A carriage return (line break).
---@field empty pandoc.Doc An empty document.
---@field lparen pandoc.Doc A left parenthesis.
---@field rparen pandoc.Doc A right parenthesis.
---@field space pandoc.Doc A space character.
local layout = {}

--- Creates a Doc which is conditionally included only
--- if it comes at the beginning of a line.
---@param text pandoc.Doc|string Content to include when placed after a break
---@return pandoc.Doc
function layout.after_break(n) end

--- Inserts blank lines unless they exist already.
---@param n integer Number of blank lines
---@return pandoc.Doc
function layout.blanklines(n) end

--- Concatenate a list of documents.
---@param docs (pandoc.Doc|string)[]|pandoc.List<pandoc.Doc|string> Documents to concatenate
---@param sep? pandoc.Doc|string Separator between documents
---@return pandoc.Doc
function layout.concat(docs, sep) end

--- Create a literal string document.
---@param str string String content
---@return pandoc.Doc
function layout.literal(str) end

--- Returns the real length of a string in a monospace font:
--- 0 for a combining character, 1 for a regular character,
--- 2 for an East Asian wide character.
---@param str string String to check
---@return integer|string
function layout.real_length(doc) end

---An expandable border that, when placed next to a box, expands to the height of
---the box. Strings cycle through the list provided.
---@param doc string
---@return pandoc.Doc
function layout.vfill(border) end

--- Reflowable plain-text document that can be rendered to different widths.
---@class pandoc.Doc
---@operator concat(pandoc.Doc): pandoc.Doc
---@operator add(pandoc.Doc): pandoc.Doc
---@operator div(pandoc.Doc): pandoc.Doc
---@operator idiv(pandoc.Doc): pandoc.Doc
local Doc = {}

---@param other pandoc.Doc
---@return pandoc.Doc
function Doc:__concat(other) end

---@param other pandoc.Doc
---@return pandoc.Doc
function Doc:__add(other) end

---@param other pandoc.Doc
---@return pandoc.Doc
function Doc:__div(other) end

---@param other pandoc.Doc
---@return pandoc.Doc
function Doc:__idiv(other) end

--- Creates a Doc which is conditionally included only
--- if it is not followed by a blank line.
---@param text pandoc.Doc|string Content to include when placed before a non-blank line
---@return pandoc.Doc
function Doc.before_non_blank(n) end

--- Wrap a document in curly braces.
---@param doc pandoc.Doc|string Document to wrap
---@return pandoc.Doc
function Doc.braces(doc) end

--- Wrap a document in square brackets.
---@param doc pandoc.Doc|string Document to wrap
---@return pandoc.Doc
function Doc.brackets(doc) end

--- Center a document within a given width.
---@param doc pandoc.Doc|string Document to center
---@param width integer Width to center within
---@return pandoc.Doc
function Doc.cblock(doc, width) end

--- Remove trailing blank lines from a document.
---@param doc pandoc.Doc|string Document to chomp
---@return pandoc.Doc
function Doc.chomp(doc) end

--- Wrap a document in double quotes.
---@param doc pandoc.Doc|string Document to quote
---@return pandoc.Doc
function Doc.double_quotes(doc) end

--- Flush a document to the left margin.
---@param doc pandoc.Doc|string Document to flush
---@return pandoc.Doc
function Doc.flush(doc) end

--- Create a hanging indent.
---@param doc pandoc.Doc|string Document to indent
---@param indent integer Number of spaces to prefix lines 2+ with
---@param start pandoc.Doc|string First line prefix
---@return pandoc.Doc
function Doc.hang(doc, indent, start) end

--- Returns the height of a block/Doc.
---@param doc pandoc.Doc|string Document to query
---@return integer|string
function Doc.height() end

--- Place a document inside delimiters.
---@param doc pandoc.Doc|string Document to wrap
---@param start pandoc.Doc|string Starting delimiter
---@param end_doc pandoc.Doc|string Ending delimiter
---@return pandoc.Doc
function Doc.inside(doc, start, end_doc) end

--- Checks whether a Doc is empty.
---@param doc pandoc.Doc|string Document to check
---@return boolean
function Doc.is_empty() end

--- Left-align a document within a given width.
---@param doc pandoc.Doc|string Document to align
---@param width integer Width to align within
---@return pandoc.Doc
function Doc.lblock(doc, width) end

--- Returns the minimal width of a Doc when reflowed
--- at breakable spaces.
---@param doc pandoc.Doc|string Document to query
---@return integer|string
function Doc.min_offset(doc) end

--- Nest a document with indentation.
---@param doc pandoc.Doc|string Document to nest
---@param indent integer Indentation amount
---@return pandoc.Doc
function Doc.nest(doc, indent) end

--- Removes leading blank lines from a document.
---@param doc pandoc.Doc|string Document to nestle
---@return pandoc.Doc
function Doc.nestle(doc) end

--- Makes a Doc non-reflowable.
---@param doc pandoc.Doc|string Document to prevent wrapping
---@return pandoc.Doc
function Doc.nowrap(doc) end

--- Returns the width of a Doc as number of characters.
---@param doc pandoc.Doc|string Document to query
---@return pandoc.Doc
function Doc.offset(doc) end

--- Wrap a document in parentheses.
---@param doc pandoc.Doc|string Document to wrap
---@return pandoc.Doc
function Doc.parens(doc) end

--- Add a prefix to each line of a document, except the
--- first if it is not at the beginnnig of the line.
---@param doc pandoc.Doc|string Document to prefix
---@param prefix string Prefix string
---@return pandoc.Doc
function Doc.prefixed(doc, prefix) end

--- Wrap a document in single quotes.
---@param doc pandoc.Doc|string Document to quote
---@return pandoc.Doc
function Doc.quotes(doc) end

--- Right-align a document within a given width.
---@param doc pandoc.Doc|string Document to align
---@param width integer Width to align within
---@return pandoc.Doc
function Doc.rblock(doc, width) end

--- Render a Doc. The text is reflowed on breakable spaces
--- to match the given line length. Text is not reflowed
--- if the line line length parameter is omitted or nil.
---@param doc pandoc.Doc|string Document to render
---@param colwidth? integer Column width for line wrapping
---@param style? "plain"|"ansi" #
---    Whether to generate plain text or ANSI terminal output.
---    Defaults to plain.
---@return string
function Doc.render(doc, colwidth, style) end

--- Returns the column that would be occupied by
--- the last laid out character.
---@param doc pandoc.Doc|string Document to query
---@param i integer Start column
---@return integer|string column_number
function Doc.update_column(doc, i) end

--- Command line options and argument parsing
---@class pandoc.cli
---@field default_options table Default CLI options, using a JSON-like representation.
local cli = {}

--- Parses command line arguments into pandoc options.
--- Typically this function will be used in stand-alone pandoc Lua scripts,
--- taking the list of arguments from the global `arg`.
---@param args string[] List of command line options
---@return table parsed_options Parsed options, using their JSON-like representation
function cli.parse_options(args) end

--- Starts a read-eval-print loop (REPL). The function returns all values of the last evaluated input.
--- Exit the REPL by pressing ctrl-d or ctrl-c; press F1 to get a list of all key bindings.
--- The REPL is started in the global namespace, unless the env parameter is specified.
--- In that case, the global namespace is merged into the given table and the result is used as _ENV value for the repl.
--- Specifically, local variables cannot be accessed, unless they are explicitly passed via the env parameter; e.g.
--- ```lua
--- function Pandoc (doc)
---   -- start repl, allow to access the `doc` parameter
---   -- in the repl
---   return pandoc.cli.repl{ doc = doc }
--- end
--- ````
--- @param env? table<string, string> Extra environment; the global environment is merged into this table.
--- @return any... results The result(s) of the last evaluated input, or nothing if the last input resulted in an error.
function cli.repl(env) end

--- Basic image querying functions.
---@class pandoc.image
local image = {}

--- Returns a table containing the size and resolution of an image;
--- throws an error if the given string is not an image, or if the size of the image cannot be determined.
---@param image string Binary image data
---@param opts? pandoc.WriterOptions|{dpi: number}
---@return {width: integer, height: integer, dpi_horiz: number, dpi_vert: number}
function image.size(image, opts) end

--- Returns the format of an image as a lowercase string.
--- Formats recognized by pandoc include png, gif, tiff, jpeg, pdf, svg, eps, and emf.
---@param image string Binary image data
---@return string? format
function image.format(image) end

--- JSON module to work with JSON
---@class pandoc.json
local json = {}

--- Decode a JSON string into a Lua value.
---@param str string JSON string to decode
---@param pandoc_types? boolean Whether to use pandoc types when possible
---@return any value Decoded Lua value
function json.decode(str, pandoc_types) end

--- Encode a Lua value into a JSON string.
--- `__tojson` metamethods are respected.
---@param obj any Lua value to encode
---@return string json JSON string representation
function json.encode(obj) end

--- Access to pandoc’s logging system
---@class pandoc.log
local log = {}

--- Log an info-level message.
---@param message any Message to log
---@param ... any Additional values to log
function log.info(message, ...) end

--- Log a warning-level message.
---@param message any Message to log
---@param ... any Additional values to log
function log.warn(message, ...) end

--- Applies the function to the given arguments while preventing log messages from being added to the log.
---@generic Rets
---@param fn fun(): Rets... Function to be silenced
---@return string[] log_messages
---@return Rets... inner_rets Variadic returns of `fn`
function log.silence(fn) end

--- The pandoc.mediabag module allows accessing pandoc’s media storage
---@class pandoc.mediabag
local mediabag = {}

--- Removes a single entry from the media bag.
---@param filepath string Filename of the item to deleted. The media bag will be left unchanged if no entry with the given filename exists
function mediabag.delete(filepath) end

--- Clear-out the media bag, deleting all items.
function mediabag.empty() end

--- Fetch media from a source and add to mediabag.
---@param source string Source URL or path to fetch from
---@return string? contents
---@return string? mime_type
function mediabag.fetch(source) end

--- Fills the mediabag with the images in the given document.
---@param doc pandoc.Pandoc Document from which to fill the mediabag
---@return pandoc.Pandoc modified_doc
function mediabag.fill(doc) end

--- Insert media content into the mediabag.
---@param filepath string Path where the media will be stored
---@param mime_type? string MIME type of the content
---@param content string Binary content to store
function mediabag.insert(filepath, mime_type, content) end

--- Returns an iterator triple to be used with Lua’s generic for statement.
--- The iterator returns the filepath, MIME type, and content of a media bag item on each invocation.
--- Items are processed one-by-one to avoid excessive memory use.
--- Usage:
---
--- ```lua
--- for fp, mt, contents in pandoc.mediabag.items() do
---   -- print(fp, mt, contents)
--- end
--- ````
function mediabag.items() end

--- Get a summary of the current media bag contents.
---@return {path: string, type: string, length: integer}[] items A list of elements summarizing each entry in the media bag.
function mediabag.list() end

--- Look up media content from the mediabag.
---@param filepath string Path to look up
---@return string? content Binary content
---@return string? mime_type MIME type of the content
function mediabag.lookup(filepath) end

--- Convert the input data into a data URI as defined by RFC 2397.
---@param mime_type string MIME type of the data
---@param raw_data string Data to encode
---@return string data_uri
function mediabag.make_data_uri(mime_type, raw_data) end

--- Writes the contents of mediabag to the given target directory.
--- If fp is given, then only the resource with the given name will be extracted.
--- Omitting that parameter means that the whole mediabag gets extracted.
--- An error is thrown if fp is given but cannot be found in the mediabag.
---@param dir string Path of the target directory
---@param fp? string Canonical name (relative path) of resource
function mediabag.write(dir, fp) end

--- Module for file path manipulations.
---@class pandoc.path
---@field separator string Directory separator
---@field search_path_separator string Character that is used to separate the entries in the PATH environment variable
local path = {}

--- Get the directory part of a filepath.
---@param filepath string File path
---@return string directory Directory path
function path.directory(filepath) end

--- Check whether there exists a filesystem object at the given path.
--- If type is given and either `directory` or `file`, then the function returns true if and only if
--- the file system object has the given type, or if it’s a symlink pointing to an object of that type.
--- Passing `symlink` as type requires the path itself to be a symlink.
--- Types other than those will cause an error.
---@param path string File path to check
---@param type? "directory"|"file"|"symlink" The required type of the filesystem object
---@return boolean exists
function path.exists(path, type) end

--- Get the filename part of a filepath.
---@param filepath string File path
---@return string filename Filename without directory
function path.filename(filepath) end

--- Check if a path is absolute.
---@param filepath string Path to check
---@return boolean is_absolute True if path is absolute
function path.is_absolute(filepath) end

--- Check if a path is relative.
---@param filepath string Path to check
---@return boolean is_relative True if path is relative
function path.is_relative(filepath) end

--- Join path components into a single path.
---@param components string[] Path components to join
---@return string path Joined path
function path.join(components) end

--- Make a path relative to a root directory.
---@param path string Path to make relative
---@param root string Root directory
---@param unsafe? boolean whether to allow `..` in the result
---@return string relative_path Relative path
function path.make_relative(path, root, unsafe) end

--- Normalize a path by removing redundant elements.
---@param path string Path to normalize
---@return string normalized_path Normalized path
function path.normalize(path) end

--- Split a path into components.
---@param filepath string Path to split
---@return string[] components Path components
function path.split(filepath) end

--- Split filename and extension.
---@param filepath string File path
---@return string name Filename without extension
---@return string extension File extension (including dot)
function path.split_extension(filepath) end

--- Split a search path into individual paths.
---@param search_path string Search path string
---@return string[] paths Individual directories in search path
function path.split_search_path(search_path) end

--- Augment the string module such that strings can be used as path objects.
function path.treat_strings_as_paths() end

--- Access to the higher-level document structure, including hierarchical sections and the table of contents
---@class pandoc.structure
local structure = {}

--- Make sections from a list of blocks based on headers.
--- Wraps content between headers into Div elements with section classes.
---@param blocks pandoc.Blocks|pandoc.Pandoc Blocks to process
---@param opts? {number_sections?: boolean, base_level?: integer, slide_level?: integer} #
---    If `number_sections` is true, a number attribute containing the section number is added to each `Header`.
---    If `base_level` is an integer, then `Header` levels will be reorganized so that there are no gaps,
---    with numbering levels shifted by the given value.
---    Finally, an integer slide_level value triggers the creation of slides at that heading level.
---@return pandoc.Blocks sections Blocks with section structure
function structure.make_sections(blocks, opts) end

--- Find level of header that starts slides
--- (defined as the least header level that occurs before a non-header/non-hrule in the blocks).
---@param blocks pandoc.Blocks|pandoc.Pandoc Blocks to process
---@return integer slide_level
function structure.slide_level(blocks) end

--- Split a document into chunks based on its structure.
--- Creates a chunked document with separate files for each section.
---@param doc pandoc.Pandoc Document to split
---@param opts? {path_template?: string, number_sections?: boolean, chunk_level?: integer, base_heading_level?: integer} #
---    `path_template`: template used to generate the chunks' filepaths
---    `number_sections`: whether sections should be numbered
---    `chunk_level`: Heading level the document should be split into chunks at
---    `base_heading_level`: Base level to be used for numbering
---@return pandoc.ChunkedDoc chunked Chunked document
function structure.split_into_chunks(doc, opts) end

--- Generates a table of contents for the given object.
---@param toc_source pandoc.Pandoc|pandoc.Blocks|pandoc.ChunkedDoc Document blocks
---@param opts? pandoc.WriterOptions
---@return pandoc.BulletList toc Table of contents as list
function structure.table_of_contents(toc_source, opts) end

--- Generates a unique identifier from a list of inlines, similar to what’s generated by the `auto_identifiers` extension.
---@param inlines pandoc.Inlines Base for identifier
---@param used? table<string, boolean> Set of identifiers that have been used already
---@param exts? string[] List of format extensions
---@return string unique_identifier
function structure.unique_identifier(inlines, used, exts) end

--- Document chunking for multi-file output.
---@class pandoc.ChunkedDoc
---@field chunks pandoc.Chunk[] List of document chunks
---@field meta pandoc.Meta Document metadata
---@field toc table Table of contents information

--- Individual chunk of a document.
---@class pandoc.Chunk
---@field heading pandoc.Inlines Heading text
---@field id string Chunk identifier
---@field level integer Heading level
---@field number integer Chunk number
---@field section_number string Hierarchical section number
---@field path string Target filepath for chunk
---@field up pandoc.Chunk|nil Parent chunk
---@field prev pandoc.Chunk|nil Previous chunk
---@field next pandoc.Chunk|nil Next chunk
---@field unlisted boolean Whether chunk is unlisted in TOC
---@field contents pandoc.Blocks Chunk content

--- Module for system operations and information.
---@class pandoc.system
---@field arch string System architecture
---@field os string Operating system name.
local system = {}

--- Get CPU time used by the current process.
---@return number cpu_time CPU time in seconds
function system.cputime() end

--- Executes a system command with the given arguments and `input` on stdin.
---@param command string Command to execute
---@param args string[] Command arguments
---@param input? string Input on `stdin`
---@param opts? table Process options
---@return integer|false failure Exit code on failure, `false` on success
---@return string stdout
---@return string stderr
function system.command(command, args, input, opts) end

--- Copy a file with its permissions. If the destination file already exists, it is overwritten.
---@param source string Source path
---@param target string Target path
function system.copy(source, target) end

--- Get all environment variables.
---@return table<string, string> environment Environment variables
function system.environment() end

--- Get the current working directory.
---@return string directory Current working directory path
function system.get_working_directory() end

--- List the contents of a directory.
---@param directory? string Directory to list. Defaults to `.`
function system.list_directory(directory) end

--- Create a new directory.
---@param dirname string Path of the new directory
---@param create_parent? boolean Create all missing intermediate directories as well
function system.make_directory(dirname, create_parent) end

--- Read a file.
---@param filepath string File to read
---@return string contents
function system.read_file(filepath) end

--- Rename a path.
--- If `old` is a directory and `new` is a directory that already exists,
--- then `new` is atomically replaced by the `old` directory.
--- On Win32 platforms, this function fails if `new` is an existing directory.
--- If `old` does not refer to a directory, then neither may `new`.
---@param old string Path to rename
---@param new string New path of `old`
function system.rename(old, new) end

--- Delete a file.
---@param filename string Path of file to delete
function system.remove(filename) end

--- Delete a directory.
--- Needs to be empty or requires `recursive` to be set to `true`.
---@param dirname string Path of directory to delete
---@param recursive? boolean Delete the directory and its contents recursively.
function system.remove_directory(dirname, recursive) end

--- Obtain the modification and access time of a file or directory.
--- The times are returned as strings using the ISO 8601 format.
---@param filepath string Path of file or directory
---@return string last_modified
---@return string last_accessed
function system.times(filepath) end

--- Run a function with modified environment variables.
---@generic Rets
---@param env table<string, string> Environment variables to set
---@param callback fun(): Rets... Function to run with modified environment
---@return Rets... rets Variadic returns of `callback`
function system.with_environment(env, callback) end

--- Run a function with a temporary directory.
---@generic Rets
---@param parent string Parent directory for temp directory
---@param templ string Template for temp directory name
---@param callback fun(tmpdir: string): Rets... Function to run with temp directory
---@return Rets... rets Variadic returns of `callback`
function system.with_temporary_directory(parent, templ, callback) end

--- Run a function with a different working directory.
---@generic Rets
---@param dir string Directory to use as working directory
---@param callback fun(): Rets... Function to run in that directory
---@return Rets... rets Variadic returns of `callback`
function system.with_working_directory(dir, callback) end

--- Writes a string to a file.
---@param filepath string Path to write to
---@param contents string Contents to write
function system.write_file(filepath, contents) end

--- Access special directories and directory search paths.
--- Special directories for storing user-specific application data,
--- configuration, and cache files, as specified by the XDG Base Directory Specification.
---@overload fun(xdg_directory_type: "datadirs"|"configdirs"): string[]
---@overload fun(xdg_directory_type: "config"|"data"|"cache"|"state"): string
---@overload fun(xdg_directory_type: "config"|"data"|"cache"|"state", filepath: string): string
---@param xdg_directory_type "config"|"data"|"cache"|"state"|"datadirs"|"configdirs" Type of the XDG directory or search path
---@param filepath? string Relative path that is appended to the path; ignored if the result is a list of search paths
---@return string|string[]
function system.xdg(xdg_directory_type, filepath) end

--- Handle pandoc templates
---@class pandoc.template: pandoc.Template
local template = {}

--- Compile a template string.
---@param template_string string Template string
---@param templates_path? string Determines a default path and extension for partials; uses the data files templates path by default.
---@return pandoc.Template template Compiled template
function template.compile(template_string, templates_path) end

--- Get the default template for a given writer.
---@param writer? string Output format name. Defaults to global default format.
---@return string raw_template
function template.default(writer) end

--- Get a template from a file.
---@param filename string Template filename
---@return string contents
function template.get(filename) end

--- Creates template context from the document’s Meta data, using the given functions to convert Blocks and Inlines to Doc values.
---@param meta pandoc.Meta Document metadata
---@param blocks_writer fun(blocks: pandoc.Blocks): pandoc.Doc[] Converter from `Blocks` to `Doc` values
---@param inlines_writer fun(inlines: pandoc.Inlines): pandoc.Doc[] Converter from `Inlines` to `Doc` values
---@return table template_context
function template.meta_to_context(meta, blocks_writer, inlines_writer) end

--- Compiled template object.
---@class pandoc.Template
local Template = {}

--- Apply a template with a context.
---@param template pandoc.Template Template to apply
---@param context table Template variables context
---@return string output Rendered template
function Template.apply(template, context) end

--- UTF-8 aware text manipulation functions, implemented in Haskell
---@class pandoc.text
local text = {}

--- Convert a string from a specific encoding to UTF-8.
---@param s string String to convert
---@param encoding? string Source encoding
---@return string converted UTF-8 encoded string
function text.fromencoding(s, encoding) end

--- Get the length of a UTF-8 string in characters.
---@param s string UTF-8 string
---@return integer length Number of characters
function text.len(s) end

--- Convert a UTF-8 string to lowercase.
---@param s string String to convert
---@return string lowercase Lowercase string
function text.lower(s) end

--- Reverse a UTF-8 string.
---@param s string String to reverse
---@return string reversed Reversed string
function text.reverse(s) end

--- Extract a substring from a UTF-8 string.
---@param s string Source string
---@param i integer Start position (1-indexed)
---@param j? integer End position (defaults to end of string)
---@return string substring Extracted substring
function text.sub(s, i, j) end

--- Tries to convert the string into a Unicode subscript version of the string.
--- Returns nil if not all characters of the input can be mapped to a subscript Unicode character.
--- Supported characters include numbers, parentheses, and plus/minus.
---@param input string String to convert
---@return string? converted
function text.subscript(input) end

--- Tries to convert the string into a Unicode superscript version of the string.
--- Returns nil if not all characters of the input can be mapped to a superscript Unicode character.
--- Supported characters include numbers, parentheses, and plus/minus.
---@param input string String to convert
---@return string? converted
function text.superscript(input) end

--- Convert a UTF-8 string to a specific encoding.
---@param s string UTF-8 string to convert
---@param encoding? string Target encoding
---@return string converted String in target encoding
function text.toencoding(s, encoding) end

--- Convert a UTF-8 string to uppercase.
---@param s string String to convert
---@return string uppercase Uppercase string
function text.upper(s) end

--- Constructors for types that are not part of the pandoc AST
---@class pandoc.types
---@field version pandoc.types.Version Version of pandoc-types.
local types = {}

---@alias pandoc.VersionSpec string|number|integer[]|pandoc.types.Version
--- Create a Version object.
---@param spec pandoc.VersionSpec
---@return pandoc.types.Version version
function types.Version(spec) end

--- Version object. This represents a software version like `2.7.3`.
--- The object behaves like a numerically indexed table.
---@class pandoc.types.Version
---@field [integer] integer
local Version = {}

--- Raise an error message if the actual version is older than the expected version.
---@param actual pandoc.VersionSpec Actual version
---@param expected pandoc.VersionSpec Expected version
---@param error_message? string #
---    Optional error message template. The string is used as format string, with the expected and actual versions as arguments.
function Version.must_be_at_least(actual, expected, error_message) end

--- Internal pandoc and utility functions
---@class pandoc.utils
local utils = {}

--- Squash a list of blocks into a list of inlines.
---@param blocks pandoc.Blocks Blocks to flatten
---@param sep? pandoc.Inline[] Separator between blocks
---@return pandoc.Inlines inlines Flattened inlines
function utils.blocks_to_inlines(blocks, sep) end

--- Process citations in a document.
---@param doc pandoc.Pandoc Document to process
---@return pandoc.Pandoc processed Document with processed citations
function utils.citeproc(doc) end

--- Test equality of AST elements (deprecated, use == instead).
---@deprecated Use == operator instead
---@param a any First element
---@param b any Second element
---@return boolean equal True if elements are equal
function utils.equals(a, b) end

--- Convert a SimpleTable to a Table.
---@param simple pandoc.SimpleTable Simple table to convert
---@return pandoc.Table table Regular table
function utils.from_simple_table(simple) end

--- Convert blocks into sections with divs.
---@param number_sections boolean Whether section `divs` should get an additional number attribute containing the section number.
---@param baselevel? integer Shift top-level headings to this level
---@param blocks pandoc.Blocks Blocks to sectionize
---@return pandoc.Blocks sections Blocks with section divs
function utils.make_sections(number_sections, baselevel, blocks) end

--- Parse and normalize a date string to YYYY-MM-DD format.
---@param date_string string Date string to normalize
---@return string? normalized Normalized date or nil if parsing failed
function utils.normalize_date(date_string) end

--- Get bibliography references from a document.
---@param doc pandoc.Pandoc Document to extract references from
---@return table[] references List of reference objects
function utils.references(doc) end

--- Run a JSON filter on a document.
---@param doc pandoc.Pandoc Document to filter
---@param filter string Filter to run
---@param args? string[] Arguments to pass to filter
---@return pandoc.Pandoc filtered Filtered document
function utils.run_json_filter(doc, filter, args) end

--- Run a Lua filter on a document.
---@param doc pandoc.Pandoc Document to filter
---@param filter string Filesystem path of filter to run
---@param env? table Environment to load and run the filter in
---@return pandoc.Pandoc filtered Filtered document
function utils.run_lua_filter(doc, filter, env) end

--- Calculate SHA1 hash of a string.
---@param content string Content to hash
---@return string hash SHA1 hexdigest
function utils.sha1(content) end

--- Extract plain text from an element, removing all formatting.
---@param element pandoc.Pandoc|pandoc.Meta|pandoc.Block|pandoc.Inline Element to stringify
---@return string text Plain text content
function utils.stringify(element) end

--- Convert a number to Roman numerals.
---@param n integer Number to convert (positive integer below 4000)
---@return string roman Roman numeral representation
function utils.to_roman_numeral(n) end

--- Convert a Table to a SimpleTable.
---@param table pandoc.Table Table to convert
---@return pandoc.SimpleTable simple Simple table
function utils.to_simple_table(table) end

--- Pandoc-friendly version of Lua’s default type function,
--- returning type information similar to what is presented in the manual.
---@param obj any Value to check
---@return string type_name Type of the given value
function utils.type(obj) end

-- Custom pandoc writer to transform docstrings into somewhat valid vim help snippets
-- for rendering API docs.
--
-- Reason: The included writer does not handle links gracefully and panvimdoc targets whole files.
--         The use case is very specific, so it's better to be able to tweak parsing.
--
-- Somewhat opinionated:
--   * Headers are stripped
--   * Inline text is balance-wrapped
--
-- Inspired by https://github.com/kdheepak/panvimdoc.
-- Most complete reference: https://github.com/nanotee/vimdoc-notes
--
-- NOTE: Not intended to render full documents! Primary target are docstring snippets.

MAXWIDTH = 78

PANDOC_VERSION:must_be_at_least("3.0")

local lo = pandoc.layout
local current_indent = 0

---@generic Args, Rets
---@param ctx {indent: integer} Context modifications to apply during `fn`.
---@param fn fun(...: Args...): Rets... Inner function to run
---@param ... Args... Arguments to pass to `fn`
---@return Rets... inner_rets Variadic returns of `fn`
local function with(ctx, fn, ...)
  current_indent = current_indent + ctx.indent
  ---@diagnostic disable-next-line: assign-type-mismatch
  local rets = table.pack(fn(...))
  current_indent = current_indent - ctx.indent
  if (rets.n or 0) == 0 then return end
  ---@cast rets.n -?
  ---@diagnostic disable-next-line: param-type-not-match
  return table.unpack(rets, 1, rets.n)
end

local function dump_table(tbl)
  local ret = {}
  for key, value in pairs(tbl) do
    if type(value) == "table" then
      ret[#ret + 1] = tostring(key) .. " = " .. dump_table(value)
    else
      ret[#ret + 1] = tostring(key) .. " = " .. tostring(value)
    end
  end
  return "\n" .. table.concat(ret, "\n")
end

--- Return a balanced paragraph. Balancing includes the last line by default.
---@param words string[] Paragraph as list of non-whitespace strings to balance.
---@param max integer Maximum line length (absolute, unless a single word breaks it)
---@param opts? {indent?: integer, soft_max?: integer, ignore_last?: boolean} #
---    Influence the balancing algorithm. Fields:
---    * indent      integer  Optionally account for indented lines (number of indent chars).
---    * soft_max    integer  Try to fit to this maximum, but consider up to `max`.
---    * ignore_last boolean  Heavily reduce penalty for last line not being balanced.
---@return string[] balanced_paragraph
local function balanced_wrap(words, max, opts)
  local n = #words
  if n == 0 then return {} end -- Don't trip on empty paragraphs
  opts = opts or {}
  local indent = opts.indent or 0
  local soft_max = opts.soft_max or max -- preferred width

  -- Pre-calculate absolute length of concatenated words 1 to n (== #words).
  -- This allows to quickly derive word-boundary substring lengths.
  local cumulative_word_chars_at = {} ---@type integer[]
  for i = 1, n do
    cumulative_word_chars_at[i] = (cumulative_word_chars_at[i - 1] or 0) + #words[i]
  end

  --- Calculate total substring length of words i to j (inclusive),
  --- including separating spaces.
  ---@param i integer First word to include
  ---@param j integer Last word to include
  ---@return integer length Sum of characters in words i to j + separating spaces
  local function line_length(i, j)
    if i > j then return 0 end
    ---@diagnostic disable-next-line: need-check-nil
    -- Number of word chars of words i to j equals the difference of absolute length at word j
    -- to absolute length before word i.
    local word_char_cnt = cumulative_word_chars_at[j] - (cumulative_word_chars_at[i - 1] or 0)
    ---@cast word_char_cnt integer
    -- Spaces are not included in the above count.
    -- Example: If we're calculating substring length of word i=3 to j=5, we have
    -- 3 words in total (3, 4, 5) separated by 5-3 = 2 spaces.
    return word_char_cnt + j - i + indent
  end

  -- These arrays keep a running tally of the best break points.
  -- optimal_partner_of[y] => Best place x to start the line ending at word y (the line thus equals the concatenation of words x to y).
  local optimal_partner_of = {} ---@type table<integer,integer>
  -- We define cost as the sum of all penalties of a given list of break points,
  -- which is the value we want to minimize.
  -- In `min_cost[y]`, we track this minimum possible sum of penalties for breaking
  -- words 1 to y into a number of lines of which the last one includes y as the final word.
  -- The corresponding starting point (the index of the word that achieved this value)
  -- is remembered in `optimal_partner_of` above.
  -- This min_cost is not just the undesirability of the line x to y, it also considers the other
  -- side of the coin (beginning a line at x means we're forcing a break at x - 1,
  -- which might not be ideal, even if the line resulting from x to y is).
  -- TLDR: min_cost[j] gives the minimum total penalty for breaking words 1 to j,
  --       the value we want to minimize. When we find a lower cost, we
  --       save the index of the first word of the line in `optimal_parner_of`.
  local min_cost = { [0] = 0 } ---@type table<integer,number>

  -- For each word with index j in our list, measure the cost of creating a break there.
  -- In theory, we're testing all continuous and ordered combinations of words from 1 to j which include j.
  -- In practice, we can exclude previously found to be invalid low i in later j
  -- iterations because the line length increases monotonically with j.
  -- In simpler terms: Try all possible starting positions for the line ending at j.
  local min_valid_i = 1 -- Keep track of minimum sensible i.

  for j = 1, n do
    min_cost[j] = math.huge
    local is_last_line = j == n
    local base_penalty_factor = 1 ---@type number
    -- Don't punish short last lines as much if requested
    if is_last_line and opts.ignore_last then base_penalty_factor = 0.01 end

    -- Iterate i backward so we can break early when the line exceeds max.
    for i = j, min_valid_i, -1 do
      local len = line_length(i, j)
      if len > max then
        -- Remember to skip this i in future j loops, the line length would only increase further.
        -- We can exit since lower i would only yield longer lines.
        min_valid_i = i + 1
        if i ~= j then break end -- allow breaking max if a single word is too long
      end
      local penalty_factor = base_penalty_factor
      --- Penalty measures undesirability of creating a line out of words i to j,
      --- just focusing on the deviation of the produced line length from the desired maximum line length.
      --- Does not consider the other side of the coin (we're cutting something into two parts after all).
      local slack = soft_max - len
      if slack < 0 then
        -- This means a soft_max lower than max was specified.
        -- Introduce bias in favor of lines shorter than soft_max.
        slack = slack * -2
        if is_last_line then
          -- We want to allow the last line to be shorter than
          -- the intended width, not longer.
          penalty_factor = 1
        end
      end
      local myopic_penalty = slack * slack * slack * penalty_factor
      -- Starting a line at i necessarily means we're creating a line that ends at i - 1.
      -- The actual cost of starting a line at i should consider this side effect.
      -- Since i <= j implies (i - 1) < j, we can conclude we already calculated
      -- the minimum undesirability of breaking at i - 1 in a previous outer loop, which
      -- in turn means we can perform a single extra calculation to account for all externalities:
      -- Since (i - 1)'s undesirability accounts for the same, we're actually considering
      -- the complete chain reaction (~ all resulting previous lines).
      local macroscopic_cost = min_cost[i - 1] + myopic_penalty
      if macroscopic_cost < min_cost[j] then -- we found a better partner for j
        min_cost[j] = macroscopic_cost
        optimal_partner_of[j] = i
      end
    end
  end

  -- Reconstruct all lines backwards, starting with the last word
  -- since it must be at the end of a line. This implies we're optimizing for
  -- balancing all lines, including the last one (which is typically ignored).
  -- Artificially reducing the penalties for combinations where j == n would
  -- allow to exclude the last line from balancing/limiting its effect on it.
  local lines = {}
  local last_word_of_current_line = n
  while last_word_of_current_line > 0 do
    -- Look up optimal partner
    local first_word_of_current_line = optimal_partner_of[last_word_of_current_line]
    -- Aggregate words in current line
    local line_words = {}
    for i = first_word_of_current_line, last_word_of_current_line do
      line_words[#line_words + 1] = words[i]
    end
    -- We're reconstructing backwards, so insert in front of all previous lines
    table.insert(lines, 1, table.concat(line_words, " "))
    -- The previous line must end one word before the word this one started with.
    last_word_of_current_line = first_word_of_current_line - 1
  end

  return lines
end

--- Join list items with a separator.
---@param tbl (string|pandoc.Doc)[]|pandoc.List<pandoc.Doc>
---@param sep? string|pandoc.Doc Join items with this separator. Defaults to `\n`.
---@return pandoc.Doc
local function join(tbl, sep)
  return lo.concat(tbl, sep or "\n")
end

---@param s string|pandoc.Doc
---@param pre string
---@param post? string
---@return pandoc.Doc
local function wrap(s, pre, post)
  post = post or pre
  if type(s) == "string" then s = lo.literal(s) end
  return s:inside(pre, post)
end

---@param text string|pandoc.Doc
---@param width? integer
---@param opts? {indent?: integer, soft_max?: integer, ignore_last?: boolean} #
---    Influence the balancing algorithm. Fields:
---    * indent      integer  Optionally account for indented lines (number of indent chars).
---    * soft_max    integer  Try to fit to this maximum, but consider up to `max`.
---    * ignore_last boolean  Heavily reduce penalty for last line not being balanced.
---@return pandoc.Doc
local function wrapParagraph(text, width, opts)
  local words = {}
  text = tostring(text)
  width = width or MAXWIDTH
  opts = opts or {}
  local buf = {}
  local nobreak = false
  for word in text:gmatch("%S+") do
    -- Avoid breaking `literal stuff` (should be on the same line)
    local _, cnt = word:gsub("`", "")
    if cnt and (cnt % 2) ~= 0 then
      table.insert(buf, word)
      nobreak = not nobreak
      if not nobreak then
        table.insert(words, table.concat(buf, " "))
        buf = {}
      end
    elseif nobreak then
      table.insert(buf, word)
    else
      table.insert(words, word)
    end
  end
  if #buf > 0 then table.insert(words, table.concat(buf, " ")) end
  opts.ignore_last = true
  local lines = balanced_wrap(words, width, opts)
  return join(lines)
end

--- Get an iterator over lines. By default, cuts empty lines.
---@param s pandoc.Doc|string
---@param preserve_empty? boolean Preserve empty lines. Defaults to false. When true, always adds an empty line at the end.
---@return fun(): string?
local function liter(s, preserve_empty)
  s = tostring(s)
  if preserve_empty then
    return s:gmatch("([^\r\n]*)\r?\n?")
  else
    return s:gmatch("[^\r\n]+")
  end
end

--- Get an iterator over lines. By default, cuts empty lines.
---@param s pandoc.Doc|string
---@param preserve_empty? boolean Preserve empty lines. Defaults to false. When true, always adds an empty line at the end.
---@return string[]
local function splitlines(s, preserve_empty)
  local lines = {}
  for line in liter(s, preserve_empty) do
    lines[#lines + 1] = line
  end
  if preserve_empty and lines[#lines + 1] == "" then lines[#lines] = nil end
  return lines
end

---@param s string|pandoc.Doc
---@param prefix string
---@return boolean
local function startswith(s, prefix)
  return string.sub(tostring(s), 1, #prefix) == prefix
end

---@param s string|pandoc.Doc
---@param suffix string
---@return boolean
local function endswith(s, suffix)
  return suffix == "" or string.sub(tostring(s), -#suffix) == suffix
end

local function lstrip(s, chars)
  return string.match(s, "^[" .. chars .. "]*(.-)$")
end

local function rstrip(s, chars)
  return string.match(s, "^(.-)[" .. chars .. "]*$")
end

local function strip(s, chars)
  return string.match(s, "^[" .. chars .. "]*" .. "(.-)[" .. chars .. "]*$")
end

-- patterns are anchored to the start automatically
local codeblock_start = re.compile([['>'%a^-7!.]])
local codeblock_end = re.compile([[%s*'<'!.]])

--- Forcefully format lines in a string, e.g. for a list item.
---@param s pandoc.Doc|string
---@param default_indent string Indent lines with this string
---@param first_indent? string Use a different indent for the first line. Defaults to `indent`.
---@param keep_trailing_nl? bool
---@return pandoc.Doc indented
local function indent(s, default_indent, first_indent, keep_trailing_nl)
  local ret = {}
  local did_first
  local trailing_newlines = 0
  if keep_trailing_nl ~= false then trailing_newlines = #(tostring(s):match("(\n+)$") or "") end
  for line in liter(s, true) do
    if not did_first then
      ret[#ret + 1] = (first_indent or default_indent) .. line
      did_first = true
    elseif line == "" or codeblock_end:match(line) then
      -- Don't indent empty lines or code block endings (not hidden otherwise).
      -- The latter is a hack, consider better methods.
      ret[#ret + 1] = line
    elseif codeblock_start:match(line) then
      for i = #ret, 1, -1 do
        if ret[i] ~= "" then
          ret[i] = ret[i] .. " " .. line
          if i < #ret then
            for j = i + 1, #ret do
              ret[j] = nil
            end
          end
          break
        elseif i == 1 then
          ret[i] = line
        end
      end
    else
      ret[#ret + 1] = default_indent .. line
    end
  end
  return join(ret) .. lo.blanklines(trailing_newlines)
end

---@param cols [string, string]
---@param left_width integer
---@param opts? {wraplines?: boolean, sep?: string}
---@return pandoc.Doc
local function to_cols(cols, left_width, opts)
  opts = opts or {}
  local sep, sepl, left, right
  if opts.wraplines then
    sep = opts.sep or "  "
    sepl = #sep
    left, right =
      pandoc.List(splitlines(wrapParagraph(cols[1], left_width), true)),
      pandoc.List(splitlines(cols[2], true))
  else
    left, right = pandoc.List(splitlines(cols[1], true)), pandoc.List(splitlines(cols[2], true))
    sep = opts.sep or ""
    sepl = #sep
  end
  local sep_visible = sepl > 0 and sep:find("%S")
  local buf = {}
  local li, ri = 1, 1
  local lm, rm = #left, #right
  while li <= lm or ri <= rm do
    local ll, rl = left[li] or "", right[ri] or ""
    local pad = left_width - #ll
    assert(pad >= 0, "Width of left column is too small!")
    if #rl > 0 and (#ll > 0 and codeblock_start:match(ll) or codeblock_start:match(rl)) then
      if codeblock_start:match(ll) then
        buf[#buf] = buf[#buf] ~= "" and ((buf[#buf] .. " ") or "") .. ll
        while li < lm and not codeblock_end:match(ll) do
          li = li + 1
          ll = left[li]
          buf[#buf + 1] = ll
        end
        li = li + 1
        ll = left[li] or ""
      else
        buf[#buf] = buf[#buf] ~= "" and ((buf[#buf] .. " ") or "") .. rl
        while ri < rm and not codeblock_end:match(rl) do
          ri = ri + 1
          rl = right[ri]
          -- unsure if code blocks should be indented correctly
          -- or break the flow
          -- buf[#buf + 1] = rl
          buf[#buf + 1] = (" "):rep(left_width + sepl) .. rl
        end
        if ri < rm or codeblock_end:match(buf[#buf]) then buf[#buf] = "<" end
        ri = ri + 1
        rl = right[ri] or ""
      end
    end
    if #rl > 0 then
      buf[#buf + 1] = ll .. (" "):rep(left_width - #ll) .. sep .. rl
    elseif sep_visible then
      buf[#buf + 1] = ll .. (" "):rep(left_width - #ll) .. rstrip(sep, "%s")
    else
      buf[#buf + 1] = ll
    end
    li, ri = li + 1, ri + 1
  end
  return join(buf)
end

Writer = pandoc.scaffolding.Writer

---@param inlines pandoc.Inline[]|pandoc.List<pandoc.Inline>
local function dump_inlines(inlines)
  if inlines.map == nil then
    inlines = pandoc.List(inlines --[[@as pandoc.Inline[] ]])
  end
  ---@cast inlines pandoc.List<pandoc.Inline>
  local parts = inlines:map(Writer.Inline)
  return lo.concat(parts)
end

---@param blocks pandoc.Block[]|pandoc.List<pandoc.Block>
---@param sep? string|pandoc.Doc
local function dump_blocks(blocks, sep)
  if blocks.map == nil then
    blocks = pandoc.List(blocks --[[@as pandoc.Block[] ]])
  end
  ---@cast blocks pandoc.List<pandoc.Block>
  local parts = blocks:map(Writer.Block)
  return lo.concat(parts, sep)
end

---@param el pandoc.Para
---@param width? integer
---@return pandoc.Doc
local function dump_para(el, width)
  ---@diagnostic disable-next-line: return-type-mismatch
  return wrapParagraph(dump_inlines(el.content), width, { indent = current_indent }) .. lo.blankline
end

---@param el pandoc.Plain
---@param width? integer
---@return pandoc.Doc
local function dump_plain(el, width)
  return wrapParagraph(dump_inlines(el.content), width, { indent = current_indent })
end

Writer.Pandoc = function(doc, opts)
  MAXWIDTH = opts.columns or MAXWIDTH
  return dump_blocks(doc.blocks)
end

Writer.Block.Header = function(el)
  -- Force all headers into a basic one.
  return ("%s ~"):format(dump_inlines(el.content)) .. lo.blankline
end

Writer.Block.Para = function(el)
  -- Otherwise than just regular paragraphs, e.g. used in list items
  -- of a list where at least one item contains another block element
  -- such as a code block
  return dump_para(el, MAXWIDTH)
end

Writer.Block.OrderedList = function(el)
  local ind = #(tostring(#el.content))
  local items = with({ indent = ind }, function()
    return el.content:map(function(it)
      -- Can't map directly because the index is passed as the second argument,
      -- which is used as the separator to join blocks
      return dump_blocks(it)
    end)
  end)
  local list = {}
  for i, it in ipairs(items) do
    local add_ind = ind - #tostring(i)
    list[i] = indent(it, (" "):rep(ind + 2), ("%s. "):format(i) .. (" "):rep(add_ind), false)
  end
  return lo.blanklines(0) .. join(list) .. lo.blankline
end

Writer.Block.BulletList = function(el)
  local items = with({ indent = 2 }, function()
    return el.content:map(function(it)
      return indent(dump_blocks(it), "  ", "• ", false)
      -- Alternative (does not handle code blocks correctly though):
      -- return dump_blocks(it):hang(2, "• ")
    end)
  end)
  return lo.blanklines(0) .. lo.concat(items, lo.blanklines(0)) .. lo.blankline
end

local dl_sepwidth = 8

Writer.Block.DefinitionList = function(dl)
  local longest_dt = 0
  ---@type pandoc.List<[pandoc.Doc, pandoc.Blocks]>
  local buf = dl.content:map(function(it)
    ---@cast it [pandoc.Inlines, pandoc.List<pandoc.Blocks>]
    local dt = dump_inlines(it[1])
    local dt_len = #tostring(dt)
    if dt_len > longest_dt then longest_dt = dt_len end
    -- One term can have multiple definitions, but ignore that for now
    local dd_blocks = it[2][1]
    ---@cast dd_blocks pandoc.Blocks
    -- Render blocks later once we know how much space we have for wrapping accordingly.
    -- Cannot wrap the rendered dd because it might contain code blocks etc.
    return { dt, dd_blocks }
  end)

  local dd_width = MAXWIDTH - longest_dt - dl_sepwidth
  ---@type pandoc.List<pandoc.Doc>
  local dl_pairs = buf:map(function(it)
    ---@type pandoc.List<pandoc.Doc>
    local dd_blocks_rend = it[2]:map(
      ---@return pandoc.Doc
      function(el)
        if el.tag == "Para" then
          return dump_para(el, dd_width)
        elseif el.tag == "Plain" then
          return dump_plain(el, dd_width)
        else
          return Writer.Block(el)
        end
      end
    )
    return to_cols({ tostring(it[1]), tostring(join(dd_blocks_rend)) }, longest_dt + dl_sepwidth)
  end)

  return join(dl_pairs, lo.blankline) .. lo.blankline
end

Writer.Block.CodeBlock = function(el)
  local attr = el.attr
  if #attr.classes > 0 and attr.classes[1] == "vimdoc" then
    return el.text .. lo.blankline
  else
    local lang = attr.classes[1] or ""
    local indented = lo.literal(el.text):nest(4)
    return lo.blanklines(0) .. indented:inside(">" .. lang .. "\n", "\n<") .. lo.blanklines(0)
  end
end

Writer.Inline.Str = function(el)
  local s = el.text
  if startswith(s, "(http") and endswith(s, ")") then
    return wrap(string.sub(s, 2, #s - 2), " <", ">")
  else
    return s
  end
end

Writer.Inline.Space = " "
Writer.Inline.SoftBreak = "\n"
Writer.Inline.LineBreak = "\n"
Writer.Inline.Image = ""
Writer.Inline.RawInline = ""

Writer.Inline.Emph = function(el)
  return wrap(dump_inlines(el.content), "_")
end

Writer.Inline.Strong = function(el)
  local text = dump_inlines(el.content)
  if tostring(text):find("%s") then
    return wrap(text, "__", "__")
  else
    return wrap(text, "{", "}")
  end
end

Writer.Inline.Subscript = function(el)
  return "_" .. dump_inlines(el.content)
end

Writer.Inline.Superscript = function(el)
  return "^" .. dump_inlines(el.content)
end

Writer.Inline.SmallCaps = function(el)
  return dump_inlines(el.content)
end

Writer.Inline.Strikeout = function(el)
  return wrap(dump_inlines(el.content), "~")
end

Writer.Inline.Link = function(el)
  local s = dump_inlines(el.content)
  local tgt = el.target
  if startswith(tgt, "https://neovim.io/doc/") then
    return wrap(s, "|")
  elseif startswith(tgt, "#") then
    return s .. " |" .. tgt:lower():sub(2):gsub("%s", "-") .. "|"
  elseif startswith(s, "http") then
    return wrap(s, "<", ">")
  else
    return s .. wrap(tgt, " <", ">")
  end
end

Writer.Inline.Code = function(el)
  local vim_help = el.text:match("^:h %s*([^%s]+)$")
  if vim_help then return wrap(vim_help, "|") end
  local vim_opt = el.text:match("^'([^%s]+)'$")
  if vim_opt then return wrap(vim_opt, "'") end
  return wrap(el.text, "`")
end

Writer.Inline.Math = function(el)
  return wrap(el.text, "`")
end

Writer.Inline.Quoted = function(el)
  if el.quotetype == "DoubleQuote" then
    return wrap(dump_inlines(el.content), '"')
  else
    return wrap(dump_inlines(el.content), "'")
  end
end

Writer.Inline.Note = function(el)
  return dump_blocks(el.content, lo.blanklines(0))
end

Writer.Inline.Span = function(el)
  return dump_inlines(el.content)
end

-- Writer.Inline.Null = ""
-- Writer.Inline.Citation = function(el)
--   return el
-- end
--
Writer.Inline.Cite = function(el)
  return dump_inlines(el.content)
end

Writer.Block.Plain = function(el)
  -- e.g. used in list items of lists that don't contain other elements like code blocks
  return wrapParagraph(dump_inlines(el.content), nil, { indent = current_indent })
end

Writer.Block.RawBlock = ""

Writer.Block.Table = function(el)
  return pandoc.write(pandoc.Pandoc({ el }), "plain")
end

Writer.Block.Div = "\n"

Writer.Block.Figure = function(el)
  return dump_blocks(el.content)
end

Writer.Block.BlockQuote = function(el)
  return lo.blankline .. dump_blocks(el.content):prefixed("  > ") .. lo.blankline
end

Writer.Block.HorizontalRule = function()
  return lo.blankline .. ("-"):rep(MAXWIDTH) .. lo.blankline
end

Writer.Block.LineBlock = function(el)
  local res = join(el.content:map(function(it)
    return dump_inlines(it)
  end))
  return lo.blankline .. res:prefixed("| ") .. lo.blankline
  -- Alternative:
  -- return lo.blankline .. lo.vfill("| ") .. res:lblock(MAXWIDTH) .. lo.blankline
end

Template = pandoc.template.default("vimdoc")

# OK, hi!

Let's try this with a regular Markdown document. Maybe this allows me to see the elements as they arrive. Does wrapping work here? Probably not - now it does.

def_term
: This is a short description of `def_term`.

another_term
: This is a longer description of `another_term` with inline code. I'm unsure how this should wrap properly rn, lemme check

     ```lua
     local foo = "bar"
     local bar = foo
     ```

## Trying to break literals

- **notify_opts**? `table`

  Some basic options to pass to `vim.notify`. Defaults to `{ title = "Continuity"}`

## From the other template

Example:

```lua
local foo = true
```

- foo is **bold**
- bar is _italic_
- create a [hyperlink](#target)
- so, what happens with reaaaaaaally long lines? are they wrapped automatically or do I have to do something? just for the lulz, it seems I have to do something, but let's try anyways

Ok, it seems I need to do it manually and it currently only works for paragraphs of course, right? This should be wrapped, right? Hopefully not in between words...

1. See vim help: `:h marks`

   ```lua
   local bufname = vim.api.nvim_buf_get_name(0) -- Code blocks should not be wrapped at all

   local othername = bar
   ```

1. See vim opt: `'shiftwidth'`

   ```
   Ensure regular code blocks work the same as those with language hints
   ```

1. Just ensure that long lines are wrapped for numbered lists as well because it would be dumb if not
1. also
1. check
1. that
1. long
1. numbered
1. lists
1. are
1. indented
1. correctly

## Note:

- Currently this doesn't support "scripting" multiple mouse events by calling it multiple times in a loop: the intermediate mouse positions will be ignored. It should be used to implement real-time mouse input in a GUI. The deprecated pseudokey form (`<LeftMouse><col,row>`) of [nvim_input][] has the same limitation.

### Check what happens when trying list with code

- A looooong ass text before this should make this break, but still indent the code correctly. This is an example code:
  ```lua
  local bufname = vim.api.nvim_buf_get_name(0)
  ```
- Another item with `inline` code and not linking [Note][] lol

## Now nested lists

- Note the following stuff:
  - Foo
  - Bar
  - Baz
    - quux
    - And can I get over the line limit here? Lorem ipsum blablabla hi there nice to meet you what are you doing?
      And add code blocks?
      ```yaml
      # no wrapping should take place here as well, even though we're probably very much past the limit
      foo:
        bar:
          baz: true
      ```

1. Not this:
   - a
   - b
   - c
2. Or this:
   1. A
   2. B
   3. C

| Now try a lineblock
| what is this? _lol_

Right Left Center Default

---

     12     12        12            12
    123     123       123          123
      1     1          1             1

> Now do whatever this is
> and something else
> OK dummy, it's a blockquote. Does it get wrapped automatically if it exceeds the line length?

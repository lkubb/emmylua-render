from textwrap import dedent

import pytest

from emmylua_render.jinja import render_template_str


def render(md) -> str:
    return render_template_str("{{ md | vimdoc }}", {"md": md})


@pytest.mark.parametrize("level", range(1, 6))
def test_heading(level):
    text = f"{'#' * level} OK, hi!"
    rendered = render(text)
    assert rendered == "OK, hi! ~\n"


def test_para():
    text = "Let's try this with a regular Markdown document. Maybe this allows me to see the elements as they arrive. Does wrapping work here? Probably not - now it does."
    rendered = render(text)
    assert rendered.replace("\n", " ").replace("’", "'").strip() == text
    assert all(len(line) <= 78 for line in rendered.splitlines())


def test_link():
    text = "[some description](#link-target)"
    rendered = render(text)
    assert rendered == "some description |link-target|\n"


def test_vimhelp_link():
    text = "`:h foobar`"
    rendered = render(text)
    assert rendered == "|foobar|\n"


def test_vimhelp_opt():
    text = "`'foobar'`"
    rendered = render(text)
    assert rendered == "'foobar'\n"


def test_deflist():
    text = dedent(
        """
        def_term
        : This is a short description of `def_term`.

        another_term
        : This is a longer description of `another_term` with inline code. I'm unsure how this should wrap properly rn, lemme check

             ```lua
             local foo = "bar"
             local bar = foo
             ```
        """
    )
    expected = dedent(
        """
        def_term            This is a short description of `def_term`.

        another_term        This is a longer description of `another_term` with
                            inline code. I’m unsure how this should wrap
                            properly rn, lemme check >lua
                                local foo = "bar"
                                local bar = foo
        <
        """
    ).lstrip()
    rendered = render(text)
    assert all(len(line) <= 78 for line in rendered.splitlines())
    assert rendered == expected


def test_code_block():
    text = dedent(
        """
        Example:

        ```lua
        local foo = true
        ```
        """
    )
    expected = dedent(
        """
        Example:

        >lua
            local foo = true
        <
        """
    ).lstrip()
    rendered = render(text)
    assert rendered == expected


def test_heavy_em():
    text = "**Foobar**"
    rend = render(text)
    assert rend == "{Foobar}\n"


def test_em():
    text = "*Foobar*"
    rend = render(text)
    assert rend == "_Foobar_\n"


@pytest.mark.parametrize("style", ("*", "-"))
def test_flat_unordered_list(style):
    text = dedent(
        """
        {style} foo is **bold**
        {style} bar is _italic_
        {style} create a [hyperlink](#target)
        {style} so, what happens with reaaaaaaally long lines? are they wrapped automatically or do I have to do something? just for the lulz, it seems I have to do something, but let's try anyways
        {style} A looooong ass text before this should make this break, but still indent the code correctly. This is an example code:
          ```lua
          local bufname = vim.api.nvim_buf_get_name(0)
          ```
        {style} Another item with `inline` code and not linking [Note][] lol
        """.format(style=style)
    )
    expected = dedent(
        """
        • foo is {bold}
        • bar is _italic_
        • create a hyperlink |target|
        • so, what happens with reaaaaaaally long lines? are they wrapped
          automatically or do I have to do something? just for the lulz, it
          seems I have to do something, but let’s try anyways
        • A looooong ass text before this should make this break, but still
          indent the code correctly. This is an example code: >lua
              local bufname = vim.api.nvim_buf_get_name(0)
        <
        • Another item with `inline` code and not linking [Note][] lol
        """
    ).lstrip()
    rend = render(text)
    assert rend == expected


def test_flat_ordered_list():
    text = dedent(
        """
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
        """
    )
    expected = dedent(
        """
        1.  See vim help: |marks| >lua
                local bufname = vim.api.nvim_buf_get_name(0) -- Code blocks should not be wrapped at all

                local othername = bar
        <
        2.  See vim opt: 'shiftwidth' >
                Ensure regular code blocks work the same as those with language hints
        <
        3.  Just ensure that long lines are wrapped for numbered lists as well
            because it would be dumb if not
        4.  also
        5.  check
        6.  that
        7.  long
        8.  numbered
        9.  lists
        10. are
        11. indented
        12. correctly
        """
    ).lstrip()
    rend = render(text)
    assert rend == expected


def test_nested_unordered_list():
    text = dedent(
        """
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

        """
    )
    expected = dedent(
        """
        • Note the following stuff:
          • Foo
          • Bar
          • Baz
            • quux
            • And can I get over the line limit here? Lorem ipsum blablabla hi
              there nice to meet you what are you doing? And add code blocks? >yaml
                  # no wrapping should take place here as well, even though we're probably very much past the limit
                  foo:
                    bar:
                      baz: true
        <
        """
    ).lstrip()
    rend = render(text)
    assert rend == expected


def test_nested_ordered_list():
    text = dedent(
        """
        1. Not this:
           1. a
           1. b
           1. c
        1. Or this:
           1. A
           1. B
           1. C
        """
    )
    expected = dedent(
        """
        1. Not this:
           1. a
           2. b
           3. c
        2. Or this:
           1. A
           2. B
           3. C
        """
    ).lstrip()
    rend = render(text)
    assert rend == expected


def test_nested_mixed_list():
    text = dedent(
        """
        1. Not this:
           * a
           * b
           * c
        1. Or this:
           - A
           - B
           - C

        * Neither this:
          1. a
          1. b
          1. c
        * Nor this:
          1. A
          1. B
          1. C
        """
    )
    expected = dedent(
        """
        1. Not this:
           • a
           • b
           • c
        2. Or this:
           • A
           • B
           • C

        • Neither this:
          1. a
          2. b
          3. c
        • Nor this:
          1. A
          2. B
          3. C
        """
    ).lstrip()
    rend = render(text)
    assert rend == expected


def test_lineblock():
    text = dedent(
        """
        | Now try a lineblock
        | what is this? _lol_
        """
    )
    assert render(text) == text.lstrip()


def test_table():
    text = dedent(
        """
          Right     Left     Center     Default
        -------     ------ ----------   -------
             12     12        12            12
            123     123       123          123
              1     1          1             1
        """
    )
    expected = """\
    Right Left    Center  Default
  ------- ------ -------- ---------
       12 12        12    12
      123 123      123    123
        1 1         1     1
    """.rstrip(" ")
    assert render(text) == expected


def test_blockquote():
    text = dedent(
        """
        > Now do whatever this is
        > and something else
        > OK dummy, it's a blockquote. Does it get wrapped automatically if it exceeds the line length?
        """
    )
    expected = """\
  > Now do whatever this is and something else OK dummy, it’s a
  > blockquote. Does it get wrapped automatically if it exceeds the line
  > length?
    """.rstrip(" ")
    assert render(text) == expected

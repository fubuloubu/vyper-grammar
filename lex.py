from itertools import chain as _chain
from more_itertools import peekable as _peekable
from sly.lex import (
    Lexer as _Lexer,
    Token as _Token,
)


class VyperToken(_Token):
    __slots__ = _Token.__slots__ + ("colno",)

    def __init__(self):
        super().__init__()
        self.colno = 0


# Compute column.
#     input is the input text string
#     token is a token instance
def _find_column(text, token):
    last_cr = text.rfind("\n", 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = (token.index - last_cr) + 1
    return column


class VyperLexer(_Lexer):
    tokens = {
        NAME,
        STRING,
        DOCSTR,
        DEC_NUM,
        HEX_NUM,
        OCT_NUM,
        BIN_NUM,
        FLOAT,
        BOOL,
        IMPORT,
        FROM,
        DOT,
        AS,
        DEF,
        IF,
        ELIF,
        ELSE,
        FOR,
        IN,
        ARROW,
        AND,
        OR,
        NOT,
        XOR,
        SHL,
        SHR,
        ADD,
        SUB,
        MUL,
        DIV,
        POW,
        MOD,
        AUGADD,
        AUGSUB,
        AUGMUL,
        AUGDIV,
        AUGPOW,
        AUGMOD,
        EQ,
        NE,
        LT,
        LE,
        GT,
        GE,
        SKIP,
        PASS,
        BREAK,
        CONTINUE,
        LOG,
        EVENT,
        RETURN,
        RAISE,
        ASSERT,
        UNREACHABLE,
        STRUCT,
        INTERFACE,
        INDENT,
        DEDENT,
        ENDSTMT,  # Added during post-processing
        TAB,
        SPACE,
        NEWLINE,  # Discarded after post-processing
    }

    literals = {
        "=",
        ",",
        ":",
        "@",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
    }

    # Tokens

    @_("|".join([r'"""(.|\s)*"""', r"'''(.|\s)*'''"]))
    def DOCSTR(self, t):
        # Docstrings are multiline
        self.lineno += max(t.value.count("\n"), t.value.count("\r"))
        return t

    STRING = "|".join([r'"(?!"").*"', r"'(?!" ").*'"])

    HEX_NUM = r"0x[\da-f]*"
    OCT_NUM = r"0o[0-7]*"
    BIN_NUM = r"0b[0-1]*"
    FLOAT = r"((\d+\.\d*|\.\d+)(e[-+]?\d+)?|\d+(e[-+]?\d+))"
    DEC_NUM = r"0|[1-9]\d*"

    ARROW = "->"
    SHL = "<<"
    SHR = ">>"
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="

    AUGPOW = r"\*\*="
    AUGADD = r"\+="
    AUGSUB = "-="
    AUGMUL = r"\*="
    AUGDIV = "/="
    AUGMOD = "%="

    POW = r"\*\*"
    ADD = r"\+"
    SUB = "-"
    MUL = r"\*"
    DIV = "/"
    MOD = "%"

    DOT = r"\."
    ENDSTMT = ";"  # Can either separate lines via this, or with a newline

    NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"
    # Keywords
    NAME["def"] = DEF
    NAME["if"] = IF
    NAME["else"] = ELSE
    NAME["import"] = IMPORT
    NAME["from"] = FROM
    NAME["as"] = AS
    NAME["if"] = IF
    NAME["elif"] = ELIF
    NAME["else"] = ELSE
    NAME["for"] = FOR
    NAME["in"] = IN
    NAME["_"] = SKIP
    NAME["pass"] = PASS
    NAME["break"] = BREAK
    NAME["continue"] = CONTINUE
    NAME["log"] = LOG
    NAME["return"] = RETURN
    NAME["raise"] = RAISE
    NAME["assert"] = ASSERT
    NAME["and"] = AND
    NAME["or"] = OR
    NAME["not"] = NOT
    NAME["xor"] = XOR
    NAME["True"] = BOOL
    NAME["False"] = BOOL
    NAME["UNREACHABLE"] = UNREACHABLE
    NAME["struct"] = STRUCT
    NAME["event"] = EVENT
    NAME["interface"] = INTERFACE

    @_(r"[#].*")
    def ignore_comment(self, t):
        pass  # Ignore comments

    @_(r"[\r\n]+")
    def NEWLINE(self, t):
        self.lineno += max(t.value.count("\n"), t.value.count("\r"))
        return t

    # Python tab-aware scoping is tricky to parse.
    # The below functionality is only here to aid in parsing whitespace for scoping.
    @_(r" {4}|\t")
    def TAB(self, t):
        if t.value == "\t":
            self.__using_tab_char = True
        else:
            self.__using_spaces = True

        # Can only use 4 spaces or the tab char to denote indent, not both
        if self.__using_spaces and self.__using_tab_char:
            col = _find_column(self.text, t)
            raise SyntaxError(f"Mixing tabs and spaces @ line {self.lineno}, col {col}")

        return t

    @_(r" {1,3}")
    def SPACE(self, t):
        # Only need this for parsing, discard later
        return t

    def __init__(self, *args, **kwargs):
        self.__using_tab_char = False
        self.__using_spaces = False
        super().__init__(*args, **kwargs)

    def error(self, t):
        col = _find_column(self.text, t)
        raise SyntaxError(
            f"Illegal Character {t.value[0]} @ line {self.lineno}, col {col}"
        )


# The tokens that actually get exported by tokenize() below
TOKENS = VyperLexer.tokens - {"TAB", "SPACE", "NEWLINE"}


def annotate_columns(text, tokens):
    for token in tokens:
        vy_token = VyperToken()
        vy_token.type = token.type
        vy_token.value = token.value
        vy_token.index = token.index
        vy_token.lineno = token.lineno
        vy_token.colno = _find_column(text, token)
        yield vy_token


def indent_tracker(tokens):
    """
    Filter a stream of tokens to insert INDENT and DEDENT characters
    in place of TABs and NEWLINEs depending on the indent level of the code.
    Also discard SPACEs.
    """
    # Need a peekable iterator
    tokens = _peekable(tokens)

    # Python tab-aware scoping is tricky to parse.
    # The below functionality is only here to aid in parsing whitespace for scoping.
    indent_level = 0

    for t in tokens:

        if t.type == "NEWLINE":
            starting_t = (
                t  # Keep this in case we need to abort, or there's no indent change
            )

            lvl = 0
            try:
                # Count how many tabs we have
                while tokens.peek().type == "TAB":
                    t = next(tokens)  # We know it's a tab
                    lvl += 1

                    # TAB followed by a NEWLINE is just whitespace
                    # Resetting the level and breaking allows the
                    # detection of TAB -> NEWLINE below to skip
                    # yielding a token
                    if tokens.peek().type == "NEWLINE":
                        lvl = indent_level
                        break

                    # If we have 1+ spaces after a tab, it's a problem
                    if tokens.peek().type == "SPACE":
                        raise SyntaxError(f"Misaligned indent @ line {t.lineno}")

            except StopIteration as e:
                # If token.peek() throws, dedent all the way
                lvl = 0

            # Can only indent once per line, check if one too many tabs!
            if lvl - indent_level > 1:
                raise SyntaxError(f"Too much indenting @ line {t.lineno}")
            # One ore indent than current indent level (discard the newline)
            elif lvl > indent_level:
                t.type = "INDENT"  # change TAB to INDENT (we"re skipping all the tabs)
                indent_level += 1  # increment indent by one level
                yield t

            # Less indent than current indent level (discard the newline)
            elif lvl < indent_level:
                yield t  # We want the newline
                dedent = VyperToken()  # Create a new token from the last one
                dedent.type = "DEDENT"  # Change TAB to DEDENT
                dedent.value = t.value
                dedent.index = t.index
                dedent.lineno = t.lineno
                # yield number of DEDENTs equal to the difference in levels
                missing_levels = indent_level - lvl
                for _ in range(missing_levels):
                    indent_level -= 1  # dedent by one level
                    yield dedent
            # No indent, so keep the newline
            elif t.type != "TAB":
                yield starting_t
            # TAB(s) + NEWLINE is whitespace, which we ignore

        elif t.type in ("SPACE", "TAB"):
            continue  # We don't care about spaces or tabs otherwise

        else:
            yield t  # Normal token


def collapse_unnecessary_multiline(tokens):
    """
    Filter a stream of tokens for instances where a unnecessary INDENT-DEDENT pair occurs
    and remove it. It is considered "unnecessary" if a ":" doesn't preceed the INDENT.
    Throws if it finds two INDENTs in a row under these conditions, because it was not
    inteded to handle that.
    """
    # Need a peekable iterator
    tokens = _peekable(tokens)

    for t in tokens:

        try:
            next_t = tokens.peek()
        except StopIteration as e:
            yield t  # Yield the last token no matter what
            break

        if t.type != ":" and next_t.type == "INDENT":
            # We will yield the token in the while loop, it's fine
            next(tokens)  # Skip the INDENT
            assert t.type != "DEDENT"  # DEDENT should never be followed by INDENT
            while t.type != "DEDENT":  # Look for the next DEDENT
                yield t
                try:
                    t = next(tokens)
                except StopIteration as e:
                    raise SyntaxError(
                        f"No corresponding DEDENT for INDENT: {next_t}"
                    ) from e

                if t.type == "INDENT":
                    raise SyntaxError(f"Cannot further indent here: {t}")
            # t is "DEDENT" and we want to skip it, so skip it
            continue  # This will fail to yield t
        else:
            yield t


def remove_double(tokens, token_type):
    """
    Filter a stream of tokens for instances of >1 TOKENs in a row,
    skipping all but one of them.
    """
    # Need a peekable iterator
    tokens = _peekable(tokens)

    for t in tokens:
        if t.type == token_type:
            try:
                # Ignoring comments leaves extra newlines in place
                while tokens.peek().type == token_type:
                    t = next(tokens)
            except StopIteration as e:
                pass  # Allow the last token to yield
        yield t


def skip_before(tokens, token_type, skip_before_tokens):
    """
    Filter a stream of tokens, seeing if the given token type occurs
    before any one of a given set of tokens. If it does, skip it.
    """
    # Need a peekable iterator
    tokens = _peekable(tokens)

    for t in tokens:
        if t.type == token_type:
            try:
                if tokens.peek().type in skip_before_tokens:
                    t = next(tokens)  # Skip t, yielding next token
            except StopIteration as e:
                pass  # Yield t anyways

        yield t  # Yield all tokens


def skip_after(tokens, token_type, skip_after_tokens):
    """
    Filter a stream of tokens, seeing if the given token type occurs
    after any one of a given set of tokens. If it does, skip it.
    """
    # Need a peekable iterator
    tokens = _peekable(tokens)

    for t in tokens:
        if t.type in skip_after_tokens:
            yield t  # This token is fine, so yield it
            try:
                while tokens.peek().type == token_type:
                    next(tokens)  # Skip this token
            except StopIteration as e:
                pass  # Nothing to yield
        else:
            yield t  # Doesn't matter, yield it anyways


def skip_begin(tokens, token_type):
    """
    Check if the first token is the given type,
    if it is then skip that one (and that one only)
    """
    tokens = _peekable(tokens)

    try:
        if tokens.peek().type == token_type:
            next(tokens)  # Skip the first one
    except StopIteration as e:
        return  # Empty program

    return tokens


def substitute(tokens, token_type, substitute_type):
    """
    Filter a stream of tokens looking for a particular token type and replace
    them for another type.
    """

    for t in tokens:

        if t.type == token_type:
            substitute = VyperToken()
            substitute.type = substitute_type
            substitute.value = t.value
            substitute.index = t.index
            substitute.lineno = t.lineno
            yield substitute
        else:
            yield t  # Not our target type, so yield it


def swap_order(tokens, a_type, b_type):
    """
    Filter a stream of tokens swapping the ordering of two different token
    types every time they occur.
    """
    assert a_type != b_type, "Cannot swap same type!"

    # Need a peekable iterator
    tokens = _peekable(tokens)

    for t in tokens:
        try:
            if t.type == a_type and tokens.peek().type == b_type:
                yield next(tokens)  # Swap token order
        except StopIteration as e:
            pass

        yield t


def add_last(tokens, type_to_add):
    """
    Pass-through all the tokens in the stream, appending an additional token
    of `type_to_add` to the end
    """
    for t in tokens:
        yield t

    last_t = VyperToken()
    last_t.type = type_to_add
    last_t.value = t.value
    last_t.index = t.index
    last_t.lineno = t.lineno
    yield last_t


def tokenize(text):
    """
    Override behavior to integrate various token modification filters
    """
    tokens = VyperLexer().tokenize(text)

    # Add colno to all tokens
    tokens = annotate_columns(text, tokens)

    # Since we are ignoring comments above, we have instances
    # where there are >1 comments in a row, which messes with
    # our indent tracker
    tokens = remove_double(tokens, "NEWLINE")

    # Ensure that we can parse programs that don't end with an newline
    tokens = add_last(tokens, "NEWLINE")

    # Do our indent algorithm, returning a stream without contextual whitespace
    tokens = indent_tracker(tokens)

    # We allow users to make certain definitions into multiline defs
    # e.g. a = ( NEWLINE INDENT 1, NEWLINE 2, NEWLINE 3, NEWLINE DEDENT )
    # But the parser doesn't need to know about them, so remove the INDENT/DEDENT pairs
    # NOTE: The indent_tracker already removes the NEWLINEs
    tokens = collapse_unnecessary_multiline(tokens)

    # We don't need a program that starts with a newline
    tokens = skip_begin(tokens, "NEWLINE")

    # Ignore newlines that occur after actual ENDSTMT tokens (e.g. ";")
    # and commas (e.g. multi-line comma-separated values)
    # Ignore newlines after DOCSTR because it screws with function body docstrings
    tokens = skip_after(tokens, "NEWLINE", ("ENDSTMT", ",", "DOCSTR"))

    # Turn all the NEWLINES into ENDSTMTS, as we no longer need them present
    tokens = substitute(tokens, "NEWLINE", "ENDSTMT")

    # INDENT denotes the start of a body, and we do this to help the parser
    # ensure that a docstring only appears inside a function body at the top.
    # Otherwise we would have to post-process the body to ensure that it was
    # the top-most statement.
    tokens = swap_order(tokens, "DOCSTR", "INDENT")

    return tokens

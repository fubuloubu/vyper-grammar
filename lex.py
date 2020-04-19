from more_itertools import peekable as _peekable
from sly.lex import (
    Lexer as _Lexer,
    Token,
)

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
        NAME, STRING, COMMENT, DOCSTR,
        DEC_NUM, HEX_NUM, OCT_NUM,
        BIN_NUM, FLOAT, BOOL,
        IMPORT, FROM, AS, DEF,
        IF, ELIF, ELSE, FOR, IN, ARROW,
        AND, OR, NOT, XOR, SHL, SHR,
        ADD, SUB, MUL, DIV, POW, MOD,
        EQ, NE, LT, LE, GT, GE,
        SKIP, PASS, BREAK, CONTINUE,
        LOG, EVENT, RETURN, RAISE, ASSERT,
        UNREACHABLE, STRUCT, INTERFACE,
        INDENT, DEDENT,
        TAB, SPACE, NEWLINE,
    }

    literals = {
        "=", ",",
        ".", ":",
        "@",
        "(", ")",
        "[", "]",
        "{", "}",
    }

    # Tokens

    @_('|'.join([r'"""(.|\s)*"""', r"'''(.|\s)*'''"]))
    def DOCSTR(self, t):
        # Docstrings are multiline
        self.lineno += max(t.value.count("\n"), t.value.count("\r"))
        return t

    COMMENT = r"[#].*"
    STRING = '|'.join([r'"(?!"").*"', r"'(?!"").*'"])

    HEX_NUM = r"0x[\da-f]*"
    OCT_NUM = r"0o[0-7]*"
    BIN_NUM = r"0b[0-1]*"
    FLOAT = r"((\d+\.\d*|\.\d+)(e[-+]?\d+)?|\d+(e[-+]?\d+))"
    DEC_NUM = r"0|[1-9]\d*"

    ARROW = "->"
    POW = "\*\*"
    SHL = "<<"
    SHR = ">>"
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="

    ADD = "\+"
    SUB = "-"
    MUL = "\*"
    DIV = "/"
    MOD = "%"

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
    NAME["contract"] = INTERFACE  # TODO Change the name of this

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
            raise SyntaxError(
                f"Mixing tabs and spaces @ line {self.lineno}, col {col}"
            )

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


TOKENS = VyperLexer.tokens - {"TAB", "SPACE", "NEWLINE"}


def indent_tracker(tokens):
    """
    Filter a stream of tokens to insert INDENT and DEDENT characters
    in place of TABs and NEWLINEs depending on the indent level of the code.
    Also discard SPACEs.
    """

    # Python tab-aware scoping is tricky to parse.
    # The below functionality is only here to aid in parsing whitespace for scoping.
    indent_level = 0

    for t in tokens:
        if t.type == 'NEWLINE':
            yield t  # We want the newline

            try:
                lvl = 0
                # Count how many tabs we have
                while tokens.peek().type == 'TAB':
                    t = next(tokens)  # We know it's a tab
                    lvl += 1

                    if tokens.peek().type == 'NEWLINE':
                        break  # TAB(s) + NEWLINE is whitespace

                    # If we have 1+ spaces after a tab, it's a problem
                    if tokens.peek().type == 'SPACE':
                        raise SyntaxError(
                            f"Misaligned indent @ line {t.lineno}"
                        )

            except StopIteration as e:
                # If token.peek() throws, so dedent all the way
                lvl = 0

            # Can only indent once per line, check if one too many tabs!
            if lvl - indent_level > 1:
                raise SyntaxError(
                    f"Too much indenting @ line {t.lineno}"
                )
            # One ore indent than current indent level
            elif lvl > indent_level:
                t.type = 'INDENT'  # change TAB to INDENT (we're skipping all the tabs)
                indent_level += 1  # increment indent by one level
                yield t

            # Less indent than current indent level
            elif lvl < indent_level:
                dedent = Token()  # Create a new token from the last one
                dedent.type = 'DEDENT'  # Change TAB to DEDENT
                dedent.value  = t.value
                dedent.index  = t.index
                dedent.lineno = t.lineno
                # yield number of DEDENTs equal to the difference in levels
                missing_levels = indent_level - lvl
                for _ in range(missing_levels):
                    indent_level -= 1  # dedent by one level
                    yield dedent

        elif t.type == 'SPACE':
            continue  # We don't care about spaces otherwise
        else:
            yield t  # Normal token


def tokenize(text):
    """
    Override behavior to integrate various token modification filters
    """
    tokens = VyperLexer().tokenize(text)
    tokens = indent_tracker(_peekable(tokens))
    return tokens

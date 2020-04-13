from more_itertools import peekable as _peekable
from sly.lex import (
    Lexer as _Lexer,
    Token,
)

# Compute column.
#     input is the input text string
#     token is a token instance
def _find_column(text, token):
    last_cr = text.rfind('\n', 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = (token.index - last_cr) + 1
    return column


class _VyperLexer(_Lexer):
    tokens = {
        NAME,
        IF,
        ELSE,
        INDENT,
        DEDENT,
        COLON,
        TAB,
        SPACE,
    }

    # Tokens
    NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
    NAME['if'] = IF
    NAME['else'] = ELSE

    COLON = r':'

    @_(r'\n+')
    def NEWLINE(self, t):
        self.lineno += t.value.count('\n')
        return t

    # Python tab-aware scoping is tricky to parse.
    # The below functionality is only here to aid in parsing whitespace for scoping.
    @_(r' {4}|\t')
    def TAB(self, t):
        col = _find_column(self.text, t)
        if t.value == '\t' > 0:
            if self.__using_spaces:
                raise SyntaxError(
                    f"Mixing tabs and spaces @ line {self.lineno}, col {col}"
                )
            self.__using_tab_char = True
        else:
            if self.__using_tab_char:
                raise SyntaxError(
                    f"Mixing tabs and spaces @ line {self.lineno}, col {col}"
                )
            self.__using_spaces = True
        return t

    @_(r' {1,3}')
    def SPACE(self, t):
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


TOKENS = _VyperLexer.tokens - {'TAB', 'SPACE'}


def tokenize(text):
    """
    Override behavior to integrate Python indent counter
    """
    tokens = _peekable(_VyperLexer().tokenize(text))

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

from sly import Parser as _Parser

from lex import VyperLexer


class _VyperParser(_Parser):
    tokens = VyperLexer.tokens - {'TAB', 'SPACE'}
    literals = VyperLexer.literals

    storage = {}

    precedence = (
       ('left', "+", "-"),
       ('left', "*", "/"),
       ('left', POW, "%"),
       ('right', UMINUS, NOT),
    )

    start = 'module'

    @_('imports',
       'functions')
    def module(self, p):
        [f() for f in p.functions]

    @_('imports import_stmt',
       'import_stmt', '')
    def imports(self, p):
        pass

    @_('IMPORT import_path maybe_alias')
    def import_stmt(self, p):
        pass

    @_('FROM import_path IMPORT NAME maybe_alias')
    @_('FROM import_path IMPORT "*"')
    def import_stmt(self, p):
        pass

    @_('import_path "." NAME',
       '"." import_path',
       'NAME')
    def import_path(self, p):
        pass

    @_('AS NAME', '')
    def maybe_alias(self, p):
        pass

    @_('functions function',
       'function', '')
    def functions(self, p):
        return p.functions + [p.function] if len(p) > 0 else None

    @_('DEF NAME arguments maybe_return ":" maybe_docstr body')
    def function(self, p):
        self.storage[p.NAME] = lambda p: p.body

    @_('DOCSTR', '')
    def maybe_docstr(self, p):
        pass

    @_('ARROW NAME', '')
    def maybe_return(self, p):
        return p.NAME if len(p) > 0 else None

    @_('INDENT stmt maybe_stmt DEDENT')
    def body(self, p):
        p.stmt
        p.maybe_stmt

    @_('INDENT PASS DEDENT')
    def body(self, p):
        pass

    @_('stmt', '')
    def maybe_stmt(self, p):
        return p.stmt if len(p) > 0 else None

    @_('stmt maybe_comment')
    def stmt(self, p):
        p.stmt

    @_('expr')
    def stmt(self, p):
        p.expr

    @_('multiple_assign = expr')
    def stmt(self, p):
        p.multiple_assign = p.expr

    @_('multiple_assign "," NAME',
       'multiple_assign "," SKIP',
       'SKIP',
       'NAME')
    def multiple_assign(self, p):
        if len(p) > 0:
            return self.multiple_assign + (p[1],)
        return (p[0],)

    @_('NAME "+" "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] += p.expr

    @_('NAME "-" "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] -= p.expr

    @_('NAME "*" "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] *= p.expr

    @_('NAME "/" "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] /= p.expr

    @_('NAME POW "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] **= p.expr

    @_('NAME "%" "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] %= p.expr

    @_('NAME ":" NAME "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] = p.expr

    @_('NAME "=" expr')
    def stmt(self, p):
        self.storage[p.NAME] = p.expr

    @_('BREAK')
    def stmt(self, p):
        pass

    @_('CONTINUE')
    def stmt(self, p):
        pass

    @_('ASSERT expr')
    def stmt(self, p):
        pass

    @_('RAISE')
    def stmt(self, p):
        pass

    @_('RETURN expr')
    def stmt(self, p):
        print(p.expr)

    @_('LOG NAME "(" dict ")"')
    def stmt(self, p):
        print(p.expr)

    @_('FOR NAME IN expr ":" body')
    def stmt(self, p):
        for val in p.expr:
            self.storage[p.NAME] = val
            p.body

    @_('IF expr ":" body maybe_else')
    def stmt(self, p):
        if p.expr:
            p.body
        else:
            p.maybe_else

    @_('ELIF expr ":" body maybe_else')
    def maybe_else(self, p):
        if p.expr:
            return p.body
        else:
            return p.maybe_else

    @_('ELSE ":" body')
    def maybe_else(self, p):
        return p.body

    @_('')
    def maybe_else(self, p):
        return None

    @_('expr "+" expr')
    def expr(self, p):
        return p.expr0 + p.expr1

    @_('expr "-" expr')
    def expr(self, p):
        return p.expr0 - p.expr1

    @_('expr "*" expr')
    def expr(self, p):
        return p.expr0 * p.expr1

    @_('expr "/" expr')
    def expr(self, p):
        return p.expr0 / p.expr1

    @_('expr POW expr')
    def expr(self, p):
        return p.expr0 ** p.expr1

    @_('expr "%" expr')
    def expr(self, p):
        return p.expr0 % p.expr1

    @_('"-" expr %prec UMINUS')
    def expr(self, p):
        return -p.expr

    @_('expr AND expr')
    def expr(self, p):
        return p.expr0 and p.expr1

    @_('expr OR expr')
    def expr(self, p):
        return p.expr0 or p.expr1

    @_('expr XOR expr')
    def expr(self, p):
        return (p.expr0 and not p.expr1) or (not p.expr0 and p.expr1)

    @_('expr SHL expr')
    def expr(self, p):
        return (p.expr0 and not p.expr1) << (not p.expr0 and p.expr1)

    @_('expr SHR expr')
    def expr(self, p):
        return (p.expr0 and not p.expr1) >> (not p.expr0 and p.expr1)

    @_('NOT expr')
    def expr(self, p):
        return not p.expr

    @_('expr LT expr')
    def expr(self, p):
        return p.expr0 < p.expr1

    @_('expr LE expr')
    def expr(self, p):
        return p.expr0 <= p.expr1

    @_('expr GT expr')
    def expr(self, p):
        return p.expr0 > p.expr1

    @_('expr GE expr')
    def expr(self, p):
        return p.expr0 >= p.expr1

    @_('expr EQ expr')
    def expr(self, p):
        return p.expr0 == p.expr1

    @_('expr NE expr')
    def expr(self, p):
        return p.expr0 != p.expr1

    @_('expr IN expr')
    def expr(self, p):
        return p.expr0 in p.expr1

    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    @_('literal',
       'variable_access',
       'list',
       'tuple')
    def expr(self, p):
        return p[0]

    @_('"(" argument_seq ")"')
    def arguments(self, p):
        return p.argument_seq

    @_('argument_seq "," NAME "=" argument_val',
       'NAME "=" argument_val ","')
    def argument_seq(self, p):
        return p.argument_seq + (p.argument_val,)

    @_('argument_seq "," argument_val',
       'argument_val ","')
    def argument_seq(self, p):
        if len(p) > 1:
            return p.argument_seq + (p.argument_val,)
        return (p.argument_val,)

    @_('literal',
       'variable_access',
       'list',
       'tuple',
       'expr',
       '')
    def argument_val(self, p):
        if len(p) > 0:
            return (p[0],)
        return tuple()

    @_('"{" dict_seq "}"')
    def dict(self, p):
        return p.dict_seq

    @_('dict_seq "," NAME ":" dict_val',
       'NAME ":" dict_val')
    def dict_seq(self, p):
        return p.dict_seq + [p.dict_val]

    @_('literal',
       'variable_access',
       'list',
       'tuple',
       'expr',
       '')
    def dict_val(self, p):
        if len(p) > 0:
            return [p[0]]
        return dict()

    @_('"(" tuple_seq ")"')
    def tuple(self, p):
        return p.tuple_seq

    @_('tuple_seq "," tuple_val',
       'tuple_val ","')
    def tuple_seq(self, p):
        if len(p) > 1:
            return p.tuple_seq + (p.tuple_val,)
        return (p.tuple_val,)

    @_('literal',
       'variable_access',
       'list',
       'tuple',
       'expr',
       '')
    def tuple_val(self, p):
        if len(p) > 0:
            return (p[0],)
        return tuple()

    @_('"[" list_seq "]"')
    def list(self, p):
        return p.list_seq

    @_('list_seq "," list_val',
       'list_val')
    def list_seq(self, p):
        return p.list_seq + [p.list_val]

    @_('literal',
       'variable_access',
       'list',
       'tuple',
       'expr',
       '')
    def list_val(self, p):
        if len(p) > 0:
            return [p[0]]
        return list()
 
    @_('"(" variable_access ")"')
    def variable_access(self, p):
        return self.variable_access
 
    @_('variable_access arguments')
    def variable_access(self, p):
        return self.variable_access(*self.arguments)

    @_('variable_access "." NAME')
    def variable_access(self, p):
        return getattr(self.variable_access, self.NAME)

    @_('variable_access "[" expr "]"')
    def variable_access(self, p):
        return self.variable_access[self.expr]

    @_('NAME',
       'SELF')
    def variable_access(self, p):
        if p.SELF:
            return self.storage
        return self.storage[p.NAME]

    @_('number',
       'string',
       'bool')
    def literal(self, p):
        return p[0]

    @_('DEC_NUM')
    def number(self, p):
        return int(p.DEC_NUM)

    @_('HEX_NUM')
    def number(self, p):
        return int(p.HEX_NUM, 16)

    @_('OCT_NUM')
    def number(self, p):
        return int(p.OCT_NUM, 8)

    @_('BIN_NUM')
    def number(self, p):
        return int(p.BIN_NUM, 2)

    @_('FLOAT')
    def number(self, p):
        return float(p.FLOAT)

    @_('STRING')
    def string(self, p):
        return p[0]

    @_('BOOL')
    def bool(self, p):
        return bool(p.BOOL)

    @_('', 'COMMENT')
    def maybe_comment(self, p):
        pass


def parse(tokens):
    return _VyperParser().parse(tokens)

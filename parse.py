from sly import Parser as _Parser

from lex import VyperLexer

class _VyperParser(_Parser):

    def error(self, tok):
        raise SyntaxError(f"""Could not parse line {tok.lineno}:

    {tok.value}
    """)

    tokens = VyperLexer.tokens - {'TAB', 'SPACE'}
    literals = VyperLexer.literals

    precedence = (
       ('left', "+", "-"),
       ('left', "*", "/"),
       ('left', POW, "%"),
       ('right', UMINUS, NOT),
    )

    start = 'module'

    @_('module_items')
    def module(self, p):
        return ('module', p.module_items)

    @_('module_items module_item')
    @_('module_item')
    @_('')
    def module_items(self, p):
        items = getattr(p, 'module_items', [])
        item = getattr(p, 'module_item', None)
        if item:
            items += [item]
        return items

    @_('COMMENT NEWLINE')
    @_('NEWLINE')
    def newline(self, p):
        # This helper token identifies logical end of line
        pass

    @_('newline')
    def module_item(self, p):
        pass

    ##### IMPORTS #####
    @_('import_stmt')
    def module_item(self, p):
        return p.import_stmt

    @_('IMPORT import_path maybe_alias newline')
    def import_stmt(self, p):
        return {'path': p.import_path, 'alias': p.maybe_alias}

    @_('FROM import_path IMPORT NAME maybe_alias newline')
    def import_stmt(self, p):
        return {'path': p.import_path + [p.NAME], 'alias': p.maybe_alias}

    @_('FROM import_path IMPORT "*" newline')
    def import_stmt(self, p):
        return {'path': p.import_path + ['*'], 'alias': None}

    @_('import_path "." NAME')
    def import_path(self, p):
        return p.import_path + [p.NAME]

    @_('"." import_path')
    def import_path(self, p):
        return ['.'] + p.import_path

    @_('NAME')
    def import_path(self, p):
        return [p.NAME]

    @_('AS NAME', '')
    def maybe_alias(self, p):
        return p.NAME if p.NAME else None

    ##### FUNCTION DEFS #####
    @_('function')
    def module_item(self, p):
        return p.function

    @_('decorators NEWLINE DEF NAME "(" arguments ")" maybe_return ":" body')
    def function(self, p):
        return {
            'decorators': p.maybe_decorators,
            'name': p.NAME,
            'arguments': p.arguments,
            'returns': p.maybe_return,
            'doc': p.maybe_docstr,
            'body': p.body
        }

    @_('decorators NEWLINE decorator')
    @_('decorator')
    @_('')
    def decorators(self, p):
        decorators = getattr(p, 'decorators', [])
        decorator = getattr(p, 'decorator', None)
        if decorator:
            decorators += [decorator]
        return decorators

    @_('"@" NAME')
    def decorator(self, p):
        return {'name': p.NAME}

    @_('arguments "," argument')
    @_('argument')
    @_('')
    def arguments(self, p):
        arguments = getattr(p, 'arguments', [])
        argument = getattr(p, 'argument', None)
        if argument:
            arguments += [argument]
        return arguments

    @_('NAME ":" type "=" variable')
    @_('NAME ":" type')
    def argument(self, p):
        return {
            'name': p.NAME,
            'type': p.type,
            'default_value': p.variable if p.variable else None
        }

    @_('ARROW NAME', '')
    def maybe_return(self, p):
        return p.NAME if p.NAME else None

    @_('INDENT stmts DEDENT')
    def body(self, p):
        return p.stmts

    @_('stmts stmt')
    @_('stmt')
    @_('')
    def stmts(self, p):
        return _get_list(p, 'stmts', 'stmt')

    @_('DOCSTR newline')
    def stmt(self, p):
        return ('doc', p.DOCSTR)

    @_('PASS newline')
    def stmt(self, p):
        pass

    @_('expr newline')
    def stmt(self, p):
        return p.expr

    @_('multiple_assign = expr newline')
    def stmt(self, p):
        p.multiple_assign = p.expr

    @_('multiple_assign "," variable')
    @_('multiple_assign "," SKIP')
    @_('variable')
    @_('SKIP')
    def multiple_assign(self, p):
        assign_list = _get_list(p, 'multiple_assign', 'variable')
        if getattr(p, 'SKIP', False):
            assign_list += [None]
        return assign_list

    @_('variable "+" "=" expr newline')
    @_('variable "-" "=" expr newline')
    @_('variable "*" "=" expr newline')
    @_('variable "/" "=" expr newline')
    @_('variable POW "=" expr newline')
    @_('variable "%" "=" expr newline')
    def stmt(self, p):
        if p.POW:
            op = '**'
        else:
            op = p[1]
        expr = (op, p.variable, p.expr)
        # Re-arrange to BinOp
        return {'target': p.variable, 'expr': expr}

    @_('NAME ":" type "=" expr newline')
    def stmt(self, p):
        return {'name': p.NAME, 'type': p.type, 'initial_value': p.expr}

    @_('variable "=" expr newline')
    def stmt(self, p):
        return {'target': p.variable, 'expr': p.expr}

    @_('BREAK newline')
    def stmt(self, p):
        return 'break'

    @_('CONTINUE newline')
    def stmt(self, p):
        return 'continue'

    @_('ASSERT expr newline')
    def stmt(self, p):
        return ('assert', p.expr)

    @_('RAISE newline')
    def stmt(self, p):
        return 'raise'

    @_('RETURN expr newline')
    def stmt(self, p):
        return ('return', p.expr)

    @_('LOG NAME "(" dict ")" newline')
    def stmt(self, p):
        return ('log', {'type': p.NAME, 'args': p.dict })

    @_('FOR NAME IN expr ":" body')
    def stmt(self, p):
        return ('for', {'iter_var': p.NAME, 'iter': p.expr, 'body': p.body})

    @_('IF expr ":" body elif_list maybe_else')
    def stmt(self, p):
        return ('if', [(p.expr, p.body)] + p.maybe_elif + p.maybe_else)

    @_('elif_list ELIF expr ":" body')
    @_('ELIF expr ":" body')
    @_('')
    def elif_list(self, p):
        items = getattr(p, 'elif_list', [])
        cond = getattr(p, 'expr', None)
        action = getattr(p, 'body', None)
        if cond and action:
            items += [(cond, action)]
        return items

    @_('ELSE ":" body')
    @_('')
    def maybe_else(self, p):
        if p.body:
            return [(None, p.body)]
        else:
            return []

    # Binary Opertaions
    # Mathematical operations
    @_('expr "+" expr')
    @_('expr "-" expr')
    @_('expr "*" expr')
    @_('expr "/" expr')
    @_('expr POW expr')
    @_('expr "%" expr')
    # Logical Operations
    @_('expr AND expr')
    @_('expr OR expr')
    @_('expr XOR expr')
    @_('expr SHL expr')
    @_('expr SHR expr')
    # Comparisons
    @_('expr LT expr')
    @_('expr LE expr')
    @_('expr GT expr')
    @_('expr GE expr')
    @_('expr EQ expr')
    @_('expr NE expr')
    @_('expr IN expr')
    def expr(self, p):
        if p.POW:
            op = '**'
        else:
            op = p[1]
        return (op, p.expr0, p.expr1)

    # Unary Operations
    @_('"-" expr %prec UMINUS')
    @_('NOT expr')
    def expr(self, p):
        op = p[0]
        return (op, p.expr)

    # Ensure wrapping in parens doesn't do anything
    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    # Endpoint of expr
    @_('literal')
    @_('variable')
    @_('list')
    @_('tuple')
    def expr(self, p):
        return p[0]

    ##### Type definitions #####
    @_('NAME')
    def type(self, p):
        pass

    # Dict
    @_('"{" dict_items "}"')
    def dict(self, p):
        return ('dict', p.dict_items)

    @_('dict_items "," NAME ":" dict_item')
    @_('NAME ":" dict_item')
    @_('')
    def dict_items(self, p):
        dict_items = getattr(p, 'dict_items', [])
        key = getattr(p, 'NAME', None)
        val = getattr(p, 'dict_item', None)
        if key and val:
            dict_items[key] = val
        return dict_items

    @_('literal')
    @_('variable')
    @_('list')
    @_('tuple')
    @_('expr')
    @_('')
    def dict_item(self, p):
        return p[0]

    # Tuple
    @_('"(" tuple_items ")"')
    def tuple(self, p):
        return ('tuple', p.tuple_items)

    @_('tuple_items "," tuple_item ","')
    @_('tuple_item ","')
    @_('","')
    @_('tuple_items "," tuple_item')
    @_('tuple_item')
    @_('')
    def tuple_items(self, p):
        tuple_items = getattr(p, 'tuple_items', [])
        tuple_item = getattr(p, 'tuple_item', None)
        if tuple_item:
            tuple_items += [tuple_item]
        return tuple_items

    @_('literal')
    @_('variable')
    @_('tuple')
    @_('list')
    @_('expr')
    @_('')
    def tuple_item(self, p):
        return p[0]

    # List
    @_('"[" list_items "]"')
    def list(self, p):
        return ('list', p.list_items)

    @_('list_items "," list_item')
    @_('list_item')
    @_('')
    def list_items(self, p):
        list_items = getattr(p, 'list_items', [])
        list_item = getattr(p, 'list_item', None)
        if list_item:
            list_items += [list_item]
        return list_items

    @_('literal')
    @_('variable')
    @_('tuple')
    @_('list')
    @_('expr')
    @_('')
    def list_item(self, p):
        return p[0]

    ##### VARIABLES ####
    # Just ensure parenthesis don't do anything
    @_('"(" variable ")"')
    def variable(self, p):
        return self.variable

    # Make a Call
    @_('variable "(" parameters ")"')
    def variable(self, p):
        return self.variable(*self.arguments)

    # Call parameters
    @_('parameters "," parameter')
    @_('parameter')
    @_('')
    def parameters(self, p):
        parameters = getattr(p, 'parameters', [])
        parameter = getattr(p, 'parameter', None)
        if parameter:
            parameters += [parameter]
        return parameters

    # Keyword arguments
    @_('NAME "=" parameter')
    def parameter(self, p):
        return {p.NAME: p[0]}

    # Endpoint for parameter
    @_('literal')
    @_('variable')
    @_('list')
    @_('tuple')
    @_('expr')
    def parameter(self, p):
        return p[0]

    # Get attribute
    @_('variable "." NAME')
    def variable(self, p):
        return getattr(self.variable, self.NAME)

    # Get item
    @_('variable "[" expr "]"')
    def variable(self, p):
        return self.variable[self.expr]

    # Endpoint for variable
    @_('NAME')
    def variable(self, p):
        return p.NAME

    ##### LITERALS #####
    @_('number')
    @_('string')
    @_('bool')
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


def parse(tokens):
    return _VyperParser().parse(tokens)

from sly import Parser as _Parser

from lex import VyperLexer

class _VyperParser(_Parser):

    def error(self, tok):
        if tok:
            raise SyntaxError(f"Could not parse line {tok.lineno}:\n\n{tok.value}\n")
        else:
            raise SyntaxError("Ran out of tokens!")

    tokens = VyperLexer.tokens - {'TAB', 'SPACE'}
    literals = VyperLexer.literals

    precedence = (
       ('left', ADD, SUB),
       ('left', MUL, DIV),
       ('left', POW, MOD),
       ('right', USUB, NOT),
    )

    ##### TOP-LEVEL MODULE #####
    start = 'module'

    @_('''
    [ NEWLINE ]
    [ DOCSTR ]
    [ NEWLINE ]
    { import_stmt }
    { interface_def }
    [ NEWLINE ]
    { struct_def }
    [ NEWLINE ]
    { event_def }
    { storage_def }
    { constant_def }
    { function_def }
    [ NEWLINE ]
    ''')
    def module(self, p):
        return ('module', {
            "doc": p.DOCSTR,
            "imports": p.import_stmt,
            "interfaces": p.interface_def,
            "structs": p.struct_def,
            "events": p.event_def,
            "storage": p.storage_def,
            "constants": p.constant_def,
            "functions": p.function,
        })

    ##### IMPORTS #####
    @_('IMPORT import_path [ alias ] NEWLINE')
    def import_stmt(self, p):
        return ('import', {'path': p.import_path, 'alias': p.alias})

    @_('FROM import_path IMPORT NAME [ alias ] NEWLINE')
    def import_stmt(self, p):
        return ('import', {'path': p.base_path + [p.NAME], 'alias': p.alias})

    @_('FROM import_path IMPORT MUL NEWLINE')
    def import_stmt(self, p):
        return ('import', {'path': p.import_path + ['*'], 'alias': None})

    @_('FROM import_path IMPORT "(" import_list ")" NEWLINE')
    @_('FROM import_path IMPORT "(" INDENT import_list DEDENT ")" NEWLINE')
    def import_stmt(self, p):
        return [
            ('import', {'path': p.import_path + [name], 'alias': alias})
            for name, alias in p.import_list
        ]

    @_('NAME [ alias ] { "," [ NEWLINE ] NAME [ alias ] } [ "," ] [ NEWLINE ]')
    def import_list(self, p):
        return zip([p.NAME0] + p.NAME1, [p.alias0] + p.alias1)

    @_('"." [ import_path ]')
    def import_path(self, p):
        return ['.'] + p.import_path

    @_('{ NAME "." } NAME')
    def import_path(self, p):
        return p.NAME0 + [p.NAME1]

    @_('AS NAME')
    def alias(self, p):
        return p.NAME

    ##### TYPE DEFINITIONS #####
    # Base Types
    @_('NAME')
    def type(self, p):
        return ('Type', p.NAME)

    # Array definitions
    @_('type "[" DEC_NUM "]"')
    def type(self, p):
        return ('ArrayType', {'type': p.type, 'size': p.DEC_NUM})

    @_('type "[" NAME "]"')
    def type(self, p):
        return ('ArrayType', {'type': p.type, 'size': p.NAME})

    # Tuple definitions
    @_('"(" type { "," type } "," ")"')
    def type(self, p):
        return ('TupleType', {"types": [p.type0] + p.type1})

    @_('"(" type "," type { "," type } ")"')
    def type(self, p):
        return ('TupleType', {"types": [p.type0, p.type1] + p.type2})

    @_('"(" "," ")"')
    def type(self, p):
        return ('TupleType', {"types": list()})

    ##### VARIABLE DEFINITIONS #####
    @_('NAME ":" type NEWLINE')
    def storage_def(self, p):
        return ('StorageDef', {"name": p.NAME, "type": p.type, "decorator": None})

    # TODO Change to an actual decorator
    @_('NAME ":" NAME "(" type ")" NEWLINE')
    def storage_def(self, p):
        return ('StorageDef', {"name": p.NAME0, "type": p.type, "decorator": p.NAME1})

    # TODO Change to an actual decorator
    @_('NAME ":" NAME "(" type ")" "=" expr NEWLINE')
    def constant_def(self, p):
        assert p.NAME1 == "constant"
        return ('ConstantDef', {"name": p.NAME0, "type": p.type, "value": p.expr})

    @_('''
    STRUCT NAME ":" NEWLINE
    INDENT
        NAME ":" type
      { NAME ":" type }
    DEDENT
    ''')
    def struct_def(self, p):
        return ('StructDef', {"members": [
            {"name": n, "type": t} for n, t
            in zip([p.NAME0] + p.NAME1, [p.type0] + p.type1)
        ]})

    @_('''
    STRUCT NAME ":" NEWLINE
    INDENT
        PASS
    DEDENT
    ''')
    def struct_def(self, p):
        return ('StructDef', {"members": list()})

    @_('''
    INTERFACE NAME ":" NEWLINE
    INDENT
        function_type ":" NAME
      { function_type ":" NAME }
    DEDENT
    ''')
    def interface_def(self, p):
        return ('InterfaceDef', {"functions": [
            {**f, "mutability": n} for f, n
            in zip([p.function_type0] + p.function_type1, [p.NAME0] + p.NAME1)
        ]})

    @_('STRUCT NAME ":" NEWLINE INDENT PASS DEDENT')
    def interface_def(self, p):
        return ('InterfaceDef', {"functions": list()})

    @_('NAME ":" NAME "(" type ")"')
    def event_member(self, p):
        assert p.NAME1 == "indexed"
        return {"name": p.NAME0, "indexed" : True, "type": p.type}

    @_('NAME ":" type')
    def event_member(self, p):
        return {"name": p.NAME, "indexed" : False, "type": p.type}

    @_('''
    NAME ":" EVENT "(" "{"
      { event_member }
    "}" ")" NEWLINE
    ''')
    def event_def(self, p):
        # TODO Change this syntax to be like struct
        return ('EventDef', {"members": p.event_member})

    @_('''
    NAME ":" EVENT "(" "{"
    "}" ")" NEWLINE
    ''')
    def event_def(self, p):
        return ('EventDef', {"members": list()})

    ##### FUNCTION DEFINITIONS #####
    @_('"@" NAME [ "(" arguments ")" ] NEWLINE')
    def decorator(self, p):
        return ('decorator', {'name': p.NAME, 'arguments': p.arguments})

    @_('{ parameter "," [ NEWLINE ] } [ "," ] [ NEWLINE ]')
    def parameters(self, p):
        return p.parameter

    @_('NAME ":" type [ "=" variable ]')
    def parameter(self, p):
        return ('parameter', {
            'name': p.NAME,
            'type': p.type,
            'default_value': p.variable,
        })

    @_('ARROW NAME')
    def returns(self, p):
        return p.NAME

    @_('DEF NAME "(" parameters ")" [ returns ]')
    def function_type(self, p):
        return ('FunctionType', {
            'name': p.NAME,
            'parameters': p.parameters,
            'returns': p.returns,
        })

    @_('{ decorator } function_type ":" NEWLINE fn_body')
    def function_def(self, p):
        function = p.function_type[1]
        function.update({
            'decorators': p.decorator,
            'doc': p.fn_body[0],
            'body': p.fn_body[1],
        })
        return ('function', function)

    @_('INDENT [ DOCSTR ] stmt { stmt } DEDENT')
    def fn_body(self, p):
        # Only function bodies can have docstrings inside
        return p.DOCSTR, [p.stmt0] + p.stmt1

    @_('INDENT [ DOCSTR ] PASS NEWLINE DEDENT')
    def fn_body(self, p):
        # Function bodies can either be a list of 1+ stmts, or PASS
        return p.DOCSTR, []

    @_('INDENT stmt { stmt } DEDENT')
    def body(self, p):
        # Bodies of multiline statements
        return [p.stmt0] + p.stmt1

    @_('INDENT PASS NEWLINE DEDENT')
    def body(self, p):
        # Non-function bodies can either be a list of 1+ stmts, or PASS
        return []

    ##### ASSIGNMENT STATEMENTS #####
    @_('NAME ":" type "=" expr NEWLINE')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.expr})
    @_('dict')

    # Object Creation Assignments
    # Dict Object
    @_('"{" NAME ":" expr { "," NAME ":" expr } [ "," ] "}"')
    def dict(self, p):
        return ('dict', {"keys": [p.NAME0] + p.NAME1, "values": [p.expr0] + p.expr1})

    @_('"{" "}"')
    def dict(self, p):
        return ('dict', {"keys": list(), "values": list()})

    @_('NAME ":" type "=" dict NEWLINE')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.dict})

    # List Object
    @_('"[" expr { "," expr } [ "," ] "]"')
    def list(self, p):
        return ('list', {"values": [p.expr0] + p.expr1})

    @_('"[" "]"')
    def list(self, p):
        return ('list', {"values": list()})

    @_('NAME ":" type "=" list NEWLINE')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.list})

    # Tuple Object
    @_('"(" expr { "," expr } "," ")"')
    def tuple(self, p):
        return ('tuple', {"values": [p.expr0] + p.expr1})

    @_('"(" expr "," expr { "," expr } ")"')
    def tuple(self, p):
        return ('tuple', {"values": [p.expr0, p.expr1] + p.expr2})

    @_('"(" "," ")"')
    def tuple(self, p):
        return ('tuple', {"values": list()})

    @_('NAME ":" type "=" tuple NEWLINE')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.tuple})

    # Allow multiple assignments (and skipping)
    @_('variable')
    @_('SKIP')
    def target(self, p):
        return getattr(p, 'variable', None)

    @_('target { "," target } = expr NEWLINE')
    def stmt(self, p):
        if p.target1:
            target = ('tuple', [p.target0] + p.target1)
        else:
            target= p.target0
        return ('assign', {'target': target, 'expr': p.expr})

    # Augmented Assignment
    @_('target ADD "=" expr NEWLINE')
    @_('target SUB "=" expr NEWLINE')
    @_('target MUL "=" expr NEWLINE')
    @_('target DIV "=" expr NEWLINE')
    @_('target POW "=" expr NEWLINE')
    @_('target MOD "=" expr NEWLINE')
    def stmt(self, p):
        expr = (p[1].lower(), p.target, p.expr)
        # Re-arrange to Assign from BinOp
        return ('assign', {'target': p.target, 'expr': expr})

    ##### NON-ASSIGNMENT STATEMENTS #####
    @_('expr NEWLINE')
    def stmt(self, p):
        return p.expr

    @_('BREAK NEWLINE')
    def stmt(self, p):
        return ('break',)

    @_('CONTINUE NEWLINE')
    def stmt(self, p):
        return ('continue',)

    @_('ASSERT expr [ "," STRING ] NEWLINE')
    def stmt(self, p):
        return ('assert', p.expr, p.STRING)

    @_('ASSERT expr "," UNREACHABLE NEWLINE')
    def stmt(self, p):
        return ('assert', p.expr, 'unreachable')

    @_('RAISE [ STRING ] NEWLINE')
    def stmt(self, p):
        return ('raise', p.STRING)

    @_('RAISE UNREACHABLE NEWLINE')
    def stmt(self, p):
        return ('raise', 'unreachable')

    @_('RETURN expr NEWLINE')
    def stmt(self, p):
        return ('return', p.expr)

    @_('LOG NAME "(" dict ")" NEWLINE')
    def stmt(self, p):
        return ('log', {'type': p.NAME, 'args': p.dict })

    ##### MULTILINE STATEMENTS #####
    @_('FOR NAME IN expr ":" NEWLINE body')
    def stmt(self, p):
        return ('for', {'iter_var': p.NAME, 'iter': p.expr, 'body': p.body})

    @_('IF expr ":" NEWLINE body elif_list [ else_clause ]')
    def stmt(self, p):
        return ('if', [(p.expr, p.body)] + p.elif_list + [p.else_clause])

    @_('{ ELIF expr ":" NEWLINE body }')
    def elif_list(self, p):
        return list(zip(p.expr, p.body))

    @_('ELSE ":" NEWLINE body')
    def else_clause(self, p):
        return (None, p.body)

    ##### EXPRESSIONS #####

    # Binary Operations
    # Mathematical operations
    @_('expr ADD expr')
    @_('expr SUB expr')
    @_('expr MUL expr')
    @_('expr DIV expr')
    @_('expr POW expr')
    @_('expr MOD expr')
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
        return (p[1].lower(), p.expr0, p.expr1)

    # Unary Operations
    @_('SUB expr %prec USUB')
    @_('NOT expr')
    def expr(self, p):
        op = 'u' + p[0].lower()
        return (op, p.expr)

    # Ensure wrapping in parens doesn't do anything
    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    # Endpoint of an expression
    @_('literal')
    @_('variable')
    def expr(self, p):
        return p[0]

    ##### VARIABLES ####
    # Just ensure parenthesis don't do anything
    @_('"(" variable ")"')
    def variable(self, p):
        return self.variable

    # Make a Call
    @_('variable "(" [ arguments ] ")"')
    def variable(self, p):
        return ('call', {"target": p.variable, "args": p.arguments})

    # Call arguments
    @_('argument { "," argument } [ "," ]')
    def arguments(self, p):
        return [p.argument0] + p.argument1

    # Keyword arguments
    @_('[ NAME "=" ] expr')
    def argument(self, p):
        return {"name": p.NAME, "value": p.expr}

    # Get attribute
    @_('variable "." NAME')
    def variable(self, p):
        return ("getattr", {"target": self.variable, "attribute": self.NAME})

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

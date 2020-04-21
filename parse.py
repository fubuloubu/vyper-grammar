from sly import Parser as _Parser

from lex import VyperLexer, tokenize

class _VyperParser(_Parser):

    # Uncomment if you want to see the parse table
    #debugfile = 'parser.out'

    def __init__(self, text):
        self._text = text
        super().__init__()

    def error(self, tok):
        if tok:
            line = self._text.splitlines()[tok.lineno]
            raise SyntaxError(f"Could not parse line:\n\n   {line}")
        else:  # End of file
            raise SyntaxError("Ran out of tokens!")

    # HACK: Cannot import these from constant in lex, for whatever reason
    tokens = VyperLexer.tokens - {'TAB', 'SPACE', 'NEWLINE'}
    literals = VyperLexer.literals

    precedence = (
        # These operations can be used in a series e.g. 1 + 2 + 3 + 4
        # The evaluation order is left to right evaluation e.g. (...((a + b) + c) + ...
        ('left', ADD, SUB),
        ('left', MUL, DIV),  # Top-down is order of operations (lowest first)
        ('left', AND, OR, XOR),
        # These operations can be used in series e.g. not not not True
        # The evaluation order is right to left evaluation e.g. -(-(-(a)))
        ('right', USUB, NOT),
        # Cannot use these operators multiple times in a row without parens
        # e.g. 1 < 2 < 3 < ...
        ('nonassoc', EQ, NE, LT, GT, LE, GE),
        ('nonassoc', SHL, SHR), # Only nonassociative with those in it's group
        ('nonassoc', POW, MOD),
    )

    ##### TOP-LEVEL MODULE #####
    start = 'module'

    @_('[ DOCSTR ] { module_stmt }')
    def module(self, p):
        module = {
            "doc": p.DOCSTR,
            "imports": list(),
            "interfaces": list(),
            "structs": list(),
            "events": list(),
            "storage": list(),
            "constants": list(),
            "functions": list(),
        }
        for stmt in p.module_stmt:
            for k, v in stmt.items():
                module[k].append(v)
        return ('Module', module)

    ##### IMPORTS #####
    @_('import_stmt')
    def module_stmt(self, p):
        return {"import": p.import_stmt}

    @_('IMPORT { "." } import_path [ import_alias ] ENDSTMT')
    def import_stmt(self, p):
        return ('import', {'path': ["."] * (len(p) - 4) + p.import_path, 'alias': p.import_alias})

    @_('import_from IMPORT MUL ENDSTMT')
    def import_stmt(self, p):
        return ('import', {'path': p.import_from + ['*'], 'alias': None})

    @_('import_from IMPORT NAME [ import_alias ] ENDSTMT')
    def import_stmt(self, p):
        return ('import', {'path': p.import_from + [p.NAME], 'alias': p.import_alias})

    @_('import_from IMPORT "(" import_list ")" ENDSTMT')
    def import_stmt(self, p):
        return [
            ('import', {'path': p.import_from + [name], 'alias': alias})
            for name, alias in p.import_list
        ]

    @_('FROM "." { "." }')
    def import_from(self, p):
        return ["."] * (len(p) - 1)

    @_('FROM { "." } import_path')
    def import_from(self, p):
        return ["."] * (len(p) - 2) + p.import_path

    @_('NAME [ import_alias ] { "," NAME [ import_alias ] } [ "," ]')
    def import_list(self, p):
        return zip([p.NAME0] + p.NAME1, [p.import_alias0] + p.import_alias1)

    @_('NAME { "." NAME }')
    def import_path(self, p):
        return [p.NAME0] + p.NAME1

    @_('AS NAME')
    def import_alias(self, p):
        return p.NAME

    ##### TYPE DEFINITIONS #####
    # Base Types
    @_('NAME')
    def type(self, p):
        return ('Type', p.NAME)

    # Array definitions
    @_('type "[" DEC_NUM "]"')
    def type(self, p):
        return ('ArrayType', {'type': p.type, 'size': p.DEC_NUM, 'len': p.DEC_NUM})

    @_('type "[" NAME "]"')
    def type(self, p):
        return ('ArrayType', {'type': p.type, 'size': p.NAME, 'len': p.NAME})

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
    @_('storage_def')
    def module_stmt(self, p):
        return {"storage": p.storage_def}

    @_('NAME ":" type ENDSTMT')
    def storage_def(self, p):
        return ('StorageDef', {"name": p.NAME, "type": p.type, "decorator": None})

    # TODO Change to an actual decorator
    @_('NAME ":" NAME "(" type ")" ENDSTMT')
    def storage_def(self, p):
        return ('StorageDef', {"name": p.NAME0, "type": p.type, "decorator": p.NAME1})

    ##### CONSTANT DEFINITIONS #####
    @_('constant_def')
    def module_stmt(self, p):
        return {"constant": p.constant_def}

    # TODO Change to an actual decorator
    @_('NAME ":" NAME "(" type ")" "=" expr ENDSTMT')
    def constant_def(self, p):
        assert p.NAME1 == "constant"
        return ('ConstantDef', {"name": p.NAME0, "type": p.type, "value": p.expr})

    ##### STRUCT DEFINITIONS #####
    @_('struct_def')
    def module_stmt(self, p):
        return {"struct": p.struct_def}

    @_('''
    STRUCT NAME ":"
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
    STRUCT NAME ":"
    INDENT
        PASS
    DEDENT
    ''')
    def struct_def(self, p):
        return ('StructDef', {"members": list()})

    ##### INTERFACE DEFINTIIONS #####
    @_('interface_def')
    def module_stmt(self, p):
        return {"interface": p.interface_def}

    @_('''
    INTERFACE NAME ":"
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

    @_('''
    INTERFACE NAME ":"
    INDENT
        PASS
    DEDENT
    ''')
    def interface_def(self, p):
        return ('InterfaceDef', {"functions": list()})

    ##### EVENT DEFITIONS #####
    @_('event_def')
    def module_stmt(self, p):
        return {"event": p.event_def}

    @_('''
    NAME ":" EVENT "(" "{"
      { event_member }
    "}" ")" ENDSTMT
    ''')
    def event_def(self, p):
        # TODO Change this syntax to be like struct
        return ('EventDef', {"members": p.event_member})

    @_('''
    NAME ":" EVENT "(" "{"
    "}" ")" ENDSTMT
    ''')
    def event_def(self, p):
        return ('EventDef', {"members": list()})

    @_('NAME ":" NAME "(" type ")"')
    def event_member(self, p):
        assert p.NAME1 == "indexed"
        return {"name": p.NAME0, "indexed" : True, "type": p.type}

    @_('NAME ":" type')
    def event_member(self, p):
        return {"name": p.NAME, "indexed" : False, "type": p.type}

    ##### FUNCTION DEFINITIONS #####
    @_('function_def')
    def module_stmt(self, p):
        return {"function": p.function_def}

    @_('"@" NAME [ "(" arguments ")" ] ENDSTMT')
    def decorator(self, p):
        return ('decorator', {'name': p.NAME, 'arguments': p.arguments})

    @_('{ parameter "," } [ "," ]')
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

    @_('{ decorator } function_type ":" [ DOCSTR ] body')
    def function_def(self, p):
        function = p.function_type[1]
        function.update({
            'decorators': p.decorator,
            'doc': p.DOCSTR,
            'body': p.fn_body,
        })
        return ('function', function)

    @_('INDENT stmt { stmt } DEDENT')
    def body(self, p):
        # Bodies of multiline statements
        return [p.stmt0] + p.stmt1

    @_('INDENT PASS ENDSTMT DEDENT')
    def body(self, p):
        # Bodies can either be a list of 1+ stmts, or PASS
        return list()

    ##### ASSIGNMENT STATEMENTS #####
    @_('NAME ":" type "=" expr ENDSTMT')
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

    @_('NAME ":" type "=" dict ENDSTMT')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.dict})

    # List Object
    @_('"[" expr { "," expr } [ "," ] "]"')
    def list(self, p):
        return ('list', {"values": [p.expr0] + p.expr1})

    @_('"[" "]"')
    def list(self, p):
        return ('list', {"values": list()})

    @_('NAME ":" type "=" list ENDSTMT')
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

    @_('NAME ":" type "=" tuple ENDSTMT')
    def stmt(self, p):
        return ('allocate', {'name': p.NAME, 'type': p.type, 'initial_value': p.tuple})

    # Allow multiple assignments (and skipping)
    @_('variable')
    @_('SKIP')
    def target(self, p):
        return getattr(p, 'variable', None)

    @_('target { "," target } = expr ENDSTMT')
    def stmt(self, p):
        if p.target1:
            target = ('tuple', [p.target0] + p.target1)
        else:
            target= p.target0
        return ('assign', {'target': target, 'expr': p.expr})

    # Augmented Assignment
    @_('target ADD "=" expr ENDSTMT')
    @_('target SUB "=" expr ENDSTMT')
    @_('target MUL "=" expr ENDSTMT')
    @_('target DIV "=" expr ENDSTMT')
    @_('target POW "=" expr ENDSTMT')
    @_('target MOD "=" expr ENDSTMT')
    def stmt(self, p):
        expr = (p[1].lower(), p.target, p.expr)
        # Re-arrange to Assign from BinOp
        return ('assign', {'target': p.target, 'expr': expr})

    ##### NON-ASSIGNMENT STATEMENTS #####
    @_('expr ENDSTMT')
    def stmt(self, p):
        return p.expr

    @_('BREAK ENDSTMT')
    def stmt(self, p):
        return ('break',)

    @_('CONTINUE ENDSTMT')
    def stmt(self, p):
        return ('continue',)

    @_('ASSERT expr [ "," STRING ] ENDSTMT')
    def stmt(self, p):
        return ('assert', p.expr, p.STRING)

    @_('ASSERT expr "," UNREACHABLE ENDSTMT')
    def stmt(self, p):
        return ('assert', p.expr, 'unreachable')

    @_('RAISE [ STRING ] ENDSTMT')
    def stmt(self, p):
        return ('raise', p.STRING)

    @_('RAISE UNREACHABLE ENDSTMT')
    def stmt(self, p):
        return ('raise', 'unreachable')

    @_('RETURN expr ENDSTMT')
    def stmt(self, p):
        return ('return', p.expr)

    @_('LOG NAME "(" dict ")" ENDSTMT')
    def stmt(self, p):
        return ('log', {'type': p.NAME, 'args': p.dict })

    ##### MULTILINE STATEMENTS #####
    @_('FOR NAME IN expr ":" body')
    def stmt(self, p):
        return ('for', {'iter_var': p.NAME, 'iter': p.expr, 'body': p.body})

    @_('IF expr ":" body elif_list [ else_clause ]')
    def stmt(self, p):
        return ('if', [(p.expr, p.body)] + p.elif_list + [p.else_clause])

    @_('{ ELIF expr ":" body }')
    def elif_list(self, p):
        return list(zip(p.expr, p.body))

    @_('ELSE ":" body')
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


def parse(text):
    tokens = tokenize(text)
    ast = _VyperParser(text).parse(tokens)
    return ast

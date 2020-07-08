import pytest
from parse import parse

IMPORTS = [
    "import a",
    "import a as b",
    "import .a",
    "import .a as b",
    "import .a.b",
    "import .a.b as c",
    "from a import b",
    "from a import b as c",
    "from .a import b",
    "from .a import b as c",
    "from ..a import b",
    "from ..a import b as c",
    "from . import a",
    "from . import a as b",
    "from .. import a",
    "from .. import a as b",
    "from ... import a",
    "from ... import a as b",
    "from a import (b, d as e)",
    "from a import (b as c, d)",
    "from a import (b, d)",
    "from a import (b as c, d as e)",
]

MAPPINGS = [
    "a: HashMap[uint256, uint256]",
    "b: HashMap[uint256, HashMap[uint256, uint256]]",
    "c: HashMap[A, HashMap[B, HashMap[C, D]]]",
]

TUPLES = [
    "a: (,)",
    "b: (A,)",
    "c: (A, B)",
    "d: (A, B,)",
    "e: (A, B, C)",
    "f: (A, B, C,)",
]

CONSTANTS = [
    "a: constant(uint256) = 0",
]

EVENTS = [
    "event A:\n    pass",
    "event A:\n    a: uint256\n    b: indexed(uint256)",
]

STRUCTS = [
    "struct A:\n    pass",
    "struct A:\n    a: uint256\n    b: uint256",
]

INTERFACES = [
    "interface A:\n    def foo(): nonpayable",
    "interface A:\n    def bar() -> uint256: view",
    "interface A:\n    def baz(a: uint256): payable",
    "interface A:\n    def biz(a: uint256) -> uint256: pure",
]

SOURCES = IMPORTS + MAPPINGS + TUPLES + CONSTANTS + EVENTS + STRUCTS + INTERFACES


@pytest.mark.parametrize("source", SOURCES)
def test_grammar(source):
    parse(source, display_tokens=True)

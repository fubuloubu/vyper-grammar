import pytest
from parse import parse

IMPORTS = [
    "import a\n",
    "import a as b\n",
    "import .a\n",
    "import .a as b\n",
    "import .a.b\n",
    "import .a.b as c\n",
    "from a import b\n",
    "from a import b as c\n",
    "from .a import b\n",
    "from .a import b as c\n",
    "from ..a import b\n",
    "from ..a import b as c\n",
    "from . import a\n",
    "from . import a as b\n",
    "from .. import a\n",
    "from .. import a as b\n",
    "from ... import a\n",
    "from ... import a as b\n",
    "from a import (b, d as e)\n",
    "from a import (b as c, d)\n",
    "from a import (b, d)\n",
    "from a import (b as c, d as e)\n",
]

MAPPINGS = [
    "a: HashMap[uint256, uint256]\n",
    "b: HashMap[uint256, HashMap[uint256, uint256]]\n",
    "c: HashMap[A, HashMap[B, HashMap[C, D]]]\n",
]

TUPLES = [
    "a: (,)\n",
    "b: (A,)\n",
    "c: (A, B)\n",
    "d: (A, B,)\n",
    "e: (A, B, C)\n",
    "f: (A, B, C,)\n",
]

CONSTANTS = [
    "a: constant(uint256) = 0\n",
]

EVENTS = [
    "event A:\n    pass\n",
    "event A:\n    a: uint256\n    b: indexed(uint256)\n",
]

STRUCTS = [
    "struct A:\n    pass\n",
    "struct A:\n    a: uint256\n    b: uint256\n",
]

INTERFACES = [
    "interface A:\n    def foo(): nonpayable\n",
    "interface A:\n    def bar() -> uint256: view\n",
    "interface A:\n    def baz(a: uint256): payable\n",
    "interface A:\n    def biz(a: uint256) -> uint256: pure\n",
]

SOURCES = IMPORTS + MAPPINGS + TUPLES + CONSTANTS + EVENTS + STRUCTS + INTERFACES


@pytest.mark.parametrize("source", SOURCES)
def test_grammar(source):
    parse(source)

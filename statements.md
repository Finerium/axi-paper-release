# AXI-Fresh v2: the 62 problem statements (CC BY 4.0; rewritten from the issues and fixes, no issue text copied)

## fresh_parse_223 (r1chardj0n3s/parse, base 738447715c76)

Fractional seconds lose precision when parsing timestamps

Parsing an ISO 8601 timestamp with fractional seconds sometimes gives a microsecond value that is off by one:

```python
import parse

r = parse.parse("{:ti}", "2023-10-14T15:09:08.501902Z")
print(r[0].microsecond)
# 501901  (expected 501902)
```

It looks like the fraction goes through a float conversion somewhere and gets rounded down. The same problem can affect the other datetime formats that accept fractional seconds.

Expected: the microsecond value is taken exactly from the digits in the input. Fewer than six fractional digits are padded on the right (`.1` gives 100000), exactly six are used as they are (`.123456` gives 123456), and more than six are truncated to the first six (`.1234567` gives 123456).

## fresh_parse_221 (r1chardj0n3s/parse, base 5bfb45d9f308)

Grouping option in integer format specs is rejected

`str.format` supports a thousands separator in integer format specs (`format(1000000, ",d")` gives `'1,000,000'`, `format(1000000, "_d")` gives `'1_000_000'`, PEP 378 and PEP 515). `parse` is meant to invert `format`, but it does not accept these specs at all:

```python
import parse

parse.parse("a {:,d} b", "a 1,000,000 b")
# ValueError: format spec ',d' not recognised

parse.parse("a {:_d} b", "a 1_000_000 b")
# ValueError: format spec '_d' not recognised
```

Expected: a `,` or `_` grouping option between the width and the precision/type is accepted, and the matching grouped number is parsed to an `int`:

```python
parse.parse("a {:,d} b", "a 1,000,000 b").fixed[0]   # 1000000
parse.parse("a {:,d} b", "a -1,000,000 b").fixed[0]  # -1000000
parse.parse("a {:_d} b", "a 1_000_000 b").fixed[0]   # 1000000
parse.parse("a {:_d} b", "a -1_000_000 b").fixed[0]  # -1000000
```

Specs without a grouping option must behave exactly as before.

## fresh_parse_227 (r1chardj0n3s/parse, base 71b443f4de2e)

Zero-precision fixed-point formats cannot be parsed back

With a precision of 0, Python formats a float without a decimal point: `format(20.0, ".0f")` is `'20'` and `format(20.0, "02.0f")` is `'20'`. `parse` cannot read this output back with the same format string:

```python
import parse

parse.parse("a {:.0f} b", "a 12 b")
# None
parse.parse("foo_{:02.0f}t", "foo_20t")
# None
```

The `f` (and `F`) types always require a decimal point and at least one digit after it, whatever the precision.

Expected: when the precision is 0, `f` and `F` fields match plain digits (`parse.parse("a {:.0f} b", "a 12 b")` gives `12.0`, `parse.parse("foo_{:02.0f}t", "foo_20t")` gives `20.0`). A value with a decimal point should not match a zero-precision field (`parse.parse("a {:.0f} b", "a 12.0 b")` gives `None`), since `format` never produces one. Other precisions keep their current behaviour.

## fresh_mashumaro_313 (Fatal1ty/mashumaro, base b384b41c4b92)

JSON Schema generation fails for dataclasses with `slots=True`

`build_json_schema` raises for a dataclass declared with `slots=True` when a field has a default value:

```python
from dataclasses import dataclass
from mashumaro.jsonschema import build_json_schema

@dataclass(slots=True)
class DataClassWithSlots:
    no_default: str
    has_default: int = 42

build_json_schema(DataClassWithSlots)
# TypeError: descriptor 'no_default' for 'DataClassWithSlots' objects doesn't apply to a '...' object
```

The same class without `slots=True` works and gives:

```json
{"type": "object", "title": "DataClassWithSlots", "properties": {"no_default": {"type": "string"}, "has_default": {"type": "integer", "default": 42}}, "additionalProperties": false, "required": ["no_default"]}
```

With slots, the class attributes for the fields are slot member descriptors rather than default values, and the schema builder seems to pick them up as defaults.

Expected: the schema for the slotted dataclass is the same as for the plain one: `has_default` keeps `default: 42`, and `no_default` has no default and stays required.

## fresh_mashumaro_344 (Fatal1ty/mashumaro, base 0ad3eaed34f0)

Deserializing a union that contains a PEP 695 type alias always fails

On Python 3.12+, a field whose type is a union including a `type` alias can be serialized but not deserialized:

```python
from dataclasses import dataclass
from mashumaro import DataClassDictMixin

type ScalarAlias = int

@dataclass
class MyClass(DataClassDictMixin):
    x: ScalarAlias | list[int]

MyClass([1, 2]).to_dict()      # {'x': [1, 2]}  (works)
MyClass.from_dict({"x": 1})
# InvalidFieldValue: Field "x" of type Union[ScalarAlias, list[int]] in MyClass has invalid value 1
MyClass.from_dict({"x": [1, 2]})
# InvalidFieldValue: Field "x" of type Union[ScalarAlias, list[int]] in MyClass has invalid value [1, 2]
```

Even the list variant, which does not involve the alias, fails. The packing side handles the alias, the unpacking side does not.

Expected: `MyClass.from_dict({"x": 1}) == MyClass(1)` and `MyClass.from_dict({"x": [1, 2]}) == MyClass([1, 2])`, the same as when the field is declared as `int | list[int]`.

## fresh_mashumaro_335 (Fatal1ty/mashumaro, base e6894ef48c48)

Type arguments are bound to the wrong type variables when `Generic[...]` is listed in the bases

The Python docs say that when a class lists `Generic[...]` among its bases, the order of its type parameters is the order given in `Generic[...]`. mashumaro instead orders them by first appearance across all bases, so a subscripted subclass gets its type arguments assigned to the wrong variables:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar
from mashumaro import DataClassDictMixin

T = TypeVar("T"); S = TypeVar("S"); K = TypeVar("K")

@dataclass
class Base(DataClassDictMixin, Generic[T]):
    kind: str = "base"

class NotSerializable:
    pass

@dataclass
class Extended(Base[K], Generic[S, K]):
    payload: S | None = None

@dataclass
class Sub(Extended[Base, NotSerializable]):   # S=Base, K=NotSerializable
    pass
# UnserializableField: Field "payload" of type NotSerializable in Sub is not serializable
```

`payload` is declared as `S`, which is `Base` here, but mashumaro resolves it to `NotSerializable`. The same happens with the PEP 695 syntax (`class Extended[S: Base, K](Base[K])`), where the class's own type parameter list must define the order.

Expected: `Sub` can be built, and `Sub(payload=Base()).to_dict() == {"kind": "base", "payload": {"kind": "base"}}` for both spellings. Classes without an explicit `Generic[...]` base keep the current order.

## fresh_queuelib_89 (scrapy/queuelib, base c04e41f49ab2)

`RoundRobinQueue.pop()` loses falsy items

When an item that is falsy (for example `b""`) is pushed into a `RoundRobinQueue`, `pop()` does not return it. The item is removed from the queue but the caller gets `None`, or the next item, as if the queue had skipped it:

```python
from queuelib import RoundRobinQueue
from queuelib.queue import FifoMemoryQueue

q = RoundRobinQueue(lambda key: FifoMemoryQueue())
q.push(b"", "a")
len(q)    # 1
q.pop()   # None   (expected b"")
len(q)    # 0

q.push(b"one", "a"); q.push(b"", "b"); q.push(b"two", "c")
[q.pop(), q.pop(), q.pop()]
# [b'one', b'two', None]   (expected [b'one', b'', b'two'])
```

This happens with every internal queue type, in memory or on disk. Expected: `pop()` returns every pushed item, falsy or not, in round-robin key order, and returns `None` only when the queue is empty.

## fresh_tomlkit_520 (python-poetry/tomlkit, base ae1b6790d99b)

`tomlkit.key()` with a one-element list creates a key that cannot be looked up

`tomlkit.key()` accepts either a string or a list of strings; a list is meant for dotted keys. A list with a single element produces a key that renders like a plain key but does not behave like one:

```python
import tomlkit

doc = tomlkit.document()
doc.append(tomlkit.key(["foo"]), "value")
print(doc.as_string())   # foo = "value"
"foo" in doc             # False
doc["foo"]               # NonExistentKey: 'Key "foo" does not exist.'
```

Expected: `tomlkit.key(["foo"])` is equivalent to `tomlkit.key("foo")`, so that after the append `"foo" in doc` is true, `doc["foo"] == "value"` and the document still renders as `foo = "value"\n`. Lists with two or more elements must keep producing dotted keys (`tomlkit.key(["foo", "bar"])` renders as `foo.bar = 1`).

## fresh_tomlkit_471 (python-poetry/tomlkit, base 8e32f9cb7fcf)

`dumps(..., sort_keys=True)` ignores `sort_keys` for parsed documents

`tomlkit.dumps` has a `sort_keys` argument. It works for plain dicts, but a document returned by `tomlkit.loads`/`parse` is written out unsorted:

```python
import tomlkit

doc = tomlkit.loads('zzz = 1\naaa = "foo"')
tomlkit.dumps(doc, sort_keys=True)
# 'zzz = 1\naaa = "foo"'          (keys not sorted)
tomlkit.dumps(dict(doc), sort_keys=True)
# 'aaa = "foo"\nzzz = 1\n'        (sorted)
```

Expected: `tomlkit.dumps(doc, sort_keys=True)` returns `'aaa = "foo"\nzzz = 1\n'` for the document above, the same as for the equivalent dict. With `sort_keys=False` (the default), parsed documents, tables and inline tables must still be dumped exactly as they were parsed, preserving formatting.

## fresh_tomlkit_499 (python-poetry/tomlkit, base 5ceae3e55353)

Appending to a comma-first array produces invalid TOML

Some TOML files write multiline arrays in "comma-first" style, where each element after the first starts with the separator:

```python
import tomlkit

doc = tomlkit.parse('a = [\n      1 # one\n     ,2\n    ]\n')
doc["a"].append(99)
print(doc.as_string())
```

prints

```
a = [
      1 # one
     ,2,
     ,99
    ]
```

The element `2` gets a trailing comma although the new element already brings its own leading comma, so the output has two separators in a row and `tomlkit.parse()` rejects it (`UnexpectedCharError: Unexpected character: ','`). `insert()` in the middle of such an array has the same problem.

Expected: appending or inserting into a comma-first array keeps exactly one separator between elements. The result must parse back to the right values (`[1, 2, 99]` after the append; `[1, 99, 2]` after `insert(1, 99)`) and must round-trip (`parse(s).as_string() == s`). Inserting at position 0 must also work and give a valid array.

## fresh_tomlkit_532 (python-poetry/tomlkit, base 9c126774d3f3)

Inline tables accept a (non-inline) table and then serialize invalid TOML

A `tomlkit` `Table` can be put into an `InlineTable`, which TOML does not allow, and the result is garbage:

```python
import tomlkit

table = tomlkit.table()
table.append("a", 1)
inline = tomlkit.inline_table()
inline.append("table", table)
print(inline.as_string())
# '{table = a = 1\n}'
```

Putting the result in a document gives `x = {table = a = 1\n}`, which `tomlkit.parse` then rejects. The same happens with `inline["table"] = table`.

Expected: adding a `Table` to an inline table, through `append()` or item assignment, raises `ValueError` with a message saying that inline tables cannot contain a table (the message must contain the words "cannot contain a table"), and the inline table is left unchanged. Other values, including nested inline tables and plain dicts, keep working.

## fresh_tomlkit_563 (python-poetry/tomlkit, base 495a42ecc911)

tomlkit scalar items are reported as sequences

Every tomlkit item class inherits `__getitem__`, `__setitem__` and `__delitem__` from the `Item` base class. They only raise `TypeError`, but because they exist, CPython's sequence protocol check (`PySequence_Check`, which code like NumPy, `memoryview` consumers and C extensions use) reports scalar values such as `Float` and `Integer` as sequences:

```python
import ctypes, tomlkit

value = tomlkit.parse("a = [1.0, 2.0, 3.0]")["a"][0]   # tomlkit.items.Float
check = ctypes.pythonapi.PySequence_Check
check.argtypes = [ctypes.py_object]
check.restype = ctypes.c_int
check(value)   # 1, but a float is not a sequence
```

C code that branches on "is this a sequence?" then treats a TOML float as a container and fails or behaves differently than for a plain `float`.

Expected: scalar items (`Float`, `Integer` and the other non-container items) are not sequences, so the check above returns 0 like it does for `1.0`. Containers (tables, inline tables, arrays) must keep supporting item access, assignment and deletion.

## fresh_w3lib_253 (scrapy/w3lib, base 61db33b20f61)

`safe_url_string` strips the brackets from IPv6 hosts

`w3lib.url.safe_url_string` breaks URLs whose host is an IPv6 literal. The brackets around the address are dropped, so the result is no longer a valid URL and the port can no longer be told apart from the address:

```python
from w3lib.url import safe_url_string

safe_url_string("http://[::1]:8080/path?q=1")
# 'http://::1:8080/path?q=1'
safe_url_string("https://[2402:4e00:40:40::2:3b6]")
# 'https://2402:4e00:40:40::2:3b6'
```

Expected: IPv6 hosts keep their brackets, and the rest of the URL is handled as before:

```python
safe_url_string("http://[::1]")                                # 'http://[::1]'
safe_url_string("http://[::1]:8080/path?q=1")                  # 'http://[::1]:8080/path?q=1'
safe_url_string("https://[2402:4e00:40:40::2:3b6]:443")        # 'https://[2402:4e00:40:40::2:3b6]:443'
safe_url_string("http://[2a01:5cc0:1:2::4]")                   # 'http://[2a01:5cc0:1:2::4]'
```

Invalid IPv6 literals (for example `http://[2a01:5cc0:1:2:3:4]`) must still raise `ValueError`, and IDNA encoding of regular host names must not change.

## fresh_w3lib_300 (scrapy/w3lib, base 67046530caec)

`to_unicode` does not decode byte 0x80 as the euro sign in GB18030

The WHATWG Encoding Standard, which browsers follow, decodes a single byte `0x80` in GB18030 as `€` (U+20AC), for compatibility with GBK/CP936. Python's `gb18030` codec rejects that byte, so `w3lib.encoding.to_unicode` turns it into the replacement character:

```python
from w3lib.encoding import to_unicode

to_unicode(b"100\x80", "gb18030")   # '100\ufffd'   (expected '100€')
```

Expected: for every encoding name that resolves to GB18030 (`"gb18030"`, `"GB18030"`, `"gb18030_2000"`, ...), a lone lead byte `0x80` decodes to `€`. Other undecodable bytes are still replaced with U+FFFD, and valid sequences decode as before:

```python
to_unicode(b"\x80", "gb18030")       # '€'
to_unicode(b"\xff\x80", "gb18030")   # '\ufffd€'
to_unicode(b"\x81\x80", "gb18030")   # '\u4e90'
to_unicode(b"\xa2\xe3", "gb18030")   # '€'
to_unicode(b"\xff", "gb18030")       # '\ufffd'
```

Decoding with other encodings must not change.

## fresh_w3lib_297 (scrapy/w3lib, base 67046530caec)

`safe_url_string` leaves URLs with a query but no path without a `/` path

For special schemes (http, https, ftp, file, ws, wss), a URL like `https://example.com?a=b` has an empty path. `safe_url_string` keeps it that way, and code that builds an HTTP request target from the path and the query then sends `?a=b` as the target instead of `/?a=b`:

```python
from w3lib.url import safe_url_string

safe_url_string("https://example.com?a=b")   # 'https://example.com?a=b'
```

Expected: when the scheme is special, the path is empty and the query is non-empty, the result gets `/` as its path, as the URL Standard does:

```python
safe_url_string("https://example.com?a")      # 'https://example.com/?a'
safe_url_string("https://example.com?a=")     # 'https://example.com/?a='
safe_url_string("https://example.com?a=b")    # 'https://example.com/?a=b'
safe_url_string("https://example.com?ñ")      # 'https://example.com/?%C3%B1'
safe_url_string("wss://example.com?a=b")    # 'wss://example.com/?a=b'
```

The `/` is added only when the query is non-empty. Unchanged cases: URLs that already have a path, URLs without a query, and non-special schemes (`a://example.com?x` stays as is). Query encoding rules are not affected.

## fresh_voluptuous_542 (alecthomas/voluptuous, base 73237e9014f5)

`Number` validator raises a raw `TypeError` for "Infinity" and "NaN"

The `Number` validator with `precision`/`scale` reports bad input as `Invalid`, except for non-finite values, which escape as a plain `TypeError` and bypass the schema's error handling:

```python
from voluptuous import Schema, Number

schema = Schema({"number": Number(precision=6, scale=2)})
schema({"number": "abc"})
# MultipleInvalid: Value must be a number enclosed with string for dictionary value @ data['number']
schema({"number": "NaN"})
# TypeError: infinity and NaN have no precision
```

Expected: `"Infinity"`, `"-Infinity"` and `"NaN"` are rejected like any other value that is not a valid number. The schema raises `MultipleInvalid` and its string is `"Value must be a number enclosed with string for dictionary value @ data['number']"` (or the validator's custom `msg` when one is given).

## fresh_voluptuous_544 (alecthomas/voluptuous, base aa158af6f740)

Value-transforming validators are not applied to set elements

For lists and dicts, voluptuous returns the validated values, so validators that transform their input (such as `Coerce`) change the output. For `set` and `frozenset` schemas the elements are validated but the original input is returned unchanged:

```python
from voluptuous import Schema, Coerce

Schema([Coerce(int)])(["1", "2"])    # [1, 2]
Schema({Coerce(int)})({"1", "2"})    # {'1', '2'}   (expected {1, 2})
```

Expected: set and frozenset schemas return a new collection of the same type that contains the values returned by the validators:

```python
Schema({Coerce(int)})({"1", "2"}) == {1, 2}
result = Schema(frozenset([Coerce(int)]))(frozenset({"1", "2"}))
result == frozenset({1, 2}) and isinstance(result, frozenset)
Schema({int})({1, 2}) == {1, 2}
```

Validation errors for set elements must be reported as before.

## fresh_voluptuous_546 (alecthomas/voluptuous, base aa158af6f740)

`repr()` of `Invalid` errors drops the path and the error type

`str()` of a voluptuous `Invalid` error includes the error type and the path, but `repr()` falls back to the exception default and shows only the bare message. Logs and `MultipleInvalid` reprs therefore lose the context:

```python
from voluptuous import Schema, MultipleInvalid

try:
    Schema({"k": int})({"k": "x"})
except MultipleInvalid as e:
    err = e.errors[0]
    str(err)    # "expected int for dictionary value @ data['k']"
    repr(err)   # "TypeInvalid('expected int')"
    repr(e)     # "MultipleInvalid([TypeInvalid('expected int')])"
```

Expected: `repr()` of an `Invalid` (and of every subclass) is the class name with the full `str()` text as its argument, e.g. `repr(err) == 'TypeInvalid("expected int for dictionary value @ data[\'k\']")'`, and that text also appears inside `repr()` of the enclosing `MultipleInvalid`.

## fresh_pygments_3171 (pygments/pygments, base 2a131b1adf32)

Ruby lexer duplicates the body of an unterminated heredoc

When a Ruby heredoc is never terminated (for example a truncated snippet), the Ruby lexer emits its body twice, so the highlighted output contains text that is not in the input:

```python
from pygments.lexers import RubyLexer

text = 'exec_query(<<-end_sql)\n  SELECT a.attname\n  FROM pg_attribute a'
print(repr("".join(v for _, v in RubyLexer().get_tokens(text))))
# 'exec_query(<<-end_sql)\n  SELECT a.attname\n  FROM pg_attribute a\n  SELECT a.attname\n  FROM pg_attribute a\n'
```

Expected: every input character is emitted exactly once, so the joined token values equal the input plus the trailing newline that `get_tokens` adds. The lines of the unterminated heredoc body are reported as `Error` tokens, one per line (`'  SELECT a.attname\n'` and `'  FROM pg_attribute a\n'` here), and nothing after them is lexed twice.

## fresh_pygments_3180 (pygments/pygments, base 076a676155ad)

Styles cannot use the color `transparent`

CSS supports `transparent` as a color, but a Pygments `Style` that uses it cannot even be defined:

```python
from pygments.style import Style
from pygments.token import Name

class TransparentStyle(Style):
    styles = {Name: "transparent bg:transparent border:transparent"}
# AssertionError: wrong color format 'transparent'
```

Expected: `transparent` is accepted wherever a color is, for the foreground, `bg:` and `border:`. `TransparentStyle.style_for_token(Name)` reports `'transparent'` for `color`, `bgcolor` and `border`, and the HTML formatter passes the value through unchanged: `HtmlFormatter(style=TransparentStyle).get_style_defs()` contains `.n { color: transparent; background-color: transparent; border: 1px solid transparent } /* Name */`. Existing hex colors and `var(...)`/`calc(...)` values behave as before.

## fresh_pygments_3204 (pygments/pygments, base b6aaaca75fd3)

TeX lexer does not highlight math inside LaTeX math environments

The TeX lexer highlights math between `$...$`, `$$...$$`, `\(...\)` and `\[...\]`, but not inside the standard math environments. Their content is lexed as plain text:

```python
from pygments.lexers import TexLexer

list(TexLexer().get_tokens(r"\begin{equation}x+1\end{equation}"))
# [..., (Token.Text, 'equation'), ..., (Token.Text, 'x+1'), ...]
list(TexLexer().get_tokens(r"$x+1$"))
# [..., (Token.Name.Builtin, 'x'), (Token.Operator, '+'), (Token.Literal.Number, '1'), ...]
```

Expected: the bodies of the `math`, `displaymath`, `equation`, `equation*`, `align` and `align*` environments are lexed with the same math rules as inline math. For `\begin{equation}x+1\end{equation}` the tokens include `(Name.Builtin, 'x')` and `(Operator, '+')`. The environment ends at the matching `\end{...}`, after which normal TeX lexing resumes.

## fresh_schema_347 (keleshev/schema, base 340d3f0596b9)

`TypeError` instead of `SchemaError` when a tuple dict key fails validation

When a dictionary schema uses a tuple as a key and the value for that key is invalid, building the error message crashes:

```python
from schema import Schema

Schema({("a", "b"): int}).validate({("a", "b"): "not-an-int"})
# TypeError: not all arguments converted during string formatting

Schema({(): [(str,)]}).is_valid({(): ["foo", ("bar",)]})
# TypeError: not enough arguments for format string
```

Expected: a `SchemaError` is raised as for any other key, and its message names the key with the usual `Key '...' error:` prefix; for the first example the error text contains `Key '('a', 'b')' error:`. `is_valid()` returns `False` instead of raising.

## fresh_schema_348 (keleshev/schema, base 27e268d4fc36)

Custom `error=` on a key schema is lost when the key is reported as wrong

When a dictionary key schema has its own `error=` message and a data key does not match it, the data key ends up reported as a wrong key and the custom message disappears:

```python
from schema import Schema, Regex, SchemaWrongKeyError

schema = Schema({Regex(r"^[A-Z][A-Za-z0-9]+$", error="Invalid profile name"): dict})
try:
    schema.validate({"Foo": {}, "bar": {}})
except SchemaWrongKeyError as e:
    print(e.code)
# Wrong key 'bar' in {'Foo': {}, 'bar': {}}
```

Expected: when a data key is reported as wrong and a key schema that rejected it carries a custom error, that message is surfaced, so `e.code` is `"Invalid profile name"` above. The same holds for other key schemas with `error=`, e.g. `And(str, str.isupper, error="must be upper")` with data `{"FOO": 1, "bar": 2}` gives `e.code == "must be upper"`. Without a custom error, the default `Wrong key ...` message is unchanged.

## fresh_cron_descriptor_108 (Salamek/cron-descriptor, base 8883990d1eac)

Validation of malformed month or weekday lists takes exponential time

`ExpressionValidator.validate` checks month and day-of-week lists with a regular expression that backtracks catastrophically. A long comma-separated list with a bad last element takes exponential time to reject:

```python
from cron_descriptor.ExpressionValidator import ExpressionValidator

ExpressionValidator().validate("* * * " + ",".join(["1"] * 1000) + "X *")
# does not finish in any reasonable time (it should raise FormatError at once)
```

The same happens in the day-of-week field and with names (`JAN,JAN,...X`, `MON,MON,...X`).

Expected: such input is rejected with `FormatError` quickly (well under a second). The accepted syntax must stay the same. Each list element is a number, a number range, a three-letter name or a name range, and names and numbers may be mixed, as in `* * * JAN,2,MAR-MAY,6-12 *`, `* * * 1-2,mar,4,may-jun *`, `* * * * SUN,1,TUE-THU,5-6` and `* * * * 0-1,tue,3,thu-sat`. Empty elements (`JAN,,FEB`, `JAN,`, `,MON`), trailing garbage (`JAN,2-3X`) and lists longer than 12 months or 7 weekdays still raise `FormatError`.

## fresh_cron_descriptor_101 (Salamek/cron-descriptor, base d1bc211c5be4)

Comma lists that contain a step expression cannot be described

`get_description` fails, or produces a wrong description, when one field mixes a comma list with a step (`/`) element:

```python
from cron_descriptor import get_description

get_description("0 0,6-23/2 * * *")
# FormatError
get_description("5,10-30/5 9 * * *")
# 'Every 5 minutes, minutes 5,10 through 30 past the hour, between 09:00 AM and 09:59 AM'
```

A plain step (`0 6-23/2 * * *`) and a plain list (`0 0,12 * * *`) work.

Expected: each list element is described on its own, and a step element is described as an interval within its range:

```python
get_description("0 0,6-23/2 * * *")
# 'At 12:00 AM and every 2 hours, 06:00 AM through 11:59 PM'
get_description("5,10-30/5 9 * * *")
# 'At 5 and every 5 minutes, 10 through 30 minutes past the hour, between 09:00 AM and 09:59 AM'
get_description("0 0,12,18-23/2 * * *")
# 'At 12:00 AM, 12:00 PM, and every 2 hours, 06:00 PM through 11:59 PM'
```

(These use the default options.) Descriptions of expressions without such mixes must not change.

## fresh_python_tabulate_386 (astanin/python-tabulate, base 8ca340f59e07)

asciidoc output puts the column alignment after the width

For `tablefmt="asciidoc"`, tabulate writes the column specifiers as width followed by alignment:

```python
from tabulate import tabulate

print(tabulate([["spam", 42]], ["item", "qty"], tablefmt="asciidoc"))
# [cols="8<,7>",options="header"]
# |====
# ...
```

AsciiDoc's column specifier syntax puts the horizontal alignment before the width (`<8`, `>7`). In the current order AsciiDoc ignores the alignment, so every column is rendered with the default alignment.

Expected: the specifiers are written alignment first, e.g. `[cols="<8,>7",options="header"]` for the table above, and `[cols="<6,>10"]` for a table without headers. The rest of the asciidoc output is unchanged.

## fresh_markdown_it_py_416 (executablebooks/markdown-it-py, base c92ed7b02d09)

IndexError when a document ends with a blockquote marker inside a quoted table

With tables enabled, rendering a document whose last line is a bare `>` that continues a blockquote containing a table crashes:

```python
from markdown_it import MarkdownIt

MarkdownIt().enable("table").render("> | a | b |\n> |---|---|\n>")
# IndexError: string index out of range
```

The crash also happens with HTML disabled (`MarkdownIt("commonmark", {"html": False}).enable("table")`). Block rules that are asked whether the next line terminates the table read a character past the end of the source.

Expected: rendering this input does not raise for either configuration, and it produces the normal output for a blockquote containing a table. Other input must render as before.

## fresh_pyparsing_638 (pyparsing/pyparsing, base 057a2e6d1b83)

`Located` includes leading whitespace in `locn_start` for compound expressions

`pp.Located` is supposed to report where the wrapped expression's match starts. For a single token it does, but when the wrapped expression is a `MatchFirst` (`|`) or an `And` (`+`), the whitespace that the inner expressions skip ends up inside the reported span:

```python
import pyparsing as pp

abc = pp.Keyword("abc")
pp.Located(abc).parse_string("   abc")          # [3, ['abc'], 6]
r = pp.Located(abc | abc).parse_string("   abc")
r.as_list()                                       # [0, ['abc'], 6]   (expected [3, ['abc'], 6])
```

Expected: `locn_start` points to the first character of the match for every kind of wrapped expression. `"   abc"[r.locn_start:r.locn_end] == "abc"` above, and for `pp.Located(pp.Literal("ID") + pp.Word(pp.alphanums))` on `"   ID PARI12345678"` the slice is `"ID PARI12345678"`. An expression that keeps its whitespace (`leave_whitespace()`), e.g. `pp.Located(pp.Word(" abc").leave_whitespace())` on `"   abc"`, must still report `locn_start == 0`.

## fresh_jsonpickle_588 (jsonpickle/jsonpickle, base 992cdefdd651)

A `defaultdict` key named "default_factory" is lost when encoding

jsonpickle stores a `defaultdict`'s factory under the key `"default_factory"` in the same JSON object as the dict's items. If the dict itself has a key with that name, the factory overwrites the item and the value is lost:

```python
import collections, jsonpickle

d = collections.defaultdict(int)
d["default_factory"] = 42
d["other_key"] = 100
r = jsonpickle.decode(jsonpickle.encode(d))
dict(r)   # {'other_key': 100}   (the "default_factory" item is gone)
```

Expected: the round trip preserves both the factory and all items, so `isinstance(r, collections.defaultdict)`, `r.default_factory is int`, `r["default_factory"] == 42` and `r["other_key"] == 100`. JSON produced by earlier versions, where the factory is stored under `"default_factory"`, must still decode.

## fresh_w3lib_266 (scrapy/w3lib, base d5877fe47986)

`get_meta_refresh` is quadratic on inputs with many unclosed `<meta` tags

`w3lib.html.get_meta_refresh` slows down quadratically when the document contains many `<meta` openings without a closing `>`. Doubling the input roughly quadruples the time:

```python
import time
from w3lib.html import get_meta_refresh

for n in (5000, 10000, 20000):
    t = time.time()
    get_meta_refresh("<meta " * n)
    print(n, round(time.time() - t, 2))
# 5000 0.05 / 10000 0.19 / 20000 0.74 ...
```

At 80,000 repetitions a single call takes many seconds, and a hostile page can stall a crawler.

Expected: `get_meta_refresh` runs in roughly linear time on such input. `get_meta_refresh("<meta " * 80000)` returns `(None, None)` well under a second, and a real refresh tag after that prefix is still found: appending `'<meta http-equiv="refresh" content="3; url=http://example.org/next/">'` gives `(3.0, "http://example.org/next/")`. All current results for well-formed documents must stay the same.

## fresh_parse_230 (r1chardj0n3s/parse, base 4ded1bc8897b)

Uppercase `E`, `G` and `X` format types are not supported

`str.format` supports uppercase versions of the exponent, general and hex types, and `parse` is meant to read back what `format` produces. The uppercase types are rejected:

```python
import parse

format(1.1e10, "E")                          # '1.100000E+10'
parse.parse("a {:E} b", "a 1.10000E10 b")
# ValueError: format spec 'E' not recognised
parse.parse("a {:X} b", "a FF b")
# ValueError: format spec 'X' not recognised
```

Expected: `E`, `G` and `X` work exactly like `e`, `g` and `x`. They accept upper- or lowercase digits and exponent markers, and give the same values:

```python
parse.parse("a {:E} b", "a 1.0E10 b")[0]            # 10000000000.0
parse.parse("a {:E} b", "a -1.0E10 b")[0]           # -10000000000.0
parse.parse("a {:E} b", "a INF b")[0]               # inf
parse.parse("a {:G} b", "a 1E10 b")[0]              # 10000000000.0
parse.parse("a {:X} b", "a 0X1234567890ABCDEF b")[0]  # 0x1234567890ABCDEF
parse.parse("a {:X} b", "a 1234567890abcdef b")[0]    # 0x1234567890ABCDEF
```

## fresh_pyparsing_644 (pyparsing/pyparsing, base ecb1b14dbf1a)

`set_debug()` output is corrupted by control characters in the input line

The default debug action prints the current input line and a caret under the match location. Control characters in the line are printed raw, so a `\r` moves the terminal cursor back to column 0 and the debug output becomes unreadable:

```python
import pyparsing as pp

word = pp.Word(pp.alphas).set_name("word").set_debug()
word[...].parse_string("abc\rdef", parse_all=True)
```

Expected: control characters (U+0000 to U+001F and U+007F) in the printed line are shown escaped the way `repr()` shows them (`\r`, `\t`, `\x00`, ...), and the caret stays under the match location in the escaped line. For the example the output is:

```
Match word at loc 0(1,1)
  abc\rdef
  ^
Matched word -> ['abc']
Match word at loc 4(1,5)
  abc\rdef
       ^
Matched word -> ['def']
Match word at loc 7(1,8)
  abc\rdef
          ^
Match word failed, ParseException raised: Expected word, found end of text  (at char 7), (line:1, col:8)
```

The reported `loc`, line and column numbers stay those of the original string. Lines without control characters print exactly as before.

## fresh_python_fastjsonschema_209 (horejsek/python-fastjsonschema, base 9c385ea8055e)

Validation crashes with `UnboundLocalError` when a `not` schema is combined with `additionalProperties`

A schema with `additionalProperties: false` and a `not` subschema that checks object properties compiles fine, but validating an ordinary object crashes inside the generated code:

```python
import fastjsonschema

validate = fastjsonschema.compile({
    "type": "object",
    "properties": {"a": {}, "b": {}},
    "additionalProperties": False,
    "not": {"properties": {"a": {}, "b": {}}, "required": ["a", "b"]},
})
validate({"a": 1})
# UnboundLocalError: cannot access local variable 'data_keys' where it is not associated with a value
```

Helper variables created while generating the `not` branch seem to be reused afterwards, outside the branch, where they were never assigned.

Expected: `validate({"a": 1})` and `validate({"b": 2})` return their input unchanged, and `validate({"a": 1, "b": 2})` raises `JsonSchemaValueException` with the message `data must NOT match a disallowed definition` (rule `not`).

## fresh_python_fastjsonschema_202 (horejsek/python-fastjsonschema, base 5f81f448c1cb)

An empty `patternProperties` object generates invalid code

`patternProperties: {}` is valid JSON Schema (it constrains nothing), but fastjsonschema produces Python source that does not compile:

```python
import fastjsonschema

fastjsonschema.validate({"type": "object", "patternProperties": {}}, {})
# IndentationError: expected an indented block after 'for' statement ...
```

Expected: an empty `patternProperties` is accepted and has no effect, so the call above returns `{}` and any object validates as it would without the keyword. Non-empty `patternProperties` must behave as before.

## fresh_python_fastjsonschema_212 (horejsek/python-fastjsonschema, base a2fb34ce02b2)

Non-finite float defaults generate code that fails with `NameError`

With defaults enabled (the default), fastjsonschema writes each schema `default` into the generated code with `repr()`. For NaN and infinity that gives `nan` and `inf`, which are not names in the generated module:

```python
import fastjsonschema

fastjsonschema.validate({
    "type": "object",
    "properties": {"a": {"type": "number", "default": float("nan")}},
}, {})
# NameError: name 'nan' is not defined
```

Expected: NaN, `inf` and `-inf` work as defaults wherever defaults are filled in, including inside nested default values:

```python
out = fastjsonschema.validate({"type": "object", "properties": {
    "a": {"type": "number", "default": float("nan")},
    "b": {"type": "number", "default": float("inf")},
    "c": {"type": "number", "default": float("-inf")}}}, {})
# math.isnan(out["a"]); out["b"] == inf; out["c"] == -inf

fastjsonschema.validate({"type": "array", "items": [{"type": "number", "default": float("nan")}]}, [])
# a one-element list containing NaN

fastjsonschema.validate({"type": "object", "properties": {
    "a": {"default": {"x": float("inf"), "y": [1, float("nan")]}}}}, {})
# out["a"]["x"] == inf and out["a"]["y"][1] is NaN
```

Other defaults are generated as before. Error messages that embed the schema definition must also not break when it contains such values.

## fresh_python_fastjsonschema_210 (horejsek/python-fastjsonschema, base a2fb34ce02b2)

`UnboundLocalError` when `minItems`/`maxItems` are combined with `minLength`/`maxLength`

A schema that has no `type` and mixes array and string length keywords crashes on a valid list:

```python
import fastjsonschema

fastjsonschema.validate({"minItems": 1, "minLength": 1}, ["str"])
# UnboundLocalError: cannot access local variable 'data_len' where it is not associated with a value
fastjsonschema.validate({"maxItems": 2, "maxLength": 2}, ["a"])
# same error
```

The generated code computes the length helper inside the string branch only, then reuses it in the array branch, which runs when the data is a list.

Expected: both calls return their input (the list satisfies the item constraints, and the string constraints do not apply to a list). In general, a helper variable must only be reused where the code that defines it is guaranteed to have run. Schemas that previously validated correctly must keep doing so.

## fresh_docopt_ng_71 (jazzband/docopt-ng, base fab01f5f19c9)

Repeated option values are duplicated when the usage has several alternatives

When an option that can repeat (`[--to=SITE]...`) appears in more than one usage pattern, the parsed list contains duplicate values:

```python
from docopt import docopt

doc = '''
Usage:
    test.py [--to=SITE]... [--] FILE...
    test.py [--to=SITE]... --config CONFIG [[--] FILE...]

Options:
    --config CONFIG     Configuration file.
    --to=SITE           Target site
'''
docopt(doc, "--to a --to b c")
# {'--': False, '--config': None, '--to': ['a', 'b', 'b'], 'FILE': ['c']}
```

Trying one alternative seems to change the option objects that the next alternative then sees.

Expected: the result is `{'--': False, '--config': None, '--to': ['a', 'b'], 'FILE': ['c']}`, the values given on the command line, each exactly once. Trying one usage alternative must not affect the outcome of another.

## fresh_pyfakefs_1332 (pytest-dev/pyfakefs, base 6b77856b216e)

`os.ftruncate` always fails with `EBADF` under pyfakefs

With the fake filesystem active, `os.ftruncate` rejects a perfectly valid file descriptor:

```python
import os
from pyfakefs.fake_filesystem_unittest import Patcher

with Patcher() as patcher:
    patcher.fs.create_file("/x", contents="0123456789012345")
    fd = os.open("/x", os.O_RDWR)
    os.ftruncate(fd, 10)
    # OSError: [Errno 9] Bad file descriptor
```

Expected: `os.ftruncate(fd, length)` works on a descriptor opened for writing, as on a real filesystem. After the call above, `os.stat("/x").st_size == 10` and reading the file gives `"0123456789"`. An invalid descriptor must still raise `OSError` with `EBADF`.

## fresh_pyfakefs_1277 (pytest-dev/pyfakefs, base ac6e70b7543f)

`size` of a fake file object is a method instead of a property

File objects returned by `open()` under pyfakefs (`FakeFileWrapper`) expose `size` as a method. Code that reads `f.size` as a value, like the attribute on other file-like objects, gets a bound method:

```python
from pyfakefs.fake_filesystem_unittest import Patcher

with Patcher() as patcher:
    patcher.fs.create_file("/x", contents="0123")
    f = open("/x")
    f.size     # <bound method FakeFileWrapper.size of ...>
    f.size()   # 4
```

Expected: `size` is a read-only property that returns the current size in bytes of the underlying fake file (`f.size == 4` above). It reflects the file's stored size: while a file opened in append mode has unflushed writes, `size` still reports the size before those writes, and a newly opened handle sees the size after the data was written and closed.

## fresh_geojson_242 (jazzband/geojson, base 68901cb26528)

`GeoJSON.to_instance` leaves the features of a FeatureCollection as plain dicts

Converting a FeatureCollection dictionary with `geojson.GeoJSON.to_instance` gives a `FeatureCollection` object, but its features are still plain dictionaries. As a result, validation fails:

```python
import geojson

obj = geojson.GeoJSON.to_instance({
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"foo": "bar"},
        "geometry": {"type": "Polygon",
                     "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
    }],
})
type(obj.features[0])   # dict
obj.is_valid            # AttributeError: is_valid
```

Expected: each feature given as a mapping is converted into a `geojson.Feature` (with its geometry converted too), so `isinstance(obj.features[0], geojson.Feature)` holds and `obj.is_valid` is `True`. Features that are already GeoJSON objects are kept as they are.

## fresh_pynetbox_783 (netbox-community/pynetbox, base d619dcf80812)

Probing a dunder attribute on a Record triggers a fetch and discards local edits

Accessing an attribute that a `pynetbox` `Record` does not have makes it fetch the full object from NetBox and re-parse it. This also happens for dunder names, which are never NetBox fields but get probed by libraries all the time: pydantic checks `hasattr(obj, "__pydantic_decorators__")`, and copy and pickle look up `__deepcopy__`, `__getstate__` and so on. Each probe fires an HTTP request and overwrites unsaved local changes with the server values:

```python
record = nb.dcim.devices.get(123)      # a lazily loaded Record
record.name = "modified"
hasattr(record, "__pydantic_decorators__")   # performs a full_details() fetch
record.name                                  # back to the server value
```

Expected: looking up a missing attribute whose name starts and ends with a double underscore raises `AttributeError` immediately. It does not call `full_details()`, makes no request, and leaves local modifications in place. Missing regular attributes are still fetched as before.

## fresh_pynetbox_782 (netbox-community/pynetbox, base 4008e3ff3e4a)

List-valued fields marked `JsonField` are turned into Records

A `Record` subclass can declare that a field holds raw JSON with `my_field = JsonField`. This works for dict values, but when the field holds a list of dicts, every dict in the list is still converted into a nested `Record`. Those items then have no `id`, which breaks `serialize()` and `save()`:

```python
from pynetbox.core.response import Record, JsonField

class PluginRecord(Record):
    my_json_list = JsonField

obj = PluginRecord({"id": 123, "my_json_list": [{"example": "bug"}, {"another": "value"}]}, api, None)
type(obj.my_json_list[0])   # Record, expected dict
```

Expected: a field marked `JsonField` keeps its value exactly as received, whether it is a dict or a list, with the items left as plain dicts. `obj.my_json_list` equals the input list, `obj.serialize()["my_json_list"]` returns it unchanged, and an untouched record reports no changes (`obj._diff()` is empty). Fields that are not marked keep the current conversion behaviour.

## fresh_pynetbox_785 (netbox-community/pynetbox, base d619dcf80812)

Assigning a subset of `custom_fields` is reported as a change to the omitted fields

NetBox applies `custom_fields` in a PATCH with merge semantics: fields left out of the body are not changed. pynetbox's change detection instead compares the whole dict, so assigning only the field you care about, even with its current value, marks `custom_fields` as changed and `save()` sends a needless PATCH:

```python
from pynetbox.core.response import Record

obj = Record({"id": 123, "name": "testsite",
              "custom_fields": {"testfield": "val", "other_field": None}}, None, None)
obj.custom_fields = {"testfield": "val"}
obj._diff()   # {'custom_fields'}  (nothing actually changed)
```

Expected: when both the original and the current `custom_fields` are dicts, only the keys present in the current value are compared:

- `obj.custom_fields = {"testfield": "val"}` gives an empty diff.
- `obj.custom_fields = {"testfield": "new_val"}` gives `{"custom_fields"}`.
- Assigning a key that was not in the original response (e.g. `{"brand_new_key": "val"}`) is a change.
- Setting a field explicitly to `None` remains the way to clear it.

Other fields are compared as before.

## fresh_pynetbox_811 (netbox-community/pynetbox, base 1f9c0113865e)

Pending local edits are lost when a Record is lazily re-fetched

When a lazily loaded `Record` is asked for an attribute it does not have yet, it fetches the full object and re-parses it. This overwrites attributes the caller has modified and also resets the baseline used for change tracking, so the edit disappears and a later `save()` sends nothing:

```python
record = Record(server_values, api, None)       # partial record with custom_fields={"my_field": "old"}
record.custom_fields["my_field"] = "new"
str(record)          # looks up `label`, which triggers the full fetch
record.custom_fields # {'my_field': 'old'}  (edit lost)
record.updates()     # {}                    (nothing to save)
```

The same happens to plain scalar fields (e.g. after `record.name = "x"`).

Expected: re-fetching keeps every field that has pending local changes, both the current value and its original baseline, so after the fetch `record.custom_fields == {"my_field": "new"}` and `record.updates() == {"custom_fields": {"my_field": "new"}}`. Fields without local changes are refreshed from the server response, and fields that were not loaded before become available.

## fresh_vermin_354 (netromdk/vermin, base 6879540c6499)

False violation for `typing_extensions` when targets are given

When vermin analyses code with explicit targets (for example `-t=3.8`) and violations are reported, the line

```python
import typing_extensions
```

is reported as a violation, although `typing_extensions` is an unversioned backport that works on every Python 3 version. Its rule has no real minimum versions, only vermin's internal "unversioned" placeholder entries, and the violation check treats those placeholders like a real requirement.

Expected: a module (or any other rule) whose version requirements are all placeholders or missing never produces a violation. Analysing `import typing_extensions` with a target of 3.8, or of 3.7, gives empty violation output. Rules with real minimum versions keep being reported as violations as before.

## fresh_vermin_353 (netromdk/vermin, base 6879540c6499)

Missing minimum-version rules for newer `pathlib.Path` features

vermin does not know about several `pathlib.Path` members and keyword arguments added in recent Python versions, so code using them is reported with a too-low minimum version:

```python
from pathlib import Path
Path('foo').with_stem('bar')         # needs 3.9, vermin does not detect it
Path('foo').relative_to('bar', walk_up=True)   # needs 3.12
```

Expected: vermin detects these when used through `Path` (`from pathlib import Path`):

| Usage | Minimum version |
|---|---|
| `Path.with_stem` | 3.9 |
| `Path.is_relative_to` | 3.9 |
| `Path.with_segments` | 3.12 |
| `Path.full_match` | 3.13 |
| `Path.parser` | 3.13 |
| `Path.match(case_sensitive=...)` | 3.12 |
| `Path.relative_to(walk_up=...)` | 3.12 |

For example, `Path('foo').with_stem('bar')` makes the minimum version 3.9. Existing rules must not change.

## fresh_vermin_344 (netromdk/vermin, base 88eab7676904)

Keyword-argument rules are missed when the method is called on a chained receiver

vermin detects `Path.exists(follow_symlinks=True)` (3.12+), but not when the method is called on the result of another call, which is the common way to write it:

```python
from pathlib import Path
Path.cwd().exists(follow_symlinks=True)   # requires 3.12, not detected
Path.cwd().is_file(follow_symlinks=True)  # requires 3.13, not detected
Path.cwd().is_dir(follow_symlinks=True)   # requires 3.13, not detected
```

The intermediate call (`cwd()`) ends up in the resolved name (`pathlib.Path.cwd.exists`), which matches no keyword-argument rule.

Expected: when the full dotted name of a call matches no keyword-argument rule, the intermediate calls are taken out of the receiver chain and the receiver plus the final method name is tried (e.g. `pathlib.Path.exists`). A rule is only applied when that shortened name has a keyword rule. The three lines above then require 3.12, 3.13 and 3.13. Calls already detected today must give the same results.

## fresh_marko_256 (frostming/marko, base 88e65f1f51c1)

Markdown renderer loses list indentation for GFM tables inside list items

Round-tripping Markdown through marko's `MarkdownRenderer` with the GFM extension breaks a table nested in a list item. The table rows lose their indentation, and the blank line gets the indentation instead:

```python
from marko import Markdown
from marko.ext.gfm import GFM
from marko.md_renderer import MarkdownRenderer

md = Markdown(renderer=MarkdownRenderer, extensions=[GFM])
md("- Item.\n\n  |foo|bar|\n  |---|---|\n  |foo|bar|")
# '- Item.\n  \n| foo | bar |\n| --- | --- |\n| foo | bar |\n'
```

The output is no longer a table inside the list item.

Expected: `'- Item.\n\n  | foo | bar |\n  | --- | --- |\n  | foo | bar |\n'`. Every table line (header, delimiter row and body rows) carries the list item's indentation, and blank lines are emitted without trailing indentation. Rendering of other block elements must not change.

## fresh_marko_252 (frostming/marko, base e34793226fc0)

GFM alerts: type is case-sensitive, and text on the marker line is accepted

marko's GFM extension recognises alert blocks (`> [!NOTE]`, `> [!WARNING]`, ...). It has two problems compared with GitHub's behaviour:

1. The alert type is matched case-sensitively, so `> [!warning]` or `> [!Caution]` render as ordinary blockquotes.
2. A marker line that has more text after the marker is still treated as an alert, and that text is dropped:

```python
from marko.ext.gfm import gfm

gfm("> [!warning]\n> Foo bar\n")
# '<blockquote>\n<p>[!warning]\nFoo bar</p>\n</blockquote>\n'
gfm("> [!NOTE] This is not allowed.\n> Foo bar\n")
# '<blockquote class="alert alert-note">\n<p>Note</p>\n<p>Foo bar</p>\n</blockquote>\n'
```

Expected:

- The type is matched case-insensitively and normalised to upper case in the AST (`alert_type == "WARNING"` for `[!warning]`). The HTML is the same as for the upper-case form: `<blockquote class="alert alert-warning">` with a title paragraph `<p>Warning</p>`.
- An alert marker must be alone on its line (only trailing whitespace is allowed). Otherwise the block is a normal blockquote whose paragraph starts with the literal text, e.g. `<blockquote>\n<p>[!NOTE] This is not allowed.`.

## fresh_filesystem_spec_2136 (fsspec/filesystem_spec, base 8c9bdede3e6e)

`FSMap.pop(key, None)` raises `KeyError` for a missing key

`FSMap` (the mapping returned by `fsspec.get_mapper`) is a `MutableMapping`, but its `pop` does not follow the mapping protocol when the default is `None`:

```python
import fsspec

m = fsspec.get_mapper("memory://mapping", create=True)
m.pop("missing", None)
# KeyError: 'missing'
```

`pop` treats a `None` default the same as no default at all.

Expected: `pop(key)` without a default raises `KeyError` for a missing key, while `pop(key, default)` returns the given default, whatever it is (`None`, `False`, `0`, `b""`, `[]`, ...), returning the very same object. For an existing key, `pop` returns the value and removes the key. This must hold for every backend (e.g. `memory://` and `file://`).

## fresh_filesystem_spec_2114 (fsspec/filesystem_spec, base a42b5b3bcb7e)

Credentials in URLs are passed to backends still percent-encoded

`fsspec.utils.infer_storage_options` extracts the username and password from a URL but does not percent-decode them, so backends (ftp, sftp, smb, ...) receive the encoded form and authentication fails:

```python
from fsspec.utils import infer_storage_options

infer_storage_options("sftp://user%40corp:p%23ass%2Fword%20!@example.com:22/path")
# {..., 'username': 'user%40corp', 'password': 'p%23ass%2Fword%20!'}
```

Expected: the username and password are percent-decoded (`'user@corp'` and `'p#ass/word !'` above), while host, port and path are unchanged. Plain credentials pass through as they are. For backwards compatibility, a value that cannot be decoded cleanly is returned exactly as it appears in the URL. That covers passwords like `50%off`, `pass%` and `pass%ab`, where `%ab` would decode to a byte that is not valid UTF-8.

## fresh_filesystem_spec_2139 (fsspec/filesystem_spec, base 2f7dc0c02305)

`ZipFileSystem(mode="a")` fails when the archive does not exist yet

`zipfile.ZipFile(path, mode="a")` creates the archive if it is missing, but fsspec's `ZipFileSystem` raises instead:

```python
from fsspec.implementations.zip import ZipFileSystem

ZipFileSystem(fo="memory://new.zip", mode="a")
# FileNotFoundError: /new.zip
```

The same happens for a local path.

Expected: in append mode, a missing archive is created, both for local paths and for other fsspec URLs such as `memory://`. Appending twice must keep earlier members:

```python
for name, data in [("first", b"original"), ("second", b"appended")]:
    fs = ZipFileSystem(fo=path, mode="a"); fs.pipe_file(name, data); fs.close()
fs = ZipFileSystem(fo=path)
fs.cat("first") == b"original"; fs.cat("second") == b"appended"
fs.find("") == ["first", "second"]
```

An existing archive opened with `mode="a"` must not be truncated, and read mode on a missing archive must still raise.

## fresh_tomlkit_508 (python-poetry/tomlkit, base f9b4b227f88a)

`dumps()` reorders and reformats documents wrapped in a mapping-like object

Libraries such as `dotty_dict` wrap a parsed `TOMLDocument` in an object that forwards attribute access, including `as_string`, to the document. `tomlkit.dumps()` used to render such wrappers verbatim, but now converts them through a plain dict, which loses the original table order and layout:

```python
import tomlkit

class DocumentWrapper:
    def __init__(self, document): self._document = document
    def __getitem__(self, key): return self._document[key]
    def __getattr__(self, name): return getattr(self._document, name)

content = '[tool.a]\nx = 1\n\n[project]\nname = "demo"\n\n[tool.b]\ny = 2\n'
tomlkit.dumps(DocumentWrapper(tomlkit.parse(content)))
# '[tool.a]\nx = 1\n\n[tool.b]\ny = 2\n\n[project]\nname = "demo"\n\n'
```

Expected: `dumps()` returns `content` unchanged for such a wrapper. Real `Mapping` objects keep being dumped through the dict path, honouring `sort_keys`. Objects that are neither a mapping nor provide `as_string` raise `TypeError`.

## fresh_tomlkit_620 (python-poetry/tomlkit, base 8c959b51c7da)

tomlkit `Time` and `DateTime` items drop the `fold` attribute

`datetime.time` and `datetime.datetime` have a `fold` attribute (PEP 495). tomlkit's `Time` and `DateTime` items ignore it, both when converting a standard object and in `replace()`:

```python
from datetime import time, datetime
from tomlkit import item

item(time(12, 34, 56, fold=1)).fold                 # 0, expected 1
item(datetime(2018, 7, 22, 12, 34, 56)).replace(fold=1).fold   # 0, expected 1
```

Expected: `Time` and `DateTime` accept and preserve `fold` like the standard types:

- `item()` keeps the fold of the converted value.
- `replace()` keeps the current fold unless a new one is passed.
- `replace(fold=1)` sets it.
- The constructors accept `fold` as a keyword argument, e.g. `Time(12, 34, 56, 0, None, fold=1)` and `DateTime(2018, 7, 22, 12, 34, 56, 0, None, fold=1)`. Pure-Python `datetime` implementations call the constructor in exactly this way from `replace()`.

The TOML text produced is unchanged (`fold` is not part of TOML), e.g. `item(time(12, 34, 56, fold=1)).as_string() == "12:34:56"`.

## fresh_tomlkit_537 (python-poetry/tomlkit, base b2821370ca8a)

Assigning a table onto itself rewrites its header

Re-assigning a table to the same key, a common pattern in code that walks and updates a document, normalises the table's header and loses the original spelling (whitespace and quoting):

```python
import tomlkit

content = "[keys.a]\n[keys .'a'.'c']\n  'd'\t= 'e'\n"
doc = tomlkit.parse(content)
for mode in doc["keys"]:
    doc["keys"][mode] = doc["keys"][mode]
doc.as_string()
# "[keys.a]\n[keys.a.'c']\n  'd'\t= 'e'\n"
```

Expected: assigning the very same table object back to its key changes nothing, and `doc.as_string() == content`. Assigning a different table must still update the display name as it does today.

## fresh_pygments_3175 (pygments/pygments, base a1fd09bc1f53)

`LatexEmbeddedLexer` ignores the wrapped lexer's options such as `stripnl`

The LaTeX formatter's `escapeinside` support wraps the real lexer in `LatexEmbeddedLexer` (the command line does this too). The wrapper is built with default lexer options, so input-processing options of the wrapped lexer, such as `stripnl`, `stripall`, `ensurenl` and `tabsize`, are silently replaced by the defaults:

```python
from pygments.formatters.latex import LatexEmbeddedLexer
from pygments.lexers.special import TextLexer

inner = TextLexer(stripnl=False)
wrapped = LatexEmbeddedLexer("|", "|", inner)
wrapped.stripnl                      # True
list(wrapped.get_tokens("\nLINE\n"))  # [(Token.Text, 'LINE\n')]  (leading blank line stripped)
list(inner.get_tokens("\nLINE\n"))    # [(Token.Text, '\nLINE\n')]
```

Expected: the wrapper inherits the wrapped lexer's options, so `wrapped.stripnl is False` and `wrapped.get_tokens(src)` yields the same tokens as `inner.get_tokens(src)` for the input above. Options passed explicitly to `LatexEmbeddedLexer` still take precedence, e.g. `LatexEmbeddedLexer("|", "|", inner, stripnl=True).stripnl is True`.

## fresh_pygments_3158 (pygments/pygments, base 27afd50c783a)

Wrong token offsets for code blocks embedded in Markdown, reST and TiddlyWiki

`Lexer.get_tokens_unprocessed()` documents the first element of each tuple as the token's start position in the input. For fenced or directive code blocks that are delegated to another lexer, the Markdown, reStructuredText and TiddlyWiki5 lexers report positions relative to the code block, not to the whole document:

```python
from pygments.lexers.markup import MarkdownLexer

text = "intro\n```python\nx = 1\ny = 2\n```\nend\n"
for index, token, value in MarkdownLexer().get_tokens_unprocessed(text):
    assert text[index:index + len(value)] == value
# fails for the token 'x': its index is 0, but text[0] is 'i'
```

Expected: for every token yielded by these three lexers, `text[index:index + len(value)] == value`, including tokens inside embedded code blocks. Examples are a fenced `python` block in Markdown, a `.. code-block:: python` directive in reST, and a fenced block in TiddlyWiki5. The token types and values themselves must not change.

## fresh_pyparsing_653 (pyparsing/pyparsing, base 038ff39cbc29)

`match_previous_expr` fails on nested and repeated matches

`pp.match_previous_expr(expr)` is supposed to match the same text that `expr` matched earlier. It only works once per parse:

```python
import pyparsing as pp

first = pp.Word(pp.alphas)
second = pp.match_previous_expr(first)
expr = first + pp.Suppress(":") + second
pp.OneOrMore(expr).parse_string("a:a b:b c:c", parse_all=True)
# ParseException: Expected end of text, found 'b'
```

Each match of `expr` adds another check to the repeater and never removes it, so later matches must satisfy every earlier one. Once a parse fails, the expression keeps rejecting valid input. This also makes it impossible to use for nested open/close tags.

Expected:

- Repeated use within one parse works (`"a:a b:b c:c"` gives `["a", "a", "b", "b", "c", "c"]`).
- A failed parse does not affect later parses: after `"e:f"` fails, `"g:g"` parses.
- Nested matches pair with the nearest enclosing occurrence. With `tag = Word(alphanums + "_")`, `open = "{" + tag + "}"`, `close = "{/" + match_previous_expr(tag) + "}"` and `content <<= (open + Group(content) + close) | Word(alphas)`:
  - `{a}xx{/a}`, `{a}{b}xx{/b}{/a}` and `{a}{b}{c}xx{/c}{/b}{/a}` parse.
  - `{a}{b}xx{/a}{/b}`, `{a}{b}xx{/b}{/c}` and `{a}xx{/b}` fail.

(Packrat parsing remains unsupported for this helper.)

## fresh_w3lib_299 (scrapy/w3lib, base 67046530caec)

`html_body_declared_encoding` misses charsets in meta tags with non-standard attributes

`w3lib.encoding.html_body_declared_encoding` only accepts a `<meta>` content-type declaration whose attributes match the expected `http-equiv="Content-Type"` form. Browsers are more lenient: they take the charset from any `<meta>` tag that declares one. Pages in the wild that misspell the other attribute are therefore decoded with the wrong encoding:

```python
from w3lib.encoding import html_body_declared_encoding

html_body_declared_encoding(b'<meta httpequiv="ContentType" content="text/html; charset=gbk" />')
# None, expected 'gb18030'
html_body_declared_encoding(b'<meta http-equiv="Fake-Content-Type-Header" content="text/html; charset=utf-8">')
# None, expected 'utf-8'
```

Expected: the charset is taken from any `<meta>` tag that contains a `charset=` declaration, however its other attributes are spelled, for both bytes and str input. The result is normalised as today (`gbk` resolves to `gb18030`). XML declarations (`<?xml ... encoding="...">`) and `<meta charset="...">` keep working, and the search still stops at `<body>`.

## fresh_tomlkit_549 (python-poetry/tomlkit, base e23a25438c6c)

Replacing a dotted key with an array of tables swallows the following sibling

When a key that was written with dotted-key syntax is replaced by an array of tables, the new `[[header]]` is rendered at the dotted key's position. Any dotted sibling that follows ends up inside the array's table:

```python
import tomlkit

doc = tomlkit.parse("a.b = 1\nc.d = 2\n")
arr = tomlkit.aot()
tbl = tomlkit.table()
tbl["x"] = 9
arr.append(tbl)
doc["a"] = arr
doc.as_string()
# '[[a]]\nx = 9\nc.d = 2\n'
tomlkit.parse(doc.as_string())
# {'a': [{'x': 9, 'c': {'d': 2}}]}   (c moved into the array)
```

Expected: the array of tables is rendered after the inline entries it would otherwise capture, so `doc.as_string() == "c.d = 2\n\n[[a]]\nx = 9\n"` and parsing it back gives `{"c": {"d": 2}, "a": [{"x": 9}]}`. This should work the same way it already does when such a dotted key is replaced by a regular table.

## fresh_pygments_3090 (pygments/pygments, base 08902846770e)

`html_escape` crashes on non-string values

`pygments.util.html_escape` is documented to return a safe version of the passed value, and an empty string for `None`. Some callers (and formatter options set programmatically) pass numbers or booleans, which crash:

```python
from pygments import util

util.html_escape(2)
# AttributeError: 'int' object has no attribute 'replace'
```

Expected: any non-`None` value is converted to a string and then escaped: `util.html_escape(2) == "2"`, `util.html_escape(2.2) == "2.2"`, `util.html_escape(True) == "True"`. `None` still gives `""`, and strings are escaped as before, honouring `quote`.

## fresh_traitlets_941 (ipython/traitlets, base 3646337430a8)

Add a `Path` trait type for filesystem paths

traitlets has no trait type for filesystem paths, so applications declare paths as `Unicode` and convert them by hand everywhere. Please add a `Path` trait, importable as `from traitlets import Path`:

```python
from traitlets import HasTraits, Path
import pathlib

class Config(HasTraits):
    value = Path()

c = Config()
c.value = "foo/bar"
c.value          # PosixPath('foo/bar'), a pathlib.Path
c.value = pathlib.PurePath("foo")   # accepted, stored as pathlib.Path("foo")
c.value = 0      # TraitError
```

Expected behaviour:

- Strings and `os.PathLike` objects are accepted and stored as `pathlib.Path(value)`.
- Anything else (numbers, lists, ...) raises `TraitError`, and so does `None` unless `allow_none=True`.
- When the value comes from a string (command line or config), `from_string` returns `pathlib.Path(s)`, or `None` for the string `"None"` when `allow_none` is set.
- The trait describes itself as "a filesystem path" in error messages.

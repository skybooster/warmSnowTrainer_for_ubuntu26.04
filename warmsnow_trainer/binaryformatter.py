"""Minimal .NET BinaryFormatter parser.

Warm Snow stores its save files as .NET BinaryFormatter-serialized object
graphs (PlayerSave, SaveBoardData, ...).  This module parses just enough of
the format to locate primitive (integer) member values and edit them in
place, while still walking nested arrays / List<> / struct objects so that
arbitrary fields can be reached.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Record types (BinaryHeaderEnum)
# ---------------------------------------------------------------------------
SERIALIZED_STREAM_HEADER = 0
CLASS_WITH_ID = 1
SYSTEM_CLASS_WITH_ID = 2
CLASS_WITH_MEMBERS = 3
SYSTEM_CLASS_WITH_MEMBERS = 4
CLASS_WITH_MEMBERS_AND_TYPES = 5
BINARY_OBJECT_STRING = 6
BINARY_ARRAY = 7
MEMBER_PRIMITIVE_TYPED = 8
MEMBER_REFERENCE = 9
OBJECT_NULL = 10
MESSAGE_END = 11
BINARY_LIBRARY = 12
OBJECT_NULL_MULTIPLE_256 = 13
OBJECT_NULL_MULTIPLE = 14
ARRAY_SINGLE_PRIMITIVE = 15
ARRAY_SINGLE_OBJECT = 16
ARRAY_SINGLE_STRING = 17
METHOD_CALL = 21
METHOD_RETURN = 22

# ---------------------------------------------------------------------------
# BinaryTypeEnum
# ---------------------------------------------------------------------------
BT_PRIMITIVE = 0
BT_STRING = 1
BT_OBJECT = 2
BT_SYSTEM_CLASS = 3
BT_CLASS = 4
BT_OBJECT_ARRAY = 5
BT_STRING_ARRAY = 6
BT_PRIMITIVE_ARRAY = 7

# ---------------------------------------------------------------------------
# PrimitiveTypeEnum
# ---------------------------------------------------------------------------
PT_BOOLEAN = 1
PT_BYTE = 2
PT_CHAR = 3
PT_DECIMAL = 5
PT_DOUBLE = 6
PT_INT16 = 7
PT_INT32 = 8
PT_INT64 = 9
PT_SBYTE = 10
PT_SINGLE = 11
PT_TIMESPAN = 12
PT_DATETIME = 13
PT_UINT16 = 14
PT_UINT32 = 15
PT_UINT64 = 16
PT_NULL = 17
PT_STRING = 18


class BinaryFormatterError(Exception):
    pass


# A "hint" describes the element type of an array whose type is not written
# in the stream (ArraySinglePrimitive etc.) or of a List<T>.  One of:
#   ("primitive", ptype)
#   ("string", None)
#   ("object", None)
#   ("class", type_name)
#   ("system_class", type_name)


@dataclass
class MemberInfo:
    name: str
    binary_type: int
    extra: Any = None


@dataclass
class ClassMeta:
    name: str
    members: List[MemberInfo] = field(default_factory=list)


@dataclass
class ObjValue:
    object_id: int
    meta: Optional[ClassMeta]
    values: Dict[str, Any] = field(default_factory=dict)
    offsets: Dict[str, int] = field(default_factory=dict)


@dataclass
class ParseResult:
    root: Any
    objects: Dict[int, ObjValue] = field(default_factory=dict)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def tell(self) -> int:
        return self.pos

    def u8(self) -> int:
        if self.pos >= len(self.data):
            raise BinaryFormatterError("unexpected end of stream")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def i32(self) -> int:
        if self.pos + 4 > len(self.data):
            raise BinaryFormatterError("unexpected end of stream (i32)")
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def i64(self) -> int:
        v = struct.unpack_from("<q", self.data, self.pos)[0]
        self.pos += 8
        return v

    def f32(self) -> float:
        v = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return v

    def f64(self) -> float:
        v = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def bytes(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise BinaryFormatterError("unexpected end of stream (bytes)")
        b = self.data[self.pos : self.pos + n]
        self.pos += n
        return b

    def string(self) -> str:
        length = self.read_7bit_length()
        if length < 0:
            raise BinaryFormatterError("negative string length")
        raw = self.bytes(length)
        return raw.decode("utf-8", "replace")

    def read_7bit_length(self) -> int:
        result = 0
        shift = 0
        while True:
            b = self.u8()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift > 35:
                raise BinaryFormatterError("invalid 7-bit length")
        return result


class BinaryFormatterParser:
    def __init__(self, data: bytes):
        self.data = data
        self.r = Reader(data)
        self.objects: Dict[int, ObjValue] = {}
        self.meta_by_id: Dict[int, ClassMeta] = {}
        self.id_hints: Dict[int, Tuple[str, Any]] = {}
        self.root: Any = None
        self.trace: List[str] = []

    def _note_ref(self, value: Any, hint: Optional[Tuple[str, Any]]) -> None:
        if hint is not None and isinstance(value, tuple) and value and value[0] == "ref":
            self.id_hints[value[1]] = hint

    def parse(self) -> ParseResult:
        rectype = self.r.u8()
        if rectype != SERIALIZED_STREAM_HEADER:
            raise BinaryFormatterError(f"expected stream header, got {rectype}")
        top_id = self.r.i32()
        self.r.i32()
        self.r.i32()
        self.r.i32()
        self.trace.append(f"header top={top_id}")

        self.root = None
        while True:
            value = self.read_record(None)
            if value == "MESSAGE_END":
                break
            if isinstance(value, tuple) and value and value[0] == "library":
                continue
            if self.root is None:
                self.root = value

        return ParseResult(root=self.root, objects=self.objects)

    # ------------------------------------------------------------------
    def read_record(self, hint: Optional[Tuple[str, Any]]) -> Any:
        rectype = self.r.u8()
        pos = self.r.tell() - 1
        if rectype == CLASS_WITH_ID:
            return self.read_class_with_id()
        if rectype == SYSTEM_CLASS_WITH_ID:
            return self.read_system_class_with_id()
        if rectype == CLASS_WITH_MEMBERS:
            return self.read_class_with_members()
        if rectype == SYSTEM_CLASS_WITH_MEMBERS:
            return self.read_system_class_with_members()
        if rectype == CLASS_WITH_MEMBERS_AND_TYPES:
            return self.read_class_with_members_and_types()
        if rectype == BINARY_OBJECT_STRING:
            return self.read_binary_object_string()
        if rectype == BINARY_ARRAY:
            return self.read_binary_array()
        if rectype == MEMBER_PRIMITIVE_TYPED:
            return self.read_member_primitive_typed()
        if rectype == MEMBER_REFERENCE:
            return self.read_member_reference()
        if rectype == OBJECT_NULL:
            return None
        if rectype == MESSAGE_END:
            return "MESSAGE_END"
        if rectype == BINARY_LIBRARY:
            return self.read_binary_library()
        if rectype == OBJECT_NULL_MULTIPLE_256:
            self.r.u8()
            return None
        if rectype == OBJECT_NULL_MULTIPLE:
            self.r.i32()
            return None
        if rectype == ARRAY_SINGLE_PRIMITIVE:
            return self.read_array_single_primitive(hint)
        if rectype == ARRAY_SINGLE_OBJECT:
            return self.read_array_single_object()
        if rectype == ARRAY_SINGLE_STRING:
            return self.read_array_single_string()
        if rectype in (METHOD_CALL, METHOD_RETURN):
            raise BinaryFormatterError(f"unexpected method record {rectype} at {pos}")
        raise BinaryFormatterError(f"unknown record type {rectype} at offset {pos}")

    # ------------------------------------------------------------------
    def read_class_with_id(self) -> ObjValue:
        object_id = self.r.i32()
        metadata_id = self.r.i32()
        meta = self.meta_by_id.get(metadata_id)
        if meta is None:
            raise BinaryFormatterError(
                f"ClassWithId references unknown metadata id {metadata_id}"
            )
        return self.read_members_into(object_id, meta)

    def read_system_class_with_id(self) -> ObjValue:
        object_id = self.r.i32()
        name = self.r.string()
        meta = ClassMeta(name)
        obj = ObjValue(object_id, meta)
        if name.startswith("System.Collections.Generic.List`1[["):
            element_hint = self._generic_arg_hint(name[len("System.Collections.Generic.List`1[["): -2])
            obj.offsets["_items"] = self.r.tell()
            obj.values["_items"] = self.read_record(element_hint)
            self._note_ref(obj.values["_items"], element_hint)
            obj.values["_size"] = self.r.i32()
            obj.values["_version"] = self.r.i32()
        elif name.startswith("System.Collections.Generic.KeyValuePair`2[["):
            key_hint, value_hint = self._kvp_hints(name)
            obj.values["key"] = self.read_record(key_hint)
            obj.values["value"] = self.read_record(value_hint)
        elif name == "System.Guid":
            obj.values["_a"] = self.r.i32()
            obj.values["_bc"] = self.r.bytes(12)
        else:
            raise BinaryFormatterError(f"unsupported system class {name!r}")
        self.objects[object_id] = obj
        return obj

    def _kvp_hints(self, name: str) -> Tuple[Tuple[str, Any], Tuple[str, Any]]:
        inner = name[len("System.Collections.Generic.KeyValuePair`2[["): -2]
        key_part, value_part = self._split_type_args(inner)
        return self._generic_arg_hint(key_part), self._generic_arg_hint(value_part)

    @staticmethod
    def _split_type_args(inner: str) -> Tuple[str, str]:
        depth = 0
        for i, ch in enumerate(inner):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            elif ch == "," and depth == 0:
                return inner[:i], inner[i + 1:]
        return inner, ""

    def _generic_arg_hint(self, arg: str) -> Tuple[str, Any]:
        arg = arg.strip()
        if not arg:
            return ("object", None)
        if arg == "System.Boolean":
            return ("primitive", PT_BOOLEAN)
        if arg == "System.Int32":
            return ("primitive", PT_INT32)
        if arg == "System.Single":
            return ("primitive", PT_SINGLE)
        if arg == "System.String":
            return ("string", None)
        if arg.startswith("System.Collections.Generic.List`1[["):
            return ("system_class", arg + "]]" if not arg.endswith("]]") else arg)
        if arg.startswith("System.Collections.Generic.KeyValuePair`2[["):
            return ("system_class", arg + "]]" if not arg.endswith("]]") else arg)
        simple = arg.split(", ")[0]
        return ("class", simple)

    def read_class_with_members(self) -> ObjValue:
        object_id = self.r.i32()
        name = self.r.string()
        member_count = self.r.i32()
        names = [self.r.string() for _ in range(member_count)]
        meta = ClassMeta(name, [MemberInfo(n, BT_OBJECT) for n in names])
        self.meta_by_id[object_id] = meta
        return self.read_members_into(object_id, meta)

    def read_system_class_with_members(self) -> ObjValue:
        object_id = self.r.i32()
        name = self.r.string()
        member_count = self.r.i32()
        names = [self.r.string() for _ in range(member_count)]
        types = self.read_member_types(member_count)
        meta = ClassMeta(
            name, [MemberInfo(n, t[0], t[1]) for n, t in zip(names, types)]
        )
        self.meta_by_id[object_id] = meta
        return self.read_members_into(object_id, meta)

    def read_class_with_members_and_types(self) -> ObjValue:
        object_id = self.r.i32()
        name = self.r.string()
        member_count = self.r.i32()
        names = [self.r.string() for _ in range(member_count)]
        types = self.read_member_types(member_count)
        self.r.i32()  # class library id
        meta = ClassMeta(
            name, [MemberInfo(n, t[0], t[1]) for n, t in zip(names, types)]
        )
        self.meta_by_id[object_id] = meta
        return self.read_members_into(object_id, meta)

    def read_member_types(self, count: int) -> List[Tuple[int, Any]]:
        enums = [self.r.u8() for _ in range(count)]
        result: List[Tuple[int, Any]] = []
        for e in enums:
            if e == BT_PRIMITIVE:
                result.append((e, self.r.u8()))
            elif e in (BT_STRING, BT_OBJECT, BT_STRING_ARRAY):
                result.append((e, None))
            elif e == BT_SYSTEM_CLASS:
                result.append((e, self.r.string()))
            elif e == BT_CLASS:
                type_name = self.r.string()
                library_id = self.r.i32()
                result.append((e, (type_name, library_id)))
            elif e == BT_OBJECT_ARRAY:
                sub = self.r.u8()
                if sub == BT_PRIMITIVE:
                    result.append((e, ("array", sub, self.r.u8())))
                elif sub == BT_STRING:
                    result.append((e, ("array", sub, None)))
                elif sub in (BT_SYSTEM_CLASS, BT_CLASS):
                    result.append((e, ("array", sub, self.r.string())))
                else:
                    result.append((e, ("array", sub, None)))
            elif e == BT_PRIMITIVE_ARRAY:
                result.append((e, self.r.u8()))
            else:
                raise BinaryFormatterError(f"unknown binary type enum {e}")
        return result

    def read_members_into(self, object_id: int, meta: ClassMeta) -> ObjValue:
        obj = ObjValue(object_id, meta)
        for member in meta.members:
            value_pos = self.r.tell()
            hint = self._member_hint(member)
            if member.binary_type == BT_PRIMITIVE:
                value = self.read_primitive_value(member.extra)
            else:
                value = self.read_record(hint)
                self._note_ref(value, hint)
            obj.values[member.name] = value
            obj.offsets[member.name] = value_pos
        self.objects[object_id] = obj
        return obj

    def _member_hint(self, member: MemberInfo) -> Optional[Tuple[str, Any]]:
        bt = member.binary_type
        extra = member.extra
        if bt == BT_PRIMITIVE_ARRAY:
            return ("primitive", extra)
        if bt == BT_OBJECT_ARRAY:
            _, sub, inner = extra
            if sub == BT_PRIMITIVE:
                return ("primitive", inner)
            if sub == BT_STRING:
                return ("string", None)
            if sub == BT_CLASS:
                return ("class", inner)
            if sub == BT_SYSTEM_CLASS:
                return ("system_class", inner)
            return ("object", None)
        if bt == BT_STRING_ARRAY:
            return ("string", None)
        if bt == BT_CLASS:
            type_name = extra[0] if isinstance(extra, tuple) else extra
            if type_name.endswith("[]"):
                return ("class", type_name[:-2])
            return ("class", type_name)
        if bt == BT_SYSTEM_CLASS:
            return ("system_class", extra)
        return None

    # ------------------------------------------------------------------
    def read_binary_object_string(self) -> str:
        self.r.i32()
        return self.r.string()

    def read_member_primitive_typed(self) -> Any:
        ptype = self.r.u8()
        return self.read_primitive_value(ptype)

    def read_primitive_value(self, ptype: int) -> Any:
        if ptype == PT_BOOLEAN:
            return self.r.u8() != 0
        if ptype == PT_BYTE:
            return self.r.u8()
        if ptype == PT_CHAR:
            return chr(struct.unpack("<H", self.r.bytes(2))[0])
        if ptype == PT_INT16:
            return struct.unpack("<h", self.r.bytes(2))[0]
        if ptype == PT_INT32:
            return self.r.i32()
        if ptype == PT_INT64:
            return self.r.i64()
        if ptype == PT_SBYTE:
            return struct.unpack("<b", self.r.bytes(1))[0]
        if ptype == PT_SINGLE:
            return self.r.f32()
        if ptype == PT_DOUBLE:
            return self.r.f64()
        if ptype == PT_UINT16:
            return struct.unpack("<H", self.r.bytes(2))[0]
        if ptype == PT_UINT32:
            return struct.unpack("<I", self.r.bytes(4))[0]
        if ptype == PT_UINT64:
            return struct.unpack("<Q", self.r.bytes(8))[0]
        if ptype == PT_DECIMAL:
            return self.r.bytes(16)
        if ptype == PT_TIMESPAN:
            return self.r.i64()
        if ptype == PT_DATETIME:
            return self.r.i64()
        if ptype == PT_NULL:
            return None
        if ptype == PT_STRING:
            return self.r.string()
        raise BinaryFormatterError(f"unknown primitive type {ptype}")

    def read_member_reference(self) -> Any:
        ref_id = self.r.i32()
        return ("ref", ref_id)

    def read_binary_library(self) -> Any:
        library_id = self.r.i32()
        name = self.r.string()
        return ("library", library_id, name)

    # ------------------------------------------------------------------
    def read_binary_array(self) -> Any:
        self.r.i32()  # object id
        array_type = self.r.u8()
        rank = self.r.i32()
        lengths = [self.r.i32() for _ in range(rank)]
        total = 1
        for n in lengths:
            total *= n
        if array_type in (3, 4, 5):
            for _ in range(rank):
                self.r.i32()
        type_enum = self.r.u8()
        element_hint: Optional[Tuple[str, Any]] = None
        if type_enum == BT_PRIMITIVE:
            element_hint = ("primitive", self.r.u8())
        elif type_enum == BT_STRING:
            element_hint = ("string", None)
        elif type_enum == BT_SYSTEM_CLASS:
            element_hint = ("system_class", self.r.string())
        elif type_enum == BT_CLASS:
            element_hint = ("class", self.r.string())
            self.r.i32()  # library id
        items = []
        for _ in range(total):
            value = self.read_record(element_hint)
            self._note_ref(value, element_hint)
            items.append(value)
        return items

    def read_array_single_primitive(self, hint: Optional[Tuple[str, Any]]) -> List[Any]:
        self.r.i32()  # object id
        length = self.r.i32()
        ptype = self.r.u8()  # primitive type enum is part of the record
        return [self.read_primitive_value(ptype) for _ in range(length)]

    def read_array_single_object(self) -> Any:
        self.r.i32()
        length = self.r.i32()
        return [("ref", self.r.i32()) for _ in range(length)]

    def read_array_single_string(self) -> Any:
        self.r.i32()
        length = self.r.i32()
        return [self.r.string() for _ in range(length)]


def parse(data: bytes) -> ParseResult:
    parser = BinaryFormatterParser(data)
    return parser.parse()

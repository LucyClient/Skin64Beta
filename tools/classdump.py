#!/usr/bin/env python3
"""Minimal pure-Python .class file reader.
Dumps: class/super/interfaces, fields (name+type), methods (name+sig),
and for each method, every symbolic constant-pool reference it touches
(field refs, method refs, string constants) in bytecode order, which is
enough to reverse-engineer call graphs and field usage without a full
decompiler.
"""
import struct
import sys

CONSTANT_TAGS = {
    1: "Utf8", 3: "Integer", 4: "Float", 5: "Long", 6: "Double",
    7: "Class", 8: "String", 9: "Fieldref", 10: "Methodref",
    11: "InterfaceMethodref", 12: "NameAndType", 15: "MethodHandle",
    16: "MethodType", 17: "Dynamic", 18: "InvokeDynamic", 19: "Module", 20: "Package",
}


class ClassFile:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self._parse()

    def u1(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u2(self):
        v = struct.unpack_from(">H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def u4(self):
        v = struct.unpack_from(">I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def s4(self):
        v = struct.unpack_from(">i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def bytes_(self, n):
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v

    def _parse(self):
        magic = self.u4()
        assert magic == 0xCAFEBABE, "not a class file"
        self.minor = self.u2()
        self.major = self.u2()
        cp_count = self.u2()
        self.cp = [None] * cp_count
        i = 1
        while i < cp_count:
            tag = self.u1()
            kind = CONSTANT_TAGS.get(tag, f"Unknown({tag})")
            if kind == "Utf8":
                length = self.u2()
                raw = self.bytes_(length)
                try:
                    val = raw.decode("utf-8")
                except UnicodeDecodeError:
                    val = raw.decode("utf-8", errors="replace")
                self.cp[i] = (kind, val)
            elif kind in ("Integer", "Float"):
                self.cp[i] = (kind, self.u4())
            elif kind in ("Long", "Double"):
                self.cp[i] = (kind, (self.u4(), self.u4()))
                i += 1  # takes two slots
            elif kind == "Class":
                self.cp[i] = (kind, self.u2())
            elif kind == "String":
                self.cp[i] = (kind, self.u2())
            elif kind in ("Fieldref", "Methodref", "InterfaceMethodref"):
                self.cp[i] = (kind, self.u2(), self.u2())
            elif kind == "NameAndType":
                self.cp[i] = (kind, self.u2(), self.u2())
            elif kind == "MethodHandle":
                self.cp[i] = (kind, self.u1(), self.u2())
            elif kind == "MethodType":
                self.cp[i] = (kind, self.u2())
            elif kind in ("Dynamic", "InvokeDynamic"):
                self.cp[i] = (kind, self.u2(), self.u2())
            elif kind in ("Module", "Package"):
                self.cp[i] = (kind, self.u2())
            else:
                raise ValueError(f"unknown cp tag {tag} at index {i}")
            i += 1

        self.access_flags = self.u2()
        self.this_class = self.u2()
        self.super_class = self.u2()
        iface_count = self.u2()
        self.interfaces = [self.u2() for _ in range(iface_count)]

        field_count = self.u2()
        self.fields = []
        for _ in range(field_count):
            self.fields.append(self._parse_member())

        method_count = self.u2()
        self.methods = []
        for _ in range(method_count):
            self.methods.append(self._parse_member())

        attr_count = self.u2()
        self.attributes = [self._parse_attribute() for _ in range(attr_count)]

    def _parse_member(self):
        access_flags = self.u2()
        name_idx = self.u2()
        desc_idx = self.u2()
        attr_count = self.u2()
        attrs = [self._parse_attribute() for _ in range(attr_count)]
        return {
            "access_flags": access_flags,
            "name": self.utf8(name_idx),
            "desc": self.utf8(desc_idx),
            "attributes": attrs,
        }

    def _parse_attribute(self):
        name_idx = self.u2()
        length = self.u4()
        raw = self.bytes_(length)
        return {"name": self.utf8(name_idx), "raw": raw}

    def utf8(self, idx):
        if idx == 0:
            return None
        entry = self.cp[idx]
        return entry[1]

    def cp_str(self, idx):
        """Human-readable string for any constant pool entry, resolving refs."""
        if idx == 0 or idx >= len(self.cp) or self.cp[idx] is None:
            return "?"
        entry = self.cp[idx]
        kind = entry[0]
        if kind == "Utf8":
            return entry[1]
        if kind == "Class":
            return self.cp_str(entry[1])
        if kind == "String":
            return repr(self.cp_str(entry[1]))
        if kind == "NameAndType":
            return f"{self.cp_str(entry[1])}:{self.cp_str(entry[2])}"
        if kind in ("Fieldref", "Methodref", "InterfaceMethodref"):
            cls = self.cp_str(entry[1])
            nt = self.cp[entry[2]]
            nm = self.cp_str(nt[1])
            ds = self.cp_str(nt[2])
            return f"{cls}.{nm}:{ds}"
        if kind in ("Integer", "Float"):
            return str(entry[1])
        return f"<{kind}>"

    def class_name(self):
        return self.cp_str(self.this_class)

    def super_name(self):
        return self.cp_str(self.super_class)

    def get_code(self, method):
        for a in method["attributes"]:
            if a["name"] == "Code":
                return a["raw"]
        return None


CP_REF_2BYTE = {
    0xb2: "getstatic", 0xb3: "putstatic", 0xb4: "getfield", 0xb5: "putfield",
    0xb6: "invokevirtual", 0xb7: "invokespecial", 0xb8: "invokestatic",
    0xbb: "new", 0xc0: "checkcast", 0xc1: "instanceof",
    0x13: "ldc_w", 0x14: "ldc2_w",
}
INVOKE_INTERFACE = 0xb9
INVOKE_DYNAMIC = 0xba
LDC = 0x12

FIXED_OPERANDS = {
    0x10: 1, 0x11: 2, 0x12: 1, 0x13: 2, 0x14: 2, 0x15: 1, 0x16: 1, 0x17: 1,
    0x18: 1, 0x19: 1, 0x36: 1, 0x37: 1, 0x38: 1, 0x39: 1, 0x3a: 1,
    0xa9: 1, 0xbc: 1,
    0xb2: 2, 0xb3: 2, 0xb4: 2, 0xb5: 2, 0xb6: 2, 0xb7: 2, 0xb8: 2,
    0xb9: 4, 0xba: 4, 0xbb: 2, 0xbd: 2, 0xc0: 2, 0xc1: 2,
    0xc5: 3, 0xc6: 2, 0xc7: 2, 0xbf: 0,
    0x84: 2,
    0x99: 2, 0x9a: 2, 0x9b: 2, 0x9c: 2, 0x9d: 2, 0x9e: 2, 0x9f: 2, 0xa0: 2,
    0xa1: 2, 0xa2: 2, 0xa3: 2, 0xa4: 2, 0xa5: 2, 0xa6: 2,
    0xa7: 2, 0xa8: 2,
    0xc8: 4, 0xc9: 4,
}


def disassemble_refs(cf, code):
    max_stack, max_locals, code_len = struct.unpack_from(">HHI", code, 0)
    body = code[10:10 + code_len]
    refs = []
    i = 0
    n = len(body)
    while i < n:
        op = body[i]
        i += 1
        if op == LDC:
            idx = body[i]
            i += 1
            refs.append(("ldc", cf.cp_str(idx)))
            continue
        if op in CP_REF_2BYTE:
            idx = struct.unpack_from(">H", body, i)[0]
            i += 2
            refs.append((CP_REF_2BYTE[op], cf.cp_str(idx)))
            continue
        if op == INVOKE_INTERFACE:
            idx = struct.unpack_from(">H", body, i)[0]
            i += 4
            refs.append(("invokeinterface", cf.cp_str(idx)))
            continue
        if op == INVOKE_DYNAMIC:
            idx = struct.unpack_from(">H", body, i)[0]
            i += 4
            refs.append(("invokedynamic", cf.cp_str(idx)))
            continue
        if op == 0xc5:
            idx = struct.unpack_from(">H", body, i)[0]
            i += 3
            refs.append(("multianewarray", cf.cp_str(idx)))
            continue
        if op in (0xaa, 0xab):
            pad = (4 - (i % 4)) % 4
            i += pad
            if op == 0xaa:
                default, low, high = struct.unpack_from(">iii", body, i)
                i += 12
                count = high - low + 1
                i += 4 * count
            else:
                default, npairs = struct.unpack_from(">ii", body, i)
                i += 8
                i += 8 * npairs
            continue
        if op == 0xc4:
            sub = body[i]
            i += 1
            if sub == 0x84:
                i += 4
            else:
                i += 2
            continue
        if op in FIXED_OPERANDS:
            i += FIXED_OPERANDS[op]
            continue
    return refs


def access_str(flags, is_method=False):
    names = []
    table = [
        (0x0001, "public"), (0x0002, "private"), (0x0004, "protected"),
        (0x0008, "static"), (0x0010, "final"), (0x0020, "synchronized" if is_method else "super"),
        (0x0040, "bridge" if is_method else "volatile"),
        (0x0080, "varargs" if is_method else "transient"),
        (0x0400, "abstract"),
    ]
    for bit, name in table:
        if flags & bit:
            names.append(name)
    return " ".join(names)


def dump_class(cf, show_code=True, method_filter=None):
    print(f"class {cf.class_name()} extends {cf.super_name()}")
    if cf.interfaces:
        print("  implements " + ", ".join(cf.cp_str(i) for i in cf.interfaces))
    print()
    print("FIELDS:")
    for f in cf.fields:
        print(f"  {access_str(f['access_flags'])} {f['desc']} {f['name']}".strip())
    print()
    print("METHODS:")
    for m in cf.methods:
        if method_filter and method_filter not in m["name"]:
            continue
        print(f"  {access_str(m['access_flags'], True)} {m['name']}{m['desc']}".strip())
        if show_code:
            code = cf.get_code(m)
            if code:
                refs = disassemble_refs(cf, code)
                for kind, ref in refs:
                    print(f"      {kind:16s} {ref}")
        print()


if __name__ == "__main__":
    jar_path = sys.argv[1]
    class_path = sys.argv[2]
    method_filter = sys.argv[3] if len(sys.argv) > 3 else None
    import zipfile
    with zipfile.ZipFile(jar_path) as z:
        data = z.read(class_path)
    cf = ClassFile(data)
    dump_class(cf, method_filter=method_filter)

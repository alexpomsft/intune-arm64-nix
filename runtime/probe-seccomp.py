import ctypes
import os
import sys


class Comparison(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_int),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


library = ctypes.CDLL("libseccomp.so.2")
library.seccomp_init.argtypes = [ctypes.c_uint32]
library.seccomp_init.restype = ctypes.c_void_p
library.seccomp_rule_add.argtypes = [
    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint,
]
library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
library.seccomp_release.argtypes = [ctypes.c_void_p]
context = library.seccomp_init(0x7FFF0000)
if not context:
    raise RuntimeError("Cannot initialize filter")
try:
    if library.seccomp_rule_add(context, 0x50001, 39, 0):
        raise RuntimeError("Cannot translate getpid rule")
    comparison = Comparison(0, 4, 99999, 0)
    if library.seccomp_rule_add(context, 0x50001, 3, 1, comparison):
        raise RuntimeError("Cannot translate argument-filtered close rule")
    with open(sys.argv[1], "wb") as output:
        if library.seccomp_export_bpf(context, output.fileno()):
            raise RuntimeError("Cannot export native filter")
finally:
    library.seccomp_release(context)
print("Native filter exported with unconditional and argument-filtered rules")

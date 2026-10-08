import ctypes

library = ctypes.CDLL("/usr/lib/x86_64-linux-gnu/libjavascriptcoregtk-4.1.so.0")
library.JSGlobalContextCreate.argtypes = [ctypes.c_void_p]
library.JSGlobalContextCreate.restype = ctypes.c_void_p
library.JSGlobalContextRelease.argtypes = [ctypes.c_void_p]
library.JSStringCreateWithUTF8CString.argtypes = [ctypes.c_char_p]
library.JSStringCreateWithUTF8CString.restype = ctypes.c_void_p
library.JSStringRelease.argtypes = [ctypes.c_void_p]
library.JSEvaluateScript.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_void_p),
]
library.JSEvaluateScript.restype = ctypes.c_void_p
library.JSValueToNumber.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
]
library.JSValueToNumber.restype = ctypes.c_double
print("Initializing JavaScriptCore", flush=True)
context = library.JSGlobalContextCreate(None)
if not context:
    raise RuntimeError("JavaScriptCore did not create a context")
source = library.JSStringCreateWithUTF8CString(b"1 + 1")
try:
    exception = ctypes.c_void_p()
    value = library.JSEvaluateScript(context, source, None, None, 1, ctypes.byref(exception))
    if exception.value or not value:
        raise RuntimeError("JavaScript evaluation failed")
    result = library.JSValueToNumber(context, value, ctypes.byref(exception))
    if exception.value or result != 2:
        raise RuntimeError("JavaScript evaluation returned the wrong result")
finally:
    library.JSStringRelease(source)
    library.JSGlobalContextRelease(context)
print("JavaScriptCore creation/evaluation/release: OK", flush=True)

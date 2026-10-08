import ctypes
import sys
import time

gtk = ctypes.CDLL("libgtk-3.so.0")
webkit = ctypes.CDLL("libwebkit2gtk-4.1.so.0")
gobject = ctypes.CDLL("libgobject-2.0.so.0")
glib = ctypes.CDLL("libglib-2.0.so.0")
jsc = ctypes.CDLL("libjavascriptcoregtk-4.1.so.0")

gtk.gtk_init_check.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gtk.gtk_window_new.argtypes = [ctypes.c_int]
gtk.gtk_window_new.restype = ctypes.c_void_p
gtk.gtk_container_add.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gtk.gtk_widget_show_all.argtypes = [ctypes.c_void_p]
gtk.gtk_widget_destroy.argtypes = [ctypes.c_void_p]
gtk.gtk_window_set_default_size.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
webkit.webkit_web_view_new.restype = ctypes.c_void_p
webkit.webkit_web_view_load_uri.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
gobject.g_signal_connect_data.argtypes = [
    ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
]
glib.g_main_context_iteration.argtypes = [ctypes.c_void_p, ctypes.c_int]
webkit.webkit_web_view_evaluate_javascript.argtypes = [
    ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ssize_t, ctypes.c_char_p,
    ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
]
webkit.webkit_web_view_evaluate_javascript_finish.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
]
webkit.webkit_web_view_evaluate_javascript_finish.restype = ctypes.c_void_p
jsc.jsc_value_to_boolean.argtypes = [ctypes.c_void_p]
gobject.g_object_unref.argtypes = [ctypes.c_void_p]

state = {"finished": False, "failed": False, "form": False, "pending": False}
check_form = "--login-form" in sys.argv

class GError(ctypes.Structure):
    _fields_ = [
        ("domain", ctypes.c_uint),
        ("code", ctypes.c_int),
        ("message", ctypes.c_char_p),
    ]


@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
def changed(view, event, data):
    print("WebKit load event:", event, flush=True)
    if event == 3:
        state["finished"] = True


@ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
)
def failed(view, event, uri, error, data):
    state["failed"] = True
    details = ctypes.cast(error, ctypes.POINTER(GError)).contents
    print("WebKit load error:", details.code, details.message.decode(), flush=True)
    return 0


@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
def terminated(view, reason, data):
    state["failed"] = True
    print("WebKit renderer terminated:", reason, flush=True)

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
def evaluated(source, result, data):
    state["pending"] = False
    error = ctypes.c_void_p()
    value = webkit.webkit_web_view_evaluate_javascript_finish(
        source, result, ctypes.byref(error),
    )
    if not value:
        state["failed"] = True
        print("Sign-in form JavaScript evaluation failed", flush=True)
        return
    state["form"] = bool(jsc.jsc_value_to_boolean(value))
    gobject.g_object_unref(value)


if not gtk.gtk_init_check(None, None):
    raise RuntimeError("GTK cannot connect to the display")
window = gtk.gtk_window_new(0)
gtk.gtk_window_set_default_size(window, 900, 700)
view = webkit.webkit_web_view_new()
gobject.g_signal_connect_data(view, b"load-changed", changed, None, None, 0)
gobject.g_signal_connect_data(view, b"load-failed", failed, None, None, 0)
gobject.g_signal_connect_data(view, b"web-process-terminated", terminated, None, None, 0)
gtk.gtk_container_add(window, view)
gtk.gtk_widget_show_all(window)
print("Loading public Microsoft HTTPS endpoint in WebKit", flush=True)
webkit.webkit_web_view_load_uri(
    view,
    b"https://login.microsoftonline.com/" if check_form else
    b"https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
)
deadline = time.monotonic() + 60
next_evaluation = 0
while not state["failed"] and time.monotonic() < deadline:
    glib.g_main_context_iteration(None, False)
    if state["finished"]:
        if not check_form or state["form"]:
            break
        if not state["pending"] and time.monotonic() >= next_evaluation:
            state["pending"] = True
            next_evaluation = time.monotonic() + 1
            webkit.webkit_web_view_evaluate_javascript(
                view,
                b"(()=>{const e=document.querySelector('#i0116');"
                b"return !!e && !e.disabled && e.getBoundingClientRect().width>0"
                b" && e.getBoundingClientRect().height>0;})()",
                -1, None, None, None, evaluated, None,
            )
    time.sleep(0.05)
gtk.gtk_widget_destroy(window)
if state["failed"] or not state["finished"]:
    raise RuntimeError("Embedded HTTPS page did not load successfully")
print("Embedded WebKit HTTPS load: OK", flush=True)
if check_form:
    if not state["form"]:
        raise RuntimeError("No visible, enabled Microsoft sign-in input rendered")
    print("Microsoft sign-in form JavaScript and visible input: OK", flush=True)

import gi

gi.require_version("Secret", "1")
from gi.repository import Gio, GLib, Secret

service = Secret.Service.get_sync(
    Secret.ServiceFlags.OPEN_SESSION | Secret.ServiceFlags.LOAD_COLLECTIONS, None,
)
connection = service.get_connection()


def read_alias(alias):
    return connection.call_sync(
        "org.freedesktop.secrets", "/org/freedesktop/secrets",
        "org.freedesktop.Secret.Service", "ReadAlias",
        GLib.Variant("(s)", (alias,)), GLib.VariantType.new("(o)"),
        Gio.DBusCallFlags.NONE, 10000, None,
    ).unpack()[0]


original_default = read_alias("default")
if read_alias("login") != "/":
    raise RuntimeError("A login alias already exists; refusing to replace it")
print("Creating only the login collection; choose its protection in the native dialog",
      flush=True)
collection = Secret.Collection.create_sync(
    service, "login", None, Secret.CollectionCreateFlags.NONE, None,
)
if collection is None:
    raise RuntimeError("Collection creation was canceled or returned no collection")
if read_alias("default") != original_default:
    raise RuntimeError("Default alias changed unexpectedly; stop before sign-in")
if collection.get_object_path() != "/org/freedesktop/secrets/collection/login":
    raise RuntimeError("New collection did not use the required login path")
if collection.get_locked():
    raise RuntimeError("New login collection is locked")
print("Login collection created and unlocked; original default alias unchanged",
      flush=True)

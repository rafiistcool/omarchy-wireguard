#!/usr/bin/env python3
"""Small JSON bridge. Never returns configuration contents or private keys."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from urllib.parse import unquote, urlparse


class BackendError(Exception):
    pass


def nmcli(*args):
    try:
        result = subprocess.run(
            ["nmcli", "--wait", "30", *args], capture_output=True, text=True,
            timeout=40, env={**os.environ, "LC_ALL": "C"},
        )
    except FileNotFoundError:
        raise BackendError("nmcli fehlt. Bitte NetworkManager installieren.") from None
    except subprocess.TimeoutExpired:
        raise BackendError("NetworkManager antwortet nicht rechtzeitig. Status aktualisieren.") from None
    if result.returncode:
        # Do not relay arbitrary diagnostics that might contain secrets.
        raise BackendError("NetworkManager hat die Aktion abgelehnt. Dienst, Berechtigung und Profil prüfen.")
    return result.stdout


def split_fields(line):
    fields, part, escaped = [], [], False
    for char in line:
        if escaped:
            part.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(part))
            part = []
        else:
            part.append(char)
    if escaped:
        part.append("\\")
    return fields + ["".join(part)]


def profiles():
    output = nmcli("-t", "-f", "UUID,TYPE,ACTIVE,NAME", "connection", "show")
    result = []
    for line in output.splitlines():
        fields = split_fields(line)
        if len(fields) == 4 and fields[1] == "wireguard":
            result.append({"uuid": fields[0], "name": fields[3], "active": fields[2] == "yes"})
    return sorted(result, key=lambda p: (not p["active"], p["name"].casefold(), p["uuid"]))


def change_connection(action, identifier):
    try:
        identifier = str(uuid.UUID(identifier))
    except ValueError:
        raise BackendError("Ungültige Profil-ID.") from None
    if not any(p["uuid"] == identifier for p in profiles()):
        raise BackendError("WireGuard-Profil nicht mehr vorhanden. Bitte aktualisieren.")
    nmcli("connection", action, "uuid", identifier)
    return {"ok": True}


def config_path(value):
    if value.startswith("file:"):
        url = urlparse(value)
        if url.netloc not in ("", "localhost"):
            raise BackendError("Bitte eine lokale Datei auswählen.")
        value = unquote(url.path)
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".conf" or not path.is_file():
        raise BackendError("Bitte eine vorhandene WireGuard-.conf-Datei auswählen.")
    if path.stat().st_size > 1024 * 1024:
        raise BackendError("Konfigurationsdatei ist zu groß (maximal 1 MiB).")
    # libnm does not implement wg-quick shell hooks. Refuse instead of silently
    # dropping routing/firewall behavior on which this profile might depend.
    content = path.read_text(encoding="utf-8")
    if re.search(r"^\s*(PreUp|PostUp|PreDown|PostDown|Table|SaveConfig)\s*=", content, re.M | re.I):
        raise BackendError("wg-quick-Sonderoptionen gefunden (Hooks, Table oder SaveConfig). Bitte zuerst für NetworkManager anpassen.")
    return path


def prepare_import(value):
    path = config_path(value)
    try:
        import gi
        gi.require_version("NM", "1.0")
        from gi.repository import NM
    except (ImportError, ValueError):
        raise BackendError("Import benötigt python-gobject und libnm.") from None
    try:
        connection = NM.conn_wireguard_import(str(path))
        setting = connection.get_setting_connection()
        # Set this BEFORE submitting to the daemon: no autoactivation race.
        setting.set_property("autoconnect", False)
        setting.set_property("uuid", str(uuid.uuid4()))
        connection.verify()
    except Exception:
        raise BackendError("Ungültige oder nicht unterstützte WireGuard-Konfiguration.") from None
    return connection


def import_config(value):
    connection = prepare_import(value)
    from gi.repository import Gio, GLib, NM
    client = NM.Client.new(None)
    if not client.get_nm_running():
        raise BackendError("NetworkManager läuft nicht.")
    setting = connection.get_setting_connection()
    if any(c.get_id() == setting.get_id() for c in client.get_connections()):
        raise BackendError("Ein Profil mit diesem Namen existiert bereits. Datei vor dem Import umbenennen.")
    loop, cancel, outcome = GLib.MainLoop(), Gio.Cancellable(), {}

    def finished(source, result, _data):
        try:
            saved = source.add_connection_finish(result)
            outcome["uuid"] = saved.get_uuid()
        except GLib.Error:
            outcome["error"] = "Import fehlgeschlagen oder abgebrochen. NetworkManager-Berechtigung prüfen."
        loop.quit()

    def timed_out():
        cancel.cancel()
        outcome["error"] = "Zeitüberschreitung beim Import. Vor erneutem Import die Profilliste prüfen."
        loop.quit()
        return GLib.SOURCE_REMOVE

    client.add_connection_async(connection, True, cancel, finished, None)
    timeout_id = GLib.timeout_add_seconds(60, timed_out)
    loop.run()
    if "uuid" in outcome:
        GLib.source_remove(timeout_id)
        return {"ok": True, "uuid": outcome["uuid"], "message": "Profil importiert. Zum Verbinden das Profil auswählen."}
    raise BackendError(outcome.get("error", "Import fehlgeschlagen."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "up", "down", "import"])
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "status":
            result = {"ok": True, "profiles": profiles()}
        elif not args.value:
            raise BackendError("Profil-ID oder Dateipfad fehlt.")
        elif args.action == "import":
            result = import_config(args.value)
        else:
            result = change_connection(args.action, args.value)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (BackendError, OSError, UnicodeError) as error:
        message = str(error) if isinstance(error, BackendError) else "Datei oder Dienst nicht zugänglich."
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({"ok": False, "error": "Unerwarteter Backend-Fehler. Abhängigkeiten und NetworkManager prüfen."}))
        return 1


if __name__ == "__main__":
    sys.exit(main())

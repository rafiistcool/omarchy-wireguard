# Omarchy WireGuard

WireGuard-Plugin für die Omarchy-Shell (Quickshell), Plugin-ID `rafi.wireguard`.

## Installation von GitHub

```bash
omarchy plugin add https://github.com/rafiistcool/omarchy-wireguard --enable
```

Danach erscheint **WG** rechts in der Leiste. Anklicken öffnet die Profile und den Konfigurationsimport.

Updates und Deaktivierung:

```bash
omarchy plugin update rafi.wireguard
omarchy plugin disable rafi.wireguard
```

## Funktionen

- WireGuard-Profile aus NetworkManager anzeigen.
- Profile gezielt über ihre UUID verbinden und trennen.
- `.conf`-Dateien per Dateiauswahl importieren, z. B. vom Heimrouter oder VPN-Anbieter.
- Neue Profile werden **ohne automatische Verbindung** gespeichert. Erst „Verbinden“ aktiviert den Tunnel.
- Statusänderungen über `nmcli monitor`, zusätzlich Aktualisierung alle 30 Sekunden.
- Fehlermeldungen und laufende Aktionen im Panel anzeigen.

Die Anzeige „Tunnel aktiv“ bedeutet, dass NetworkManager das Profil aktiviert hat. Sie bestätigt weder einen WireGuard-Handshake noch die Erreichbarkeit des Heimnetzes. Mehrere Profile können gleichzeitig aktiv sein; Routen und DNS müssen dafür zusammenpassen. Bestehende Profile behalten ihre Einstellungen.

## Voraussetzungen

Omarchy mit der Quickshell-Plugin-API (`omarchy plugin`), laufender NetworkManager, Python 3, `python-gobject`, `libnm` und `zenity` für die Dateiauswahl. Die laufende Sitzung braucht die üblichen NetworkManager-/Polkit-Berechtigungen. Es wird kein eigener Root-Helfer installiert. Die Dateiauswahl läuft in einem separaten Prozess, damit Fehler nativer Dialogbibliotheken nicht die Shell betreffen.

Fehlende Pakete unter Omarchy bei Bedarf installieren:

```bash
omarchy pkg add networkmanager python python-gobject libnm zenity
```

## Lokal installieren

Aus diesem Repository heraus ausführen:

```bash
omarchy plugin validate .
destination="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/rafi.wireguard"
if [ -e "$destination" ]; then
  echo "Ziel existiert bereits: $destination"
else
  mkdir -p "$destination"
  cp manifest.json Panel.qml Service.qml backend.py "$destination/"
  omarchy plugin enable rafi.wireguard
fi
```

Das Repository selbst anzulegen aktiviert das Plugin noch nicht. Bei späteren Änderungen die vier Laufzeitdateien erneut in den Pluginordner kopieren; die Shell lädt Änderungen automatisch neu.

Das Panel lässt sich nach Installation auch über IPC öffnen:

```bash
omarchy-shell rafi.wireguard toggle
omarchy-shell rafi.wireguard status
```

## Konfiguration hinzufügen

1. WireGuard-Client-Konfiguration vom Heimrouter oder VPN-Anbieter exportieren.
2. Im WG-Panel „Konfiguration hinzufügen …“ anklicken und die lokale `.conf` auswählen.
3. Bei Bedarf die Polkit-Abfrage bestätigen.
4. Beim importierten Profil „Verbinden“ anklicken; später „Trennen“.

Der Dateiname wird von libnm als Profil-/Interfacename verwendet. Kurze Namen wie `zuhause.conf` oder `arbeit.conf` verwenden. Bereits vorhandene Profilnamen werden beim Import abgelehnt. Neue Profile werden dauerhaft von NetworkManager gespeichert; die Originaldatei wird weder verändert noch gelöscht. Sie enthält Schlüssel und sollte geschützt aufbewahrt werden.

Der Import verwendet den WireGuard-Parser von libnm. `PreUp`, `PostUp`, `PreDown`, `PostDown`, `Table` und `SaveConfig` werden ausdrücklich abgelehnt, weil ihre wg-quick-Semantik nicht übernommen wird. Keine Shell-Hooks werden ausgeführt. Profile löschen/bearbeiten und automatische WLAN-abhängige Umschaltung gehören noch nicht zu Version 0.1.0.

## Entwicklung und Prüfung

```bash
python3 -m unittest discover -s tests -v
python3 backend.py status
omarchy plugin validate .
git diff --check
```

Die Tests prüfen UUID-Auswahl, maskierte Profilnamen, Fehlerfälle und einen echten **offline**-Import einer synthetischen Konfiguration mit libnm. Sie verändern keine Netzwerkprofile. Ein erfolgreicher Heimnetz-/VPN-Verbindungstest erfordert eine echte Konfiguration und ein erreichbares Gegenüber.

Die QML-Oberfläche ruft das Backend mit Argumentlisten auf. Konfigurationsinhalte und Schlüssel werden nicht als JSON zurückgegeben; `.conf`, `.key` und `.nmconnection` sind in Git ignoriert.

Referenzen: [nmcli](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html), [NetworkManager API](https://networkmanager.dev/docs/api/latest/).

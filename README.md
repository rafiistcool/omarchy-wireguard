# Omarchy WireGuard

WireGuard direkt aus der Omarchy-Leiste: Profile anzeigen, verbinden, trennen und `.conf`-Dateien importieren.

## Installation

Benötigt Omarchy mit Quickshell-Plugins und einen laufenden NetworkManager.

```bash
omarchy pkg add networkmanager python python-gobject libnm zenity
omarchy plugin add https://github.com/rafiistcool/omarchy-wireguard --enable
```

## Nutzung

**WG** in der Leiste öffnen → **Konfiguration hinzufügen …** → `.conf` auswählen → **Verbinden**.

- Vorhandene WireGuard-Profile aus NetworkManager erscheinen automatisch.
- Neue Profile werden gespeichert, verbinden sich aber erst nach deinem Klick.
- **Trennen** beendet die Verbindung.

Für Importdateien kurze Namen wie `zuhause.conf` verwenden. Bereits vorhandene Profilnamen und wg-quick-Sonderoptionen (`PreUp`, `PostUp`, `PreDown`, `PostDown`, `Table`, `SaveConfig`) werden beim Import abgelehnt.

„Tunnel aktiv“ zeigt den NetworkManager-Status an, bestätigt aber keinen erfolgreichen Handshake. Das Plugin benötigt wie WireGuard eine erreichbare UDP-Verbindung.

## Verwaltung

```bash
omarchy plugin update rafi.wireguard    # Aktualisieren
omarchy plugin disable rafi.wireguard  # Deaktivieren
```

## Entwicklung

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Die Tests verändern keine Netzwerkprofile. VPN-Konfigurationen und Schlüssel gehören nicht ins Repository.

[MIT-Lizenz](LICENSE)

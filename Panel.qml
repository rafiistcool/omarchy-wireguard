import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
  id: root
  moduleName: "rafi.wireguard"
  ipcTarget: "rafi.wireguard"
  manageIpc: false
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  onOpenedChanged: if (opened) vpn.refresh()

  Service { id: vpn }

  function chooseConfig() {
    if (vpn.busy || picker.running || !vpn.available) return
    root.close()
    picker.running = true
  }

  IpcHandler {
    target: root.ipcTarget
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function refresh(): void { vpn.refresh() }
    function chooseConfig(): void { root.chooseConfig() }
    function status(): string {
      return JSON.stringify({available: vpn.available, busy: vpn.busy,
        profiles: vpn.profiles, error: vpn.error, opened: root.opened})
    }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: vpn.busy ? "WG …" : vpn.activeCount > 0 ? "WG ●" : "WG"
    dimmed: vpn.available && vpn.activeCount === 0
    tooltipText: vpn.error || (vpn.activeCount > 0 ? "WireGuard: " + vpn.activeCount + " Tunnel aktiv" : "WireGuard öffnen")
    onPressed: root.toggle()
  }

  // The file chooser runs outside the long-lived shell: native GTK/GVfs
  // failures cannot take the bar, notifications and lock service down.
  Process {
    id: picker
    command: ["zenity", "--file-selection", "--title=WireGuard-Konfiguration importieren", "--file-filter=WireGuard | *.conf"]
    property string output: ""
    onStarted: output = ""
    stdout: StdioCollector { onStreamFinished: picker.output = text }
    onExited: function(exitCode, exitStatus) {
      if (exitCode === 0 && output !== "") vpn.run("import", output.replace(/\n$/, ""))
      else if (exitCode !== 1) vpn.actionError = "Dateiauswahl konnte nicht geöffnet werden. Bitte zenity prüfen."
      root.open()
    }
  }

  KeyboardPanel {
    id: popup
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: content
    contentWidth: fittedContentWidth(Style.space(380))
    contentHeight: fittedContentHeight(column.implicitHeight, Style.space(520))

    FocusScope {
      id: content
      anchors.fill: parent
      Keys.onEscapePressed: root.close()
      Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        Controls.ScrollBar.vertical: Controls.ScrollBar {}
        Column {
          id: column
          width: parent.width
          spacing: Style.space(12)
          Label { text: "WireGuard"; font.pixelSize: Style.font.title }
          Label {
            text: vpn.busy ? "Aktion läuft …" : vpn.activeCount > 0 ? "Tunnel aktiv" : "Kein Tunnel aktiv"
          }
          Label {
            visible: vpn.activeCount > 0
            text: "Tunnelstatus laut NetworkManager. Die Erreichbarkeit des Ziels wird nicht geprüft."
            opacity: 0.65
          }
          Label { visible: vpn.error !== ""; text: vpn.error; color: Color.urgent }
          Label { visible: vpn.message !== ""; text: vpn.message }
          Label {
            visible: vpn.available && vpn.profiles.length === 0
            text: "Noch keine WireGuard-Profile. Importiere die .conf-Datei deines Routers oder VPN-Anbieters."
          }
          Repeater {
            model: vpn.profiles
            delegate: Column {
              required property var modelData
              width: column.width
              spacing: Style.space(4)
              Label { text: modelData.name }
              Label {
                text: modelData.uuid.slice(0, 8) + " · " + (modelData.active ? "Aktiv" : "Getrennt")
                opacity: 0.65
              }
              Button {
                text: modelData.active ? "Trennen" : "Verbinden"
                enabled: !vpn.busy && vpn.available
                focusable: true
                bordered: true
                onClicked: vpn.run(modelData.active ? "down" : "up", modelData.uuid)
              }
            }
          }
          Button {
            text: "Konfiguration hinzufügen …"
            enabled: !vpn.busy && vpn.available
            focusable: true
            bordered: true
            onClicked: root.chooseConfig()
          }
          Button {
            text: "Aktualisieren"
            enabled: !vpn.busy
            focusable: true
            onClicked: { vpn.actionError = ""; vpn.message = ""; vpn.refresh() }
          }
          Label {
            text: "Neue Profile verbinden sich erst nach deinem Klick."
            opacity: 0.65
          }
        }
      }
    }
  }

  component Label: Text {
    width: parent.width
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
    color: Color.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.body
  }
}

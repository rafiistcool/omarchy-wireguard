import QtQuick
import Quickshell.Io

Item {
  id: root
  property var profiles: []
  property string statusError: ""
  property string actionError: ""
  readonly property string error: actionError || statusError
  property string message: ""
  property bool available: false
  readonly property bool busy: action.running
  readonly property int activeCount: profiles.filter(function(p) { return p.active }).length
  readonly property string backend: decodeURIComponent(Qt.resolvedUrl("backend.py").toString().replace(/^file:\/\//, ""))

  function parse(text) {
    try { return JSON.parse(text) }
    catch (_) { return {ok: false, error: "Backend konnte nicht gestartet werden oder lieferte keine gültige Antwort."} }
  }
  function refresh() {
    if (query.running || busy) { debounce.restart(); return }
    query.running = true
  }
  function run(kind, value) {
    if (busy) return
    actionError = ""
    message = ""
    action.command = ["python3", backend, kind, value]
    action.running = true
  }
  Component.onCompleted: refresh()
  Timer { id: debounce; interval: 400; onTriggered: root.refresh() }
  // Event driven updates; slow fallback also recovers a restarted daemon.
  Timer { interval: 30000; running: true; repeat: true; onTriggered: root.refresh() }
  Timer { id: monitorRetry; interval: 10000; onTriggered: monitor.running = true }
  Process {
    id: monitor
    command: ["nmcli", "monitor"]
    running: true
    stdout: SplitParser { onRead: debounce.restart() }
    onExited: monitorRetry.restart()
  }
  Process {
    id: query
    command: ["python3", root.backend, "status"]
    property string output: ""
    onStarted: output = ""
    stdout: StdioCollector { onStreamFinished: query.output = text }
    onExited: {
      var result = root.parse(output)
      root.available = result.ok
      root.profiles = result.ok ? result.profiles : []
      root.statusError = result.ok ? "" : result.error
    }
  }
  Process {
    id: action
    property string output: ""
    onStarted: output = ""
    stdout: StdioCollector { onStreamFinished: action.output = text }
    onExited: {
      var result = root.parse(output)
      if (!result.ok) root.actionError = result.error
      else root.message = result.message || "Aktion abgeschlossen."
      debounce.restart()
    }
  }
}

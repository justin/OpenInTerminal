import Cocoa
import OpenInTerminalCore
import ShortcutRecorder

let suiteName = "com.justinwme.OpenInTerminal.tests.\(UUID().uuidString)"
let fixture = UserDefaults(suiteName: suiteName)!
Defaults = fixture
defer { fixture.removePersistentDomain(forName: suiteName) }

_ = NSApplication.shared
let delegate = AppDelegate()
let monitor = GlobalShortcutMonitor.shared
defer { monitor.removeAllActions() }

delegate.bindShortcuts()
let actions = [delegate.terminalShortcutAction!, delegate.editorShortcutAction!, delegate.copyPathShortcutAction!]
for action in actions {
    precondition(action.shortcut == nil, "Fixture must start without a saved shortcut")
    precondition(monitor.actions.contains(action), "Unassigned shortcut must be observed by the monitor")
}
print("Passed registration of all three initially unassigned shortcut actions")

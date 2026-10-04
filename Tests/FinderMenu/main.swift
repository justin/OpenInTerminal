import Cocoa
import OpenInTerminalCore

// Keep the fixture separate from the app's shared preferences.
let suiteName = "com.justinwme.OpenInTerminal.tests.\(UUID().uuidString)"
let fixture = UserDefaults(suiteName: suiteName)!
Defaults = fixture
defer { fixture.removePersistentDomain(forName: suiteName) }

let finder = FinderSync()
let rootURL = URL(fileURLWithPath: "/", isDirectory: true)
let externalURL = URL(fileURLWithPath: "/Volumes/External", isDirectory: true)
precondition(FinderSync.monitoredDirectories(including: nil) == [rootURL])
precondition(FinderSync.monitoredDirectories(including: []) == [rootURL])
precondition(FinderSync.monitoredDirectories(including: [externalURL]) == [rootURL, externalURL])
var checks = 3

func verify(_ menu: NSMenu, grouped: Bool, expectedActions: [Selector]) {
    let items: [NSMenuItem]
    if grouped {
        precondition(menu.items.count == 1, "Expected one submenu")
        items = menu.items[0].submenu!.items
    } else {
        items = menu.items
    }
    precondition(items.compactMap(\.action) == expectedActions,
                 "Unexpected actions: \(items.compactMap(\.action))")
    checks += 1
}

let copy = #selector(FinderSync.copyPathToClipboard)
let terminal = #selector(FinderSync.openDefaultTerminal)
let editor = #selector(FinderSync.openDefaultEditor)

for grouped in [false, true] {
    for hasTerminal in [false, true] {
        for hasEditor in [false, true] {
            fixture.removePersistentDomain(forName: suiteName)
            if hasTerminal { fixture.set("Terminal", forKey: "DefaultTerminal") }
            if hasEditor { fixture.set("TextEdit", forKey: "DefaultEditor") }
            fixture.set(grouped, forKey: "ContextMenuUseSubmenu")
            let actions = (hasTerminal ? [terminal] : []) + (hasEditor ? [editor] : []) + [copy]
            verify(finder.menu(for: .contextualMenuForItems), grouped: grouped, expectedActions: actions)
            verify(finder.menu(for: .toolbarItemMenu), grouped: false, expectedActions: actions)
        }
    }
    for data in [nil, Data("invalid JSON".utf8), Data("[]".utf8)] as [Data?] {
        fixture.removePersistentDomain(forName: suiteName)
        if let data = data { fixture.set(data, forKey: "CustomMenuOptions") }
        fixture.set(true, forKey: "CustomMenuApplyToContext")
        fixture.set(true, forKey: "CustomMenuApplyToToolbar")
        fixture.set(grouped, forKey: "ContextMenuUseSubmenu")
        verify(finder.menu(for: .contextualMenuForItems), grouped: grouped, expectedActions: [copy])
        verify(finder.menu(for: .toolbarItemMenu), grouped: false, expectedActions: [copy])
    }
}
fixture.set(true, forKey: "HideContextMenuItems")
precondition(finder.menu(for: .contextualMenuForItems).items.isEmpty)
checks += 1
print("Passed \(checks) Finder menu checks")

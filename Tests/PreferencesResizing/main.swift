import Cocoa

let application = NSApplication.shared
let storyboardURL = URL(fileURLWithPath: "OpenInTerminal/PreferencesWindow/Base.lproj/Preferences.storyboard")
let storyboard = try XMLDocument(contentsOf: storyboardURL)
let controllers = try storyboard.nodes(forXPath: "//tabViewController[@customClass='PreferencesTabViewController']")
precondition(controllers.count == 1, "Preferences must use the animated tab controller")

let tabs = PreferencesTabViewController()
tabs.tabStyle = .toolbar
tabs.transitionOptions = [.allowUserInteraction]
for height in [200, 400] {
    let child = NSViewController()
    child.view = NSView(frame: NSRect(x: 0, y: 0, width: 500, height: height))
    child.preferredContentSize = child.view.frame.size
    child.view.widthAnchor.constraint(equalToConstant: 500).isActive = true
    child.view.heightAnchor.constraint(equalToConstant: CGFloat(height)).isActive = true
    child.view.wantsLayer = true
    let label = NSTextField(labelWithString: "Preferences pane")
    label.translatesAutoresizingMaskIntoConstraints = false
    label.wantsLayer = true
    child.view.addSubview(label)
    NSLayoutConstraint.activate([
        label.topAnchor.constraint(equalTo: child.view.topAnchor, constant: 20),
        label.leadingAnchor.constraint(equalTo: child.view.leadingAnchor, constant: 20)
    ])
    tabs.addTabViewItem(NSTabViewItem(viewController: child))
}

let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 500, height: 200),
                      styleMask: [.titled, .closable], backing: .buffered, defer: false)
window.contentViewController = tabs
window.orderFront(nil)
RunLoop.main.run(until: Date().addingTimeInterval(0.3))

func verifyResize(to index: Int, heightChange: CGFloat) {
    let originalFrame = window.frame
    let targetHeight = originalFrame.height + heightChange
    let previousLabel = tabs.tabViewItems[tabs.selectedTabViewItemIndex].viewController!.view.subviews[0]
    let expectedLabelTop = window.convertToScreen(previousLabel.convert(previousLabel.bounds, to: nil)).maxY
    tabs.selectedTabViewItemIndex = index
    let pane = tabs.tabViewItems[index].viewController!.view
    let label = pane.subviews[0]
    let settledLabelFrame = label.frame

    var intermediateHeights: [CGFloat] = []
    let deadline = Date().addingTimeInterval(0.6)
    while Date() < deadline {
        RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        let frame = window.frame
        let labelTop = window.convertToScreen(label.convert(label.bounds, to: nil)).maxY
        precondition(abs(labelTop - expectedLabelTop) < 1, "The pane must stay fixed beneath the toolbar during resizing")
        precondition(label.frame == settledLabelFrame, "The selected pane's controls must be laid out before resizing")
        if let presentation = label.layer?.presentation(), let layer = label.layer {
            precondition(abs(presentation.position.y - layer.position.y) < 1,
                         "The selected pane's controls must not slide during resizing")
        }
        precondition(abs(frame.maxY - originalFrame.maxY) < 1, "Resizing must keep the window's top edge fixed")
        if frame.height > min(originalFrame.height, targetHeight) + 1,
           frame.height < max(originalFrame.height, targetHeight) - 1 {
            intermediateHeights.append(frame.height)
        }
    }

    precondition(abs(window.frame.height - targetHeight) < 1, "The window must reach the selected tab's height")
    if !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion {
        precondition(!intermediateHeights.isEmpty, "The window must animate through intermediate heights")
    }
    print("Preferences resize: \(originalFrame.height) -> \(window.frame.height), intermediate heights: \(intermediateHeights)")
}

verifyResize(to: 1, heightChange: 200)
verifyResize(to: 0, heightChange: -200)
let smallFrame = window.frame
tabs.selectedTabViewItemIndex = 1
RunLoop.main.run(until: Date().addingTimeInterval(0.08))
tabs.selectedTabViewItemIndex = 0
RunLoop.main.run(until: Date().addingTimeInterval(0.6))
precondition(abs(window.frame.height - smallFrame.height) < 1, "Rapid switching must finish at the last selected pane's size")
precondition(window.contentViewController === tabs, "The live tab controller must be restored after resizing")
precondition(tabs.view.autoresizingMask == [.width, .height], "Resizing must restore the content view's autoresizing mask")
window.orderOut(nil)
print("Preferences resizing tests passed")

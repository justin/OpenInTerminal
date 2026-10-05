import Cocoa

class PreferencesTabViewController: NSTabViewController {

    private var contentAutoresizingMask: NSView.AutoresizingMask?

    override func tabView(_ tabView: NSTabView, didSelect tabViewItem: NSTabViewItem?) {
        guard let window = self.view.window, window.isVisible else {
            super.tabView(tabView, didSelect: tabViewItem)
            return
        }

        let originalFrame = window.frame
        if let autoresizingMask = self.contentAutoresizingMask {
            self.view.autoresizingMask = autoresizingMask
            self.contentAutoresizingMask = nil
            window.contentViewController = self
        }
        super.tabView(tabView, didSelect: tabViewItem)
        window.layoutIfNeeded()
        let targetFrame = window.frame
        guard originalFrame != targetFrame,
              !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else { return }

        // Keep the live pane at its final size and pinned below the toolbar. AppKit's
        // implicit layout animation otherwise moves the pane with the bottom edge.
        let container = NSView(frame: self.view.frame)
        let toolbar = window.toolbar
        let autoresizingMask = self.view.autoresizingMask
        self.contentAutoresizingMask = autoresizingMask
        window.contentView = container
        window.toolbar = toolbar
        self.view.autoresizingMask = [.minYMargin]
        container.addSubview(self.view)
        window.setFrame(originalFrame, display: false)

        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.25
            window.animator().setFrame(targetFrame, display: true)
        } completionHandler: { [self, weak window] in
            guard let window, window.contentView === container else { return }
            self.view.autoresizingMask = autoresizingMask
            self.contentAutoresizingMask = nil
            window.contentViewController = self
        }
    }

}

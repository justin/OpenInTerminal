//
//  PreferencesWindowController.swift
//  OpenInTerminal
//
//  Created by Jianing Wang on 2019/4/29.
//  Copyright © 2019 Jianing Wang. All rights reserved.
//

import Cocoa

class PreferencesWindow: NSWindow {

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if event.modifierFlags.intersection([.command, .control, .option, .shift]) == .command,
           event.charactersIgnoringModifiers?.lowercased() == "w" {
            self.performClose(nil)
            return true
        }
        return super.performKeyEquivalent(with: event)
    }

}

class PreferencesWindowController: NSWindowController {

    override func windowDidLoad() {
        super.windowDidLoad()

        self.window?.toolbarStyle = .preference
        self.window?.toolbar?.displayMode = .iconAndLabel
    }
    
}

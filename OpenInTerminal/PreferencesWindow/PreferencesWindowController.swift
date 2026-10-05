//
//  PreferencesWindowController.swift
//  OpenInTerminal
//
//  Created by Jianing Wang on 2019/4/29.
//  Copyright © 2019 Jianing Wang. All rights reserved.
//

import Cocoa

class PreferencesWindowController: NSWindowController {

    override func windowDidLoad() {
        super.windowDidLoad()

        self.window?.toolbarStyle = .preference
        self.window?.toolbar?.displayMode = .iconAndLabel
    }
    
}

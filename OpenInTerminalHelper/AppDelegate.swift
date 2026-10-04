//
//  AppDelegate.swift
//  OpenInTerminalHelper
//
//  Created by Jianing Wang on 2019/5/5.
//  Copyright © 2019 Jianing Wang. All rights reserved.
//

import Cocoa

@NSApplicationMain
class AppDelegate: NSObject, NSApplicationDelegate {

    public func applicationDidFinishLaunching(_ aNotification: Notification) {
        let mainAppIdentifier = "com.justinwme.OpenInTerminal"
        let running = NSWorkspace.shared.runningApplications
        var alreadyRunning = false
        
        for app in running {
            if app.bundleIdentifier == mainAppIdentifier {
                alreadyRunning = true
                break
            }
        }
        
        if !alreadyRunning {
            LaunchNotifier.addObserver(observer: NSApp,
                                       selector: #selector(NSApplication.terminate(_:)),
                                       notification: .terminateApp,
                                       object: mainAppIdentifier)
            
            let appURL = Bundle.main.bundleURL
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
            NSWorkspace.shared.openApplication(at: appURL, configuration: .init()) { _, error in
                if let error = error {
                    NSLog("Unable to launch OpenInTerminal: %@", error.localizedDescription)
                }
                DispatchQueue.main.async {
                    NSApp.terminate(nil)
                }
            }
        } else {
            NSApp.terminate(self)
        }
    }
    
    func applicationWillTerminate(_ aNotification: Notification) {
        print("helper app terminated")
    }


}


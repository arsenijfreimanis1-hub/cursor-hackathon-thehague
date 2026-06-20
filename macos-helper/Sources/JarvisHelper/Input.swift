import AppKit
import ApplicationServices
import CoreGraphics
import Foundation

enum Input {
    static var accessibilityGranted: Bool {
        AXIsProcessTrusted()
    }

    static func promptAccessibility() -> [String: Any] {
        let key = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        let options = [key: true] as CFDictionary
        let granted = AXIsProcessTrustedWithOptions(options)
        return ["ok": true, "granted": granted, "prompted": true]
    }

    static func click(x: Double, y: Double) -> [String: Any] {
        guard accessibilityGranted else {
            return ["ok": false, "error": "Enable Accessibility for JarvisHelper in System Settings"]
        }
        let point = CGPoint(x: x, y: y)
        guard let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left),
              let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left) else {
            return ["ok": false, "error": "could not create mouse event"]
        }
        down.post(tap: .cghidEventTap)
        up.post(tap: .cghidEventTap)
        return ["ok": true, "x": x, "y": y]
    }

    static func typeText(_ text: String) -> [String: Any] {
        guard accessibilityGranted else {
            return ["ok": false, "error": "Enable Accessibility for JarvisHelper in System Settings"]
        }
        guard !text.isEmpty else {
            return ["ok": false, "error": "empty text"]
        }
        let source = CGEventSource(stateID: .hidSystemState)
        text.unicodeScalars.forEach { scalar in
            var chars = [UniChar(scalar.value)]
            if let keyDown = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: true),
               let keyUp = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: false) {
                keyDown.keyboardSetUnicodeString(stringLength: 1, unicodeString: &chars)
                keyUp.keyboardSetUnicodeString(stringLength: 1, unicodeString: &chars)
                keyDown.post(tap: .cghidEventTap)
                keyUp.post(tap: .cghidEventTap)
            }
        }
        return ["ok": true, "length": text.count]
    }

    static func pressKey(_ key: String, modifiers: [String] = []) -> [String: Any] {
        guard accessibilityGranted else {
            return ["ok": false, "error": "Enable Accessibility for JarvisHelper in System Settings"]
        }
        let keyMap: [String: CGKeyCode] = [
            "a": 0x00, "b": 0x0B, "c": 0x08, "d": 0x02, "e": 0x0E, "f": 0x03,
            "g": 0x05, "h": 0x04, "i": 0x22, "j": 0x26, "k": 0x28, "l": 0x25,
            "m": 0x2E, "n": 0x2D, "o": 0x1F, "p": 0x23, "q": 0x0C, "r": 0x0F,
            "s": 0x01, "t": 0x11, "u": 0x20, "v": 0x09, "w": 0x0D, "x": 0x07,
            "y": 0x10, "z": 0x06,
            "return": 0x24, "enter": 0x24, "tab": 0x30, "escape": 0x35,
            "space": 0x31, "delete": 0x33, "up": 0x7E, "down": 0x7D,
            "left": 0x7B, "right": 0x7C,
        ]
        guard let code = keyMap[key.lowercased()] else {
            return ["ok": false, "error": "unknown key: \(key)"]
        }
        var flags: CGEventFlags = []
        for mod in modifiers.map({ $0.lowercased() }) {
            switch mod {
            case "cmd", "command": flags.insert(.maskCommand)
            case "shift": flags.insert(.maskShift)
            case "alt", "option": flags.insert(.maskAlternate)
            case "ctrl", "control": flags.insert(.maskControl)
            default: break
            }
        }
        let source = CGEventSource(stateID: .hidSystemState)
        guard let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true),
              let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false) else {
            return ["ok": false, "error": "could not create key event"]
        }
        down.flags = flags
        up.flags = flags
        down.post(tap: .cghidEventTap)
        up.post(tap: .cghidEventTap)
        return ["ok": true, "key": key]
    }
}

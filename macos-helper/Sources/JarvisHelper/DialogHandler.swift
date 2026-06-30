import AppKit
import ApplicationServices
import Foundation

/// Native macOS dialog handler — uses Accessibility only (no Screen Recording required).
/// Presses Allow/OK on TCC sheets and enables JarvisHelper toggles in System Settings.
enum DialogHandler {
    private static let allowTitles = [
        "allow", "ok", "open", "continue", "grant", "enable", "turn on", "accept", "yes",
    ]
    private static let denyTitles = [
        "don't allow", "dont allow", "deny", "cancel", "no", "delete", "erase", "remove",
    ]
    private static let jarvisAppNames = ["jarvishelper", "william agent", "jarvis helper"]
    private static let settingsBundles = [
        "com.apple.systempreferences",
        "com.apple.SystemSettings",
        "com.apple.coreservices.uiagent",
        "com.apple.SecurityAgent",
        "com.apple.TCC",
    ]

    static func handleDialogs() -> [String: Any] {
        guard Input.accessibilityGranted else {
            return [
                "ok": false,
                "acted": false,
                "error": "Enable Accessibility for JarvisHelper in System Settings",
            ]
        }

        var actions: [[String: Any]] = []
        let apps = NSWorkspace.shared.runningApplications

        for bundle in settingsBundles {
            if let app = apps.first(where: { $0.bundleIdentifier == bundle }),
               let action = scanApplication(app, includeToggles: true) {
                actions.append(action)
            }
        }

        if actions.isEmpty {
            for app in apps where app.activationPolicy == .regular && !app.isHidden {
                if let action = scanApplication(app, includeToggles: false) {
                    actions.append(action)
                    break
                }
            }
        }

        return [
            "ok": true,
            "acted": !actions.isEmpty,
            "actions": actions,
            "method": "accessibility",
        ]
    }

    private static func scanApplication(_ app: NSRunningApplication, includeToggles: Bool) -> [String: Any]? {
        let axApp = AXUIElementCreateApplication(app.processIdentifier)
        let appName = app.localizedName ?? app.bundleIdentifier ?? "app"

        if includeToggles, let toggle = enableJarvisHelperToggles(in: axApp, appName: appName) {
            return toggle
        }
        return scanElement(axApp, appName: appName, depth: 0)
    }

    /// Find JarvisHelper rows in Privacy panes and enable unchecked checkboxes/switches.
    private static func enableJarvisHelperToggles(in root: AXUIElement, appName: String) -> [String: Any]? {
        var jarvisElements: [AXUIElement] = []
        collectJarvisHelperLabels(in: root, depth: 0, into: &jarvisElements)
        for label in jarvisElements {
            if let toggle = findNearbyToggle(for: label, depth: 0) {
                if let action = pressToggleIfNeeded(toggle, appName: appName) {
                    return action
                }
            }
        }
        return nil
    }

    private static func collectJarvisHelperLabels(
        in element: AXUIElement,
        depth: Int,
        into result: inout [AXUIElement]
    ) {
        if depth > 14 { return }

        var roleValue: CFTypeRef?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""

        if role == kAXStaticTextRole as String || role == "AXTitle" {
            var titleValue: CFTypeRef?
            AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
            let title = (titleValue as? String ?? "").lowercased()
            if jarvisAppNames.contains(where: { title.contains($0) }) {
                result.append(element)
            }
        }

        for child in children(of: element) {
            collectJarvisHelperLabels(in: child, depth: depth + 1, into: &result)
        }
    }

    private static func findNearbyToggle(for label: AXUIElement, depth: Int) -> AXUIElement? {
        if depth > 4 { return nil }

        var parentValue: CFTypeRef?
        guard AXUIElementCopyAttributeValue(label, kAXParentAttribute as CFString, &parentValue) == .success,
              let parent = parentValue else { return nil }
        let row = parent as! AXUIElement

        if let toggle = firstToggle(in: row, depth: 0) {
            return toggle
        }
        return findNearbyToggle(for: row, depth: depth + 1)
    }

    private static func firstToggle(in element: AXUIElement, depth: Int) -> AXUIElement? {
        if depth > 6 { return nil }

        var roleValue: CFTypeRef?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""

        if role == kAXCheckBoxRole as String || role == "AXSwitch" || role == kAXRadioButtonRole as String {
            return element
        }

        for child in children(of: element) {
            if let hit = firstToggle(in: child, depth: depth + 1) {
                return hit
            }
        }
        return nil
    }

    private static func pressToggleIfNeeded(_ toggle: AXUIElement, appName: String) -> [String: Any]? {
        var valueRef: CFTypeRef?
        AXUIElementCopyAttributeValue(toggle, kAXValueAttribute as CFString, &valueRef)

        let isOn: Bool
        if let num = valueRef as? NSNumber {
            isOn = num.intValue != 0
        } else if let checked = valueRef as? Bool {
            isOn = checked
        } else {
            isOn = false
        }

        guard !isOn else { return nil }

        let err = AXUIElementPerformAction(toggle, kAXPressAction as CFString)
        var titleValue: CFTypeRef?
        AXUIElementCopyAttributeValue(toggle, kAXTitleAttribute as CFString, &titleValue)
        let title = (titleValue as? String ?? "JarvisHelper toggle").trimmingCharacters(in: .whitespacesAndNewlines)

        return [
            "app": appName,
            "button": title.isEmpty ? "enable JarvisHelper" : title,
            "pressed": err == .success,
            "error_code": err.rawValue,
            "kind": "privacy_toggle",
        ]
    }

    private static func scanElement(
        _ element: AXUIElement,
        appName: String,
        depth: Int
    ) -> [String: Any]? {
        if depth > 12 { return nil }

        var roleValue: CFTypeRef?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""

        if role == kAXButtonRole as String {
            var titleValue: CFTypeRef?
            AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
            let title = (titleValue as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            let lower = title.lowercased()
            if shouldPress(title: lower, appName: appName) {
                let err = AXUIElementPerformAction(element, kAXPressAction as CFString)
                return [
                    "app": appName,
                    "button": title,
                    "pressed": err == .success,
                    "error_code": err.rawValue,
                    "kind": "dialog_button",
                ]
            }
        }

        for child in children(of: element) {
            if let hit = scanElement(child, appName: appName, depth: depth + 1) {
                return hit
            }
        }
        return nil
    }

    private static func children(of element: AXUIElement) -> [AXUIElement] {
        var value: CFTypeRef?
        AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &value)
        return value as? [AXUIElement] ?? []
    }

    private static func shouldPress(title: String, appName: String) -> Bool {
        guard !title.isEmpty else { return false }
        if denyTitles.contains(where: { title.contains($0) }) {
            return false
        }
        if allowTitles.contains(where: { title == $0 || title.hasPrefix($0) }) {
            return true
        }
        if title.contains("allow") && (appName.lowercased().contains("security") || title.contains("record")) {
            return true
        }
        return false
    }
}

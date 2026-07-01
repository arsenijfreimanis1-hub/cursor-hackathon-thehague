import AppKit
import ApplicationServices
import Foundation

/// Desktop awareness via Accessibility API — no Screen Recording permission required.
enum DesktopContext {
    private static let interactiveRoles: Set<String> = [
        kAXButtonRole as String,
        "AXLink",
        kAXMenuItemRole as String,
        kAXCheckBoxRole as String,
        "AXSwitch",
        kAXRadioButtonRole as String,
        kAXPopUpButtonRole as String,
        kAXTextFieldRole as String,
        "AXTextArea",
        "AXComboBox",
        kAXTabGroupRole as String,
    ]

    private static let textRoles: Set<String> = [
        kAXStaticTextRole as String,
        "AXTitle",
        kAXTextFieldRole as String,
        "AXTextArea",
        kAXValueAttribute as String,
    ]

    static func snapshot(maxElements: Int = 180) -> [String: Any] {
        guard Input.accessibilityGranted else {
            return [
                "ok": false,
                "error": "Enable Accessibility for JarvisHelper in System Settings → Privacy & Security → Accessibility",
                "method": "accessibility",
            ]
        }

        guard let app = NSWorkspace.shared.frontmostApplication else {
            return ["ok": false, "error": "no frontmost application", "method": "accessibility"]
        }

        let axApp = AXUIElementCreateApplication(app.processIdentifier)
        let appName = app.localizedName ?? app.bundleIdentifier ?? "Unknown"
        let bundleId = app.bundleIdentifier ?? ""
        let windowTitle = focusedWindowTitle(axApp: axApp) ?? appName

        var lines: [String] = []
        var elements: [[String: Any]] = []
        var count = 0

        collect(
            element: axApp,
            depth: 0,
            appName: appName,
            lines: &lines,
            elements: &elements,
            count: &count,
            maxElements: maxElements
        )

        let focused = focusedElementSummary(axApp: axApp)
        if let focused, !focused.isEmpty {
            lines.insert("FOCUSED: \(focused)", at: 0)
        }

        let textBlock = """
        APP: \(appName)
        BUNDLE: \(bundleId)
        WINDOW: \(windowTitle)
        ---
        \(lines.joined(separator: "\n"))
        """

        return [
            "ok": true,
            "method": "accessibility",
            "app": appName,
            "bundle_id": bundleId,
            "window_title": windowTitle,
            "focused": focused as Any,
            "element_count": elements.count,
            "elements": elements,
            "text": textBlock,
        ]
    }

    static func press(target: String) -> [String: Any] {
        guard Input.accessibilityGranted else {
            return ["ok": false, "error": "Accessibility not granted", "method": "accessibility"]
        }
        let needle = target.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !needle.isEmpty else {
            return ["ok": false, "error": "empty target", "method": "accessibility"]
        }

        guard let app = NSWorkspace.shared.frontmostApplication else {
            return ["ok": false, "error": "no frontmost application", "method": "accessibility"]
        }

        let axApp = AXUIElementCreateApplication(app.processIdentifier)
        if let hit = findPressable(in: axApp, target: needle, depth: 0) {
            let err = AXUIElementPerformAction(hit.element, kAXPressAction as CFString)
            return [
                "ok": err == .success,
                "pressed": err == .success,
                "target": target,
                "matched": hit.title,
                "role": hit.role,
                "app": app.localizedName ?? "",
                "method": "accessibility",
                "error_code": err.rawValue,
            ]
        }

        return [
            "ok": false,
            "error": "no matching control for \"\(target)\"",
            "method": "accessibility",
        ]
    }

    // MARK: - Tree walk

    private struct PressableHit {
        let element: AXUIElement
        let title: String
        let role: String
    }

    private static func collect(
        element: AXUIElement,
        depth: Int,
        appName: String,
        lines: inout [String],
        elements: inout [[String: Any]],
        count: inout Int,
        maxElements: Int
    ) {
        if depth > 14 || count >= maxElements { return }

        let role = attrString(element, kAXRoleAttribute as CFString) ?? ""
        let title = (attrString(element, kAXTitleAttribute as CFString) ?? attrString(element, kAXDescriptionAttribute as CFString) ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let value = attrString(element, kAXValueAttribute as CFString) ?? ""

        let isInteractive = interactiveRoles.contains(role)
        let hasText = !title.isEmpty || !value.isEmpty

        if hasText && (isInteractive || role == kAXStaticTextRole as String || depth <= 3) {
            var label = title
            if !value.isEmpty && value != title {
                label = label.isEmpty ? value : "\(label) = \"\(value.prefix(120))\""
            }
            if !label.isEmpty {
                let shortRole = role.replacingOccurrences(of: "AX", with: "").lowercased()
                lines.append("[\(shortRole)] \(label)")
                elements.append([
                    "role": role,
                    "title": title,
                    "value": String(value.prefix(200)),
                    "depth": depth,
                ])
                count += 1
            }
        }

        for child in children(of: element) {
            collect(
                element: child,
                depth: depth + 1,
                appName: appName,
                lines: &lines,
                elements: &elements,
                count: &count,
                maxElements: maxElements
            )
        }
    }

    private static func findPressable(in element: AXUIElement, target: String, depth: Int) -> PressableHit? {
        if depth > 14 { return nil }

        let role = attrString(element, kAXRoleAttribute as CFString) ?? ""
        if interactiveRoles.contains(role) && role != kAXTextFieldRole as String && role != "AXTextArea" {
            let title = (attrString(element, kAXTitleAttribute as CFString) ?? attrString(element, kAXDescriptionAttribute as CFString) ?? "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            let lower = title.lowercased()
            if !lower.isEmpty && (lower == target || lower.contains(target) || target.contains(lower)) {
                return PressableHit(element: element, title: title, role: role)
            }
        }

        for child in children(of: element) {
            if let hit = findPressable(in: child, target: target, depth: depth + 1) {
                return hit
            }
        }
        return nil
    }

    private static func focusedWindowTitle(axApp: AXUIElement) -> String? {
        var windowValue: CFTypeRef?
        if AXUIElementCopyAttributeValue(axApp, kAXFocusedWindowAttribute as CFString, &windowValue) == .success,
           let window = windowValue {
            return attrString(window as! AXUIElement, kAXTitleAttribute as CFString)
        }
        return nil
    }

    private static func focusedElementSummary(axApp: AXUIElement) -> String? {
        var focusedValue: CFTypeRef?
        guard AXUIElementCopyAttributeValue(axApp, kAXFocusedUIElementAttribute as CFString, &focusedValue) == .success,
              let focused = focusedValue else { return nil }
        let el = focused as! AXUIElement
        let role = attrString(el, kAXRoleAttribute as CFString) ?? "element"
        let title = attrString(el, kAXTitleAttribute as CFString) ?? ""
        let value = attrString(el, kAXValueAttribute as CFString) ?? ""
        if !value.isEmpty { return "\(role) \(title) = \"\(value.prefix(80))\"" }
        if !title.isEmpty { return "\(role) \(title)" }
        return role
    }

    private static func attrString(_ element: AXUIElement, _ attribute: CFString) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute, &value) == .success else { return nil }
        if let s = value as? String { return s }
        if let n = value as? NSNumber { return n.stringValue }
        return nil
    }

    private static func children(of element: AXUIElement) -> [AXUIElement] {
        var value: CFTypeRef?
        AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &value)
        return value as? [AXUIElement] ?? []
    }
}

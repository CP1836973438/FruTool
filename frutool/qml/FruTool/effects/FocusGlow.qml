import QtQuick
import QtQuick.Window
import FruTool 1.0

Item {
    id: root
    property bool focused: false
    property bool pulse: false
    property color glowColor: Theme.focus_glow
    property color borderColor: Theme.focus_border
    property real glowStrength: Theme.glow_strength

    anchors.fill: parent
    z: -1

    readonly property bool windowIsMaximized: Window.window !== null
            && (Window.window.visibility === Window.Maximized
                || Window.window.visibility === Window.FullScreen)

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software
            && !Theme.layoutEffectsPaused
            && !(terminalVm.logDockOpen && root.windowIsMaximized)

    property real pulseBoost: 1.0

    SequentialAnimation on pulseBoost {
        running: root.focused && root.pulse
        loops: Animation.Infinite
        NumberAnimation { from: 0.55; to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1.0; to: 0.55; duration: 1200; easing.type: Easing.InOutSine }
    }

    onFocusedChanged: if (!root.focused || !root.pulse) root.pulseBoost = 1.0
    onPulseChanged: if (!root.pulse) root.pulseBoost = 1.0

    readonly property real effectiveGlow: root.focused ? root.glowStrength * (root.pulse ? root.pulseBoost : 1.0) : 0.0

    Rectangle {
        anchors.fill: parent
        radius: 4
        visible: !root.effectsEnabled
        color: "transparent"
        border.color: root.focused ? root.borderColor : "transparent"
        border.width: root.focused ? 1 : 0
        opacity: root.focused ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: 6
        visible: !root.effectsEnabled
        color: "transparent"
        border.color: root.glowColor
        border.width: 3
        opacity: root.focused ? 0.55 * root.effectiveGlow : 0.0
        Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    ShaderEffect {
        anchors.fill: parent
        anchors.margins: root.pulse ? -2 : 0
        visible: root.effectsEnabled
        property real iFocused: root.effectiveGlow
        property color iGlowColor: root.glowColor
        property color iBorderColor: root.borderColor
        opacity: root.focused ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 120 } }
        fragmentShader: Qt.resolvedUrl("../shaders/focus_glow.frag.qsb")
    }
}

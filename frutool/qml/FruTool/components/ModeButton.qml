import QtQuick
import FruTool 1.0
import QtQuick.Controls
import "../effects"

Item {
    id: root
    property string label: ""
    property bool checked: false
    property bool pulseWhenActive: false
    signal clicked()

    width: Math.max(72, labelText.implicitWidth + 24)
    height: 32

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software

    property real iTime: 0

    Timer {
        interval: 16
        running: root.checked && root.pulseWhenActive && root.effectsEnabled
        repeat: true
        onTriggered: root.iTime += interval / 1000.0
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        visible: !root.effectsEnabled || !root.pulseWhenActive || !root.checked
        color: root.checked ? Theme.accent_dim : Theme.surface2
        border.color: root.checked ? Theme.accent : Theme.border
        border.width: root.checked && root.pulseWhenActive ? 2 : 1

        SequentialAnimation on border.width {
            running: root.checked && root.pulseWhenActive && !root.effectsEnabled
            loops: Animation.Infinite
            NumberAnimation { from: 1; to: 3; duration: 1100; easing.type: Easing.InOutSine }
            NumberAnimation { from: 3; to: 1; duration: 1100; easing.type: Easing.InOutSine }
        }
    }

    ShaderEffect {
        anchors.fill: parent
        visible: root.effectsEnabled && root.checked && root.pulseWhenActive
        property real iTime: root.iTime
        property real iFlowSpeed: Theme.accent_flow_speed * 3.5
        property color iColorTop: Theme.accent_dim
        property color iColorBottom: Theme.accent
        property color iAccentColor: Theme.accent_hover
        opacity: 0.95
        fragmentShader: Qt.resolvedUrl("../shaders/gradient.frag.qsb")
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: "transparent"
        border.color: root.checked ? Theme.accent : Theme.border
        border.width: 1
        visible: root.effectsEnabled && root.checked && root.pulseWhenActive
    }

    Text {
        id: labelText
        anchors.centerIn: parent
        z: 1
        text: root.label
        color: root.checked ? Theme.text : Theme.text2
        font.pixelSize: Theme.fontSizeSubtitle
    }

    RippleOverlay {
        id: rippleFx
        z: 2
        rippleColor: Theme.accent
    }

    MouseArea {
        id: modeMouseArea
        anchors.fill: parent
        z: 3
        hoverEnabled: true
        onClicked: function(mouse) {
            rippleFx.trigger(mouse.x, mouse.y)
            root.clicked()
        }
    }

    ToolTip {
        visible: modeMouseArea.containsMouse
        text: root.checked ? "当前使用" + root.label + "模式" : "切换到" + root.label + "模式"
        delay: 600
    }
}

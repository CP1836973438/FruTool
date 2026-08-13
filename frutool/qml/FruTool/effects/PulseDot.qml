import QtQuick
import QtQuick.Window
import FruTool 1.0

Item {
    id: root
    property color dotColor: Theme.success
    property bool active: true
    /** 布局占位尺寸；涟漪动画会略超出此范围 */
    property real size: 10

    implicitWidth: size + 12
    implicitHeight: size + 12
    width: implicitWidth
    height: implicitHeight
    clip: false

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software

    property real iTime: 0

    Timer {
        interval: 16
        running: root.active && root.visible
        repeat: true
        onTriggered: root.iTime += interval / 1000.0
    }

    Rectangle {
        id: core
        anchors.centerIn: parent
        width: Math.max(5, root.size * 0.55)
        height: width
        radius: width / 2
        color: root.dotColor
        opacity: root.active ? 1.0 : 0.35
        z: 2

        SequentialAnimation on opacity {
            running: root.active
            loops: Animation.Infinite
            NumberAnimation { from: 0.35; to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1.0; to: 0.35; duration: 1200; easing.type: Easing.InOutSine }
        }

        SequentialAnimation on scale {
            running: root.active
            loops: Animation.Infinite
            NumberAnimation { from: 0.88; to: 1.12; duration: 1200; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1.12; to: 0.88; duration: 1200; easing.type: Easing.InOutSine }
        }
    }

    Repeater {
        model: root.active ? 2 : 0

        Item {
            anchors.centerIn: parent
            width: root.size + 12
            height: width

            Rectangle {
                id: ripple
                anchors.centerIn: parent
                width: root.size * 0.5
                height: width
                radius: width / 2
                color: "transparent"
                border.color: root.dotColor
                border.width: 1.5
                opacity: 0
                scale: 0.5
                transformOrigin: Item.Center
            }

            SequentialAnimation {
                running: root.active
                loops: Animation.Infinite
                PauseAnimation { duration: index * 600 }
                ParallelAnimation {
                    NumberAnimation { target: ripple; property: "opacity"; from: 0.9; to: 0; duration: 1400; easing.type: Easing.OutQuad }
                    NumberAnimation { target: ripple; property: "scale"; from: 0.5; to: 2.4; duration: 1400; easing.type: Easing.OutQuad }
                }
                PauseAnimation { duration: 400 }
            }
        }
    }

    ShaderEffect {
        anchors.centerIn: parent
        width: root.size * 3.0
        height: width
    readonly property bool windowIsMaximized: Window.window !== null
            && (Window.window.visibility === Window.Maximized
                || Window.window.visibility === Window.FullScreen)

        visible: root.effectsEnabled && root.active && !Theme.layoutEffectsPaused
                && !(terminalVm.logDockOpen && root.windowIsMaximized)
        z: 1
        property real iTime: root.iTime
        property real iActive: root.active ? 1.0 : 0.0
        property color iColor: root.dotColor
        fragmentShader: Qt.resolvedUrl("../shaders/pulse_dot.frag.qsb")
    }
}

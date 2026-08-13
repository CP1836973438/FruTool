import QtQuick
import FruTool 1.0

Item {
    id: root

    property color rippleColor: Theme.accent
    property real rippleProgress: 0
    property point rippleOrigin: Qt.point(0.5, 0.5)
    property bool rippling: false

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software

    anchors.fill: parent
    z: 10

    function trigger(localX, localY) {
        if (!effectsEnabled || width <= 0 || height <= 0) {
            rippleFallback.restart()
            return
        }
        rippleOrigin = Qt.point(localX / width, localY / height)
        rippling = true
        rippleProgress = 0
        rippleAnim.restart()
    }

    Rectangle {
        id: fallbackRipple
        visible: !root.effectsEnabled && fallbackRipple.opacity > 0
        anchors.centerIn: parent
        width: parent.width * 0.3
        height: width
        radius: width / 2
        color: root.rippleColor
        opacity: 0
        scale: 0.2
        transformOrigin: Item.Center

        SequentialAnimation {
            id: rippleFallback
            NumberAnimation { target: fallbackRipple; property: "opacity"; from: 0.25; to: 0; duration: 400 }
            NumberAnimation { target: fallbackRipple; property: "scale"; from: 0.2; to: 1.6; duration: 400; easing.type: Easing.OutQuad }
        }
    }

    SequentialAnimation {
        id: rippleAnim
        NumberAnimation {
            target: root
            property: "rippleProgress"
            from: 0
            to: 1
            duration: 420
            easing.type: Easing.OutQuad
        }
        ScriptAction { script: root.rippling = false }
    }

    ShaderEffect {
        anchors.fill: parent
        visible: root.effectsEnabled && root.rippling
        property real iRippleProgress: root.rippleProgress
        property point iRippleOrigin: root.rippleOrigin
        property color iRippleColor: root.rippleColor
        fragmentShader: Qt.resolvedUrl("../shaders/ripple.frag.qsb")
    }
}

import QtQuick
import QtQuick.Layouts
import FruTool 1.0

Item {
    id: root

    property int pageIndex: 0
    property bool emphasized: false
    property bool _initialized: false
    property int _previousPageIndex: pageIndex
    property real stackOpacity: 1.0
    property real stackOffset: 0.0
    property real stackScale: 1.0

    implicitWidth: stack.implicitWidth
    implicitHeight: stack.implicitHeight

    default property alias content: stack.data

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software

    StackLayout {
        id: stack
        anchors.fill: parent
        currentIndex: root.pageIndex
        opacity: root.stackOpacity
        scale: root.stackScale
        transform: Translate { x: root.stackOffset }
    }

    ShaderEffect {
        id: dissolveFx
        anchors.fill: parent
        visible: root.effectsEnabled && root.dissolveProgress > 0.001
        z: 10
        property real iProgress: root.dissolveProgress
        property real iTime: root.dissolveTime
        property color iColor: Theme.bg
        opacity: 0.95
        fragmentShader: Qt.resolvedUrl("../shaders/dissolve.frag.qsb")
    }

    property real dissolveProgress: 0
    property real dissolveTime: 0

    Timer {
        id: dissolveTimer
        interval: 16
        repeat: true
        onTriggered: root.dissolveTime += interval / 1000.0
    }

    NumberAnimation {
        id: dissolveAnim
        target: root
        property: "dissolveProgress"
        duration: root.emphasized ? 360 : 280
        easing.type: Easing.OutCubic
        onStarted: {
            root.dissolveTime = 0
            dissolveTimer.start()
        }
        onStopped: {
            dissolveTimer.stop()
            root.dissolveProgress = 0
        }
    }

    ParallelAnimation {
        id: pageEnter
        NumberAnimation {
            target: root
            property: "stackOpacity"
            to: 1.0
            duration: root.emphasized ? 260 : 180
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root
            property: "stackOffset"
            to: 0.0
            duration: root.emphasized ? 320 : 180
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root
            property: "stackScale"
            to: 1.0
            duration: root.emphasized ? 300 : 180
            easing.type: Easing.OutCubic
        }
    }

    Component.onCompleted: root._initialized = true

    onPageIndexChanged: {
        if (!root._initialized)
            return
        var direction = root.pageIndex >= root._previousPageIndex ? 1 : -1
        root._previousPageIndex = root.pageIndex
        root.stackOpacity = root.emphasized ? 0.72 : 0.88
        root.stackOffset = root.emphasized ? direction * 24 : 0
        root.stackScale = root.emphasized ? 0.985 : 1.0
        pageEnter.restart()
        if (root.effectsEnabled) {
            dissolveAnim.from = 0.0
            dissolveAnim.to = 1.0
            dissolveAnim.restart()
        }
    }
}

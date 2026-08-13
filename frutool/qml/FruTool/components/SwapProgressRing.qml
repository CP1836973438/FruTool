import QtQuick
import FruTool 1.0

Item {
    id: root

    property real progress: 0
    property real phaseIndex: 0
    property real phaseCount: 4
    property bool active: true
    property string statusLabel: ""
    property int ringSize: 72
    property bool compact: true

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software

    implicitWidth: compact ? 280 : ringSize + 16
    implicitHeight: compact ? 88 : ringSize + 16

    property real iTime: 0

    Timer {
        interval: 16
        running: root.visible
        repeat: true
        onTriggered: root.iTime += interval / 1000.0
    }

    Row {
        anchors.fill: parent
        visible: root.compact
        spacing: Theme.spacing_lg

        Item {
            width: root.ringSize
            height: root.ringSize
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                anchors.fill: parent
                visible: !root.effectsEnabled
                radius: width / 2
                color: "transparent"
                border.color: Theme.border
                border.width: 4
            }

            Rectangle {
                anchors.centerIn: parent
                width: 10
                height: 10
                radius: 5
                visible: !root.effectsEnabled
                color: root.active ? Theme.accent : Theme.text3
            }

            ShaderEffect {
                anchors.fill: parent
                visible: root.effectsEnabled
                property real iTime: root.iTime
                property real iProgress: root.progress
                property real iPhaseIndex: root.phaseIndex
                property real iPhaseCount: root.phaseCount
                property real iActive: root.active ? 1.0 : 0.0
                property color iAccentColor: Theme.accent
                property color iTrackColor: Theme.border
                property color iTextColor: Theme.text2
                fragmentShader: Qt.resolvedUrl("../shaders/swap_ring.frag.qsb")
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.spacing_xs
            width: parent.width - root.ringSize - Theme.spacing_lg

            Text {
                text: root.statusLabel
                color: Theme.text
                font.pixelSize: 13
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: Math.round(root.progress * 100) + "%"
                color: Theme.text3
                font.pixelSize: 11
                visible: root.progress > 0.01
            }
        }
    }

    Item {
        anchors.centerIn: parent
        visible: !root.compact
        width: root.ringSize
        height: root.ringSize

        Rectangle {
            anchors.fill: parent
            visible: !root.effectsEnabled
            radius: width / 2
            color: "transparent"
            border.color: Theme.border
            border.width: 5
        }

        Rectangle {
            anchors.centerIn: parent
            width: 14
            height: 14
            radius: 7
            visible: !root.effectsEnabled
            color: root.active ? Theme.accent : Theme.text3
        }

        ShaderEffect {
            anchors.fill: parent
            visible: root.effectsEnabled
            property real iTime: root.iTime
            property real iProgress: root.progress
            property real iPhaseIndex: root.phaseIndex
            property real iPhaseCount: root.phaseCount
            property real iActive: root.active ? 1.0 : 0.0
            property color iAccentColor: Theme.accent
            property color iTrackColor: Theme.border
            property color iTextColor: Theme.text2
            fragmentShader: Qt.resolvedUrl("../shaders/swap_ring.frag.qsb")
        }
    }
}

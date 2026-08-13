import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Rectangle {
    id: root
    property string title: ""
    property bool elevated: false
    property bool enableHoverLift: true
    property bool liveCapture: true
    property Item blurSource: null
    default property alias content: body.data

    property bool hovered: false

    radius: 6
    border.color: root.hovered ? Theme.accent_dim : Theme.border
    border.width: 1
    implicitWidth: body.implicitWidth + Theme.spacing_xl
    implicitHeight: body.implicitHeight + Theme.spacing_xl

    Behavior on border.color { ColorAnimation { duration: 200 } }

    color: "transparent"

    FrostedPanel {
        anchors.fill: parent
        blurSource: root.blurSource
        liveCapture: root.liveCapture
        panelColor: Theme.glass_card
        panelOpacity: root.enableHoverLift && root.hovered
            ? Theme.glass_card_opacity + 0.06
            : Theme.glass_card_opacity
            vibrancy: 0.48
        radius: root.radius
        borderColor: "transparent"
        z: 0

        Behavior on panelOpacity { NumberAnimation { duration: 200 } }
    }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: root.elevated ? 2 : 0
        radius: 6
        visible: root.elevated
        color: Qt.rgba(0, 0, 0, 0.18)
        opacity: root.hovered ? 0.26 : 0.18
        z: -1
        transform: Translate { y: 2 }

        Behavior on opacity { NumberAnimation { duration: 200 } }
    }

    ColumnLayout {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.spacing_md
        spacing: Theme.spacing_sm
        z: 1

        Text {
            visible: root.title !== ""
            text: root.title
            color: Theme.text
            font.pixelSize: Theme.fontSizeSubtitle
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: root.enableHoverLift
        acceptedButtons: Qt.NoButton
        onEntered: if (root.enableHoverLift) root.hovered = true
        onExited: if (root.enableHoverLift) root.hovered = false
    }
}

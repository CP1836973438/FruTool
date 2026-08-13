import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Item {
    id: root

    property string stepTitle: ""
    property string stepSubtitle: ""
    property bool locked: false
    property bool active: false
    property bool done: false
    property bool elevated: true
    property Item blurSource: null
    default property alias content: body.data

    implicitHeight: body.implicitHeight + Theme.spacing_xl

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: 6
        border.width: 1
        border.color: root.active ? Theme.accent
                               : (root.done && !root.locked ? Theme.success : Theme.border)
        opacity: root.locked ? 0.55 : (root.done && !root.active ? 0.85 : 1.0)

        Behavior on border.color { ColorAnimation { duration: 250; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

        color: "transparent"

        FrostedPanel {
            anchors.fill: parent
            blurSource: root.blurSource
            panelColor: Theme.glass_card
            panelOpacity: root.active ? Theme.glass_card_opacity + 0.06 : Theme.glass_card_opacity
            vibrancy: 0.35
            radius: panel.radius
            borderColor: "transparent"
            z: 0

            Behavior on panelOpacity { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
        }

        Rectangle {
            width: 3
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 8
            anchors.bottomMargin: 8
            radius: 2
            opacity: !root.locked && (root.active || root.done) ? 1.0 : 0.0
            color: root.active ? Theme.accent : Theme.success

            Behavior on opacity { NumberAnimation { duration: 200 } }
            Behavior on color { ColorAnimation { duration: 250; easing.type: Easing.OutCubic } }
        }

        FocusGlow {
            anchors.fill: parent
            anchors.margins: -1
            focused: root.active && !root.locked
            glowStrength: Theme.glow_strength * 0.55
            borderColor: root.active ? Theme.accent : Theme.success
        }

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: root.elevated && !root.locked && !root.done ? 2 : 0
            radius: 6
            visible: root.elevated && !root.locked && !root.done
            color: Qt.rgba(0, 0, 0, 0.16)
            z: -1
            transform: Translate { y: 2 }
        }

        ColumnLayout {
            id: body
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: (!root.locked && (root.active || root.done))
                               ? Theme.spacing_md + 4 : Theme.spacing_md
            anchors.rightMargin: Theme.spacing_md
            anchors.topMargin: Theme.spacing_md
            spacing: Theme.spacing_sm
            z: 1

            RowLayout {
                spacing: Theme.spacing_xs
                Layout.fillWidth: true

                Text {
                    Layout.fillWidth: true
                    text: root.stepTitle + (root.stepSubtitle ? " — " + root.stepSubtitle : "")
                    color: Theme.text
                    font.pixelSize: Theme.fontSizeSubtitle
                    font.weight: Font.DemiBold
                }

                Text {
                    visible: root.done && !root.active
                    text: "\u2713"
                    color: Theme.success
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
            }
        }
    }
}

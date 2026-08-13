import QtQuick
import FruTool 1.0

Item {
    id: root

    property Item blurSource: null
    property real radius: 8
    property color borderColor: Theme.border

    implicitWidth: 0
    implicitHeight: 0

    default property alias content: contentHost.data

    readonly property bool glassEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software
            && root.blurSource !== null

    Rectangle {
        id: shadow
        anchors.fill: panelFrame
        anchors.topMargin: 5
        anchors.bottomMargin: -5
        radius: root.radius + 1
        color: Qt.rgba(0, 0, 0, 0.36)
        z: -1
    }

    Rectangle {
        id: panelFrame
        anchors.fill: parent
        radius: root.radius
        opacity: Theme.dialog_backing_opacity

        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.surface_top }
            GradientStop { position: 1.0; color: Theme.surface2 }
        }
    }

    FrostedPanel {
        anchors.fill: parent
        blurSource: root.blurSource
        radius: root.radius
        panelColor: Theme.glass_dialog
        panelOpacity: Theme.glass_dialog_opacity
        vibrancy: 0.38
        edgeLight: 0.28
        borderColor: "transparent"
        visible: root.glassEnabled
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        visible: !root.glassEnabled
        color: Theme.glass_dialog
        opacity: Theme.glass_dialog_opacity * 0.9
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: Qt.rgba(1, 1, 1, 0.08)
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: root.borderColor
        border.width: 1
        opacity: 0.65
    }

    Item {
        id: contentHost
        anchors.fill: parent
        z: Theme.zContent
    }
}

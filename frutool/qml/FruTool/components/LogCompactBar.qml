import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Rectangle {
    id: root
    height: 28
    color: Theme.chrome_status
    border.color: terminalVm.lastLogLevel === "error" ? Qt.rgba(Theme.error.r, Theme.error.g, Theme.error.b, 0.55)
            : Theme.chrome_border
    border.width: 1

    opacity: 1.0
    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    function levelTextColor(level) {
        switch (level) {
        case "error": return Theme.error
        case "warning": return Theme.warning
        case "success": return Theme.success
        case "cmd": return Theme.accent
        default: return Theme.text2
        }
    }

    function levelDotColor(level) {
        switch (level) {
        case "error": return Theme.error
        case "warning": return Theme.warning
        case "success": return Theme.success
        case "cmd": return Theme.accent
        default: return Theme.text3
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: terminalVm.lastLogLevel === "error"
        color: Qt.rgba(Theme.error.r, Theme.error.g, Theme.error.b, 0.06)
        z: -1
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        PulseDot {
            id: unreadDot
            Layout.alignment: Qt.AlignVCenter
            size: 9
            dotColor: root.levelDotColor(terminalVm.lastLogLevel)
            active: terminalVm.compactHasUnread
        }

        Text {
            Layout.fillWidth: true
            text: terminalVm.lastLogPlain
            color: root.levelTextColor(terminalVm.lastLogLevel)
            font.pixelSize: Theme.fontSizeBody
            font.family: "Consolas"
            elide: Text.ElideRight
        }

        IdeFlatButton {
            text: "展开终端"
            onClicked: terminalVm.setLogDockOpen(true)
        }
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        onClicked: terminalVm.setLogDockOpen(true)
    }
}

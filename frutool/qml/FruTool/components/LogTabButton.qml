import QtQuick
import FruTool 1.0

Item {
    id: root
    property string label: ""
    property string tabKey: ""
    property int unreadCount: 0
    property bool checked: false

    signal clicked()

    implicitWidth: tabBtn.implicitWidth + (badge.visible ? badge.width - 4 : 0)
    implicitHeight: Math.max(tabBtn.implicitHeight, badge.visible ? badge.height : 0)

    IdeFlatButton {
        id: tabBtn
        text: root.label
        checkable: true
        checked: root.checked
        onClicked: root.clicked()
    }

    Rectangle {
        id: badge
        visible: root.unreadCount > 0
        anchors.right: tabBtn.right
        anchors.top: tabBtn.top
        anchors.rightMargin: -2
        anchors.topMargin: -2
        width: Math.max(14, badgeLabel.implicitWidth + 6)
        height: 14
        radius: 7
        color: Theme.error
        z: 2

        Text {
            id: badgeLabel
            anchors.centerIn: parent
            text: root.unreadCount > 99 ? "99+" : String(root.unreadCount)
            color: Theme.bg
            font.pixelSize: Theme.fontSizeSmall
            font.bold: true
        }
    }
}

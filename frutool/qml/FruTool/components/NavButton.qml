import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "."

ToolButton {
    id: navBtn
    property string pageKey: ""
    property string tip: ""
    property bool pulse: false
    property bool online: false

    Layout.alignment: Qt.AlignHCenter
    Layout.preferredWidth: 44
    Layout.preferredHeight: 44
    text: ""
    checkable: true
    checked: chromeVm.currentPage === pageKey

    ToolTip.delay: 600
    ToolTip.text: tip

    scale: navBtn.hovered ? 1.05 : 1.0
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }

    contentItem: NavIcon {
        anchors.centerIn: parent
        icon: navBtn.pageKey
        active: navBtn.checked
        hovered: navBtn.hovered
        pulse: navBtn.pulse
        online: navBtn.online
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            radius: 4
            color: navBtn.checked ? Theme.accent_dim : (navBtn.hovered ? Theme.surface3 : "transparent")
            opacity: navBtn.checked ? 0.85 : 1.0
        }

        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 2
            anchors.verticalCenter: parent.verticalCenter
            width: 2
            height: navBtn.checked ? parent.height * 0.52 : 0
            radius: 1
            color: Theme.accent
            visible: navBtn.checked
            Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

            Rectangle {
                anchors.centerIn: parent
                width: 5
                height: parent.height + 6
                radius: 2.5
                color: Theme.accent
                opacity: 0.28
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: navBtn.hovered ? parent.width * 0.55 : 0
            height: 2
            radius: 1
            color: Theme.accent
            opacity: navBtn.hovered ? 0.75 : 0
            Behavior on width { NumberAnimation { duration: 150 } }
            Behavior on opacity { NumberAnimation { duration: 150 } }
        }
    }

    onClicked: chromeVm.showPage(pageKey)
}

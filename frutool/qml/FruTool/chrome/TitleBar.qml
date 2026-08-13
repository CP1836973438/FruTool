import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "../components"

Item {
    id: root
    height: 38

    Rectangle {
        anchors.fill: parent
        color: Theme.chrome_bg
        border.color: Theme.chrome_border
        border.width: 0
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        spacing: 8
        z: Theme.zContent

        Text {
            text: chromeVm.appProductName
            color: Theme.text
            font.pixelSize: Theme.fontSizeSubtitle
        }

        Item { Layout.fillWidth: true }

        WindowCtrlButton {
            kind: "min"
            Layout.alignment: Qt.AlignVCenter
            onClicked: root.Window.window.showMinimized()
        }
        WindowCtrlButton {
            kind: "max"
            Layout.alignment: Qt.AlignVCenter
            maximized: root.Window.window.visibility === Window.Maximized
            onClicked: {
                if (root.Window.window.visibility === Window.Maximized)
                    root.Window.window.showNormal()
                else
                    root.Window.window.showMaximized()
            }
        }
        WindowCtrlButton {
            kind: "close"
            Layout.alignment: Qt.AlignVCenter
            onClicked: root.Window.window.close()
        }
    }

    MouseArea {
        anchors.fill: parent
        z: Theme.zBackground
        propagateComposedEvents: true
        onPressed: function(mouse) {
            if (mouse.button === Qt.LeftButton) {
                root.Window.window.startSystemMove()
                mouse.accepted = false
            }
        }
        onDoubleClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton) {
                if (root.Window.window.visibility === Window.Maximized)
                    root.Window.window.showNormal()
                else
                    root.Window.window.showMaximized()
            }
        }
    }
}

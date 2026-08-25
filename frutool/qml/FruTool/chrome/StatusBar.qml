import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Item {
    id: root
    implicitHeight: 26
    clip: false

    Rectangle {
        anchors.fill: parent
        color: Theme.chrome_status
        border.color: Theme.chrome_border
        border.width: 1
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing_md
        anchors.rightMargin: Theme.spacing_md
        spacing: Theme.spacing_md

        RowLayout {
            spacing: 6
            Layout.alignment: Qt.AlignVCenter

            PulseDot {
                size: 11
                dotColor: connVm.localOnline ? Theme.success : Theme.text3
                active: connVm.localOnline
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                text: "本机 " + (connVm.localOnline ? connVm.localIp : "—")
                color: Theme.text2
                font.pixelSize: Theme.fontSizeCaption
                Layout.alignment: Qt.AlignVCenter
            }
        }

        RowLayout {
            spacing: 6
            Layout.alignment: Qt.AlignVCenter

            PulseDot {
                size: 11
                dotColor: connVm.bmcOnline ? Theme.success : Theme.text3
                active: connVm.bmcOnline
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                id: bmcText
                text: "BMC " + (connVm.bmcOnline ? connVm.bmcIp : "—")
                color: connVm.bmcOnline ? Theme.accent : Theme.text2
                font.pixelSize: Theme.fontSizeCaption
                Layout.alignment: Qt.AlignVCenter

                property real clickScale: 1.0
                scale: clickScale

                MouseArea {
                    anchors.fill: parent
                    cursorShape: connVm.bmcOnline ? Qt.PointingHandCursor : Qt.ArrowCursor
                    enabled: connVm.bmcOnline
                    onClicked: {
                        connVm.openBmcWeb()
                        clickFeedback.restart()
                    }
                }

                SequentialAnimation {
                    id: clickFeedback
                    NumberAnimation {
                        target: bmcText
                        property: "clickScale"
                        to: 0.88
                        duration: 80
                        easing.type: Easing.OutQuad
                    }
                    NumberAnimation {
                        target: bmcText
                        property: "clickScale"
                        to: 1.0
                        duration: 260
                        easing.type: Easing.OutBack
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }

        Text {
            id: versionText
            text: chromeVm.versionLabel
            color: Theme.accent
            font.pixelSize: Theme.fontSizeCaption
            Layout.alignment: Qt.AlignVCenter

            MouseArea {
                id: versionMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: chromeVm.showAbout()
            }

            ToolTip {
                visible: versionMouseArea.containsMouse
                text: "MAC: " + (connVm.macAddress || "—") + "\n点击查看关于 / 联系邮箱"
                delay: 400
            }
        }
    }
}

import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Item {
    id: root

    property Item blurSource: null

    readonly property bool connected: connVm.localOnline && connVm.bmcOnline
    readonly property bool partial: connVm.localOnline || connVm.bmcOnline

    implicitHeight: 88

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: 8
        border.width: 1
        border.color: root.connected ? Theme.success : (root.partial ? Theme.warning : Theme.border)

        Behavior on border.color { ColorAnimation { duration: 300; easing.type: Easing.OutCubic } }

        color: "transparent"

        FrostedPanel {
            anchors.fill: parent
            blurSource: root.blurSource
            panelColor: Theme.glass_card
            panelOpacity: Theme.glass_card_opacity
            vibrancy: 0.48
            radius: panel.radius
            borderColor: "transparent"
            z: 0
        }

        FocusGlow {
            anchors.fill: parent
            anchors.margins: -1
            focused: root.connected
            pulse: root.connected
            borderColor: Theme.success
            glowColor: Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.45)
            glowStrength: Theme.glow_strength
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: Theme.spacing_md
            spacing: Theme.spacing_lg

            ColumnLayout {
                spacing: Theme.spacing_xs
                Layout.fillWidth: true

                Text {
                    text: "连接状态"
                    color: Theme.text
                    font.pixelSize: Theme.fontSizeSubtitle
                    font.weight: Font.DemiBold
                }

                Text {
                    text: root.connected
                          ? "本机与 BMC 均已就绪，可开始换板与 FRU 操作。"
                          : (root.partial
                             ? "部分链路在线，请检查网络与 BMC 分配。"
                             : "等待本机网卡与 BMC 连接…")
                    color: Theme.text2
                    font.pixelSize: Theme.fontSizeBody
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                IdeFlatButton {
                    visible: !root.connected
                    text: connVm.networkRefreshing ? "检测中…" : "重试检测"
                    enabled: !connVm.networkRefreshing
                    Layout.alignment: Qt.AlignRight
                    onClicked: connVm.refreshNetworks(true)
                }
            }

            RowLayout {
                spacing: Theme.spacing_lg

                ColumnLayout {
                    spacing: 4
                    PulseDot {
                        size: 12
                        dotColor: connVm.localOnline ? Theme.success : Theme.text3
                        active: connVm.localOnline
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: "本机"
                        color: Theme.text3
                        font.pixelSize: Theme.fontSizeCaption
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: connVm.localOnline ? connVm.localIp : "离线"
                        color: connVm.localOnline ? Theme.text : Theme.text3
                        font.pixelSize: Theme.fontSizeCaption
                        Layout.alignment: Qt.AlignHCenter
                    }
                }

                ColumnLayout {
                    spacing: 4
                    PulseDot {
                        size: 12
                        dotColor: connVm.bmcOnline ? Theme.success : Theme.text3
                        active: connVm.bmcOnline
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: "BMC"
                        color: Theme.text3
                        font.pixelSize: Theme.fontSizeCaption
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: connVm.bmcOnline ? connVm.bmcIp : "离线"
                        color: connVm.bmcOnline ? Theme.text : Theme.text3
                        font.pixelSize: Theme.fontSizeCaption
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }
}

import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    property Item blurSource: null

    ColumnLayout {
        id: connPageLayout
        width: Math.max(0, root.availableWidth - Theme.spacing_xl)
        x: Theme.spacing_md
        spacing: Theme.spacing_lg

        ConnectionStatusPanel {
            Layout.fillWidth: true
            blurSource: root.blurSource
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing_md

            Card {
                Layout.fillWidth: true
                Layout.preferredWidth: 0
                title: "旧板凭据"
                blurSource: root.blurSource
                FieldRow {
                    label: "旧板账号"
                    FocusTextField {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: connVm.oldBoardUser
                        onTextEdited: connVm.setConnField("old_user", text)
                    }
                }
                FieldRow {
                    label: "旧板密码"
                    FocusTextField {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: connVm.oldBoardPassword
                        echoMode: connVm.showPasswords ? TextInput.Normal : TextInput.Password
                        onTextEdited: connVm.setConnField("old_password", text)
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.preferredWidth: 0
                title: "新板凭据"
                blurSource: root.blurSource
                FieldRow {
                    label: "新板账号"
                    FocusTextField {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: connVm.newBoardUser
                        onTextEdited: connVm.setConnField("new_user", text)
                    }
                }
                FieldRow {
                    label: "新板密码"
                    FocusTextField {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: connVm.newBoardPassword
                        echoMode: connVm.showPasswords ? TextInput.Normal : TextInput.Password
                        onTextEdited: connVm.setConnField("new_password", text)
                    }
                }
            }
        }

        IdeCheckBox {
            text: "显示密码"
            checked: connVm.showPasswords
            onCheckedChanged: connVm.setShowPasswords(checked)
            ToolTip.delay: 600
            ToolTip.text: "切换密码字段的明文/掩码显示"
        }

        Card {
            Layout.fillWidth: true
            title: "网络"
            blurSource: root.blurSource
            ColumnLayout {
                spacing: Theme.spacing_sm
                Layout.fillWidth: true

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing_sm

                    Text {
                        text: "本机 IPv4"
                        color: Theme.text2
                        font.pixelSize: Theme.fontSizeBody
                        Layout.preferredWidth: 72
                        Layout.alignment: Qt.AlignVCenter
                    }

                    IdeComboBox {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 28
                        Layout.alignment: Qt.AlignVCenter
                        model: connVm.networkModelProp
                        textRole: "label"
                        currentIndex: connVm.selectedNetworkIndex
                        onActivated: connVm.setSelectedNetworkIndex(currentIndex)
                    }

                    IdeButton {
                        Layout.alignment: Qt.AlignVCenter
                        text: "刷新网卡"
                        enabled: !connVm.networkRefreshing
                        onClicked: connVm.refreshNetworks(false)
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: connVm.networkSummary || "BMC 将分配：—"
                    color: Theme.text3
                    font.pixelSize: Theme.fontSizeBody
                    wrapMode: Text.Wrap
                }

                Text {
                    Layout.fillWidth: true
                    visible: connVm.networkIpWarning !== ""
                    text: connVm.networkIpWarning
                    color: Theme.warning
                    font.pixelSize: Theme.fontSizeBody
                    wrapMode: Text.Wrap
                }
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.spacing_xl }
    }
}

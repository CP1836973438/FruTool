import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: fruPageLayout
    spacing: Theme.spacing_md
    property Item blurSource: null

    ScrollView {
        id: scroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: Math.max(0, scroll.availableWidth - Theme.spacing_xl)
            x: Theme.spacing_md
            spacing: Theme.spacing_lg

            Item {
                Layout.fillWidth: true
                implicitHeight: emptyHint.implicitHeight + Theme.spacing_xl * 2
                visible: fruVm.fruFieldModelProp.rowCount() === 0

                ColumnLayout {
                    id: emptyHint
                    anchors.centerIn: parent
                    spacing: Theme.spacing_sm

                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: "尚未读取 FRU 数据"
                        color: Theme.text
                        font.pixelSize: Theme.fontSizeSubtitle
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: "连接 BMC 后前往主页面读取 FRU，或手动填写字段。"
                        color: Theme.text2
                        font.pixelSize: Theme.fontSizeBody
                        wrapMode: Text.Wrap
                    }
                    IdeButton {
                        Layout.alignment: Qt.AlignHCenter
                        text: "尝试读取 FRU"
                        primary: true
                        enabled: connVm.bmcOnline
                        onClicked: swapVm.doStep1()
                    }
                }
            }

            Repeater {
                model: ["Chassis", "Board", "Product"]

                Card {
                    required property string modelData

                    Layout.fillWidth: true
                    title: modelData
                    blurSource: fruPageLayout.blurSource

                    ColumnLayout {
                        spacing: Theme.spacing_sm
                        Layout.fillWidth: true

                        Repeater {
                            model: fruVm.fruFieldModelProp

                            FieldRow {
                                required property int index
                                required property string name
                                required property string group
                                required property string value
                                required property string hint

                                Layout.fillWidth: true
                                visible: group === modelData
                                Layout.preferredHeight: visible ? implicitHeight : 0
                                label: name
                                FocusTextField {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    text: value
                                    placeholderText: hint
                                    onTextEdited: fruVm.fruFieldModelProp.setValueAt(index, text)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: Theme.spacing_xs
        Layout.rightMargin: Theme.spacing_xs
        spacing: Theme.spacing_sm
        Text {
            visible: !connVm.bmcOnline && fruVm.canFruWrite
            text: "BMC 离线，连接后才能刷写。"
            color: Theme.warning
            font.pixelSize: Theme.fontSizeBody
        }
        Item { Layout.fillWidth: true }
        IdeButton {
            text: "重置"
            onClicked: fruVm.doFruReset()
        }
        IdeButton {
            text: "刷写所有非空字段"
            primary: true
            enabled: fruVm.canFruWrite && connVm.bmcOnline
            onClicked: fruVm.doFruBatchWrite()
        }
    }
}

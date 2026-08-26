import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../effects"

ScrollView {
    id: root
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    property Item blurSource: null

    ColumnLayout {
        width: Math.max(0, root.availableWidth - Theme.spacing_xl)
        x: Theme.spacing_md
        spacing: Theme.spacing_lg

        WorkflowHeader {
            id: workflow
            Layout.fillWidth: true
        }

        PageTransition {
            Layout.fillWidth: true
            pageIndex: swapVm.swapMode === "auto" ? 1 : 0

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing_lg

                StepCard {
                    Layout.fillWidth: true
                    blurSource: root.blurSource
                    stepTitle: "步骤 1"
                    stepSubtitle: "导出旧板 FRU 备份"
                    done: swapVm.step1Done
                    active: !swapVm.step1Done && workflow.activeStepCard === 0
                    FieldRow {
                        label: "旧服务器 SN"
                        FocusTextField {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            placeholderText: "用于命名 .bin 备份文件"
                            text: swapVm.oldBoardSn
                            readOnly: swapVm.step1Done
                            onTextEdited: swapVm.setOldBoardSn(text)
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "连接旧主板后执行，将 FRU 导出到本地备份目录。"
                        color: Theme.text3
                        font.pixelSize: Theme.fontSizeBody
                        wrapMode: Text.Wrap
                    }
                    InfoRow {
                        label: "备份文件"
                        value: swapVm.lastExportBin
                    }
                    Text {
                        visible: !connVm.bmcOnline && swapVm.canStep1
                        Layout.fillWidth: true
                        text: "请先确保 BMC 已连接（见底栏状态）。"
                        color: Theme.warning
                        font.pixelSize: Theme.fontSizeBody
                        wrapMode: Text.Wrap
                    }
                    IdeButton {
                        text: "导出 FRU 备份"
                        primary: true
                        enabled: swapVm.canStep1 && connVm.bmcOnline
                        onClicked: swapVm.doStep1()
                    }
                }

                StepCard {
                    Layout.fillWidth: true
                    blurSource: root.blurSource
                    stepTitle: "步骤 2"
                    stepSubtitle: "克隆到新板并还原新板 SN/PN"
                    locked: swapVm.step2Locked
                    done: swapVm.step2Done
                    active: !swapVm.step2Done && workflow.activeStepCard === 1
                    Text {
                        Layout.fillWidth: true
                        text: "换上新主板后执行。写入旧板 FRU 后始终还原新板 Board Serial；若新旧主板 Board Part Number 不一致，再把新板 PN 写回去。"
                        color: Theme.text3
                        font.pixelSize: Theme.fontSizeBody
                        wrapMode: Text.Wrap
                    }
                    InfoRow {
                        label: "将使用备份"
                        value: swapVm.step1Done ? swapVm.lastExportBin : ""
                    }
                    InfoRow {
                        label: "新板 Board Serial"
                        value: swapVm.newBoardSerial
                    }
                    Text {
                        visible: !connVm.bmcOnline
                                 && (swapVm.canStep2 || swapVm.canRollback)
                        Layout.fillWidth: true
                        text: "请先确保 BMC 已连接（见底栏状态）。"
                        color: Theme.warning
                        font.pixelSize: Theme.fontSizeBody
                        wrapMode: Text.Wrap
                    }
                    IdeButton {
                        text: "克隆 FRU 并还原 SN"
                        primary: true
                        enabled: swapVm.canStep2 && connVm.bmcOnline
                        onClicked: swapVm.doStep2()
                    }
                    IdeFlatButton {
                        visible: swapVm.canRollback
                        text: "回滚新板原始 FRU"
                        enabled: swapVm.canRollback && connVm.bmcOnline
                        onClicked: swapVm.doRollback()
                    }
                }
            }

            AutoSwapPanel {
                Layout.fillWidth: true
                blurSource: root.blurSource
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.spacing_xl }
    }
}

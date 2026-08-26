import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Item {
    id: root

    readonly property string phase: swapVm.swapAutoPhase

    readonly property string phaseHint: {
        switch (root.phase) {
        case "idle":
            return "连接 BMC 后将自动读取 FRU 并开始流程。"
        case "sn_detect":
            return "正在读取旧板 FRU 信息…"
        case "sn_confirm":
            return "请在弹窗中核对 SN。"
        case "exporting":
            return "正在导出旧板 FRU 备份…"
        case "wait_swap":
            return "请更换主板；完成后 BMC 重新上线将继续流程。"
        case "wait_new":
            return swapVm.swapAutoStatus !== ""
                   ? swapVm.swapAutoStatus
                   : "等待新主板 BMC 上线…"
        case "cloning":
            return "正在克隆 FRU 并还原新板 SN/PN…"
        case "done":
            return "自动换板流程已完成。"
        default:
            return ""
        }
    }

    readonly property bool showStatusHero: {
        var activePhases = ["sn_detect", "exporting", "cloning", "wait_new"]
        return activePhases.indexOf(root.phase) >= 0 && swapVm.swapAutoStatus !== ""
    }

    property Item blurSource: null

    implicitHeight: panel.implicitHeight

    Rectangle {
        id: panel
        width: parent.width
        radius: 6
        border.width: 1
        border.color: root.phase === "done" ? Theme.success : Theme.border
        implicitHeight: body.implicitHeight + Theme.spacing_xl * 2

        color: "transparent"

        FrostedPanel {
            anchors.fill: parent
            blurSource: root.blurSource
            panelColor: Theme.glass_card
            panelOpacity: Theme.glass_card_opacity
            vibrancy: 0.45
            radius: panel.radius
            borderColor: "transparent"
            z: 0
        }

        FocusGlow {
            anchors.fill: parent
            anchors.margins: -1
            focused: root.phase !== "idle" && root.phase !== "done"
            glowStrength: Theme.glow_strength * 0.45
        }

        ColumnLayout {
            id: body
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.spacing_md
            spacing: Theme.spacing_md

            Text {
                text: "自动换板"
                color: Theme.text
                font.pixelSize: Theme.fontSizeSubtitle
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(heroText.implicitHeight, hintText.implicitHeight)

                Text {
                    id: heroText
                    width: parent.width
                    text: swapVm.swapAutoStatus
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                    opacity: root.showStatusHero ? 1.0 : 0.0
                    visible: opacity > 0.01

                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                }

                Text {
                    id: hintText
                    anchors.fill: parent
                    text: root.phaseHint
                    color: Theme.text2
                    font.pixelSize: Theme.fontSizeBody
                    wrapMode: Text.Wrap
                    opacity: (!root.showStatusHero || root.phase === "wait_swap" || root.phase === "sn_confirm") ? 1.0 : 0.0
                    visible: opacity > 0.01

                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                }
            }

            InfoRow {
                label: "备份文件"
                value: swapVm.lastExportBin
            }

            InfoRow {
                label: "新板 Board Serial"
                value: swapVm.newBoardSerial
            }

            IdeFlatButton {
                visible: swapVm.canRollback
                text: "回滚新板原始 FRU"
                enabled: swapVm.canRollback
                onClicked: swapVm.doRollback()
            }
        }
    }
}

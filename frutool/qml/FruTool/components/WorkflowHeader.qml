import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Item {
    id: root

    readonly property var manualLabels: [
        { en: "WAIT", cn: "等待" },
        { en: "EXPORT", cn: "导出" },
        { en: "CLONE", cn: "克隆" },
        { en: "DONE", cn: "完成" },
    ]
    readonly property var autoLabels: [
        { en: "STBY", cn: "待命" },
        { en: "READ", cn: "读 FRU" },
        { en: "CHECK", cn: "核对 SN" },
        { en: "EXPORT", cn: "导出" },
        { en: "SWAP", cn: "等换板" },
        { en: "NEW", cn: "等新板" },
        { en: "CLONE", cn: "克隆" },
        { en: "DONE", cn: "完成" },
    ]

    property bool isAuto: swapVm.swapMode === "auto"
    property int phaseIndex: swapVm.workflowPhaseIndex
    property real progress: swapVm.workflowProgress
    property string statusLabel: swapVm.workflowStatusLabel
    property bool flowActive: swapVm.workflowFlowActive
    property int activeStepCard: swapVm.workflowActiveStepCard

    implicitWidth: layout.implicitWidth
    implicitHeight: layout.implicitHeight

    ColumnLayout {
        id: layout
        width: parent.width
        spacing: Theme.spacing_sm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing_md

            Item {
                Layout.preferredWidth: Math.max(manualTitle.implicitWidth, autoTitle.implicitWidth)
                Layout.preferredHeight: Math.max(manualTitle.implicitHeight, autoTitle.implicitHeight)

                Text {
                    id: manualTitle
                    text: "手动换板流程"
                    color: Theme.text
                    font.pixelSize: Theme.fontSizeTitle
                    font.weight: Font.DemiBold
                    opacity: root.isAuto ? 0 : 1

                    Behavior on opacity {
                        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
                    }
                }

                Text {
                    id: autoTitle
                    text: "自动换板流程"
                    color: Theme.text
                    font.pixelSize: Theme.fontSizeTitle
                    font.weight: Font.DemiBold
                    opacity: root.isAuto ? 1 : 0

                    Behavior on opacity {
                        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            IdeFlatButton {
                text: "重置进度"
                enabled: swapVm.canSwapReset
                onClicked: swapVm.doSwapReset()
                ToolTip.delay: 600
                ToolTip.text: "将换板流程重置为初始状态"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing_sm

            Text {
                text: "换板模式"
                color: Theme.text3
                font.pixelSize: Theme.fontSizeCaption
            }

            ModeButton {
                label: "手动"
                checked: swapVm.swapMode === "manual"
                onClicked: swapVm.setSwapMode("manual")
            }
            ModeButton {
                label: "自动"
                checked: swapVm.swapMode === "auto"
                pulseWhenActive: true
                onClicked: swapVm.setSwapMode("auto")
            }
        }

        PageTransition {
            Layout.fillWidth: true
            pageIndex: root.isAuto ? 1 : 0

            WorkflowFlowScreen {
                Layout.fillWidth: true
                labels: root.manualLabels
                currentIndex: swapVm.workflowPhaseIndex
                flowActive: swapVm.workflowFlowActive
                statusLabel: swapVm.workflowStatusLabel
                statusLabelEn: swapVm.workflowStatusLabelEn
                progress: swapVm.workflowProgress
            }

            WorkflowFlowScreen {
                Layout.fillWidth: true
                labels: root.autoLabels
                currentIndex: swapVm.workflowPhaseIndex
                flowActive: swapVm.workflowFlowActive
                statusLabel: swapVm.workflowStatusLabel
                statusLabelEn: swapVm.workflowStatusLabelEn
                progress: swapVm.workflowProgress
            }
        }

        Text {
            visible: root.isAuto && swapVm.swapAutoStatus !== ""
                     && swapVm.swapAutoStatus !== root.statusLabel
            text: swapVm.swapAutoStatus
            color: Theme.text2
            font.pixelSize: Theme.fontSizeBody
            elide: Text.ElideRight
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            maximumLineCount: 2
        }
    }
}

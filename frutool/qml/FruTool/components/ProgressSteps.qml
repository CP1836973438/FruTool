import QtQuick
import FruTool 1.0

Item {
    id: root

    property bool isAuto: swapVm.swapMode === "auto"

    property int phaseIndex: swapVm.workflowPhaseIndex
    property real progress: swapVm.workflowProgress
    property string statusLabel: swapVm.workflowStatusLabel
    property bool flowActive: swapVm.workflowFlowActive

    implicitWidth: ring.implicitWidth
    implicitHeight: ring.implicitHeight

    SwapProgressRing {
        id: ring
        anchors.fill: parent
        progress: root.progress
        phaseIndex: root.phaseIndex
        phaseCount: swapVm.workflowPhaseCount
        active: root.flowActive || root.progress > 0
        statusLabel: root.statusLabel
    }
}

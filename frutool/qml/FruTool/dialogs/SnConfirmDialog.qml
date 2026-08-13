import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

BaseDialog {
    id: root
    defaultWidth: 480

    property string dialogId: ""
    property string productSerial: ""
    property string boardSerial: ""
    property string productName: ""
    property int countdown: 60

    property bool countdownPaused: false
    property bool _responded: false

    dialogTitle: "核对服务器 SN"
    dialogSubtitle: "请核对以下 FRU 信息是否正确，确认后将自动导出 FRU 备份。"

    function _respond(accepted) {
        if (root._responded)
            return
        root._responded = true
        timer.stop()
        dialogVm.snConfirmResponse(root.dialogId, accepted)
        root.close()
    }

    Timer {
        id: timer
        interval: 1000
        repeat: true
        onTriggered: {
            if (root.countdownPaused)
                return
            if (root.countdown <= 0)
                return
            root.countdown -= 1
            if (root.countdown <= 0)
                root._respond(true)
        }
    }

    onOpened: {
        root._responded = false
        root.countdownPaused = false
        if (productSerial && countdown > 0)
            timer.start()
    }

    onClosed: {
        timer.stop()
        if (!root._responded && root.dialogId !== "")
            dialogVm.snConfirmResponse(root.dialogId, false)
    }

    body: ColumnLayout {
        width: parent ? parent.width : implicitWidth
        spacing: 10

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 12
            rowSpacing: 6
            Text { text: "Product Serial（服务器 SN）"; color: Theme.text3 }
            Text { text: productSerial || "—"; color: Theme.text; font.weight: Font.Bold }
            Text { text: "Board Serial"; color: Theme.text3 }
            Text { text: boardSerial || "—"; color: Theme.text }
            Text { text: "Product Name"; color: Theme.text3 }
            Text { text: productName || "—"; color: Theme.text }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: productSerial && countdown > 0
            spacing: 8

            Text {
                text: root.countdownPaused ? "倒计时已暂停" : (countdown + "s 后自动继续导出")
                color: root.countdownPaused ? Theme.warning : Theme.text3
                font.pixelSize: Theme.fontSizeBody
                Layout.alignment: Qt.AlignVCenter
            }

            IdeFlatButton {
                text: root.countdownPaused ? "继续" : "暂停"
                onClicked: root.countdownPaused = !root.countdownPaused
            }
        }

        Text {
            Layout.fillWidth: true
            visible: !productSerial
            text: "Product Serial 为空，无法自动继续，请取消或手动填写 SN 后重试。"
            wrapMode: Text.Wrap
            color: Theme.warning
            font.pixelSize: Theme.fontSizeBody
        }
    }

    footer: RowLayout {
        spacing: 8
        width: parent ? parent.width : implicitWidth
        Item { Layout.fillWidth: true }
        IdeButton {
            text: "取消自动流程"
            onClicked: root._respond(false)
        }
        IdeButton {
            text: "确认并导出"
            primary: true
            enabled: productSerial !== ""
            onClicked: root._respond(true)
        }
    }
}

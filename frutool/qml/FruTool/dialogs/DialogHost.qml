import QtQuick
import QtQuick.Controls

Item {
    id: host
    required property Item windowOverlay
    property Item blurSource: null

    function _parsePayload(jsonText) {
        if (jsonText === undefined || jsonText === null || jsonText === "")
            return {}
        try {
            return JSON.parse(jsonText)
        } catch (e) {
            console.warn("DialogHost: invalid payload", jsonText)
            return {}
        }
    }

    function _get(payload, key, fallback) {
        if (payload === undefined || payload === null)
            return fallback
        var v = payload[key]
        if (v === undefined || v === null)
            return fallback
        return v
    }

    function _openMessage(dlg, payload, defaultTitle, buttonMode) {
        dlg.dialogId = _get(payload, "id", "")
        dlg.dialogTitle = _get(payload, "title", defaultTitle)
        dlg.dialogMessage = _get(payload, "message", "")
        dlg.buttonMode = buttonMode
        dlg.open()
    }

    AboutDialog {
        id: aboutDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
    }

    MessageDialog {
        id: infoDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
        buttonMode: "ok"
        onAccepted: dialogVm.dialogResponse(dialogId, true)
    }

    MessageDialog {
        id: warnDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
        buttonMode: "ok"
        onAccepted: dialogVm.dialogResponse(dialogId, true)
    }

    MessageDialog {
        id: critDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
        buttonMode: "ok"
        errorGlow: true
        onAccepted: dialogVm.dialogResponse(dialogId, true)
    }

    MessageDialog {
        id: questionDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
        buttonMode: "yesno"
        onAccepted: dialogVm.dialogResponse(dialogId, true)
        onRejected: dialogVm.dialogResponse(dialogId, false)
    }

    SnConfirmDialog {
        id: snDlg
        parent: host.windowOverlay
        blurSource: host.blurSource
    }

    Connections {
        target: dialogVm
        function onAboutRequested() {
            aboutDlg.open()
        }
        function onDialogRequested(jsonText) {
            var payload = host._parsePayload(jsonText)
            const t = host._get(payload, "type", "info")
            if (t === "about") {
                aboutDlg.open()
                return
            }
            if (t === "sn_confirm") {
                snDlg.dialogId = host._get(payload, "id", "")
                snDlg.productSerial = host._get(payload, "productSerial", "")
                snDlg.boardSerial = host._get(payload, "boardSerial", "")
                snDlg.productName = host._get(payload, "productName", "")
                snDlg.countdown = host._get(payload, "countdown", 60)
                snDlg.open()
                return
            }
            if (t === "question") {
                questionDlg.defaultNo = host._get(payload, "defaultNo", false) === true
                host._openMessage(questionDlg, payload, "确认", "yesno")
                return
            }
            if (t === "critical") {
                host._openMessage(critDlg, payload, "错误", "ok")
                return
            }
            if (t === "warning") {
                host._openMessage(warnDlg, payload, "警告", "ok")
                return
            }
            host._openMessage(infoDlg, payload, "提示", "ok")
        }
    }
}

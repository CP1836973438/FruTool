import QtQuick
import FruTool 1.0

Text {
    id: root

    property string fullText: ""
    property int charDelay: 26
    property bool animate: true
    property bool showCursor: true

    text: root._shown + (root.showCursor && root._typing ? "_" : "")
    elide: Text.ElideRight

    property string _shown: ""
    property bool _typing: false
    property int _charIdx: 0

    onFullTextChanged: {
        if (root.animate && root._shown.length > 0
                && root.fullText.indexOf(root._shown) === 0
                && root.fullText.length > root._shown.length) {
            root._charIdx = root._shown.length
            root._typing = true
            typeTimer.start()
            return
        }
        restart()
    }

    function restart() {
        typeTimer.stop()
        root._charIdx = 0
        if (!root.animate || root.fullText.length === 0) {
            root._shown = root.fullText
            root._typing = false
            return
        }
        root._shown = ""
        root._typing = true
        typeTimer.start()
    }

    Timer {
        id: typeTimer
        interval: root.charDelay
        repeat: true
        onTriggered: {
            if (root._charIdx < root.fullText.length) {
                root._charIdx += 1
                root._shown = root.fullText.substring(0, root._charIdx)
            } else {
                stop()
                root._typing = false
            }
        }
    }

    Component.onCompleted: restart()
}

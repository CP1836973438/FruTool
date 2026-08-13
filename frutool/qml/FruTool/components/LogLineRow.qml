import QtQuick
import FruTool 1.0

Item {
    id: root
    width: ListView.view ? ListView.view.width : parent.width
    implicitHeight: lineText.implicitHeight + 4
    height: implicitHeight

    required property string formatted
    required property string text
    required property string timestamp
    required property string color
    required property string level

    function levelEnterDuration() {
        if (level === "error" || level === "warning")
            return 120
        if (level === "cmd" || level === "success")
            return 100
        return 80
    }

    Item {
        id: content
        width: parent.width
        height: lineText.implicitHeight
        y: 2
        opacity: 0

        Text {
            id: lineText
            width: parent.width
            text: root.formatted !== "" ? root.formatted
                  : (root.timestamp !== "" ? ("[" + root.timestamp + "] " + root.text) : root.text)
            color: (root.color !== undefined && root.color !== null && root.color !== "")
                   ? root.color : Theme.log_info
            font.pixelSize: Theme.fontSizeBody
            font.family: "Consolas"
            wrapMode: Text.Wrap
        }
    }

    ParallelAnimation {
        id: enterAnim
        NumberAnimation {
            target: content
            property: "opacity"
            from: 0
            to: 1
            duration: root.levelEnterDuration()
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: content
            property: "y"
            from: content.y + 6
            to: 2
            duration: root.levelEnterDuration()
            easing.type: Easing.OutCubic
        }
    }

    Component.onCompleted: enterAnim.start()
}

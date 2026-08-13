import QtQuick
import FruTool 1.0
import QtQuick.Layouts

Row {
    id: root

    property var labels: []
    property int currentIndex: 0
    property bool flowActive: false

    spacing: Theme.spacing_xs

    Repeater {
        model: root.labels

        Rectangle {
            required property int index
            required property var modelData

            height: 24
            width: chipText.implicitWidth + Theme.spacing_md
            radius: 12
            color: index === root.currentIndex
                   ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.22)
                   : Qt.rgba(Theme.surface3.r, Theme.surface3.g, Theme.surface3.b, 0.65)
            border.color: index === root.currentIndex ? Theme.accent : Theme.border
            border.width: 1
            opacity: index < root.currentIndex ? 0.75 : 1.0

            Text {
                id: chipText
                anchors.centerIn: parent
                text: modelData
                color: index === root.currentIndex ? Theme.text : Theme.text2
                font.pixelSize: 11
                font.weight: index === root.currentIndex ? Font.DemiBold : Font.Normal
            }

            Rectangle {
                anchors.fill: parent
                radius: 12
                visible: index === root.currentIndex && root.flowActive
                color: "transparent"
                border.color: Theme.accent
                border.width: 1
                opacity: 0.15

                SequentialAnimation on opacity {
                    id: pulse
                    running: index === root.currentIndex && root.flowActive
                    loops: Animation.Infinite
                    NumberAnimation { from: 0.15; to: 0.85; duration: 1100; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.85; to: 0.15; duration: 1100; easing.type: Easing.InOutSine }
                }
            }
        }
    }
}

import QtQuick
import FruTool 1.0
import QtQuick.Controls

CheckBox {
    id: root
    implicitHeight: 22
    spacing: 6
    font.pixelSize: Theme.fontSizeBody

    indicator: Rectangle {
        implicitWidth: 14
        implicitHeight: 14
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: 2
        color: root.checked ? Theme.accent : Theme.input_bg
        border.color: root.checked ? Theme.accent : Theme.border
        border.width: 1

        Behavior on color { ColorAnimation { duration: 180 } }
        Behavior on border.color { ColorAnimation { duration: 180 } }

        Canvas {
            anchors.centerIn: parent
            width: 8
            height: 6
            scale: root.checked ? 1.0 : 0.0

            Behavior on scale {
                NumberAnimation {
                    duration: 140
                    easing.type: root.checked ? Easing.OutBack : Easing.InQuad
                }
            }

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = "#FFFFFF"
                ctx.lineWidth = 1.4
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.beginPath()
                ctx.moveTo(0, 3)
                ctx.lineTo(2.5, 5.5)
                ctx.lineTo(8, 0)
                ctx.stroke()
            }
        }
    }

    contentItem: Text {
        leftPadding: root.indicator.width + root.spacing
        text: root.text
        font: root.font
        color: Theme.text2
        verticalAlignment: Text.AlignVCenter
    }
}

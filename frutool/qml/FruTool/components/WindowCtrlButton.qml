import QtQuick
import FruTool 1.0

Item {
    id: root
    property string kind: "min"
    property bool maximized: false
    signal clicked()

    width: 46
    height: 38

    property bool _hovered: hoverArea.containsMouse

    Rectangle {
        anchors.fill: parent
        color: root.kind === "close" && root._hovered
            ? Theme.window_btn_close_hover
            : (root._hovered ? Theme.window_btn_hover : "transparent")
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = Theme.window_btn_icon
            ctx.lineWidth = 1.2
            ctx.lineCap = "square"
            var cx = width / 2
            var cy = height / 2
            if (root.kind === "min") {
                ctx.beginPath()
                ctx.moveTo(cx - 5, cy)
                ctx.lineTo(cx + 5, cy)
                ctx.stroke()
            } else if (root.kind === "max") {
                if (root.maximized) {
                    ctx.strokeRect(cx - 3, cy - 3, 8, 8)
                    ctx.beginPath()
                    ctx.moveTo(cx - 1, cy - 5)
                    ctx.lineTo(cx + 7, cy - 5)
                    ctx.moveTo(cx - 1, cy - 5)
                    ctx.lineTo(cx - 1, cy - 1)
                    ctx.moveTo(cx + 7, cy - 5)
                    ctx.lineTo(cx + 7, cy + 3)
                    ctx.stroke()
                } else {
                    ctx.strokeRect(cx - 5, cy - 5, 10, 10)
                }
            } else {
                ctx.beginPath()
                ctx.moveTo(cx - 5, cy - 5)
                ctx.lineTo(cx + 5, cy + 5)
                ctx.moveTo(cx - 5, cy + 5)
                ctx.lineTo(cx + 5, cy - 5)
                ctx.stroke()
            }
        }
    }

    Connections {
        target: Theme
        function onThemeKeyChanged() { canvas.requestPaint() }
    }

    onMaximizedChanged: canvas.requestPaint()
    onKindChanged: canvas.requestPaint()

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.clicked()
    }
}

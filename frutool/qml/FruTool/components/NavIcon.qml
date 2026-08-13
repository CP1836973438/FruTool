import QtQuick
import FruTool 1.0

Item {
    id: root

    /** main | fru | topo | conn | theme */
    property string icon: "main"
    property bool active: false
    property bool hovered: false
    /** 自动换板等进行中时呼吸发光 */
    property bool pulse: false
    /** 连接页：BMC/本机在线时弧线高亮 */
    property bool online: false

    implicitWidth: 24
    implicitHeight: 24

    readonly property color strokeColor: {
        if (root.active)
            return Theme.accent
        if (root.hovered)
            return Theme.text
        return Theme.text3
    }

    readonly property real glowAlpha: {
        var base = root.active ? 0.72 : (root.hovered ? 0.42 : 0.0)
        if (root.pulse && base < 0.38)
            base = 0.38
        return base * root.glowBoost * Theme.glow_strength
    }

    property real glowBoost: 1.0

    SequentialAnimation {
        running: root.pulse
        loops: Animation.Infinite
        NumberAnimation { target: root; property: "glowBoost"; from: 0.5; to: 1.2; duration: 1100; easing.type: Easing.InOutSine }
        NumberAnimation { target: root; property: "glowBoost"; from: 1.2; to: 0.5; duration: 1100; easing.type: Easing.InOutSine }
    }

    onIconChanged: _repaint()
    onActiveChanged: {
        if (!root.pulse)
            root.glowBoost = 1.0
        _repaint()
    }
    onHoveredChanged: _repaint()
    onOnlineChanged: _repaint()
    onPulseChanged: {
        if (!root.pulse)
            root.glowBoost = 1.0
    }

    Canvas {
        id: glowCanvas
        anchors.centerIn: parent
        width: 28
        height: 28
        opacity: root.glowAlpha
        onPaint: root._paintIcon(getContext("2d"), width, height, true)
    }

    Canvas {
        id: iconCanvas
        anchors.centerIn: parent
        width: 24
        height: 24
        onPaint: root._paintIcon(getContext("2d"), width, height, false)
    }

    function _repaint() {
        glowCanvas.requestPaint()
        iconCanvas.requestPaint()
    }

    onStrokeColorChanged: _repaint()
    onGlowAlphaChanged: glowCanvas.requestPaint()

    Connections {
        target: Theme
        function onThemeKeyChanged() { root._repaint() }
    }

    function _paintIcon(ctx, w, h, glow) {
        ctx.reset()
        var cx = w / 2
        var cy = h / 2
        var col = root.strokeColor
        ctx.strokeStyle = col
        ctx.fillStyle = col
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.lineWidth = glow ? 3.2 : (root.active ? 1.55 : 1.25)

        switch (root.icon) {
        case "main":
            _paintSwap(ctx, cx, cy, glow)
            break
        case "fru":
            _paintFru(ctx, cx, cy, glow)
            break
        case "topo":
            _paintTopo(ctx, cx, cy, glow)
            break
        case "conn":
            _paintConn(ctx, cx, cy, glow)
            break
        case "theme":
            _paintTheme(ctx, cx, cy, glow)
            break
        }
    }

    function _paintSwap(ctx, cx, cy, glow) {
        var w = 5.5
        var h = 8.5
        ctx.strokeRect(cx - 9, cy - h / 2, w, h)
        ctx.strokeRect(cx + 3.5, cy - h / 2, w, h)
        if (!glow) {
            ctx.beginPath()
            ctx.moveTo(cx - 2.8, cy)
            ctx.lineTo(cx + 2.8, cy)
            ctx.moveTo(cx + 0.2, cy - 2.2)
            ctx.lineTo(cx + 2.8, cy)
            ctx.lineTo(cx + 0.2, cy + 2.2)
            ctx.stroke()
        }
    }

    function _paintFru(ctx, cx, cy, glow) {
        var rw = 11
        var rh = 8
        ctx.strokeRect(cx - rw / 2, cy - rh / 2, rw, rh)
        if (glow)
            return
        ctx.lineWidth = 1.0
        for (var i = -1; i <= 1; i++) {
            ctx.beginPath()
            ctx.moveTo(cx - rw / 2 - 2.5, cy + i * 2.8)
            ctx.lineTo(cx - rw / 2, cy + i * 2.8)
            ctx.moveTo(cx + rw / 2, cy + i * 2.8)
            ctx.lineTo(cx + rw / 2 + 2.5, cy + i * 2.8)
            ctx.stroke()
        }
        ctx.fillRect(cx - 1.2, cy - 1.2, 2.4, 2.4)
    }

    function _paintTopo(ctx, cx, cy, glow) {
        ctx.beginPath()
        ctx.moveTo(cx, cy - 5)
        ctx.lineTo(cx - 5, cy + 4)
        ctx.lineTo(cx + 5, cy + 4)
        ctx.closePath()
        ctx.stroke()
        if (glow)
            return
        ctx.beginPath()
        ctx.arc(cx, cy - 1.5, 1.3, 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(cx - 4, cy + 3, 1.1, 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(cx + 4, cy + 3, 1.1, 0, Math.PI * 2)
        ctx.fill()
    }

    function _paintConn(ctx, cx, cy, glow) {
        ctx.beginPath()
        ctx.arc(cx, cy, 4.2, 0, Math.PI * 2)
        ctx.stroke()
        if (glow)
            return
        var arcColor = root.online ? Theme.success : root.strokeColor
        ctx.strokeStyle = arcColor
        ctx.beginPath()
        ctx.arc(cx, cy, 6.5, -Math.PI * 0.55, Math.PI * 0.15)
        ctx.stroke()
        ctx.strokeStyle = root.strokeColor
        ctx.beginPath()
        ctx.moveTo(cx, cy - 7)
        ctx.lineTo(cx, cy - 4.5)
        ctx.moveTo(cx - 1.8, cy - 6.2)
        ctx.lineTo(cx, cy - 7)
        ctx.lineTo(cx + 1.8, cy - 6.2)
        ctx.stroke()
    }

    function _paintTheme(ctx, cx, cy, glow) {
        ctx.beginPath()
        ctx.arc(cx, cy, glow ? 4.5 : 3.2, 0, Math.PI * 2)
        if (glow)
            ctx.stroke()
        else
            ctx.fill()
        if (glow)
            return
        ctx.lineWidth = 1.15
        for (var a = 0; a < 8; a++) {
            var ang = a * Math.PI / 4
            var x1 = cx + Math.cos(ang) * 5.2
            var y1 = cy + Math.sin(ang) * 5.2
            var x2 = cx + Math.cos(ang) * 7.0
            var y2 = cy + Math.sin(ang) * 7.0
            ctx.beginPath()
            ctx.moveTo(x1, y1)
            ctx.lineTo(x2, y2)
            ctx.stroke()
        }
    }
}

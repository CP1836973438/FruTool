import QtQuick
import QtQuick.Window
import FruTool 1.0

Item {
    id: root

    property Item blurSource: null
    property bool liveCapture: true
    property real panelOpacity: 0.32
    property color panelColor: Theme.chrome_bg
    property color borderColor: Theme.border
    property real radius: 8

    property real vibrancy: 0.55
    property real edgeLight: 0.42

    readonly property bool effectsEnabled: Theme.shaderEffectsEnabled
            && typeof GraphicsInfo !== "undefined"
            && GraphicsInfo.api !== GraphicsInfo.Software
            && root.blurSource !== null

    readonly property bool windowIsMaximized: Window.window !== null
            && (Window.window.visibility === Window.Maximized
                || Window.window.visibility === Window.FullScreen)

    // 模糊贴图尺寸与背景不一致时走渐变降级
    readonly property bool captureLooksStale: {
        if (!root.blurSource || !root.blurSource.sourceItem)
            return false
        var bg = root.blurSource.sourceItem
        if (bg.width <= 0 || bg.height <= 0)
            return false
        var texW = root.blurSource.width
        var texH = root.blurSource.height
        if (texW <= 0 || texH <= 0)
            return true
        var dpr = Screen.devicePixelRatio
        var wOk = Math.abs(texW - bg.width * dpr) <= 3 || Math.abs(texW - bg.width) <= 3
        var hOk = Math.abs(texH - bg.height * dpr) <= 3 || Math.abs(texH - bg.height) <= 3
        return !(wOk && hOk)
    }

    readonly property bool splitGlassBlocked: root.captureLooksStale
            || (terminalVm.logDockOpen && root.windowIsMaximized)

    readonly property bool inActivePage: {
        var stack = null
        var p = root.parent
        while (p) {
            if (p.currentIndex !== undefined && p.children && p.children.length > 1)
                stack = p
            p = p.parent
        }
        if (!stack)
            return true
        for (var i = 0; i < stack.children.length; ++i) {
            var pageRoot = stack.children[i]
            var node = root
            while (node) {
                if (node === pageRoot)
                    return stack.currentIndex === i
                node = node.parent
            }
        }
        return true
    }

    readonly property Item scrollParent: {
        var p = root.parent
        while (p) {
            if (p.contentY !== undefined)
                return p
            p = p.parent
        }
        return null
    }

    readonly property bool useShaderGlass: Theme.useLiquidGlass
            && root.effectsEnabled
            && !Theme.layoutEffectsPaused
            && !root.splitGlassBlocked
            && root.inActivePage

    readonly property real captureScale: {
        if (!root.blurSource || !root.blurSource.sourceItem)
            return 1.0
        var sw = root.blurSource.sourceItem.width
        if (sw <= 0 || blurGrab.width <= 0)
            return 1.0
        return blurGrab.width / sw
    }

    readonly property point originInBlurSource: {
        if (!root.blurSource || !root.blurSource.sourceItem)
            return Qt.point(0, 0)
        var bg = root.blurSource.sourceItem
        var sp = root.scrollParent
        if (sp) {
            void(sp.contentY)
            void(sp.contentX)
        }
        var global = root.mapToGlobal(0, 0)
        return bg.mapFromGlobal(global.x, global.y)
    }

    implicitWidth: 0
    implicitHeight: 0

    default property alias content: contentHost.data

    ShaderEffectSource {
        id: blurGrab
        sourceItem: root.blurSource
        live: root.useShaderGlass && Theme.liveBlurEnabled && root.liveCapture
        hideSource: false
        visible: false
        enabled: root.useShaderGlass
        recursive: false

        Component.onCompleted: if (root.useShaderGlass) scheduleUpdate()
        onSourceItemChanged: if (root.useShaderGlass) scheduleUpdate()

        Connections {
            target: root
            function onWidthChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
            function onHeightChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
            function onXChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
            function onYChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
        }

        Connections {
            target: root.scrollParent
            function onContentYChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
            function onContentXChanged() {
                if (root.useShaderGlass)
                    blurGrab.scheduleUpdate()
            }
        }

        Connections {
            target: Theme
            function onLayoutEffectsPausedChanged() {
                if (!Theme.layoutEffectsPaused && root.effectsEnabled && Theme.useLiquidGlass)
                    blurGrab.scheduleUpdate()
            }
        }

        Connections {
            target: terminalVm
            function onLogDockOpenChanged() {
                if (root.effectsEnabled && Theme.useLiquidGlass)
                    blurGrab.scheduleUpdate()
            }
        }

        Connections {
            target: root
            function onCaptureLooksStaleChanged() {
                if (root.captureLooksStale && root.blurSource)
                    root.blurSource.scheduleUpdate()
            }
        }
    }

    // Liquid glass (独显静态抓屏)
    ShaderEffect {
        id: liquidFx
        anchors.fill: parent
        visible: root.useShaderGlass
        property variant source: blurGrab
        property real iBlurRadius: Theme.glass_blur * 0.55
        property color iTintColor: root.panelColor
        property vector2d iSourceSize: Qt.vector2d(
            Math.max(blurGrab.width, 1),
            Math.max(blurGrab.height, 1))
        property vector2d iPanelOrigin: Qt.vector2d(
            root.originInBlurSource.x * root.captureScale,
            root.originInBlurSource.y * root.captureScale)
        property vector2d iPanelSize: Qt.vector2d(
            Math.max(root.width, 1) * root.captureScale,
            Math.max(root.height, 1) * root.captureScale)
        property real iVibrancy: root.vibrancy
        property real iEdgeLight: root.edgeLight
        opacity: Math.min(1.0, root.panelOpacity * 1.15)
        fragmentShader: Qt.resolvedUrl("../shaders/liquid_glass.frag.qsb")
    }

    // 安全毛玻璃降级（无着色器时层次更丰富）
    Item {
        anchors.fill: parent
        visible: !root.useShaderGlass

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.surface_top }
                GradientStop { position: 1.0; color: Theme.surface_bottom }
            }
            opacity: Math.min(1.0, root.panelOpacity * 1.25)
        }

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.14) }
                GradientStop { position: 0.4; color: Qt.rgba(1, 1, 1, 0.04) }
                GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.0) }
            }
            opacity: root.panelOpacity
        }

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            color: root.panelColor
            opacity: root.panelOpacity * 0.55
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: Qt.rgba(1, 1, 1, root.useShaderGlass ? 0.12 : 0.08)
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: root.borderColor
        border.width: root.borderColor === "transparent" ? 0 : 1
        opacity: 0.65
    }

    Item {
        id: contentHost
        anchors.fill: parent
        z: Theme.zContent
    }
}

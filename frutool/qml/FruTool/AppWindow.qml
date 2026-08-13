import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import FruTool 1.0
import "chrome"
import "pages"
import "components"
import "dialogs"
import "effects"

ApplicationWindow {
    id: window
    width: 800
    height: 600
    minimumWidth: 800
    minimumHeight: 560
    visible: true
    title: "FRU 自动化整合工具"
    color: Theme.bg
    // Frameless UI still needs Minimize/Maximize/SystemMenu hints so Windows
    // taskbar click can minimize/restore (WS_MINIMIZEBOX / WS_MAXIMIZEBOX).
    flags: Qt.Window
           | Qt.FramelessWindowHint
           | Qt.WindowMinimizeButtonHint
           | Qt.WindowMaximizeButtonHint
           | Qt.WindowSystemMenuHint
           | Qt.WindowCloseButtonHint

    property bool shuttingDown: false

    onClosing: function(close) {
        close.accepted = false
        if (window.shuttingDown)
            return
        if (chromeVm)
            chromeVm.requestShutdown()
    }

    Loader {
        id: uiLoader
        anchors.fill: parent
        active: !window.shuttingDown
        sourceComponent: uiRoot
    }

    Component {
        id: uiRoot
        Item {
            id: uiShell
            anchors.fill: parent

            property int resizeMargin: 8
            property int savedTerminalWidth: 260
            property int animatedTerminalWidth: 260
            property int dragPreviewTerminalWidth: savedTerminalWidth
            property bool terminalPaneDragging: false
            property bool terminalPaneAnimating: false
            property bool suppressLiveBlur: false
            property bool logPanelSettling: false
            property bool blurCaptureEnabled: true

            readonly property real captureDpr: {
                if (Window.window && Window.window.screen)
                    return Window.window.screen.devicePixelRatio
                return Screen.devicePixelRatio
            }

            function refreshBlurTexture() {
                if (!blurCaptureEnabled)
                    return
                contentBlurSource.scheduleUpdate()
                blurRefreshFollowUp.start()
            }

            function invalidateBlurCapture() {
                suppressLiveBlur = true
                logPanelSettling = true
                blurCaptureEnabled = false
                Qt.callLater(function() {
                    blurCaptureEnabled = true
                    contentBlurSource.scheduleUpdate()
                    Qt.callLater(function() {
                        contentBlurSource.scheduleUpdate()
                        layoutSettleTimer.restart()
                    })
                })
            }

            function finishLogLayoutSettle() {
                logPanelSettling = false
                suppressLiveBlur = false
                refreshBlurTexture()
            }

            readonly property bool layoutEffectsPaused: suppressLiveBlur
                    || terminalPaneAnimating
                    || logPanelSettling

            readonly property int maxTerminalPaneWidth: {
                var total = workSplit.width
                if (total <= 320)
                    return 200
                return Math.min(480, total - 320)
            }

            function clampTerminalWidth(width) {
                return Math.round(Math.max(200, Math.min(maxTerminalPaneWidth, width)))
            }

            function animateTerminalWidth(target) {
                var next = clampTerminalWidth(target)
                if (next === animatedTerminalWidth) {
                    savedTerminalWidth = next
                    terminalPaneAnimating = false
                    if (!logPanelSettling)
                        suppressLiveBlur = false
                    return
                }
                paneWidthAnimation.stop()
                paneWidthAnimation.from = animatedTerminalWidth
                paneWidthAnimation.to = next
                terminalPaneAnimating = true
                suppressLiveBlur = true
                paneWidthAnimation.start()
            }

            NumberAnimation {
                id: paneWidthAnimation
                target: uiShell
                property: "animatedTerminalWidth"
                duration: 220
                easing.type: Easing.OutCubic
                onStopped: {
                    uiShell.savedTerminalWidth = uiShell.animatedTerminalWidth
                    uiShell.terminalPaneAnimating = false
                    if (!uiShell.logPanelSettling)
                        uiShell.suppressLiveBlur = false
                    if (!Theme.layoutEffectsPaused)
                        contentBlurSource.scheduleUpdate()
                }
            }

            Timer {
                id: layoutSettleTimer
                interval: uiShell.windowIsMaximized ? 720 : 500
                repeat: false
                onTriggered: uiShell.finishLogLayoutSettle()
            }

            readonly property bool windowIsMaximized: Window.window !== null
                    && (Window.window.visibility === Window.Maximized
                        || Window.window.visibility === Window.FullScreen)

            Timer {
                id: blurRefreshFollowUp
                interval: 120
                repeat: false
                onTriggered: contentBlurSource.scheduleUpdate()
            }

            Connections {
                target: uiShell
                function onAnimatedTerminalWidthChanged() {
                    if (!Theme.layoutEffectsPaused)
                        contentBlurSource.scheduleUpdate()
                }
            }

            Binding {
                target: Theme
                property: "layoutEffectsPaused"
                value: uiShell.layoutEffectsPaused
            }

            ColumnLayout {
                id: windowChrome
                anchors.fill: parent
                spacing: 0

                TitleBar {
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    ActivityBar {
                        Layout.preferredWidth: 56
                        Layout.fillHeight: true
                    }

                    Item {
                        id: workSplitHost
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 12

                        SplitView {
                            id: workSplit
                            anchors.fill: parent
                            orientation: Qt.Horizontal
                            handle: Item {
                                implicitWidth: 0
                                implicitHeight: workSplit.height > 0 ? workSplit.height : 1
                            }

                            Item {
                                id: mainPane
                                SplitView.fillWidth: true
                                SplitView.minimumWidth: 320

                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 0

                                    Item {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true

                                        Rectangle {
                                            id: contentBg
                                            anchors.fill: parent
                                            z: Theme.zBackground
                                            gradient: Gradient {
                                                GradientStop { position: 0.0; color: Theme.bg }
                                                GradientStop {
                                                    position: 0.55
                                                    color: Qt.rgba(
                                                        Theme.accent_dim.r,
                                                        Theme.accent_dim.g,
                                                        Theme.accent_dim.b,
                                                        0.08)
                                                }
                                                GradientStop { position: 1.0; color: Theme.bg }
                                            }
                                        }

                                        ShaderEffectSource {
                                            id: contentBlurSource
                                            enabled: uiShell.blurCaptureEnabled
                                            sourceItem: contentBg
                                            textureSize: Qt.size(
                                                Math.max(1, Math.round(contentBg.width * uiShell.captureDpr)),
                                                Math.max(1, Math.round(contentBg.height * uiShell.captureDpr)))
                                            live: false
                                            recursive: false
                                            hideSource: false
                                            visible: false
                                            Component.onCompleted: scheduleUpdate()
                                            onSourceItemChanged: scheduleUpdate()

                                            Connections {
                                                target: contentBg
                                                function onWidthChanged() {
                                                    if (!Theme.layoutEffectsPaused)
                                                        contentBlurSource.scheduleUpdate()
                                                }
                                                function onHeightChanged() {
                                                    if (!Theme.layoutEffectsPaused)
                                                        contentBlurSource.scheduleUpdate()
                                                }
                                            }

                                            Connections {
                                                target: Theme
                                                function onLayoutEffectsPausedChanged() {
                                                    if (!Theme.layoutEffectsPaused)
                                                        contentBlurSource.scheduleUpdate()
                                                }
                                            }
                                        }

                                        PageTransition {
                                            anchors.fill: parent
                                            z: Theme.zContent
                                            emphasized: true
                                            pageIndex: {
                                                switch (chromeVm.currentPage) {
                                                case "main": return 0
                                                case "fru": return 1
                                                case "topo": return 2
                                                default: return 3
                                                }
                                            }
                                            MainPage { blurSource: contentBlurSource }
                                            FruPage { blurSource: contentBlurSource }
                                            TopoPage { blurSource: contentBlurSource }
                                            ConnPage { blurSource: contentBlurSource }
                                        }
                                    }

                                    LogCompactBar {
                                        Layout.fillWidth: true
                                        opacity: terminalVm.logDockOpen ? 0.0 : 1.0
                                        visible: opacity > 0.01
                                    }
                                }
                            }

                            Item {
                                id: terminalPane
                                visible: terminalVm.logDockOpen
                                SplitView.preferredWidth: terminalVm.logDockOpen ? uiShell.animatedTerminalWidth : 0
                                SplitView.minimumWidth: terminalVm.logDockOpen ? 200 : 0
                                SplitView.maximumWidth: terminalVm.logDockOpen ? uiShell.maxTerminalPaneWidth : 0

                                TerminalDock {
                                    anchors.fill: parent
                                    blurSource: contentBlurSource
                                }

                                MouseArea {
                                    id: terminalResizeRail
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: 10
                                    z: Theme.zRail
                                    hoverEnabled: true
                                    preventStealing: true
                                    cursorShape: Qt.SplitHCursor
                                    visible: terminalVm.logDockOpen

                                    readonly property bool railActive: containsMouse || pressed

                                    Rectangle {
                                        anchors.fill: parent
                                        color: Theme.border
                                        opacity: terminalResizeRail.railActive ? 0.35 : 0
                                    }

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 2
                                        height: parent.height
                                        radius: 1
                                        color: Theme.scrollbar_handle
                                        opacity: terminalResizeRail.railActive ? 1 : 0
                                    }

                                    property real _pressMouseX: 0
                                    property int _pressWidth: 0

                                    onPressed: {
                                        paneWidthAnimation.stop()
                                        uiShell.terminalPaneAnimating = false
                                        uiShell.suppressLiveBlur = true
                                        uiShell.terminalPaneDragging = true
                                        _pressMouseX = mouseX
                                        _pressWidth = terminalPane.width
                                        uiShell.animatedTerminalWidth = _pressWidth
                                        uiShell.savedTerminalWidth = _pressWidth
                                        uiShell.dragPreviewTerminalWidth = _pressWidth
                                    }

                                    onPositionChanged: {
                                        if (!pressed)
                                            return
                                        var delta = mouseX - _pressMouseX
                                        uiShell.dragPreviewTerminalWidth = uiShell.clampTerminalWidth(_pressWidth - delta)
                                    }

                                    onReleased: {
                                        uiShell.terminalPaneDragging = false
                                        uiShell.animateTerminalWidth(uiShell.dragPreviewTerminalWidth)
                                    }

                                    onCanceled: {
                                        uiShell.dragPreviewTerminalWidth = uiShell.savedTerminalWidth
                                        uiShell.terminalPaneDragging = false
                                        if (!uiShell.logPanelSettling)
                                            uiShell.suppressLiveBlur = false
                                    }
                                }
                            }
                        }

                        Rectangle {
                            visible: uiShell.terminalPaneDragging && terminalVm.logDockOpen
                            width: 2
                            height: parent.height
                            x: parent.width - uiShell.dragPreviewTerminalWidth - 1
                            color: Theme.scrollbar_handle
                            z: Theme.zDragIndicator
                        }
                    }
                }

                StatusBar { Layout.fillWidth: true }
            }

            Repeater {
                model: [
                    { edge: Qt.LeftEdge, x: 0, y: resizeMargin, w: resizeMargin, h: parent.height - 2 * resizeMargin, cursor: Qt.SizeHorCursor },
                    { edge: Qt.RightEdge, x: parent.width - resizeMargin, y: resizeMargin, w: resizeMargin, h: parent.height - 2 * resizeMargin, cursor: Qt.SizeHorCursor },
                    { edge: Qt.TopEdge, x: resizeMargin, y: 0, w: parent.width - 2 * resizeMargin, h: resizeMargin, cursor: Qt.SizeVerCursor },
                    { edge: Qt.BottomEdge, x: resizeMargin, y: parent.height - resizeMargin, w: parent.width - 2 * resizeMargin, h: resizeMargin, cursor: Qt.SizeVerCursor },
                    { edge: Qt.LeftEdge | Qt.TopEdge, x: 0, y: 0, w: resizeMargin, h: resizeMargin, cursor: Qt.SizeFDiagCursor },
                    { edge: Qt.RightEdge | Qt.TopEdge, x: parent.width - resizeMargin, y: 0, w: resizeMargin, h: resizeMargin, cursor: Qt.SizeBDiagCursor },
                    { edge: Qt.LeftEdge | Qt.BottomEdge, x: 0, y: parent.height - resizeMargin, w: resizeMargin, h: resizeMargin, cursor: Qt.SizeBDiagCursor },
                    { edge: Qt.RightEdge | Qt.BottomEdge, x: parent.width - resizeMargin, y: parent.height - resizeMargin, w: resizeMargin, h: resizeMargin, cursor: Qt.SizeFDiagCursor }
                ]
                delegate: MouseArea {
                    x: modelData.x
                    y: modelData.y
                    width: modelData.w
                    height: modelData.h
                    cursorShape: modelData.cursor
                    onPressed: function(mouse) {
                        if (mouse.button === Qt.LeftButton && window.visibility !== Window.Maximized)
                            window.startSystemResize(modelData.edge)
                    }
                }
            }

            DialogHost {
                windowOverlay: Overlay.overlay
                blurSource: windowChrome
            }

            Connections {
                target: chromeVm
                function onCurrentPageChanged() {
                    uiShell.refreshBlurTexture()
                }
            }

            Component.onCompleted: {
                chromeVm.showPage("conn")
                animatedTerminalWidth = savedTerminalWidth
            }

            Connections {
                target: terminalVm
                function onLogDockOpenChanged() {
                    uiShell.invalidateBlurCapture()
                    if (terminalVm.logDockOpen) {
                        uiShell.animatedTerminalWidth = 0
                        uiShell.animateTerminalWidth(uiShell.savedTerminalWidth)
                    } else {
                        paneWidthAnimation.stop()
                        uiShell.terminalPaneAnimating = false
                        uiShell.animatedTerminalWidth = 0
                    }
                }
            }

            Connections {
                target: Window.window
                function onVisibilityChanged() {
                    uiShell.invalidateBlurCapture()
                }
            }
        }
    }
}

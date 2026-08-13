import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../effects"

Rectangle {
    id: root
    color: "transparent"
    border.color: Theme.border
    border.width: 1

    property bool contentReady: terminalVm.logDockOpen
    property Item blurSource: null
    opacity: contentReady ? 1.0 : 0.0

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    FrostedPanel {
        anchors.fill: parent
        blurSource: root.blurSource
        panelColor: Theme.terminal_bg
        panelOpacity: 0.88
        vibrancy: 0.3
        radius: 0
        borderColor: "transparent"
        z: 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.topMargin: 6
            Layout.bottomMargin: 4

            RowLayout {
                anchors.fill: parent
                spacing: 8

                Text {
                    text: "终端日志"
                    color: Theme.text3
                    font.pixelSize: Theme.fontSizeBody
                }

                Item {
                    id: activityStrip
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 14
                    Layout.alignment: Qt.AlignVCenter
                    visible: terminalVm.logActivity
                    clip: true

                    Rectangle {
                        anchors.fill: parent
                        radius: 3
                        color: Theme.surface3
                        opacity: 0.85
                    }

                    property real scanY: -4

                    SequentialAnimation on scanY {
                        running: activityStrip.visible
                        loops: Animation.Infinite
                        NumberAnimation {
                            from: -4
                            to: activityStrip.height + 4
                            duration: 1400
                            easing.type: Easing.Linear
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        y: activityStrip.scanY
                        opacity: 0.55
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0; color: "transparent" }
                            GradientStop { position: 0.5; color: Theme.accent }
                            GradientStop { position: 1; color: "transparent" }
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                IdeFlatButton {
                    text: "收起"
                    onClicked: terminalVm.setLogDockOpen(false)
                    ToolTip.delay: 600
                    ToolTip.text: "收起终端日志面板"
                }
                IdeFlatButton {
                    text: "清空"
                    onClicked: terminalVm.clearLogs(terminalVm.activeLogTab)
                    ToolTip.delay: 600
                    ToolTip.text: "清空当前标签页的日志内容"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 4
            spacing: 4

            LogTabButton {
                label: "全部"
                tabKey: "all"
                unreadCount: terminalVm.unreadAll
                checked: terminalVm.activeLogTab === "all"
                onClicked: terminalVm.setActiveLogTab("all")
            }
            LogTabButton {
                label: "DHCP"
                tabKey: "dhcp"
                unreadCount: terminalVm.unreadDhcp
                checked: terminalVm.activeLogTab === "dhcp"
                onClicked: terminalVm.setActiveLogTab("dhcp")
            }
            LogTabButton {
                label: "FRU"
                tabKey: "fru"
                unreadCount: terminalVm.unreadFru
                checked: terminalVm.activeLogTab === "fru"
                onClicked: terminalVm.setActiveLogTab("fru")
            }
            LogTabButton {
                label: "拓扑"
                tabKey: "topo"
                unreadCount: terminalVm.unreadTopo
                checked: terminalVm.activeLogTab === "topo"
                onClicked: terminalVm.setActiveLogTab("topo")
            }
            Item { Layout.fillWidth: true }
        }

        ListView {
            id: logList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 80
            clip: true
            model: terminalVm.logModelProp
            spacing: 2

            delegate: LogLineRow {}

            onCountChanged: Qt.callLater(function() {
                if (count > 0)
                    logList.positionViewAtEnd()
            })
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: Theme.surface2
            border.color: Theme.border
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                IdeFlatButton {
                    id: modeToggle
                    Layout.preferredHeight: 28
                    text: terminalVm.cmdMode === "自由模式" ? "自由" : "IPMI"
                    font.pixelSize: Theme.fontSizeCaption
                    onClicked: terminalVm.setCmdMode(
                        terminalVm.cmdMode === "自由模式" ? "IPMI模式" : "自由模式")
                    ToolTip.delay: 600
                    ToolTip.text: terminalVm.cmdMode === "自由模式" ? "自由模式：直接执行 Shell 命令" : "IPMI 模式：通过 IPMI 协议与 BMC 通信"
                }

                IdeFlatButton {
                    id: credToggle
                    Layout.preferredHeight: 28
                    text: terminalVm.cmdCredUseNew ? "新" : "旧"
                    font.pixelSize: Theme.fontSizeCaption
                    visible: terminalVm.cmdMode !== "自由模式"
                    onClicked: terminalVm.setCmdCredUseNew(!terminalVm.cmdCredUseNew)
                    ToolTip.delay: 600
                    ToolTip.text: terminalVm.cmdCredUseNew ? "当前使用新板凭据" : "当前使用旧板凭据"
                }

                FocusTextField {
                    id: cmdField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    placeholderText: terminalVm.cmdMode === "自由模式" ? "Shell 命令…" : "IPMI 子命令…"
                    font.pixelSize: Theme.fontSizeBody
                    font.family: "Consolas, Menlo, monospace"
                    padding: 6
                    focus: true
                    KeyNavigation.tab: null
                    onTextEdited: terminalVm.resetCmdLineBrowse()

                    Keys.onTabPressed: function(event) {
                        event.accepted = true
                        text = terminalVm.completeTab(text)
                        cursorPosition = text.length
                    }

                    Keys.onUpPressed: function(event) {
                        event.accepted = true
                        text = terminalVm.cmdHistoryUp(text)
                        cursorPosition = text.length
                    }

                    Keys.onDownPressed: function(event) {
                        event.accepted = true
                        text = terminalVm.cmdHistoryDown(text)
                        cursorPosition = text.length
                    }

                    Keys.onReturnPressed: function(event) {
                        event.accepted = true
                        if (text.trim() !== "") {
                            terminalVm.runManualCmd(text)
                            text = ""
                        }
                    }

                    Keys.onEnterPressed: function(event) {
                        event.accepted = true
                        if (text.trim() !== "") {
                            terminalVm.runManualCmd(text)
                            text = ""
                        }
                    }

                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_C && (event.modifiers & Qt.ControlModifier)) {
                            if (terminalVm.interruptShellCmd())
                                event.accepted = true
                        }
                    }
                }
            }
        }
    }
}

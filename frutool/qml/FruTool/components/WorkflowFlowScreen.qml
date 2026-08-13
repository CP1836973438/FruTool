import QtQuick
import FruTool 1.0
import QtQuick.Layouts
import "../effects"

Item {
    id: root

    property var labels: []
    property int currentIndex: 0
    property bool flowActive: false
    property string statusLabel: ""
    property string statusLabelEn: ""
    property real progress: 0

    readonly property bool isIdle: root.currentIndex <= 0 && !root.flowActive
    readonly property bool isDone: root.labels.length > 0
                       && root.currentIndex >= root.labels.length - 1
                       && !root.flowActive
                       && root.currentIndex > 0
    readonly property string monoFamily: "Consolas, Menlo, monospace"
    readonly property string phaseCode: {
        var total = Math.max(1, root.labels.length)
        var idx = Math.min(Math.max(0, root.currentIndex), total - 1)
        function pad2(v) { return v < 10 ? "0" + v : "" + v }
        return pad2(idx + 1) + "/" + pad2(total)
    }
    readonly property string idleStatusText: root.bilingualLine(
        root.statusLabel !== "" ? root.statusLabel : "等待流程启动…",
        root.statusLabelEn !== "" ? root.statusLabelEn : "Await workflow start"
    )
    readonly property string activeStatusText: root.bilingualLine(root.statusLabel, root.statusLabelEn)

    function bilingualLine(cn, en) {
        if (!cn || cn === "—")
            return en || "—"
        if (!en)
            return cn
        return cn + " · " + en
    }

    function stepEn(idx) {
        if (idx < 0 || idx >= root.labels.length)
            return ""
        var item = root.labels[idx]
        return typeof item === "object" ? (item.en || "") : String(item)
    }

    function stepCn(idx) {
        if (idx < 0 || idx >= root.labels.length)
            return ""
        var item = root.labels[idx]
        return typeof item === "object" ? (item.cn || "") : ""
    }

    onCurrentIndexChanged: {
        if (!root.isIdle)
            stepGlitch.trigger()
    }

    onFlowActiveChanged: {
        if (root.flowActive && root.currentIndex <= 0)
            stepGlitch.trigger()
    }

    implicitHeight: 96
    implicitWidth: 320

    Rectangle {
        id: bezel
        anchors.fill: parent
        radius: 8
        color: Theme.surface_top
        border.color: Theme.border
        border.width: 1

        gradient: Gradient {
            GradientStop { position: 0; color: Theme.surface_top }
            GradientStop { position: 1; color: Theme.surface_bottom }
        }

        Rectangle {
            id: screen
            anchors.fill: parent
            anchors.margins: Theme.spacing_xs
            radius: 6
            color: Theme.terminal_bg
            border.color: Qt.rgba(Theme.border.r, Theme.border.g, Theme.border.b, 0.65)
            border.width: 1
            clip: true

            property real scanY: 0

            SequentialAnimation on scanY {
                running: root.visible
                loops: Animation.Infinite
                NumberAnimation {
                    from: -4
                    to: screen.height + 4
                    duration: 3200
                    easing.type: Easing.Linear
                }
            }

            Rectangle {
                width: parent.width
                height: 4
                y: screen.scanY
                opacity: 0.35
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0; color: "transparent" }
                    GradientStop { position: 0.35; color: Theme.accent }
                    GradientStop { position: 0.65; color: Theme.accent }
                    GradientStop { position: 1; color: "transparent" }
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing_sm
                spacing: Theme.spacing_xs

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 6

                    Rectangle {
                        anchors.fill: parent
                        radius: 3
                        color: Theme.surface3
                    }

                    Rectangle {
                        height: parent.height
                        radius: 3
                        width: Math.max(0, parent.width * root.progress)
                        color: root.isDone ? Theme.success : Theme.accent

                        Behavior on width {
                            NumberAnimation { duration: 280; easing.type: Easing.OutCubic }
                        }
                    }

                    Rectangle {
                        height: parent.height + 6
                        radius: 5
                        width: Math.max(0, parent.width * root.progress + 4)
                        y: -3
                        color: root.isDone ? Theme.success : Theme.accent
                        opacity: 0.15

                        Behavior on width {
                            NumberAnimation { duration: 280; easing.type: Easing.OutCubic }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing_xs

                    Text {
                        text: "FRU SWAP"
                        color: Theme.text3
                        font.pixelSize: 9
                        font.family: root.monoFamily
                        font.letterSpacing: 1.2
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        visible: !root.isIdle
                        text: "阶段 " + root.phaseCode + " · PHASE " + root.phaseCode
                        color: root.isDone ? Theme.success : Theme.accent
                        font.pixelSize: 9
                        font.family: root.monoFamily
                        font.letterSpacing: 0.4
                        elide: Text.ElideLeft
                        Layout.maximumWidth: 160
                    }
                }

                GlitchFlash {
                    id: stepGlitch
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 36

                    ColumnLayout {
                        anchors.fill: parent
                        visible: root.isIdle
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: "["
                                color: Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                            }

                            Text {
                                text: "待机"
                                color: Theme.text2
                                font.pixelSize: 11
                                font.family: root.monoFamily
                                font.weight: Font.Medium
                            }

                            Text {
                                text: "\u00B7"
                                color: Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                            }

                            Text {
                                text: "IDLE"
                                color: Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                                font.letterSpacing: 0.8
                            }

                            Text {
                                text: "]"
                                color: Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                            }

                            Text {
                                text: "_"
                                color: Theme.accent
                                font.pixelSize: 11
                                font.family: root.monoFamily
                                opacity: 1

                                SequentialAnimation on opacity {
                                    running: root.isIdle && root.visible
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 1; to: 0; duration: 520; easing.type: Easing.InOutSine }
                                    NumberAnimation { from: 0; to: 1; duration: 520; easing.type: Easing.InOutSine }
                                }
                            }
                        }

                        TypewriterText {
                            Layout.fillWidth: true
                            fullText: root.idleStatusText
                            color: Theme.text3
                            font.pixelSize: 10
                            font.family: root.monoFamily
                            charDelay: 22
                            animate: root.isIdle && root.visible
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        visible: !root.isIdle
                        spacing: 1

                        Repeater {
                            model: root.currentIndex

                            RowLayout {
                                required property int index

                                Layout.fillWidth: true
                                spacing: 4
                                opacity: 0

                                Text {
                                    text: "\u2713"
                                    color: Theme.success
                                    font.pixelSize: 9
                                    font.family: root.monoFamily
                                }

                                Text {
                                    text: root.stepCn(index)
                                    color: Theme.success
                                    font.pixelSize: 9
                                    font.family: root.monoFamily
                                    font.weight: Font.DemiBold
                                    opacity: 0.85
                                }

                                Text {
                                    text: "\u00B7"
                                    color: Theme.text3
                                    font.pixelSize: 9
                                    font.family: root.monoFamily
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.stepEn(index)
                                    color: Theme.success
                                    font.pixelSize: 9
                                    font.family: root.monoFamily
                                    opacity: 0.65
                                    elide: Text.ElideRight
                                }

                                Component.onCompleted: fadeIn.start()
                                SequentialAnimation {
                                    id: fadeIn
                                    NumberAnimation {
                                        target: parent
                                        property: "opacity"
                                        from: 0
                                        to: 0.75
                                        duration: 220
                                        easing.type: Easing.OutCubic
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: root.isDone ? "\u2713" : "\u25B6"
                                color: root.isDone ? Theme.success : Theme.accent
                                font.pixelSize: root.isDone ? 12 : 11
                                font.family: root.monoFamily
                                font.weight: Font.DemiBold

                                SequentialAnimation on opacity {
                                    running: root.flowActive && !root.isDone
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 1; to: 0.35; duration: 700; easing.type: Easing.InOutSine }
                                    NumberAnimation { from: 0.35; to: 1; duration: 700; easing.type: Easing.InOutSine }
                                }
                            }

                            Text {
                                text: root.labels.length > 0
                                      ? root.stepCn(Math.min(root.currentIndex, root.labels.length - 1))
                                      : ""
                                color: root.isDone ? Theme.success : Theme.accent
                                font.pixelSize: 13
                                font.family: root.monoFamily
                                font.weight: Font.DemiBold
                            }

                            Text {
                                text: "\u00B7"
                                color: Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.labels.length > 0
                                      ? root.stepEn(Math.min(root.currentIndex, root.labels.length - 1))
                                      : ""
                                color: root.isDone ? Theme.success : Theme.text3
                                font.pixelSize: 11
                                font.family: root.monoFamily
                                font.weight: Font.Medium
                                font.letterSpacing: 0.6
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                TypewriterText {
                    Layout.fillWidth: true
                    visible: !root.isIdle
                    fullText: root.activeStatusText
                    color: Theme.text2
                    font.pixelSize: 10
                    font.family: root.monoFamily
                    charDelay: 18
                    animate: !root.isIdle && root.visible
                }
            }
        }
    }
}

import QtQuick
import FruTool 1.0
import QtQuick.Controls

Rectangle {
    id: root

    property string manufacturer: ""
    property string platform: ""
    property string suite: ""
    property string archive: ""
    property string entryId: ""
    property bool recommended: false
    property bool selected: false
    property bool compact: false

    readonly property int _lineH: compact ? 16 : 18
    readonly property int _pad: Theme.spacing_md
    readonly property int _border: 2

    signal clicked()

    implicitWidth: compact ? 168 : 196
    implicitHeight: _pad * 2
        + _lineH * 4
        + Theme.spacing_xs * 3
    width: implicitWidth
    height: implicitHeight

    radius: 6
    color: compact
        ? Theme.surface2
        : (selected
            ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14)
            : (hoverHandler.hovered ? Theme.surface3 : Theme.surface2))
    border.width: _border
    border.color: compact
        ? (recommended ? Theme.success : Theme.border)
        : (selected ? Theme.accent : (recommended ? Theme.success : Theme.border))

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        visible: root.compact && root.selected
        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14)
        border.width: _border
        border.color: Theme.accent
        z: 1
    }

    Behavior on color {
        enabled: !compact
        ColorAnimation { duration: 160 }
    }
    Behavior on border.color {
        enabled: !compact
        ColorAnimation { duration: 160 }
    }

    Column {
        id: body
        anchors.fill: parent
        anchors.margins: _pad
        spacing: Theme.spacing_xs
        z: 2

        Row {
            width: parent.width
            height: _lineH
            spacing: Theme.spacing_xs

            Text {
                width: parent.width - (root.recommended ? 36 : 0)
                height: _lineH
                text: root.manufacturer || "未知厂商"
                color: Theme.text
                font.pixelSize: Theme.fontSizeBody
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }

            Text {
                width: 32
                height: _lineH
                visible: root.recommended
                horizontalAlignment: Text.AlignRight
                text: "推荐"
                color: Theme.success
                font.pixelSize: Theme.fontSizeCaption
                renderType: Text.NativeRendering
            }
        }

        Text {
            width: parent.width
            height: _lineH
            text: root.platform !== "" ? ("机型 " + root.platform) : " "
            opacity: root.platform !== "" ? 1 : 0
            color: Theme.text2
            font.pixelSize: Theme.fontSizeCaption
            elide: Text.ElideRight
            renderType: Text.NativeRendering
        }

        Text {
            width: parent.width
            height: _lineH
            text: root.suite
            color: Theme.accent
            font.pixelSize: Theme.fontSizeBody
            font.family: "Consolas, Menlo, monospace"
            elide: Text.ElideRight
            renderType: Text.NativeRendering
        }

        Text {
            width: parent.width
            height: _lineH * 2
            text: root.archive
            color: Theme.text3
            font.pixelSize: Theme.fontSizeCaption
            wrapMode: compact ? Text.NoWrap : Text.Wrap
            maximumLineCount: compact ? 1 : 2
            elide: Text.ElideRight
            renderType: Text.NativeRendering
        }
    }

    HoverHandler {
        id: hoverHandler
        enabled: !root.compact
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        cursorShape: Qt.PointingHandCursor
        onTapped: root.clicked()
    }
}

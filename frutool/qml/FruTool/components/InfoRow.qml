import QtQuick
import FruTool 1.0
import QtQuick.Layouts

RowLayout {
    id: root

    property string label: ""
    property string value: ""

    spacing: Theme.spacing_sm
    Layout.fillWidth: true
    visible: root.value !== ""

    Text {
        text: root.label
        color: Theme.text3
        font.pixelSize: Theme.fontSizeBody
    }

    Text {
        Layout.fillWidth: true
        text: root.value
        color: Theme.text2
        font.pixelSize: Theme.fontSizeBody
        elide: Text.ElideMiddle
    }
}

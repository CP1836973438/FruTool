import QtQuick
import FruTool 1.0
import QtQuick.Layouts

ColumnLayout {
    id: root

    property string label: ""
    property bool fillWidth: true

    spacing: Theme.spacing_xs
    Layout.fillWidth: root.fillWidth

    Text {
        visible: root.label !== ""
        text: root.label
        color: Theme.text2
        font.pixelSize: Theme.fontSizeBody
        Layout.fillWidth: true
    }

    default property alias content: contentSlot.data

    Item {
        id: contentSlot
        Layout.fillWidth: true
        implicitHeight: childrenRect.height
    }
}

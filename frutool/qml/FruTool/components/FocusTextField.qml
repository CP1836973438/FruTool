import QtQuick
import FruTool 1.0
import QtQuick.Controls
import "../effects"

TextField {
    id: root
    color: Theme.text
    placeholderTextColor: Theme.text3
    font.pixelSize: Theme.fontSizeBody
    padding: 8
    selectByMouse: true
    background: Item {
        Rectangle {
            anchors.fill: parent
            radius: 4
            color: root.readOnly ? Qt.rgba(Theme.surface3.r, Theme.surface3.g, Theme.surface3.b, 0.65) : Theme.input_bg
            border.color: root.activeFocus ? Theme.accent : Theme.border
            border.width: 1
            opacity: root.readOnly ? 0.7 : 1.0

            Behavior on opacity { NumberAnimation { duration: 200 } }
            Behavior on color { ColorAnimation { duration: 200 } }
        }
        FocusGlow {
            focused: root.activeFocus
        }
    }
}

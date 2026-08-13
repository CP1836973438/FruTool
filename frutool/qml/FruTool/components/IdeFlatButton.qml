import QtQuick
import FruTool 1.0
import QtQuick.Controls

Button {
    id: root
    flat: true
    implicitHeight: 24

    scale: root.pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutBack } }
    padding: 8
    topPadding: 2
    bottomPadding: 2
    font.pixelSize: Theme.fontSizeBody

    contentItem: Text {
        text: root.text
        font: root.font
        color: root.checkable && root.checked
            ? Theme.accent
            : (root.hovered ? Theme.text : Theme.text2)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter

        Behavior on color { ColorAnimation { duration: 150 } }
    }

    background: Rectangle {
        color: root.checkable && root.checked
            ? Theme.accent_dim
            : (root.hovered ? Theme.surface3 : "transparent")
        radius: 3

        Behavior on color { ColorAnimation { duration: 150 } }
    }
}

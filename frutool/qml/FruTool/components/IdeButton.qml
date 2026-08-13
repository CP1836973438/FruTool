import QtQuick
import FruTool 1.0
import QtQuick.Controls
import "../effects"

Button {
    id: root
    property bool primary: false

    implicitHeight: 28

    scale: root.pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutBack } }
    padding: 12
    topPadding: 4
    bottomPadding: 4
    font.pixelSize: Theme.fontSizeBody

    contentItem: Text {
        text: root.text
        font: root.font
        color: root.primary ? Theme.btn_primary_fg : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Item {
        id: bgHost

        Rectangle {
            anchors.fill: parent
            color: root.primary
                ? (root.pressed ? Theme.accent_hover : (root.hovered ? Theme.accent_hover : Theme.btn_primary_bg))
                : (root.pressed ? Theme.surface3 : (root.hovered ? Theme.btn_secondary_hover : Theme.btn_secondary_bg))
            border.color: root.primary ? Theme.btn_primary_bg : Theme.btn_secondary_border
            border.width: 1
            radius: 4
            opacity: root.enabled ? 1.0 : 0.45

            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }

        RippleOverlay {
            id: rippleFx
            rippleColor: root.primary ? Theme.btn_primary_fg : Theme.accent
        }
    }

    onPressed: rippleFx.trigger(bgHost.width / 2, bgHost.height / 2)
}

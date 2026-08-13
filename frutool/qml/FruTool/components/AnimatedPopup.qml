import QtQuick
import FruTool 1.0
import QtQuick.Controls
import "../effects"

Popup {
    id: root

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    anchors.centerIn: parent
    padding: 0
    transformOrigin: Item.Center

    property Item blurSource: null

    Overlay.modal: DialogModalOverlay {
        popupControl: root
    }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"
                from: 0.0
                to: 1.0
                duration: 220
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                property: "scale"
                from: 0.94
                to: 1.0
                duration: 260
                easing.type: Easing.OutCubic
            }
        }
    }

    exit: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"
                from: 1.0
                to: 0.0
                duration: 160
                easing.type: Easing.InCubic
            }
            NumberAnimation {
                property: "scale"
                from: 1.0
                to: 0.97
                duration: 160
                easing.type: Easing.InCubic
            }
        }
    }
}

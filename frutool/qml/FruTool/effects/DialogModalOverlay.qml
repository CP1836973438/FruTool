import QtQuick

Item {
    id: root

    anchors.fill: parent

    /** Bound by AnimatedPopup — Overlay.modal id is not in Popup scope. */
    property var popupControl: null

    property real dimOpacity: 0

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.62)
        opacity: root.dimOpacity
    }

    Behavior on dimOpacity {
        NumberAnimation {
            duration: 220
            easing.type: Easing.OutCubic
        }
    }

    function fadeIn() {
        dimOpacity = 1.0
    }

    function fadeOut() {
        dimOpacity = 0.0
    }

    Connections {
        target: root.popupControl
        function onOpened() {
            root.fadeIn()
        }
        function onAboutToHide() {
            root.fadeOut()
        }
    }
}

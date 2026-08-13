import QtQuick
import FruTool 1.0

Item {
    id: root

    default property alias content: clipper.data
    property bool active: false

    clip: true

    Item {
        id: clipper
        anchors.fill: parent
        x: root._jitterX
        opacity: root._contentOpacity

        layer.enabled: root.active
        layer.smooth: true
    }

    property real _jitterX: 0
    property real _contentOpacity: 1

    Rectangle {
        anchors.fill: parent
        color: Theme.text
        opacity: root._flashOpacity
        visible: opacity > 0.001
    }

    Repeater {
        model: 4

        Rectangle {
            required property int index

            width: parent.width
            height: 2
            x: root._sliceOffset[index]
            y: (index + 1) * parent.height / 5 + root._sliceY[index]
            color: index % 2 === 0 ? Theme.accent : Theme.text
            opacity: root._sliceOpacity
            visible: opacity > 0.001
        }
    }

    property real _flashOpacity: 0
    property real _sliceOpacity: 0
    property var _sliceOffset: [0, 0, 0, 0]
    property var _sliceY: [0, 0, 0, 0]

    function trigger() {
        glitchAnim.restart()
    }

    SequentialAnimation {
        id: glitchAnim

        ScriptAction {
            script: {
                root.active = true
                for (var i = 0; i < 4; i++) {
                    root._sliceOffset[i] = (Math.random() - 0.5) * 14
                    root._sliceY[i] = (Math.random() - 0.5) * 6
                }
            }
        }

        ParallelAnimation {
            SequentialAnimation {
                loops: 3
                NumberAnimation {
                    target: root
                    property: "_jitterX"
                    from: -3; to: 4; duration: 35
                }
                NumberAnimation {
                    target: root
                    property: "_jitterX"
                    from: 4; to: -2; duration: 35
                }
            }

            SequentialAnimation {
                NumberAnimation {
                    target: root
                    property: "_flashOpacity"
                    from: 0; to: 0.18; duration: 40
                }
                NumberAnimation {
                    target: root
                    property: "_flashOpacity"
                    from: 0.18; to: 0; duration: 60
                }
                NumberAnimation {
                    target: root
                    property: "_flashOpacity"
                    from: 0; to: 0.1; duration: 30
                }
                NumberAnimation {
                    target: root
                    property: "_flashOpacity"
                    from: 0.1; to: 0; duration: 50
                }
            }

            SequentialAnimation {
                NumberAnimation {
                    target: root
                    property: "_sliceOpacity"
                    from: 0; to: 0.55; duration: 30
                }
                NumberAnimation {
                    target: root
                    property: "_sliceOpacity"
                    from: 0.55; to: 0.15; duration: 40
                }
                NumberAnimation {
                    target: root
                    property: "_sliceOpacity"
                    from: 0.15; to: 0.35; duration: 25
                }
                NumberAnimation {
                    target: root
                    property: "_sliceOpacity"
                    from: 0.35; to: 0; duration: 45
                }
            }

            SequentialAnimation {
                loops: 2
                NumberAnimation {
                    target: root
                    property: "_contentOpacity"
                    from: 1; to: 0.55; duration: 45
                }
                NumberAnimation {
                    target: root
                    property: "_contentOpacity"
                    from: 0.55; to: 1; duration: 45
                }
            }
        }

        ScriptAction {
            script: {
                root._jitterX = 0
                root._contentOpacity = 1
                root._flashOpacity = 0
                root._sliceOpacity = 0
                root.active = false
            }
        }
    }
}

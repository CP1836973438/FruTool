import QtQuick
import FruTool 1.0
import QtQuick.Controls

ComboBox {
    id: root
    /** 紧凑模式：按文字定宽、居中（终端 IPMI/新/旧）；默认模式：可拉伸、左对齐、省略溢出 */
    property bool compact: false

    implicitHeight: 28
    implicitWidth: compact ? Math.max(labelItem.implicitWidth + 12, 28) : 72
    clip: true
    font.pixelSize: 13

    background: Rectangle {
        color: Theme.input_bg
        border.color: root.activeFocus ? Theme.accent : (root.pressed ? Theme.accent : Theme.border)
        border.width: 1
        radius: 4
    }

    indicator: Text {
        x: root.width - width - 8
        y: (root.height - height) / 2
        visible: !root.compact
        text: "▾"
        color: Theme.text2
        font.pixelSize: 10
    }

    contentItem: Text {
        id: labelItem
        width: root.width
        height: root.height
        text: root.displayText
        font.family: root.font.family
        font.pixelSize: 13
        color: Theme.text
        horizontalAlignment: root.compact ? Text.AlignHCenter : Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        leftPadding: root.compact ? 0 : 8
        rightPadding: root.compact ? 0 : 18
        elide: root.compact ? Text.ElideNone : Text.ElideRight
    }

    popup: Popup {
        y: root.height + 2
        width: root.compact ? Math.max(root.width, 96) : Math.max(root.width, 320)
        padding: 4
        transformOrigin: Item.Top

        enter: Transition {
            ParallelAnimation {
                NumberAnimation {
                    property: "opacity"
                    from: 0.0
                    to: 1.0
                    duration: 160
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    property: "scale"
                    from: 0.96
                    to: 1.0
                    duration: 180
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
                    duration: 120
                    easing.type: Easing.InCubic
                }
                NumberAnimation {
                    property: "scale"
                    from: 1.0
                    to: 0.98
                    duration: 120
                    easing.type: Easing.InCubic
                }
            }
        }

        background: Rectangle {
            radius: 4
            border.color: Theme.border
            border.width: 1
            gradient: Gradient {
                GradientStop { position: 0; color: Theme.surface_top }
                GradientStop { position: 1; color: Theme.surface_bottom }
            }
        }
        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 240)
            model: root.delegateModel
            spacing: 2
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                contentItem: Rectangle {
                    implicitWidth: 6
                    radius: 3
                    color: Theme.scrollbar_handle
                }
            }
            delegate: ItemDelegate {
                id: rowDelegate
                width: ListView.view.width
                height: 32
                font.pixelSize: 13
                font.family: root.font.family

                contentItem: Text {
                    width: parent.width
                    text: rowDelegate.text
                    font.family: rowDelegate.font.family
                    font.pixelSize: 13
                    font.weight: rowDelegate.highlighted ? Font.DemiBold : Font.Normal
                    color: rowDelegate.highlighted ? Theme.accent : Theme.text
                    horizontalAlignment: root.compact ? Text.AlignHCenter : Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: root.compact ? 0 : 8
                    rightPadding: 8
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: 3
                    color: rowDelegate.highlighted
                           ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                           : (rowDelegate.hovered ? Theme.surface2 : "transparent")
                }
            }
        }
    }
}

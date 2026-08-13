import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../effects"

AnimatedPopup {
    id: root

    /** Dialog title (required). */
    property string dialogTitle: ""
    /** Optional message below the title. */
    property string dialogSubtitle: ""
    /** Middle section — assign GridLayout, ColumnLayout, etc. */
    property Item body: null
    /** Bottom button row — assign RowLayout with IdeButton children. */
    property Item footer: null
    property color panelBorderColor: Theme.border
    property bool errorGlow: false

    width: Math.min(defaultWidth, parent ? parent.width - 40 : defaultWidth)
    property int defaultWidth: 440

    background: DialogPanel {
        radius: 8
        blurSource: root.blurSource
        borderColor: root.errorGlow ? Theme.error : root.panelBorderColor
    }

    onBodyChanged: _reparentBody()
    onFooterChanged: _reparentFooter()

    function _reparentBody() {
        if (!body)
            return
        body.parent = bodyHost
        body.anchors.left = bodyHost.left
        body.anchors.right = bodyHost.right
        body.anchors.top = bodyHost.top
    }

    function _reparentFooter() {
        if (!footer)
            return
        footer.parent = footerHost
        footer.anchors.left = footerHost.left
        footer.anchors.right = footerHost.right
        footer.anchors.top = footerHost.top
    }

    contentItem: Item {
        implicitWidth: column.implicitWidth
        implicitHeight: column.implicitHeight
        width: root.width

        FocusGlow {
            visible: root.errorGlow
            focused: root.errorGlow && root.visible
            glowColor: Theme.error
            borderColor: Theme.error
            glowStrength: Theme.glow_strength * 1.2
        }

        ColumnLayout {
            id: column
            width: root.width
            spacing: 0

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 16
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                text: root.dialogTitle
                color: root.errorGlow ? Theme.error : Theme.text
                font.pixelSize: Theme.fontSizeTitle
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 10
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: root.body ? 0 : 8
                text: root.dialogSubtitle
                color: Theme.text2
                font.pixelSize: Theme.fontSizeSubtitle
                wrapMode: Text.Wrap
                visible: root.dialogSubtitle !== ""
            }

            Item {
                id: bodyHost
                Layout.fillWidth: true
                Layout.topMargin: root.dialogSubtitle !== "" ? 10 : 0
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 8
                implicitHeight: body ? body.implicitHeight : 0
                visible: body !== null
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.border
            }

            Item {
                id: footerHost
                Layout.fillWidth: true
                Layout.margins: 12
                implicitHeight: footer ? footer.implicitHeight : 0
                visible: footer !== null
            }
        }
    }
}

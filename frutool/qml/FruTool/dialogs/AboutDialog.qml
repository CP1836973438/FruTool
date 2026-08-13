import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

BaseDialog {
    id: root
    defaultWidth: 420

    dialogTitle: chromeVm.appProductName
    dialogSubtitle: chromeVm.appDescription

    body: GridLayout {
        width: parent ? parent.width : implicitWidth
        columns: 2
        columnSpacing: 12
        rowSpacing: 6
        Text { text: "版本"; color: Theme.text3 }
        Text { text: chromeVm.appVersion; color: Theme.text }
        Text { text: "公司"; color: Theme.text3 }
        Text { text: chromeVm.appCompany; color: Theme.text }
        Text { text: "版权"; color: Theme.text3 }
        Text {
            text: chromeVm.appCopyright
            color: Theme.text
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
    }

    footer: RowLayout {
        spacing: 8
        width: parent ? parent.width : implicitWidth
        Item { Layout.fillWidth: true }
        IdeButton {
            text: "确定"
            primary: true
            onClicked: root.close()
        }
    }
}

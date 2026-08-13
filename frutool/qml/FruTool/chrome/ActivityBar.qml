import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: Theme.chrome_sidebar
    border.color: Theme.chrome_border
    border.width: 1

    implicitWidth: 56
    Layout.preferredWidth: 56
    Layout.fillHeight: true

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 4
        z: Theme.zContent

        NavButton {
            pageKey: "main"
            tip: "换板流程"
            pulse: swapVm.swapMode === "auto"
                    && swapVm.swapAutoPhase !== "idle"
                    && swapVm.swapAutoPhase !== "done"
        }
        NavButton { pageKey: "fru"; tip: "FRU 字段刷写" }
        NavButton {
            pageKey: "topo"
            tip: "PCIe 拓扑刷写"
            pulse: topoVm.topoProgressVisible
        }
        NavButton {
            pageKey: "conn"
            tip: connVm.bmcOnline && connVm.localOnline
                 ? "连接与网络（已就绪）"
                 : (connVm.bmcOnline || connVm.localOnline
                    ? "连接与网络（部分在线）"
                    : "连接与网络（离线）")
            online: connVm.bmcOnline && connVm.localOnline
        }

        Item { Layout.fillHeight: true }

        ToolButton {
            id: themeBtn
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            text: ""
            ToolTip.delay: 600
            ToolTip.text: "主题"

            contentItem: NavIcon {
                anchors.centerIn: parent
                icon: "theme"
                active: themeBtn.hovered
                hovered: themeBtn.hovered
            }

            background: Item {
                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: themeBtn.hovered ? Theme.surface3 : "transparent"
                }
            }

            onClicked: themeMenu.open()

            Menu {
                id: themeMenu
                MenuItem {
                    text: "跟随系统"
                    onTriggered: chromeVm.setThemeMode("auto")
                }
                MenuItem {
                    text: "深色"
                    onTriggered: chromeVm.setThemeMode("dark")
                }
                MenuItem {
                    text: "浅色"
                    onTriggered: chromeVm.setThemeMode("light")
                }
            }
        }
    }
}

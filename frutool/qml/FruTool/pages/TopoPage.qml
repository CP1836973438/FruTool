import QtQuick
import FruTool 1.0
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    property Item blurSource: null

    ColumnLayout {
        width: Math.max(0, root.availableWidth - Theme.spacing_xl)
        x: Theme.spacing_md
        spacing: Theme.spacing_lg

        Card {
            Layout.fillWidth: true
            title: "PCIe 拓扑文件刷写"
            blurSource: root.blurSource

            Text {
                Layout.fillWidth: true
                visible: topoVm.demoMode
                text: "演示模式：FRU 与 BMC 为模拟数据，刷写按钮仅作 UI 验证（不会连接真实硬件）。"
                color: Theme.warning
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            Text {
                Layout.fillWidth: true
                visible: topoVm.topoMatchMessage !== ""
                text: topoVm.topoMatchMessage
                color: topoVm.topoMatchOk ? Theme.success : Theme.warning
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            Text {
                Layout.fillWidth: true
                visible: topoVm.topoPath === "" && topoVm.topoMatchMessage === ""
                text: "请选择对应机型的 PCIe 拓扑 .bin 文件后开始刷写。\n文件通常由厂商提供，大小不超过 512 字节。"
                color: Theme.text2
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing_sm

                Text {
                    text: "拓扑 .bin 文件"
                    color: Theme.text2
                    font.pixelSize: Theme.fontSizeBody
                    Layout.preferredWidth: 88
                    Layout.alignment: Qt.AlignVCenter
                }

                FocusTextField {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    Layout.alignment: Qt.AlignVCenter
                    text: topoVm.topoPath
                    onTextEdited: topoVm.setTopoPath(text)
                }

                IdeButton {
                    Layout.alignment: Qt.AlignVCenter
                    text: "浏览"
                    onClicked: topoVm.browseTopoFile()
                }
            }

            Text {
                Layout.fillWidth: true
                text: "使用连接设置中的新板账号密码与当前 BMC IP，在 ipmitool 目录下调用 PcieEEpromTool.py 写入 EEPROM（0x7E00）。各厂商拓扑 .bin 不同（≤512 字节）。打包版会调用本机已安装的 Python（与终端相同 PATH）。"
                color: Theme.text3
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 32

                BusyIndicator {
                    anchors.centerIn: parent
                    width: 28
                    height: 28
                    visible: topoVm.topoProgressVisible || topoVm.topoMatchBusy
                    running: visible
                }
            }

            Text {
                Layout.fillWidth: true
                visible: !connVm.bmcOnline && topoVm.canTopoWrite
                text: "BMC 离线，连接后才能刷写拓扑。"
                color: Theme.warning
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            IdeButton {
                text: "开始刷写拓扑文件"
                primary: true
                enabled: topoVm.canTopoWrite && topoVm.topoPath !== "" && connVm.bmcOnline
                onClicked: topoVm.doTopoWrite()
            }
        }

        Card {
            Layout.fillWidth: true
            title: "匹配套餐拓扑"
            blurSource: root.blurSource
            visible: topoVm.topoCandidates.length > 0

            Text {
                Layout.fillWidth: true
                text: topoVm.topoCandidates.length > 1
                      ? "检测到多个厂商提供相同套餐号，已按 Product Manufacturer 排序并全部预加载，请点击卡片选择要刷写的版本。"
                      : "已根据新板 FRU 预加载拓扑，可直接刷写或切换其他版本。"
                color: Theme.text2
                font.pixelSize: Theme.fontSizeBody
                wrapMode: Text.Wrap
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spacing_sm

                Repeater {
                    model: topoVm.topoCandidates
                    delegate: TopoPickCard {
                        required property var modelData
                        manufacturer: modelData.manufacturer
                        platform: modelData.platform || ""
                        suite: modelData.suite
                        archive: modelData.archive
                        entryId: modelData.id
                        recommended: !!modelData.recommended
                        selected: !!modelData.selected
                        onClicked: topoVm.selectTopoCandidate(modelData.id)
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            title: "PCLE 拓扑库"
            enableHoverLift: false
            liveCapture: false
            blurSource: root.blurSource
            visible: topoVm.topoCatalog.length > 0 || topoVm.catalogFilter !== ""

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing_sm

                Text {
                    text: "筛选"
                    color: Theme.text2
                    font.pixelSize: Theme.fontSizeBody
                    Layout.preferredWidth: 36
                }

                FocusTextField {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    placeholderText: "按厂商 / 机型 / 套餐 / 压缩包或裸 bin 名筛选"
                    text: topoVm.catalogFilter
                    onTextEdited: topoVm.setCatalogFilter(text)
                }
            }

            Text {
                Layout.fillWidth: true
                visible: topoVm.topoCatalog.length === 0
                text: "没有匹配的拓扑记录。"
                color: Theme.text3
                font.pixelSize: Theme.fontSizeBody
            }

            Text {
                Layout.fillWidth: true
                visible: topoVm.topoCatalog.length > 0
                text: "按住鼠标拖动或滚轮上下浏览（类似手机滑动）。"
                color: Theme.text3
                font.pixelSize: Theme.fontSizeCaption
            }

            TopoCatalogGrid {
                Layout.fillWidth: true
                visible: topoVm.topoCatalog.length > 0
                model: topoVm.topoCatalog
                selectedCatalogId: topoVm.selectedTopoCatalogId
                onEntryClicked: (entryId) => topoVm.selectTopoCatalogEntry(entryId)
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.spacing_xl }
    }
}

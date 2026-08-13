import QtQuick
import FruTool 1.0

GridView {
    id: grid

    property int maxHeight: 380
    property string selectedCatalogId: ""

    signal entryClicked(string entryId)

    readonly property int cardWidth: 168
    readonly property int cardHeight: Theme.spacing_md * 2
        + 16 * 4
        + Theme.spacing_xs * 3
    readonly property int gap: Theme.spacing_sm

    clip: true
    width: parent ? parent.width : cardWidth
    height: contentHeight > 0 ? Math.min(contentHeight, maxHeight) : 0

    cellWidth: cardWidth + gap
    cellHeight: cardHeight + gap

    boundsBehavior: Flickable.StopAtBounds
    flickDeceleration: 3200
    maximumFlickVelocity: 4500
    pressDelay: 0
    reuseItems: true
    cacheBuffer: cardHeight * 10

    displaced: Transition {
        enabled: false
    }

    onContentHeightChanged: contentY = Math.min(contentY, Math.max(0, contentHeight - height))
    onHeightChanged: contentY = Math.min(contentY, Math.max(0, contentHeight - height))

    delegate: TopoPickCard {
        required property var modelData

        width: grid.cardWidth
        height: grid.cardHeight
        compact: true
        manufacturer: modelData.manufacturer
        platform: modelData.platform || ""
        suite: modelData.suite
        archive: modelData.archive
        entryId: modelData.id
        recommended: false
        selected: grid.selectedCatalogId === modelData.id
        onClicked: grid.entryClicked(modelData.id)
    }
}

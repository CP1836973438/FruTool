pragma Singleton
import QtQuick

// Design-time stub for qmldir. At runtime, main.py registers ThemeBridge
// via qmlRegisterSingletonInstance("FruTool", 1, 0, "Theme", themeBridge).
// All QML files access tokens through: import FruTool 1.0

QtObject {
    readonly property int zBackground: 0
    readonly property int zContent: 1
    readonly property int zOverlay: 5
    readonly property int zRail: 10
    readonly property int zPopup: 100
    readonly property int zDragIndicator: 100
}

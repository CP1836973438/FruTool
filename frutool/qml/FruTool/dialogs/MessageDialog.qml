import QtQuick

import FruTool 1.0

import QtQuick.Controls

import QtQuick.Layouts

import "../components"



BaseDialog {

    id: root



    property string dialogId: ""

    property string dialogMessage: ""

    property bool defaultNo: false

    property bool errorGlow: false

    /** "ok" | "yesno" | "cancelok" */

    property string buttonMode: "ok"



    property bool _responded: false



    dialogSubtitle: root.dialogMessage

    defaultWidth: 440



    signal accepted()

    signal rejected()



    function _accept() {

        if (root._responded)

            return

        root._responded = true

        root.accepted()

        root.close()

    }



    function _reject() {

        if (root._responded)

            return

        root._responded = true

        root.rejected()

        root.close()

    }



    onOpened: root._responded = false



    onClosed: {

        if (root._responded || root.dialogId === "")

            return

        if (root.buttonMode === "yesno" || root.buttonMode === "cancelok")

            root.rejected()

    }



    footer: RowLayout {

        spacing: 8

        width: parent ? parent.width : implicitWidth

        Item { Layout.fillWidth: true }

        IdeButton {

            visible: root.buttonMode === "yesno" || root.buttonMode === "cancelok"

            text: root.buttonMode === "cancelok" ? "取消" : "否"

            onClicked: root._reject()

        }

        IdeButton {

            text: root.buttonMode === "yesno" ? "是" : "确定"

            primary: true

            onClicked: root._accept()

        }

    }

}


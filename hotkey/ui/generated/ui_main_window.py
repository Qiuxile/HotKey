# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QStatusBar, QTabBar, QTableView,
    QToolButton, QTreeWidgetItem, QVBoxLayout, QWidget)

from hotkey.ui.widgets.block_editor import BlockListEditor
from hotkey.ui.widgets.statement_tree import StatementTree

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1120, 640)
        MainWindow.setMinimumSize(QSize(760, 520))
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        self.actionSetHotkey = QAction(MainWindow)
        self.actionSetHotkey.setObjectName(u"actionSetHotkey")
        self.actionSaveAs = QAction(MainWindow)
        self.actionSaveAs.setObjectName(u"actionSaveAs")
        self.actionRemove = QAction(MainWindow)
        self.actionRemove.setObjectName(u"actionRemove")
        self.actionImport = QAction(MainWindow)
        self.actionImport.setObjectName(u"actionImport")
        self.actionExportPython = QAction(MainWindow)
        self.actionExportPython.setObjectName(u"actionExportPython")
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName(u"actionQuit")
        self.actionNew = QAction(MainWindow)
        self.actionNew.setObjectName(u"actionNew")
        self.actionDelete = QAction(MainWindow)
        self.actionDelete.setObjectName(u"actionDelete")
        self.actionSearch = QAction(MainWindow)
        self.actionSearch.setObjectName(u"actionSearch")
        self.actionToggleEditor = QAction(MainWindow)
        self.actionToggleEditor.setObjectName(u"actionToggleEditor")
        self.actionToggleEditor.setCheckable(True)
        self.actionStart = QAction(MainWindow)
        self.actionStart.setObjectName(u"actionStart")
        self.actionStop = QAction(MainWindow)
        self.actionStop.setObjectName(u"actionStop")
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.centralWidget = QWidget(MainWindow)
        self.centralWidget.setObjectName(u"centralWidget")
        self.centralLayout = QVBoxLayout(self.centralWidget)
        self.centralLayout.setSpacing(0)
        self.centralLayout.setObjectName(u"centralLayout")
        self.centralLayout.setContentsMargins(0, 0, 0, 0)
        self.centralSplitter = QSplitter(self.centralWidget)
        self.centralSplitter.setObjectName(u"centralSplitter")
        self.centralSplitter.setOrientation(Qt.Horizontal)
        self.centralSplitter.setChildrenCollapsible(False)
        self.listPanel = QWidget(self.centralSplitter)
        self.listPanel.setObjectName(u"listPanel")
        self.listPanel.setMinimumSize(QSize(340, 0))
        self.listPanel.setMaximumSize(QSize(400, 16777215))
        self.listLayout = QVBoxLayout(self.listPanel)
        self.listLayout.setSpacing(8)
        self.listLayout.setObjectName(u"listLayout")
        self.listLayout.setContentsMargins(10, 10, 10, 10)
        self.searchEdit = QLineEdit(self.listPanel)
        self.searchEdit.setObjectName(u"searchEdit")
        self.searchEdit.setClearButtonEnabled(True)

        self.listLayout.addWidget(self.searchEdit)

        self.hotkeyTable = QTableView(self.listPanel)
        self.hotkeyTable.setObjectName(u"hotkeyTable")
        self.hotkeyTable.setAlternatingRowColors(True)
        self.hotkeyTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.hotkeyTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.hotkeyTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.hotkeyTable.setShowGrid(False)
        self.hotkeyTable.setContextMenuPolicy(Qt.CustomContextMenu)

        self.listLayout.addWidget(self.hotkeyTable)

        self.newScriptRow = QHBoxLayout()
        self.newScriptRow.setSpacing(6)
        self.newScriptRow.setObjectName(u"newScriptRow")
        self.btnNewScript = QPushButton(self.listPanel)
        self.btnNewScript.setObjectName(u"btnNewScript")

        self.newScriptRow.addWidget(self.btnNewScript)

        self.btnImportHotkey = QPushButton(self.listPanel)
        self.btnImportHotkey.setObjectName(u"btnImportHotkey")

        self.newScriptRow.addWidget(self.btnImportHotkey)


        self.listLayout.addLayout(self.newScriptRow)

        self.centralSplitter.addWidget(self.listPanel)
        self.editorPanel = QWidget(self.centralSplitter)
        self.editorPanel.setObjectName(u"editorPanel")
        self.editorLayout = QVBoxLayout(self.editorPanel)
        self.editorLayout.setSpacing(8)
        self.editorLayout.setObjectName(u"editorLayout")
        self.editorLayout.setContentsMargins(10, 10, 10, 10)
        self.editorTabs = QTabBar(self.editorPanel)
        self.editorTabs.setObjectName(u"editorTabs")
        self.editorTabs.setTabsClosable(True)
        self.editorTabs.setMovable(True)
        self.editorTabs.setDocumentMode(True)

        self.editorLayout.addWidget(self.editorTabs)

        self.lblEditing = QLabel(self.editorPanel)
        self.lblEditing.setObjectName(u"lblEditing")

        self.editorLayout.addWidget(self.lblEditing)

        self.editorBody = QHBoxLayout()
        self.editorBody.setSpacing(8)
        self.editorBody.setObjectName(u"editorBody")
        self.palettePanel = QWidget(self.editorPanel)
        self.palettePanel.setObjectName(u"palettePanel")
        self.palettePanel.setMinimumSize(QSize(190, 0))
        self.palettePanel.setMaximumSize(QSize(240, 16777215))
        self.paletteLayout = QVBoxLayout(self.palettePanel)
        self.paletteLayout.setSpacing(6)
        self.paletteLayout.setObjectName(u"paletteLayout")
        self.paletteLayout.setContentsMargins(0, 0, 0, 0)
        self.paletteSearchRow = QHBoxLayout()
        self.paletteSearchRow.setSpacing(4)
        self.paletteSearchRow.setObjectName(u"paletteSearchRow")
        self.paletteSearch = QLineEdit(self.palettePanel)
        self.paletteSearch.setObjectName(u"paletteSearch")
        self.paletteSearch.setMaximumSize(QSize(160, 16777215))
        self.paletteSearch.setClearButtonEnabled(True)

        self.paletteSearchRow.addWidget(self.paletteSearch)

        self.btnTogglePalette = QToolButton(self.palettePanel)
        self.btnTogglePalette.setObjectName(u"btnTogglePalette")
        self.btnTogglePalette.setMinimumSize(QSize(42, 0))
        self.btnTogglePalette.setMaximumSize(QSize(42, 16777215))

        self.paletteSearchRow.addWidget(self.btnTogglePalette)


        self.paletteLayout.addLayout(self.paletteSearchRow)

        self.statementTree = StatementTree(self.palettePanel)
        self.statementTree.setObjectName(u"statementTree")

        self.paletteLayout.addWidget(self.statementTree)


        self.editorBody.addWidget(self.palettePanel)

        self.editorColumn = QVBoxLayout()
        self.editorColumn.setSpacing(8)
        self.editorColumn.setObjectName(u"editorColumn")
        self.editorToolbar = QHBoxLayout()
        self.editorToolbar.setObjectName(u"editorToolbar")
        self.btnCapturePos = QPushButton(self.editorPanel)
        self.btnCapturePos.setObjectName(u"btnCapturePos")

        self.editorToolbar.addWidget(self.btnCapturePos)

        self.btnCaptureColor = QPushButton(self.editorPanel)
        self.btnCaptureColor.setObjectName(u"btnCaptureColor")

        self.editorToolbar.addWidget(self.btnCaptureColor)

        self.btnScreenSize = QPushButton(self.editorPanel)
        self.btnScreenSize.setObjectName(u"btnScreenSize")

        self.editorToolbar.addWidget(self.btnScreenSize)

        self.editorSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editorToolbar.addItem(self.editorSpacer)

        self.btnRunOnce = QPushButton(self.editorPanel)
        self.btnRunOnce.setObjectName(u"btnRunOnce")

        self.editorToolbar.addWidget(self.btnRunOnce)

        self.btnExportPython = QPushButton(self.editorPanel)
        self.btnExportPython.setObjectName(u"btnExportPython")

        self.editorToolbar.addWidget(self.btnExportPython)

        self.btnSaveScript = QPushButton(self.editorPanel)
        self.btnSaveScript.setObjectName(u"btnSaveScript")

        self.editorToolbar.addWidget(self.btnSaveScript)

        self.btnSaveAs = QPushButton(self.editorPanel)
        self.btnSaveAs.setObjectName(u"btnSaveAs")

        self.editorToolbar.addWidget(self.btnSaveAs)

        self.btnCloseEditor = QPushButton(self.editorPanel)
        self.btnCloseEditor.setObjectName(u"btnCloseEditor")

        self.editorToolbar.addWidget(self.btnCloseEditor)


        self.editorColumn.addLayout(self.editorToolbar)

        self.blockEditor = BlockListEditor(self.editorPanel)
        self.blockEditor.setObjectName(u"blockEditor")

        self.editorColumn.addWidget(self.blockEditor)


        self.editorBody.addLayout(self.editorColumn)


        self.editorLayout.addLayout(self.editorBody)

        self.centralSplitter.addWidget(self.editorPanel)

        self.centralLayout.addWidget(self.centralSplitter)

        MainWindow.setCentralWidget(self.centralWidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1120, 24))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuEdit = QMenu(self.menubar)
        self.menuEdit.setObjectName(u"menuEdit")
        self.menuAction = QMenu(self.menubar)
        self.menuAction.setObjectName(u"menuAction")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuAction.menuAction())
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionImport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionSaveAs)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExportPython)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuEdit.addAction(self.actionSetHotkey)
        self.menuEdit.addAction(self.actionRemove)
        self.menuEdit.addAction(self.actionDelete)
        self.menuAction.addAction(self.actionSearch)
        self.menuAction.addAction(self.actionToggleEditor)
        self.menuAction.addSeparator()
        self.menuAction.addAction(self.actionStart)
        self.menuAction.addAction(self.actionStop)
        self.menuAction.addSeparator()
        self.menuAction.addAction(self.actionAbout)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"HotKey - \u70ed\u952e\u5de5\u5177", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58\u811a\u672c", None))
#if QT_CONFIG(shortcut)
        self.actionSave.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionSetHotkey.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e\u70ed\u952e...", None))
#if QT_CONFIG(shortcut)
        self.actionSetHotkey.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+H", None))
#endif // QT_CONFIG(shortcut)
        self.actionSaveAs.setText(QCoreApplication.translate("MainWindow", u"\u53e6\u5b58\u4e3a...", None))
#if QT_CONFIG(shortcut)
        self.actionSaveAs.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionRemove.setText(QCoreApplication.translate("MainWindow", u"\u79fb\u9664\u70ed\u952e\uff08\u4fdd\u7559\u6587\u4ef6\uff09", None))
        self.actionImport.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u5165\u70ed\u952e...", None))
#if QT_CONFIG(shortcut)
        self.actionImport.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionExportPython.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa Python \u6587\u4ef6...", None))
#if QT_CONFIG(shortcut)
        self.actionExportPython.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", u"\u9000\u51fa", None))
#if QT_CONFIG(shortcut)
        self.actionQuit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionNew.setText(QCoreApplication.translate("MainWindow", u"\u65b0\u5efa\u70ed\u952e", None))
#if QT_CONFIG(shortcut)
        self.actionNew.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
        self.actionDelete.setText(QCoreApplication.translate("MainWindow", u"\u5220\u9664\u70ed\u952e", None))
#if QT_CONFIG(shortcut)
        self.actionDelete.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Del", None))
#endif // QT_CONFIG(shortcut)
        self.actionSearch.setText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22", None))
#if QT_CONFIG(shortcut)
        self.actionSearch.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+F", None))
#endif // QT_CONFIG(shortcut)
        self.actionToggleEditor.setText(QCoreApplication.translate("MainWindow", u"\u663e\u793a\u64cd\u4f5c\u7f16\u8f91", None))
#if QT_CONFIG(shortcut)
        self.actionToggleEditor.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionStart.setText(QCoreApplication.translate("MainWindow", u"\u542f\u52a8\u76d1\u542c", None))
#if QT_CONFIG(shortcut)
        self.actionStart.setShortcut(QCoreApplication.translate("MainWindow", u"F5", None))
#endif // QT_CONFIG(shortcut)
        self.actionStop.setText(QCoreApplication.translate("MainWindow", u"\u505c\u6b62\u76d1\u542c", None))
#if QT_CONFIG(shortcut)
        self.actionStop.setShortcut(QCoreApplication.translate("MainWindow", u"Shift+F5", None))
#endif // QT_CONFIG(shortcut)
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"\u5173\u4e8e HotKey", None))
#if QT_CONFIG(shortcut)
        self.actionAbout.setShortcut(QCoreApplication.translate("MainWindow", u"F1", None))
#endif // QT_CONFIG(shortcut)
        self.searchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u70ed\u952e...", None))
        self.btnNewScript.setText(QCoreApplication.translate("MainWindow", u"\uff0b \u65b0\u5efa\u70ed\u952e", None))
        self.btnImportHotkey.setText(QCoreApplication.translate("MainWindow", u"\uff0b \u5bfc\u5165\u70ed\u952e", None))
        self.lblEditing.setText(QCoreApplication.translate("MainWindow", u"\u64cd\u4f5c\u7f16\u8f91", None))
        self.paletteSearch.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u79ef\u6728...", None))
#if QT_CONFIG(tooltip)
        self.btnTogglePalette.setToolTip(QCoreApplication.translate("MainWindow", u"\u5c55\u5f00 / \u6536\u8d77\u6240\u6709\u79ef\u6728\u5206\u7c7b", None))
#endif // QT_CONFIG(tooltip)
        self.btnTogglePalette.setText(QCoreApplication.translate("MainWindow", u"\u6536\u8d77", None))
        self.btnCapturePos.setText(QCoreApplication.translate("MainWindow", u"\u590d\u5236\u5750\u6807", None))
        self.btnCaptureColor.setText(QCoreApplication.translate("MainWindow", u"\u590d\u5236\u989c\u8272", None))
        self.btnScreenSize.setText(QCoreApplication.translate("MainWindow", u"\u590d\u5236\u5c3a\u5bf8", None))
        self.btnRunOnce.setText(QCoreApplication.translate("MainWindow", u"\u8bd5\u8fd0\u884c", None))
        self.btnExportPython.setText(QCoreApplication.translate("MainWindow", u"\u751f\u6210 .py", None))
        self.btnSaveScript.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58", None))
        self.btnSaveAs.setText(QCoreApplication.translate("MainWindow", u"\u53e6\u5b58\u4e3a", None))
        self.btnCloseEditor.setText(QCoreApplication.translate("MainWindow", u"\u5173\u95ed", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"\u6587\u4ef6", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"\u7f16\u8f91", None))
        self.menuAction.setTitle(QCoreApplication.translate("MainWindow", u"\u64cd\u4f5c", None))
    # retranslateUi


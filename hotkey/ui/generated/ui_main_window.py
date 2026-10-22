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
        self.actionNewFile = QAction(MainWindow)
        self.actionNewFile.setObjectName(u"actionNewFile")
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        self.actionTheme = QAction(MainWindow)
        self.actionTheme.setObjectName(u"actionTheme")
        self.actionTheme.setCheckable(True)
        self.actionImport = QAction(MainWindow)
        self.actionImport.setObjectName(u"actionImport")
        self.actionExport = QAction(MainWindow)
        self.actionExport.setObjectName(u"actionExport")
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
        self.centralWidget = QWidget(MainWindow)
        self.centralWidget.setObjectName(u"centralWidget")
        self.centralLayout = QVBoxLayout(self.centralWidget)
        self.centralLayout.setSpacing(0)
        self.centralLayout.setObjectName(u"centralLayout")
        self.centralLayout.setContentsMargins(0, 0, 0, 0)
        self.tabRow = QHBoxLayout()
        self.tabRow.setSpacing(4)
        self.tabRow.setObjectName(u"tabRow")
        self.tabRow.setContentsMargins(8, 4, 8, 0)
        self.fileTabs = QTabBar(self.centralWidget)
        self.fileTabs.setObjectName(u"fileTabs")
        self.fileTabs.setTabsClosable(True)
        self.fileTabs.setMovable(True)
        self.fileTabs.setDocumentMode(True)

        self.tabRow.addWidget(self.fileTabs)

        self.btnNewFile = QToolButton(self.centralWidget)
        self.btnNewFile.setObjectName(u"btnNewFile")

        self.tabRow.addWidget(self.btnNewFile)

        self.tabSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.tabRow.addItem(self.tabSpacer)


        self.centralLayout.addLayout(self.tabRow)

        self.centralSplitter = QSplitter(self.centralWidget)
        self.centralSplitter.setObjectName(u"centralSplitter")
        self.centralSplitter.setOrientation(Qt.Horizontal)
        self.centralSplitter.setChildrenCollapsible(False)
        self.listPanel = QWidget(self.centralSplitter)
        self.listPanel.setObjectName(u"listPanel")
        self.listPanel.setMinimumSize(QSize(340, 0))
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

        self.centralSplitter.addWidget(self.listPanel)
        self.editorPanel = QWidget(self.centralSplitter)
        self.editorPanel.setObjectName(u"editorPanel")
        self.editorLayout = QVBoxLayout(self.editorPanel)
        self.editorLayout.setSpacing(8)
        self.editorLayout.setObjectName(u"editorLayout")
        self.editorLayout.setContentsMargins(10, 10, 10, 10)
        self.lblEditing = QLabel(self.editorPanel)
        self.lblEditing.setObjectName(u"lblEditing")

        self.editorLayout.addWidget(self.lblEditing)

        self.editorBody = QHBoxLayout()
        self.editorBody.setSpacing(8)
        self.editorBody.setObjectName(u"editorBody")
        self.statementTree = StatementTree(self.editorPanel)
        self.statementTree.setObjectName(u"statementTree")
        self.statementTree.setMinimumSize(QSize(190, 0))
        self.statementTree.setMaximumSize(QSize(240, 16777215))

        self.editorBody.addWidget(self.statementTree)

        self.editorColumn = QVBoxLayout()
        self.editorColumn.setSpacing(8)
        self.editorColumn.setObjectName(u"editorColumn")
        self.blockEditor = BlockListEditor(self.editorPanel)
        self.blockEditor.setObjectName(u"blockEditor")

        self.editorColumn.addWidget(self.blockEditor)

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

        self.btnCloseEditor = QPushButton(self.editorPanel)
        self.btnCloseEditor.setObjectName(u"btnCloseEditor")

        self.editorToolbar.addWidget(self.btnCloseEditor)


        self.editorColumn.addLayout(self.editorToolbar)


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
        self.menuFile.addAction(self.actionNewFile)
        self.menuFile.addAction(self.actionImport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExportPython)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuEdit.addAction(self.actionNew)
        self.menuEdit.addAction(self.actionDelete)
        self.menuAction.addAction(self.actionSearch)
        self.menuAction.addAction(self.actionToggleEditor)
        self.menuAction.addAction(self.actionTheme)
        self.menuAction.addSeparator()
        self.menuAction.addAction(self.actionStart)
        self.menuAction.addAction(self.actionStop)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"HotKey - \u70ed\u952e\u5de5\u5177", None))
        self.actionNewFile.setText(QCoreApplication.translate("MainWindow", u"\u65b0\u5efa\u6587\u4ef6", None))
#if QT_CONFIG(shortcut)
        self.actionNewFile.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+N", None))
#endif // QT_CONFIG(shortcut)
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58", None))
#if QT_CONFIG(shortcut)
        self.actionSave.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionTheme.setText(QCoreApplication.translate("MainWindow", u"\u6df1\u8272\u6a21\u5f0f", None))
        self.actionImport.setText(QCoreApplication.translate("MainWindow", u"\u6253\u5f00\u6587\u4ef6...", None))
#if QT_CONFIG(shortcut)
        self.actionImport.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"\u53e6\u5b58\u4e3a...", None))
#if QT_CONFIG(shortcut)
        self.actionExport.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+S", None))
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
        self.btnNewFile.setText(QCoreApplication.translate("MainWindow", u"+", None))
#if QT_CONFIG(tooltip)
        self.btnNewFile.setToolTip(QCoreApplication.translate("MainWindow", u"\u65b0\u5efa\u70ed\u952e\u6587\u4ef6", None))
#endif // QT_CONFIG(tooltip)
        self.searchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u70ed\u952e...", None))
        self.lblEditing.setText(QCoreApplication.translate("MainWindow", u"\u64cd\u4f5c\u7f16\u8f91", None))
        self.btnCapturePos.setText(QCoreApplication.translate("MainWindow", u"\U0001f3af \U0000590d\U00005236\U00005750\U00006807", None))
        self.btnCaptureColor.setText(QCoreApplication.translate("MainWindow", u"\U0001f58d \U0000590d\U00005236\U0000989c\U00008272", None))
        self.btnScreenSize.setText(QCoreApplication.translate("MainWindow", u"\U0001f4d0 \U0000590d\U00005236\U00005c3a\U00005bf8", None))
        self.btnRunOnce.setText(QCoreApplication.translate("MainWindow", u"\u8bd5\u8fd0\u884c", None))
        self.btnExportPython.setText(QCoreApplication.translate("MainWindow", u"\u751f\u6210 .py", None))
        self.btnSaveScript.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58", None))
        self.btnCloseEditor.setText(QCoreApplication.translate("MainWindow", u"\u5173\u95ed", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"\u6587\u4ef6", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"\u7f16\u8f91", None))
        self.menuAction.setTitle(QCoreApplication.translate("MainWindow", u"\u64cd\u4f5c", None))
    # retranslateUi


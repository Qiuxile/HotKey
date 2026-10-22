# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hotkey_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QKeySequenceEdit, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_HotKeyDialog(object):
    def setupUi(self, HotKeyDialog):
        if not HotKeyDialog.objectName():
            HotKeyDialog.setObjectName(u"HotKeyDialog")
        HotKeyDialog.resize(380, 190)
        HotKeyDialog.setMinimumSize(QSize(360, 180))
        self.dialogLayout = QVBoxLayout(HotKeyDialog)
        self.dialogLayout.setSpacing(8)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.dialogLayout.setContentsMargins(14, 14, 14, 14)
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.lblKey = QLabel(HotKeyDialog)
        self.lblKey.setObjectName(u"lblKey")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblKey)

        self.keySequenceEdit = QKeySequenceEdit(HotKeyDialog)
        self.keySequenceEdit.setObjectName(u"keySequenceEdit")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.keySequenceEdit)

        self.lblDescription = QLabel(HotKeyDialog)
        self.lblDescription.setObjectName(u"lblDescription")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblDescription)

        self.descriptionEdit = QLineEdit(HotKeyDialog)
        self.descriptionEdit.setObjectName(u"descriptionEdit")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.descriptionEdit)


        self.dialogLayout.addLayout(self.formLayout)

        self.hintLabel = QLabel(HotKeyDialog)
        self.hintLabel.setObjectName(u"hintLabel")
        self.hintLabel.setWordWrap(True)

        self.dialogLayout.addWidget(self.hintLabel)

        self.dialogSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dialogLayout.addItem(self.dialogSpacer)

        self.buttonBox = QDialogButtonBox(HotKeyDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(HotKeyDialog)

        QMetaObject.connectSlotsByName(HotKeyDialog)
    # setupUi

    def retranslateUi(self, HotKeyDialog):
        HotKeyDialog.setWindowTitle(QCoreApplication.translate("HotKeyDialog", u"\u70ed\u952e", None))
        self.lblKey.setText(QCoreApplication.translate("HotKeyDialog", u"\u70ed\u952e\uff1a", None))
#if QT_CONFIG(tooltip)
        self.keySequenceEdit.setToolTip(QCoreApplication.translate("HotKeyDialog", u"\u70b9\u51fb\u540e\u6309\u4e0b\u7ec4\u5408\u952e\uff0c\u4f8b\u5982 Ctrl+Shift+A", None))
#endif // QT_CONFIG(tooltip)
        self.lblDescription.setText(QCoreApplication.translate("HotKeyDialog", u"\u63cf\u8ff0\uff1a", None))
        self.descriptionEdit.setPlaceholderText(QCoreApplication.translate("HotKeyDialog", u"\u8fd9\u4e2a\u70ed\u952e\u505a\u4ec0\u4e48", None))
        self.hintLabel.setText(QCoreApplication.translate("HotKeyDialog", u"\u63d0\u793a\uff1a\u53ea\u652f\u6301\u5355\u4e2a\u7ec4\u5408\u952e\uff1b\u5f55\u5236 Win \u7ec4\u5408\u952e\u65f6\u7cfb\u7edf\u53ef\u80fd\u4f1a\u540c\u65f6\u54cd\u5e94\u3002", None))
    # retranslateUi


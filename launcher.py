# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from remover.dogdrip import DogdripRemover
from toollib.logger import Logger
import threading

class Ui_MainWindow(object):

    def __init__(self, remover=None):
        self.dogdrip = DogdripRemover()
        self.isLoggedIn = None

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(960, 540)
        MainWindow.setMinimumSize(QtCore.QSize(960, 540))
        MainWindow.setMaximumSize(QtCore.QSize(960, 540))
        MainWindow.setWindowOpacity(1.0)
        MainWindow.setToolTipDuration(1)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.loginId = QtWidgets.QLineEdit(self.centralwidget)
        self.loginId.setGeometry(QtCore.QRect(45, 5, 110, 21))
        self.loginId.setObjectName("loginId")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(5, 5, 40, 21))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(160, 5, 60, 21))
        self.label_2.setObjectName("label_2")
        self.loginPw = QtWidgets.QLineEdit(self.centralwidget)
        self.loginPw.setGeometry(QtCore.QRect(210, 5, 110, 21))
        self.loginPw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.loginPw.setObjectName("loginPw")
        self.linkUrl = QtWidgets.QLabel(self.centralwidget)
        self.linkUrl.setGeometry(QtCore.QRect(850, 520, 100, 20))
        self.linkUrl.setToolTip("")
        self.linkUrl.setToolTipDuration(-1)
        self.linkUrl.setOpenExternalLinks(True)
        self.linkUrl.setObjectName("linkUrl")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(5, 520, 511, 20))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.loginBtn = QtWidgets.QPushButton(self.centralwidget)
        self.loginBtn.setGeometry(QtCore.QRect(325, 5, 51, 21))
        self.loginBtn.setObjectName("loginBtn")
        self.loginBtn.clicked.connect(self.login)
        self.collectDataBtn = QtWidgets.QPushButton(self.centralwidget)
        self.collectDataBtn.setGeometry(QtCore.QRect(380, 5, 111, 21))
        self.collectDataBtn.setObjectName("collectDataBtn")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 960, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "개드립 Dogdrip.net 댓글/게시글 일괄 삭제프로그램 v 0.1"))
        self.loginId.setPlaceholderText(_translate("MainWindow", "ID"))
        self.label.setText(_translate("MainWindow", "아이디"))
        self.label_2.setText(_translate("MainWindow", "비밀번호"))
        self.loginPw.setPlaceholderText(_translate("MainWindow", "Password"))
        self.linkUrl.setText(_translate("MainWindow", "<a href=\"https://github.com/luiseok/dogdrip_remover\">Github - Source</a>"))
        self.label_3.setToolTip(_translate("MainWindow", "진짜로 수집하지 않습니다 ㅠ"))
        self.label_3.setText(_translate("MainWindow", "개드립 리무버에 입력되는 계정정보는 제 3의 서버로 전송하거나 수집하는 행위를 절대 하지 않습니다."))
        self.loginBtn.setText(_translate("MainWindow", "로그인"))
        self.collectDataBtn.setText(_translate("MainWindow", "삭제할 데이터 수집"))

    def login(self):
        # thread = threading.Thread(target=self.dogdrip.login, args=(self.loginId.text(), self.loginPw.text()))
        # thread.start()
        self.isLoggedIn = self.dogdrip.login(user_id=self.loginId.text(), password=self.loginPw.text())
        if self.isLoggedIn:
            self.loginBtn.setDisabled(True)
            self.loginId.setDisabled(True)
            self.loginPw.setDisabled(True)
        else:
            self.loginBtn.setDisabled(False)
            self.loginId.setDisabled(False)
            self.loginPw.setDisabled(False)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
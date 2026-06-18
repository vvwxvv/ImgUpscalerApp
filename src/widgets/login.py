
import sys
import hashlib
import secrets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QCursor
from src.uiitems.blink_button import BlinkingButton
from src.uiitems.notification_bar import NotificationBar
import subprocess
import os

def generate_salt():
    return secrets.token_hex(16)

def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest()

# Original password setup
PASSWORD_SALT = generate_salt()
PASSWORD_HASH = hash_password('goodday', PASSWORD_SALT)  # Changed from 'wx831218' to 'goodday'


class FrostedGlassWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.oldPos = self.pos()
        self.notification_bar = None

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 600, 500)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        self.central_widget.setStyleSheet("background-color: rgba(255, 255, 255, 180); border-radius: 20px;")

        self.title = QLabel("Login to Application", self)
        self.title.setFont(QFont('Arial', 16))
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.layout.addWidget(self.password_input)

        self.login_button = BlinkingButton("Login", self)
        self.login_button.clicked.connect(self.login)
        self.layout.addWidget(self.login_button)

        self.reset_button = BlinkingButton("Reset Password", self)
        self.reset_button.clicked.connect(self.reset_password)
        self.layout.addWidget(self.reset_button)
        self.reset_button.hide()  # Initially hidden, shown on hover

    def login(self):
        password = self.password_input.text()
        hashed_password = hash_password(password, PASSWORD_SALT)
        if hashed_password == PASSWORD_HASH:
            self.show_notification("Login successful!")
            self.open_main_application()  # Call to open the main application
        else:
            self.show_notification("Invalid password")

    def open_main_application(self):
        # Use subprocess to open main.py
        subprocess.Popen(["python", "main.py"])
        self.close()  # Optionally close the login window

    def reset_password(self):
        global PASSWORD_SALT, PASSWORD_HASH
        new_password = 'goodday'  # Change here if you want a different reset password
        PASSWORD_SALT = generate_salt()
        PASSWORD_HASH = hash_password(new_password, PASSWORD_SALT)
        self.show_notification(f"Password reset to '{new_password}'.")

    def show_notification(self, message):
        if self.notification_bar:
            self.notification_bar.hide()
        self.notification_bar = NotificationBar(message, self)
        self.layout.insertWidget(0, self.notification_bar)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()


def start_login():
    app = QApplication(sys.argv)
    window = FrostedGlassWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FrostedGlassWindow()
    window.show()
    sys.exit(app.exec_())
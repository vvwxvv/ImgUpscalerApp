from PyQt5.QtWidgets import QPushButton, QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont

class BlinkingButton(QPushButton):
    def __init__(self, text, blink_color='pink', hover_color='pink', blink_interval=0, parent=None):
        super(BlinkingButton, self).__init__(text, parent)
        self.setFont(QFont('Arial', 14))
        self.blink_color = blink_color
        self.hover_color = hover_color
        self.default_style = f"""
            QPushButton {{
                color: #FFFFFF;
                background-color: rgba(255, 192, 203, 0.5);
                border: 2px solid {self.blink_color};
                border-radius: 20px;
            }}
        """
        self.setStyleSheet(self.default_style)
        self.blink_state = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.toggle_blink)
        self.timer.start(blink_interval)

    def toggle_blink(self):
        """ Toggle the blink state and update the button style accordingly. """
        self.blink_state = not self.blink_state
        color = self.blink_color if self.blink_state else '#FFFFFF'
        self.setStyleSheet(f"""
            QPushButton {{
                color: {color};
                background-color: transparent;
                border: 2px solid {color};
                border-radius: 20px;
            }}
        """)

    def enterEvent(self, event):
        """ Change button style on mouse hover. """
        self.setStyleSheet(f"""
            QPushButton {{
                color: #FFFFFF;
                background-color: {self.hover_color};
                border: 2px solid #FFFFFF;
                border-radius: 20px;
            }}
        """)

    def leaveEvent(self, event):
        """ Revert to the default style when the mouse leaves the button. """
        self.setStyleSheet(self.default_style)

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        button = BlinkingButton("Click Me!", parent=self)
        layout.addWidget(button)
        self.setLayout(layout)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
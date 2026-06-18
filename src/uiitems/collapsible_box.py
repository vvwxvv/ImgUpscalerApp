import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtCore import QParallelAnimationGroup, QPropertyAnimation, QSize


class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("QPushButton::checked { font-weight: bold; }")

        self.content_area = QScrollArea()
        self.content_area.setStyleSheet("QScrollArea { background-color: white; }")
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setMaximumHeight(0)  # Start with the content area collapsed
        self.content_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.toggle_animation = QParallelAnimationGroup(self)
        self.content_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.content_animation.setDuration(300)  # Animation duration

        self.toggle_animation.addAnimation(self.content_animation)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)

        self.toggle_button.toggled.connect(self.toggle)
        self.expanded = False  # To track the state of the box

    def setContentLayout(self, layout):
        self.content_area.setLayout(layout)
        self.layout_initial_height = (
            layout.sizeHint().height() + 2
        )  # Add a small buffer
        self.content_animation.setStartValue(0)
        self.content_animation.setEndValue(self.layout_initial_height)

    def toggle(self, checked):
        if self.expanded:
            self.content_animation.setDirection(QPropertyAnimation.Backward)
            self.expanded = False
        else:
            self.content_animation.setDirection(QPropertyAnimation.Forward)
            self.expanded = True
        self.toggle_animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    box = CollapsibleBox("Click Me!")
    layout = QVBoxLayout()
    layout.addWidget(QPushButton("Sample Button"))
    layout.addWidget(QPushButton("Another Button"))
    box.setContentLayout(layout)
    box.show()
    sys.exit(app.exec_())

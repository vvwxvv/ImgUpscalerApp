import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

# Assuming these imports are correctly set up in your project structure
from assets.bigger_image_processor import convert_to_png_and_optimize
from src.uiitems.custom_alert import CustomAlert
from src.uiitems.dash_line import DashedLine

class ImageResizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize_resize_folder_path = None
        self.initUI()

    def initUI(self):
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Dashed line widgets
        dashline_1 = DashedLine(color='pink', orientation='horizontal')
        dashline_2 = DashedLine(color='pink', orientation='horizontal')
        layout.addWidget(dashline_1)

        # Select folder button
        self.btn_select_folder = QPushButton('Choose Imgs Folder to Shrink', self)
        self.btn_select_folder.setStyleSheet("""
            QPushButton {
                color: pink;
                background-color: transparent;
                font-size: 15px;
                text-decoration: underline;
                border: none;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.btn_select_folder.clicked.connect(self.open_resize_folder_dialog)
        layout.addWidget(self.btn_select_folder)

        # Resize button
        self.btn_resize = QPushButton('Shrink Now', self)
        self.btn_resize.setStyleSheet("""
            QPushButton {
                color: pink;
                background-color: transparent;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                border: 2px solid pink;
                text-align: center;
            }
            QPushButton:hover {
                background-color: lightpink;
            }
        """)
        self.btn_resize.clicked.connect(self.resize_images)
        self.btn_resize.setEnabled(False)  # Initially disabled
        layout.addWidget(self.btn_resize)

        layout.addWidget(dashline_2)

        # Set layout and window properties
        self.setLayout(layout)
        self.setWindowTitle('Img Shrink')
        self.setGeometry(300, 300, 300, 150)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid pink;
            }
        """)

    def open_resize_folder_dialog(self):
        resize_folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if resize_folder_path:
            self.resize_folder_path = resize_folder_path
            self.btn_resize.setEnabled(True)
        else:
            self.btn_resize.setEnabled(False)

    def resize_images(self):
        if self.resize_folder_path:
            try:
                convert_to_png_and_optimize(self.resize_folder_path, target_size_kb=700)
                self.show_completion_alert('Images have been resized successfully!')
            except Exception as e:
                self.show_completion_alert(f"An error occurred: {str(e)}", error=True)

    def show_completion_alert(self, message, error=False):
        alert = CustomAlert(self)
        if error:
            alert.set_error_message(message)
        else:
            alert.set_success_message(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageResizerWidget()
    ex.show()
    sys.exit(app.exec_())
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from src.assets.rename_files import rename_files_with_subfolder_name
from src.uiitems.custom_alert import CustomAlert
from src.uiitems.dash_line import DashedLine

class ImageRenamerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rename_folder_path = None
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
        self.rename_btn_select_folder = QPushButton('Choose Imgs Folder to Rename', self)
        self.rename_btn_select_folder.setStyleSheet("""
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
        self.rename_btn_select_folder.clicked.connect(self.open_rename_dialog)
        layout.addWidget(self.rename_btn_select_folder)

        # Resize button
        self.btn_rename = QPushButton('Re-Name Now', self)
        self.btn_rename.setStyleSheet("""
            color: pink;
            background-color: transparent;
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            border-radius: 10px;
            border: 2px solid pink;
            text-align: center;
        """)
        self.btn_rename.clicked.connect(self.rename_images)
        self.btn_rename.setEnabled(False)  # Initially disabled
        layout.addWidget(self.btn_rename)

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

    def open_rename_dialog(self):
        rename_folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if rename_folder_path:
            self.rename_folder_path = rename_folder_path
            self.btn_rename.setEnabled(True)
        else:
            self.btn_rename.setEnabled(False)

    def rename_images(self):
        if self.rename_folder_path:
            try:
                rename_files_with_subfolder_name(root_directory=self.rename_folder_path)
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
    ex = ImageRenamerWidget()
    ex.show()
    sys.exit(app.exec_())
from PyQt5.QtWidgets import QWidget, QPushButton, QLineEdit, QHBoxLayout, QFileDialog
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPalette, QColor

class FileInput(QWidget):
    fileSelected = pyqtSignal(str)

    def __init__(self, parent=None, placeholder="Select a file", dialog_title="Open file", 
                 initial_dir="/", file_filter="All files (*)", bgcolor=None):
        super().__init__(parent)
        self.dialog_title = dialog_title
        self.initial_dir = initial_dir
        self.file_filter = file_filter

        layout = QHBoxLayout(self)
        
        # Line Edit for displaying the file path
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        if bgcolor:
            # Set background color if specified
            self.set_background_color(bgcolor)
        
        # Button to trigger file dialog
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_file)
        
        # Add widgets to layout
        layout.addWidget(self.line_edit)
        layout.addWidget(btn_browse)

        # Styling the widgets
        self.apply_styling()

    def set_background_color(self, color):
        palette = QPalette()
        palette.setColor(QPalette.Base, QColor(color))
        self.line_edit.setPalette(palette)

    def apply_styling(self):
        # Example styling, can be customized further
        self.line_edit.setStyleSheet("QLineEdit { border: 2px solid gray; border-radius: 10px; padding: 0 8px; }")
        self.line_edit.setStyleSheet("QLineEdit { background-color: white; color: black; }")
        self.line_edit.setStyleSheet("QPushButton { border: 2px solid #8f8f91; border-radius: 6px; }")
        self.line_edit.setStyleSheet("QPushButton:pressed { background-color: #cccccc; }")

    def browse_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, self.dialog_title, self.initial_dir, self.file_filter)
        if fname:
            self.line_edit.setText(fname)
            self.fileSelected.emit(fname)  # Emitting signal with the selected file path
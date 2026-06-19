import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QApplication, QFileDialog, QPushButton
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import pyqtSignal
from src.uiitems.close_button import CloseButton
from src.uiitems.file_input import FileInput
from src.uiitems.blink_button import BlinkingButton  # Import the BlinkingButton


class SelectInitiationCSV(QWidget):
    csv_confirmed = pyqtSignal(object)  # Signal that emits CSV data

    def __init__(
            self, 
            on_confirm=None, 
            initial_dir=r"D:\CodingLab\Apps\TwoLanguageAppGenerator\static\data\users\initiation_json"
            ):
        super().__init__()
        self.on_confirm = on_confirm
        self.CSV_data = None  # Initialize CSV_data
        self.initial_dir = initial_dir  # Set the initial directory for browsing
        self.initUI()
        self.oldPos = None  # Initialize the old position for tracking window movement

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(200, 200, 800, 600)  # Adjusted window size for usability

        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Title bar with close button
        title_bar = QHBoxLayout()
        close_button = CloseButton()
        title_bar.addStretch(1)
        title_bar.addWidget(close_button)

        # File input and browse button
        file_input = FileInput(placeholder="Upload CSV File", dialog_title="Load CSV File",
                               initial_dir=self.initial_dir, file_filter="CSV files (*.csv)", bgcolor="pink")
        file_input.fileSelected.connect(self.preview_CSV)

        # CSV Preview Text Edit
        self.CSV_text_edit = QTextEdit()
        self.CSV_text_edit.setReadOnly(True)

        # Configure the folder path button
        self.folder_path_button = QPushButton("Set Folder Path")
        self.folder_path_button.clicked.connect(self.set_folder_path)

        # Confirm Button using BlinkingButton
        self.confirm_button = BlinkingButton("Confirm", blink_color="#FF69B4", hover_color="#FFB6C1")
        self.confirm_button.clicked.connect(self.confirm_CSV)

        main_layout.addLayout(title_bar)
        main_layout.addWidget(file_input)
        main_layout.addWidget(self.folder_path_button)
        main_layout.addWidget(self.CSV_text_edit)
        main_layout.addWidget(self.confirm_button)

        self.setLayout(main_layout)

    def confirm_CSV(self):
        if self.CSV_data:
            self.csv_confirmed.emit(self.CSV_data)
            if self.on_confirm:
                self.on_confirm(self.CSV_data)
            self.close()

    def preview_CSV(self, file_path):
        self.current_file_path = file_path
        with open(file_path, 'r',encoding='utf-8') as file:
            self.CSV_data = file.read()
            self.CSV_text_edit.setPlainText(self.CSV_data)

    def set_folder_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Select CSV Folder", self.initial_dir)
        if new_path:
            self.initial_dir = new_path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()


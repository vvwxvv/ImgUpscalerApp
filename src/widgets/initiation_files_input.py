import os
import json
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class InitiationSettingFilesInput(QLineEdit):
    schemaStructureSelected = pyqtSignal(str)  # Emit path for "schema_structure" JSON files
    titleYearSelected = pyqtSignal(str)        # Emit path for "title_year" CSV files
    initiationSettingsLoaded = pyqtSignal(dict) # Emit JSON data for "initiation_setting" JSON files

    def __init__(self, placeholder, bgcolor):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setStyleSheet(f"background-color: {bgcolor};")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return super().dropEvent(event)
        
        found_files = False
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isdir(file_path):
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        full_file_path = os.path.join(root, file)  # Combine root and file name
                        if self.processFile(full_file_path):       # Pass the full path to processFile
                            found_files = True
            else:
                if self.processFile(file_path):
                    found_files = True
    
        if not found_files:
            QMessageBox.warning(self, "No Relevant File Found", "No relevant JSON or CSV files found in the dropped items.")
            
    def processFile(self, file_path):
        file_name = os.path.basename(file_path)
        info = ""
        if "schema_structure" in file_name and file_path.lower().endswith('.json'):
            data = self.loadJsonData(file_path)
            if data:
                info = f"Schema Structure Loaded: {data} "
                self.schemaStructureSelected.emit(file_path)
                QMessageBox.information(self, "File Loaded", info)
                return True
        elif "title_year" in file_name and file_path.lower().endswith('.csv'):
            self.titleYearSelected.emit(file_path)
            return True
        elif "initiation_setting" in file_name and file_path.lower().endswith('.json'):
            data = self.loadJsonData(file_path)
            if data:
                info = f"Initiation Settings Loaded: {data} "
                self.initiationSettingsLoaded.emit(data)
                QMessageBox.information(self, "File Loaded", info)
                return True
        return False

    def loadJsonData(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            QMessageBox.warning(self, "Error Loading JSON", f"Failed to load JSON data from {file_path}: {str(e)}")
            return None
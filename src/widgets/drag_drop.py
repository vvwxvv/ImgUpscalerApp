import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Retrieve environment variables
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_DB = os.getenv('MONGO_DB', 'mydatabase')
MONGO_USER = os.getenv('MONGO_USER')
MONGO_PASS = os.getenv('MONGO_PASS')

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Drag and Drop JSON to MongoDB')
        self.setGeometry(400, 400, 300, 150)
        layout = QVBoxLayout()

        self.label = QLabel("Drag and drop a JSON file here", self)
        self.label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Enable dragging and dropping onto the GUI
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        file_path = event.mimeData().urls()[0].toLocalFile()
        self.insert_json_to_mongodb(file_path)
        self.label.setText(f"Processed: {file_path}")

    def insert_json_to_mongodb(self, file_path):
        # Use credentials to connect to MongoDB
        client = MongoClient(host=MONGO_HOST,
                             port=MONGO_PORT,
                             username=MONGO_USER,
                             password=MONGO_PASS)
        db = client[MONGO_DB]
        collection = db['mycollection']

        # Read and insert the JSON file
        with open(file_path, 'r',encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                collection.insert_many(data)
            else:
                collection.insert_one(data)
        print(f"Data from {file_path} has been inserted into MongoDB.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DragDropWidget()
    ex.show()
    sys.exit(app.exec_())
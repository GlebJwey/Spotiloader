from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui     import *
import sys

app = QApplication(sys.argv)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")
        self.setFixedSize(QSize(1000, 500))

        explorer = QFrame()
        status_frame = QFrame()
        exp_test = QLabel('file explorer', explorer)
        button = QPushButton("Press Me!", status_frame)
        file_explorer = QFileSelector(explorer)
        pre_input = QLabel('Ссылка на плейлист:')
        url = QLineEdit()
        pre_input_2 = QLabel('Папка сохранения:')
        dir_out = QLineEdit()
        dir_out_browse = QPushButton()

        explorer.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)

        directbox = QHBoxLayout()
        directbox.addWidget(pre_input_2)
        directbox.addWidget(dir_out)
        explorer.setLayout(directbox)

        fvbox = QVBoxLayout()
        fvbox.addWidget(pre_input)
        fvbox.addWidget(url)
        explorer.setLayout(fvbox)

        fhbox = QHBoxLayout()
        fhbox.addWidget(button)
        status_frame.setLayout(fhbox)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(explorer)
        splitter.addWidget(status_frame)

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(splitter)
        self.setCentralWidget(splitter)


win = MainWindow()
win.show()

app.exec()
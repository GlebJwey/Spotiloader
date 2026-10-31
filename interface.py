from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import sys

MIN_SIZE_X, MIN_SIZE_Y = 400, 200
MAX_SIZE_X, MAX_SIZE_Y = 1200, 600

FIXED_X, FIXED_Y = 1000, 500

MIN_SPLIT_RATIO = 0.5
MAX_SPLIT_RATIO = 1

app = QApplication(sys.argv)

class mainw(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Multisong loader')
        self.setFixedSize(QSize(FIXED_X, FIXED_Y))
        self.setMinimumSize(MIN_SIZE_X, MIN_SIZE_Y)
        self.setMaximumSize(MAX_SIZE_X, MAX_SIZE_Y)

        #_______________ Виджеты _______________
        url_text = QLabel("Ссылка на плейлист: ")
        url = QLineEdit(url_text)

        dir_text = QLabel("Папка для скачивания: ")
        dir_p = QLineEdit()
        dir_browse_button = QPushButton("Browse")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        # f = int(FIXED_X*100)
        splitter.setChildrenCollapsible(False)

        options = QFrame()
        # options.setMinimumSize(int(MIN_SIZE_X * MIN_SPLIT_RATIO), MIN_SIZE_Y)
        options.setMinimumSize(int(MIN_SIZE_X * MAX_SPLIT_RATIO), MIN_SIZE_Y)
        # options.setMaximumSize(int(MAX_SIZE_X * MAX_SPLIT_RATIO), MAX_SIZE_Y)
        options.setFrameShape(QFrame.Shape.StyledPanel)

        visuals = QFrame()
        visuals.setMinimumSize(int(MIN_SIZE_X * MIN_SPLIT_RATIO), MIN_SIZE_Y)
        # visuals.setMaximumSize(int(MAX_SIZE_X * MAX_SPLIT_RATIO), MAX_SIZE_Y)
        visuals.setFrameShape(QFrame.Shape.StyledPanel)

        
        #_______________ Бинды _______________
        self.dir_p = dir_p
        dir_browse_button.clicked.connect(self.browse_dir)

        #_______________ Сетка _______________
        url_hor = QHBoxLayout()
        url_hor.addWidget(url_text)
        url_hor.addWidget(url)

        dir_hor = QHBoxLayout()
        dir_hor.addWidget(dir_text)
        dir_hor.addWidget(dir_p)
        dir_hor.addWidget(dir_browse_button)

        ver = QVBoxLayout()
        ver.addLayout(url_hor)
        ver.addLayout(dir_hor)
        ver.setSpacing(10)
        ver.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        v_ver = QVBoxLayout()

        options.setLayout(ver)
        # visuals.setLayout(v_ver)

        splitter.addWidget(options)
        splitter.addWidget(visuals)
        splitter.setSizes([500, 500])
        self.setCentralWidget(splitter)

    def browse_dir(self):
        dir_browse = QFileDialog.getExistingDirectory(parent=self, caption="Выберите папку для загрузки", 
                                                      options=QFileDialog.Option.ShowDirsOnly)
        if dir_browse:
            self.dir_p.setText(dir_browse)


win = mainw()

win.show()
app.exec()
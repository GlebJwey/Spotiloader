from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import sys, logging, time, html, random

MIN_SIZE_X, MIN_SIZE_Y = 400, 200
MAX_SIZE_X, MAX_SIZE_Y = 1200, 600

FIXED_X, FIXED_Y = 1000, 500

FST_WIDTH_COEF    = 0.4
SEC_WIDTH_COEF    = 0.2
FST_HEIGHT_COEF   = 0.4
SEC_HEIGHT_COEF   = 0.1
START_WIDTH_COEF  = 0.6          # От FST
START_HEIGHT_COEF = 0.2          # От FST

app = QApplication(sys.argv)

def clear_layout(layout: QLayout, *args: int):
    """Clears the layout
    \n args - items exception index(es)"""
    # Проходим по всем элементам макета в обратном порядке
    for i in reversed(range(layout.count())):
        if i in args: continue
        item = layout.itemAt(i)
        widget = item.widget()  # Получаем виджет
        if type(widget) == QGroupBox:
            widget.hide()
            layout.removeWidget(widget)
            widget.setParent(None)
        else:
            if widget is not None:
                layout.removeWidget(widget)  # Планируем удаление
                widget.setParent(None)
        if item.spacerItem():
            layout.removeItem(item)
        if item.layout() is not None:
            # Если это вложенный макет, рекурсивно очистим его
            clear_layout(item)


class Worker(QThread):
    """Background download cycle process"""
    progress_changed = pyqtSignal(int) # Define signal

    def __init__(self, w: QMainWindow):
        super().__init__()
        self.w = w

    def run(self):
        i = self.w.i
        while not self.isInterruptionRequested() and i != self.w.goal:
            self.w.logger.info(f"Step {i+1}")
            time.sleep(0.2)
            i += 1
            self.w.i = i

            self.progress_changed.emit(i)
            self.w.progress_bar.update()
            self.w.progress_stage.setText(f"{i}/{self.w.goal}")

        if i == self.w.goal:
            self.w.i = 0
            self.w.pause_btn.setDisabled(True)
            self.w.logger.info("Done")         

class QtLogEmitter(QObject):
    message = pyqtSignal(str, int)


class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = QtLogEmitter()

    def emit(self, record):
        try:
            self.emitter.message.emit(self.format(record), record.levelno)
        except Exception:
            self.handleError(record)

class LogTextEdit(QTextEdit):
    """Built-in logging window"""
    COLORS = {
        logging.DEBUG: "#00B3FF",
        logging.INFO: "#d4d4d4",
        logging.WARNING: "#e5c07b",
        logging.ERROR: "#e06c75",
        logging.CRITICAL: "#ff3b3b",
    }

    def __init__(self, max_lines: int = 5000, parent=None):
        super().__init__(parent)

        # только просмотр, но с возможностью выделять и копировать
        self.setReadOnly(True)

        # моноширинный шрифт
        font = QFont("Consolas")  # на Linux/macOS подставится запасной
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)

        # без переноса строк, появится горизонтальная прокрутка
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # ограничение числа строк (у QTextEdit это через document())
        self.document().setMaximumBlockCount(max_lines)

        # тёмная тема
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
        self.setPalette(pal)

    def append_log(self, text: str, level: int = logging.INFO):
        color = self.COLORS.get(level, self.COLORS[logging.INFO])
        safe = html.escape(text).replace(" ", "&nbsp;")  # сохраняем пробелы

        # автоскролл только если пользователь уже внизу
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f'<span style="color:{color}">{safe}</span><br>')

        if at_bottom:
            bar.setValue(bar.maximum())

class ImageFrame(QFrame):
    """QFrame, scales an image to fit its own size, while maintaining the aspect ratio"""

    def __init__(self, image_path, parent=None):
        super().__init__(parent)

        self.original_pixmap = QPixmap(image_path)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)

        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        # Размер области под картинку с учётом рамки фрейма
        area = self.contentsRect().size()
        if area.isEmpty():
            return

        scaled = self.original_pixmap.scaled(
            area,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)   # обязательно вызвать родительский обработчик
        self._update_scaled_pixmap()

class mainw(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Multisong loader')
        self.setFixedSize(QSize(FIXED_X, FIXED_Y))
        self.setMinimumSize(MIN_SIZE_X, MIN_SIZE_Y)
        self.setMaximumSize(MAX_SIZE_X, MAX_SIZE_Y)

        self.worker, self.stop_event = None, None
        self.i, self.goal = 0, 0

        #_______________ Widgets _______________
        self.url = QLineEdit()

        self.dir_text = QLabel("Download folder: ")
        self.dir_p = QLineEdit()
        self.dir_browse_button = QPushButton("Browse")

        self.additional_options_menu = QGroupBox("Additional parameters")
        self.excepts_n_w = QLineEdit()
        self.excepts_a_w = QLineEdit()
        self.hard_excepts = QCheckBox("Hard exclusions")
        self.dw_ext = QComboBox()
        self.dw_ext.addItems(["mp3", "wav", "ogg", "opus", "flac", "alac", "m4a", "aac"])
        self.dw_ext.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.dw_format = QComboBox()
        self.dw_format.addItems(["Name - Artist(s)", "Artist(s) - Name"])
        self.dw_format.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.dwl = QLabel(f".{self.dw_ext.currentText()}")

        self.progress_label = QLabel("Progress: ")
        self.progress_bar = QProgressBar()
        self.progress_stage = QLabel("-/-")

        self.start_btn = QPushButton("Start")

        self.stop_btn = QPushButton("Stop")
        self.pause_btn = QPushButton("Pause")
        self.continue_btn = QPushButton("Continue")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.splitter = splitter

        visual_splitter = QSplitter(Qt.Orientation.Vertical)
        visual_splitter.setChildrenCollapsible(False)

        options = QFrame()
        options_min_size_x = int(self.width() * FST_WIDTH_COEF)
        options.setMinimumSize(options_min_size_x, MIN_SIZE_Y)
        options.setFrameShape(QFrame.Shape.StyledPanel)
        self.options = options

        visuals = QFrame()
        visuals_min_size_x = int(self.width() * SEC_WIDTH_COEF)
        visuals.setMinimumSize(visuals_min_size_x, MIN_SIZE_Y)
        visuals.setFrameShape(QFrame.Shape.StyledPanel)
        
        visuals_icon = ImageFrame('zero_image.svg.webp')
        visuals_icon.setMinimumSize(visuals_min_size_x, int(visuals.height() * FST_HEIGHT_COEF))
        
        visuals_stat = QFrame()
        visuals_stat.setFrameShape(QFrame.Shape.Panel)
        visuals_stat.setFrameShadow(QFrame.Shadow.Sunken)
        visuals_stat.setMinimumSize(visuals_min_size_x, int(visuals.height() * SEC_HEIGHT_COEF))

        self.log_view = LogTextEdit()

        # настройка логирования
        self.handler = QtLogHandler()
        self.handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        self.handler.emitter.message.connect(self.log_view.append_log)

        self.logger = logging.getLogger("app")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

        #_______________ Layout _______________
        self.url_hor = QFormLayout()
        self.dir_hor = QHBoxLayout()
        self.fln_hhor = QHBoxLayout()
        self.fln_hor = QHBoxLayout()
        self.additional_options_form = QFormLayout()
        self.additional_options_form.addRow(QLabel("Exclusions (write using spaces):"))       
        self.additional_options_form.addRow("By names: ", self.excepts_n_w)
        self.additional_options_form.addRow("By artists: ", self.excepts_a_w)
        self.additional_options_form.addRow(self.hard_excepts)
        self.fln_hhor.addWidget(self.dw_ext)
        self.fln_hhor.addStretch()
        self.fln_hor.addWidget(self.dw_format)
        self.fln_hor.addWidget(self.dwl)
        self.additional_options_form.addRow("File extension: ", self.fln_hhor)
        self.additional_options_form.addRow("File naming format: ", self.fln_hor)

        self.bottom_hor = QHBoxLayout()

        self.progress_hor = QHBoxLayout()
        self.bottom_active_hor = QHBoxLayout()
        self.ver = QVBoxLayout()

        self.main_menu()
        self.ver.setSpacing(10)

        visv = QVBoxLayout()

        visual_splitter.addWidget(visuals_icon)
        visual_splitter.addWidget(visuals_stat)

        horlzswc = int('1' + '0' * len(str(START_HEIGHT_COEF).split('.')[-1]))
        visual_splitter.setSizes([int(horlzswc*START_HEIGHT_COEF), horlzswc])

        visv.addWidget(visual_splitter)

        options.setLayout(self.ver)
        visuals.setLayout(visv)

        splitter.addWidget(options)
        splitter.addWidget(visuals)

        verlzswc = int('1' + '0' * len(str(START_WIDTH_COEF).split('.')[-1]))
        splitter.setSizes([verlzswc, int(verlzswc*START_WIDTH_COEF)])

        self.setCentralWidget(splitter)

        #_______________ Binds _______________
        self.dir_browse_button.clicked.connect(self.browse_dir)
        self.start_btn.clicked.connect(self.start_worker)
        self.stop_btn.clicked.connect(self.stop_worker)
        self.pause_btn.clicked.connect(self.pause_worker)
        self.continue_btn.clicked.connect(self.continue_worker)
        self.dw_ext.currentTextChanged.connect(self.on_dw_ext_changed)

    def main_menu(self):
        """Inits the main menu (options frame)"""
        clear_layout(self.ver)

        self.pause_btn.setDisabled(False)

        self.url_hor.addRow("Playlist URL: ", self.url)

        self.dir_hor.addWidget(self.dir_text)
        self.dir_hor.addWidget(self.dir_p)
        self.dir_hor.addWidget(self.dir_browse_button)

        self.additional_options_menu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.additional_options_menu.setLayout(self.additional_options_form)

        self.bottom_hor.addStretch()
        self.bottom_hor.addWidget(self.start_btn)

        self.ver.addLayout(self.url_hor)
        self.ver.addLayout(self.dir_hor)
        self.ver.insertWidget(2, self.additional_options_menu)
        self.additional_options_menu.show()
        self.ver.insertItem(3, QSpacerItem(0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))
        self.ver.addLayout(self.bottom_hor)

        # self.url_hor.setParent(self.ver)
        # self.dir_hor.setParent(self.ver)
        # self.bottom_hor.setParent(self.ver)

        
    def browse_dir(self):
        """Opens a folder catalog for browsing and choosing dir"""
        dir_browse = QFileDialog.getExistingDirectory(parent=self, caption="Select a folder for the download", 
                                                      options=QFileDialog.Option.ShowDirsOnly)
        if dir_browse:
            self.dir_p.setText(dir_browse)


    def start_worker(self):
        """Starts download and switches options frame to a logging window with a progress visualization"""
        self.goal = random.randint(25, 150)
        
        self.log_view.clear()
        clear_layout(self.ver)

        self.progress_bar.setRange(0, self.goal)
        self.progress_bar.setValue(0)
        self.progress_bar.setUpdatesEnabled(True)

        self.progress_hor.addWidget(self.progress_label)
        self.progress_hor.addWidget(self.progress_bar)
        self.progress_hor.addWidget(self.progress_stage)

        self.bottom_active_hor.addStretch()
        self.bottom_active_hor.addWidget(self.pause_btn)
        self.bottom_active_hor.addWidget(self.stop_btn)

        self.ver.addLayout(self.progress_hor)
        self.ver.addLayout(self.bottom_active_hor)
        self.ver.addWidget(self.log_view)

        # self.progress_hor.setParent(self.ver)
        # self.bottom_active_hor.setParent(self.ver)

        self.worker = Worker(self)
        self.worker.progress_changed.connect(self.progress_bar.setValue) 
        self.worker.start()

    def kill_worker(self):
        """Kills a background process"""
        if self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.quit()
            self.worker.wait()

    def stop_worker(self):
        """Stops the download and returns to the menu"""
        self.kill_worker()
        self.i = 0
        self.main_menu()

    def pause_worker(self):
        """Pauses the download"""
        self.bottom_active_hor.removeWidget(self.pause_btn)
        self.pause_btn.setParent(None)
        self.bottom_active_hor.insertWidget(1, self.continue_btn)

        self.logger.debug("Paused")
        self.kill_worker()


    def continue_worker(self):
        """Continues the download"""
        self.bottom_active_hor.removeWidget(self.continue_btn)
        self.continue_btn.setParent(None)
        self.bottom_active_hor.insertWidget(1, self.pause_btn)

        self.logger.debug("Continued")
        self.worker.start()
        
    def on_dw_ext_changed(self):
        self.dwl.setText(f".{self.dw_ext.currentText()}")

win = mainw()

win.show()
app.exec()
print('App closed')
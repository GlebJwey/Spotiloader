from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import sys, logging, time, html, random

MIN_SIZE_X, MIN_SIZE_Y = 800, 500
MAX_SIZE_X, MAX_SIZE_Y = None, None

FIXED_X, FIXED_Y = 1100, 550

FST_WIDTH_COEF    = 0.400
SEC_WIDTH_COEF    = 0.200
FST_HEIGHT_COEF   = 0.400
SEC_HEIGHT_COEF   = 0.100
START_WIDTH_COEF  = 0.675          # От FST
START_HEIGHT_COEF = 0.650          # От FST

app = QApplication(sys.argv)
screen = app.primaryScreen()
screen_size = screen.size()

def clear_layout(layout: QLayout, *keep: int):
    """Clears the layout
    \n args - items exception index(es)"""
    # Проходим по всем элементам макета в обратном порядке
    for i in reversed(range(layout.count())):
        if i in keep: continue
        item = layout.takeAt(i) # В отличие от itemAt(), takeAt() сам забирает элемент из лайаута, поэтому removeWidget() не обязателен
        widget = item.widget()  # Получаем виджет
        if item is None: continue
        if widget is not None:
            widget.setParent(None)
        if item.layout() is not None:
            # Если это вложенный макет, рекурсивно очистим его
            clear_layout(item)


class Worker(QThread):
    """Background download cycle process"""
    progress_changed = pyqtSignal(int) # Define signal
    done = pyqtSignal()

    def __init__(self, w: QMainWindow):
        super().__init__()
        self.w = w

    def run(self):
        i = self.w.i
        while not self.isInterruptionRequested() and i != self.w.goal:
            self.w.logger.info(f"Step {i+1}")
            self.msleep(200)
            i += 1
            self.w.i = i
            self.progress_changed.emit(i)

        if i == self.w.goal:  
            self.done.emit()    

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
        if FIXED_X and FIXED_Y:
            self.resize(QSize(FIXED_X, FIXED_Y))
        if MIN_SIZE_X and MIN_SIZE_Y:
            self.setMinimumSize(MIN_SIZE_X, MIN_SIZE_Y)
        if MAX_SIZE_X and MAX_SIZE_Y:
            self.setMaximumSize(MAX_SIZE_X, MAX_SIZE_Y)

        self.worker, self.stop_event = None, None
        self.i, self.goal = 0, 0

        #_______________ Widgets _______________
        # main parameters widgets
        self.url = QLineEdit()

        self.dir_text = QLabel("Download folder: ")
        self.dir_p = QLineEdit()
        self.dir_browse_button = QPushButton("Browse")
        # additional parameters widgets
        self.additional_options_menu = QGroupBox("Additional parameters")
        self.keep_tracks_buttons_group = QButtonGroup()

        self.keep_button = QRadioButton("Keep all")
        self.not_keep_button = QRadioButton("Delete all")
        self.keep_only_button = QRadioButton("Keep only with the extension")
        self.keep_button.setChecked(True)

        self.excepts_n_w = QTextEdit()
        self.excepts_a_w = QTextEdit()
        self.excepts_n_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.excepts_a_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hard_excepts = QCheckBox("Hard exclusions")

        self.dw_ext = QComboBox()
        self.dw_ext.addItems(["mp3", "wav", "ogg", "opus", "flac", "alac", "m4a", "aac"])
        self.dw_ext.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.dw_format = QComboBox()
        self.dw_format.addItems(["Name - Artist(s)", "Artist(s) - Name"])
        self.dw_format.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.dwl = QLabel(f".{self.dw_ext.currentText()}")

        self.do_naming = QCheckBox("Set track name")
        self.do_artists = QCheckBox("Set track artist(s)")
        self.do_icon_image = QCheckBox("Set track icon image")
        self.do_naming.setChecked(True)
        self.do_artists.setChecked(True)
        self.do_icon_image.setChecked(True)

        self.progress_label = QLabel("Progress: ")
        self.progress_bar = QProgressBar()
        self.progress_stage = QLabel("-/-")

        self.start_btn = QPushButton("Start")
        self.start_btn.setDisabled(True)

        self.stop_btn = QPushButton("Stop")
        self.pause_btn = QPushButton("Pause")
        self.continue_btn = QPushButton("Continue")
        # splitters
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.splitter = splitter

        visual_splitter = QSplitter(Qt.Orientation.Vertical)
        visual_splitter.setChildrenCollapsible(False)
        # frames
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
        visuals_icon_min_size_y = int(self.height() * FST_HEIGHT_COEF)
        visuals_icon.setMinimumSize(visuals_icon_min_size_y, int(visuals.height() * FST_HEIGHT_COEF))
        
        visuals_stat = QFrame()
        visuals_stat_min_size_y = int(self.height() * SEC_HEIGHT_COEF)
        visuals_stat.setFrameShape(QFrame.Shape.Panel)
        visuals_stat.setFrameShadow(QFrame.Shadow.Sunken)
        visuals_stat.setMinimumSize(visuals_stat_min_size_y, int(visuals.height() * SEC_HEIGHT_COEF))

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
        for index, btn in enumerate([self.keep_button, self.keep_only_button, self.not_keep_button], start=1):
            self.additional_options_form.addRow(btn)  # Add to visual layout
            self.keep_tracks_buttons_group.addButton(btn, index)  # Add to logical group with an ID 
               
        self.additional_options_form.addRow(self.create_separator())
        self.additional_options_form.addRow(QLabel("Exclusions (write using spaces):"))       
        self.additional_options_form.addRow("By names: ", self.excepts_n_w)
        self.additional_options_form.addRow("By artists: ", self.excepts_a_w)
        self.additional_options_form.addRow(self.hard_excepts)
        self.additional_options_form.addRow(self.create_separator())

        self.fln_hhor.addWidget(self.dw_ext)
        self.fln_hhor.addStretch()
        self.fln_hor.addWidget(self.dw_format)
        self.fln_hor.addWidget(self.dwl)

        self.additional_options_form.addRow("File extension: ", self.fln_hhor)
        self.additional_options_form.addRow("File naming format: ", self.fln_hor)
        self.additional_options_form.addRow(self.do_naming)
        self.additional_options_form.addRow(self.do_artists)
        self.additional_options_form.addRow(self.do_icon_image)

        self.bottom_hor = QHBoxLayout()

        self.progress_hor = QHBoxLayout()
        self.bottom_active_hor = QHBoxLayout()
        self.ver = QVBoxLayout()

        self.main_menu()
        self.ver.setSpacing(10)

        visv = QVBoxLayout()

        visual_splitter.addWidget(visuals_icon)
        visual_splitter.addWidget(visuals_stat)

        horlzswc = self.height()
        fst_start_height = int(horlzswc*START_HEIGHT_COEF)
        visual_splitter.setSizes([fst_start_height, horlzswc-fst_start_height])

        visv.addWidget(visual_splitter)

        options.setLayout(self.ver)
        visuals.setLayout(visv)

        splitter.addWidget(options)
        splitter.addWidget(visuals)

        verlzswc = self.width()
        fst_start_width = int(verlzswc*START_WIDTH_COEF)
        splitter.setSizes([fst_start_width, verlzswc-fst_start_width])

        self.setCentralWidget(splitter)

        #_______________ Binds _______________
        self.dir_browse_button.clicked.connect(self.browse_dir)
        self.start_btn.clicked.connect(self.start_worker)
        self.stop_btn.clicked.connect(self.stop_worker)
        self.pause_btn.clicked.connect(self.pause_worker)
        self.continue_btn.clicked.connect(self.continue_worker)
        self.url.textChanged.connect(self.on_url_dir_changed)
        self.dir_p.textChanged.connect(self.on_url_dir_changed)
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
        self.ver.insertItem(3, QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
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
        # clearing
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
        self.worker.progress_changed.connect(self.on_progress) 
        self.worker.done.connect(self.on_done)
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


    def on_url_dir_changed(self):
        if self.url.text() == "" or self.dir_p.text() == "":
            self.start_btn.setDisabled(True)
        else:
            self.start_btn.setDisabled(False)
        
    def on_dw_ext_changed(self):
        self.dwl.setText(f".{self.dw_ext.currentText()}")

    def on_progress(self, i):
        self.progress_bar.setValue(i)
        self.progress_bar.update()
        self.progress_stage.setText(f"{i}/{self.goal}")

    def on_done(self):
        self.i = 0
        self.bottom_active_hor.removeWidget(self.continue_btn)
        self.continue_btn.setParent(None)
        self.bottom_active_hor.insertWidget(1, self.pause_btn)
        self.continue_btn.setDisabled(True)
        self.pause_btn.setDisabled(True)
        self.logger.info("Done")


    def create_separator(self) -> QFrame:
        """Makes a separator, like in the QAction"""
        line = QFrame()
        # В PyQt6 используются полные имена перечислений (Enums)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

win = mainw()

avail = win.screen().availableGeometry()   # working area without taskbar

W = Qt.WindowType
flags = (W.Window | W.CustomizeWindowHint | W.WindowTitleHint |
         W.WindowSystemMenuHint | W.WindowMinimizeButtonHint |
         W.WindowCloseButtonHint | W.WindowMaximizeButtonHint)
if MAX_SIZE_X and MAX_SIZE_Y and not avail.width() <= MAX_SIZE_X and not avail.height() <= MAX_SIZE_Y:
    flags = (W.Window | W.CustomizeWindowHint | W.WindowTitleHint |
         W.WindowSystemMenuHint | W.WindowMinimizeButtonHint |
         W.WindowCloseButtonHint)

win.setWindowFlags(flags)   # before show()
win.show()
app.exec()
print('App closed')
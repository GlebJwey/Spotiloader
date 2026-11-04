from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import sys, logging, time, threading, html

MIN_SIZE_X, MIN_SIZE_Y = 400, 200
MAX_SIZE_X, MAX_SIZE_Y = 1200, 600

FIXED_X, FIXED_Y = 1000, 500

FST_WIDTH_COEF = 0.4
SEC_WIDTH_COEF = 0.2
FST_HEIGHT_COEF = 0.4
SEC_HEIGHT_COEF = 0.1
START_WIDTH_COEF = 0.6          # От FST

app = QApplication(sys.argv)

def clear_layout(layout, *args):
    # Проходим по всем элементам макета в обратном порядке
    for i in reversed(range(layout.count())):
        if i in args: continue
        item = layout.itemAt(i)
        widget = item.widget()  # Получаем виджет
        if widget is not None:
            layout.removeWidget(widget)  # Планируем удаление
            widget.setParent(None)
        elif type(item) == QSpacerItem:
            layout.removeItem(item)
        else:
            # Если это вложенный макет, рекурсивно очистим его
            clear_layout(item)


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
    COLORS = {
        logging.DEBUG: "#888888",
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
    """Фрейм, который масштабирует изображение под свой размер,
    сохраняя соотношение сторон."""

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

        #_______________ Виджеты _______________
        url_text = QLabel("Ссылка на плейлист: ")
        url = QLineEdit(url_text)
        self.url_text, self.url = url_text, url

        dir_text = QLabel("Папка для скачивания: ")
        self.dir_p = dir_text
        dir_p = QLineEdit()
        self.dir_p = dir_p
        dir_browse_button = QPushButton("Browse")

        progress_label = QLabel("Прогресс: ")

        start_btn = QPushButton("Start")

        stop_btn = QPushButton("Stop")
        pause_btn = QPushButton("Pause")
        continue_btn = QPushButton("Continue")
        self.pause_btn, self.continue_btn = pause_btn, continue_btn

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

        #_______________ Бинды _______________
        dir_browse_button.clicked.connect(self.browse_dir)
        start_btn.clicked.connect(self.start_worker)
        # stop_btn.clicked.connect(self.__init__())
        pause_btn.clicked.connect(self.pause_worker)
        continue_btn.clicked.connect(self.continue_worker)

        #_______________ Сетка _______________
        url_hor = QHBoxLayout()
        url_hor.addWidget(url_text)
        url_hor.addWidget(url)
        self.url_hor = url_hor

        dir_hor = QHBoxLayout()
        dir_hor.addWidget(dir_text)
        dir_hor.addWidget(dir_p)
        dir_hor.addWidget(dir_browse_button)
        self.dir_hor = dir_hor

        bottom_hor = QHBoxLayout()
        bottom_hor.addStretch()
        bottom_hor.addWidget(start_btn)
        self.bottom_hor = bottom_hor

        progress_hor = QHBoxLayout()
        progress_hor.addWidget(progress_label)
        self.progress_hor = progress_hor

        bottom_active_hor = QHBoxLayout()
        bottom_active_hor.addStretch()
        bottom_active_hor.addWidget(self.pause_btn)
        bottom_active_hor.addWidget(stop_btn)
        self.bottom_active_hor = bottom_active_hor

        ver = QVBoxLayout()
        ver.addLayout(self.url_hor)
        ver.addLayout(self.dir_hor)
        ver.addStretch()
        ver.addLayout(bottom_hor)
        ver.setSpacing(10)
        self.ver = ver

        visv = QVBoxLayout(visuals)
        visv.addWidget(visual_splitter)

        visual_splitter.addWidget(visuals_icon)
        visual_splitter.addWidget(visuals_stat)

        options.setLayout(self.ver)
        visuals.setLayout(visv)
        splitter.addWidget(options)
        splitter.addWidget(visuals)
        lzswc = int('1' + '0' * len(str(START_WIDTH_COEF).split('.')[-1]))
        splitter.setSizes([lzswc, int(lzswc*START_WIDTH_COEF)])
        self.setCentralWidget(splitter)

    def browse_dir(self):
        dir_browse = QFileDialog.getExistingDirectory(parent=self, caption="Выберите папку для загрузки", 
                                                      options=QFileDialog.Option.ShowDirsOnly)
        if dir_browse:
            self.dir_p.setText(dir_browse)

    def start_worker(self):
        clear_layout(self.ver)
        self.ver.addLayout(self.progress_hor)
        self.ver.addWidget(self.log_view)
        self.ver.addLayout(self.bottom_active_hor)
        threading.Thread(target=self.work, daemon=True).start()

    def pause_worker(self):
        self.bottom_active_hor.removeWidget(self.pause_btn)
        self.pause_btn.setParent(None)
        self.bottom_active_hor.insertWidget(1, self.continue_btn)

    def continue_worker(self):
        self.bottom_active_hor.removeWidget(self.continue_btn)
        self.continue_btn.setParent(None)
        self.bottom_active_hor.insertWidget(1, self.pause_btn)

    def work(self):
        for i in range(100):
            self.logger.info(f"Step {i}")
            time.sleep(0.2)
        self.logger.warning("Done")


win = mainw()

win.show()
app.exec()
print('закрыто')
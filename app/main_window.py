from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QFileDialog,
    QPlainTextEdit,
    QComboBox,
    QMessageBox,
    QProgressBar,
    QGroupBox
)

from core.pipeline import build_video


class VideoWorker(QThread):
    progress = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        sources,
        text,
        output_path,
        voice,
        orientation
    ):
        super().__init__()

        self.sources = sources
        self.text = text
        self.output_path = output_path
        self.voice = voice
        self.orientation = orientation

    def run(self):
        try:
            result = build_video(
                sources=self.sources,
                text=self.text,
                output_path=self.output_path,
                voice_name=self.voice,
                orientation=self.orientation,
                progress_callback=self.progress.emit
            )

            self.done.emit(str(result))

        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoVideoLocal")
        self.resize(850, 750)

        self.sources = []
        self.output_path = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setSpacing(12)

        title = QLabel("AUTO VIDEO LOCAL")
        title.setStyleSheet(
            "font-size: 25px; font-weight: bold;"
        )

        layout.addWidget(title)

        description = QLabel(
            "Tự động ghép video và tạo giọng đọc tiếng Việt"
        )

        layout.addWidget(description)

        # SOURCE VIDEO
        source_group = QGroupBox("1. Video source")
        source_layout = QVBoxLayout(source_group)

        self.video_list = QListWidget()
        source_layout.addWidget(self.video_list)

        buttons = QHBoxLayout()

        add_btn = QPushButton("Thêm video")
        remove_btn = QPushButton("Xóa")
        up_btn = QPushButton("Lên")
        down_btn = QPushButton("Xuống")

        add_btn.clicked.connect(self.add_videos)
        remove_btn.clicked.connect(self.remove_video)
        up_btn.clicked.connect(self.move_up)
        down_btn.clicked.connect(self.move_down)

        buttons.addWidget(add_btn)
        buttons.addWidget(remove_btn)
        buttons.addWidget(up_btn)
        buttons.addWidget(down_btn)

        source_layout.addLayout(buttons)
        layout.addWidget(source_group)

        # SCRIPT
        script_group = QGroupBox("2. Nội dung giọng đọc")
        script_layout = QVBoxLayout(script_group)

        self.script_input = QPlainTextEdit()
        self.script_input.setPlaceholderText(
            "Nhập nội dung tiếng Việt muốn đọc..."
        )

        self.script_input.setMinimumHeight(140)

        script_layout.addWidget(self.script_input)
        layout.addWidget(script_group)

        # SETTINGS
        settings_group = QGroupBox("3. Cấu hình")
        settings_layout = QHBoxLayout(settings_group)

        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "Nữ - Hoài My",
            "Nam - Minh"
        ])

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem(
            "Video dọc 9:16",
            "portrait"
        )
        self.orientation_combo.addItem(
            "Video ngang 16:9",
            "landscape"
        )

        settings_layout.addWidget(
            QLabel("Giọng đọc:")
        )
        settings_layout.addWidget(
            self.voice_combo
        )

        settings_layout.addWidget(
            QLabel("Định dạng:")
        )
        settings_layout.addWidget(
            self.orientation_combo
        )

        layout.addWidget(settings_group)

        # OUTPUT
        output_layout = QHBoxLayout()

        self.output_label = QLabel(
            "Chưa chọn vị trí lưu"
        )

        output_btn = QPushButton("Chọn nơi lưu")
        output_btn.clicked.connect(self.select_output)

        output_layout.addWidget(self.output_label)
        output_layout.addWidget(output_btn)

        layout.addLayout(output_layout)

        # GENERATE
        self.generate_btn = QPushButton(
            "BẮT ĐẦU DỰNG VIDEO"
        )

        self.generate_btn.setMinimumHeight(48)

        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #16845D;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }

            QPushButton:disabled {
                background-color: #777777;
            }
        """)

        self.generate_btn.clicked.connect(
            self.start_render
        )

        layout.addWidget(self.generate_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()

        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Sẵn sàng.")
        layout.addWidget(self.status_label)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        layout.addWidget(self.log)

        self.setCentralWidget(root)

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn video source",
            "",
            "Video (*.mp4 *.mov *.mkv *.avi *.webm)"
        )

        for file in files:
            if file not in self.sources:
                self.sources.append(file)

        self.refresh_list()

    def refresh_list(self):
        self.video_list.clear()

        for index, path in enumerate(self.sources):
            self.video_list.addItem(
                f"{index + 1}. {Path(path).name}"
            )

    def remove_video(self):
        index = self.video_list.currentRow()

        if index >= 0:
            self.sources.pop(index)
            self.refresh_list()

    def move_up(self):
        index = self.video_list.currentRow()

        if index > 0:
            self.sources[index - 1], self.sources[index] = (
                self.sources[index],
                self.sources[index - 1]
            )

            self.refresh_list()
            self.video_list.setCurrentRow(index - 1)

    def move_down(self):
        index = self.video_list.currentRow()

        if 0 <= index < len(self.sources) - 1:
            self.sources[index], self.sources[index + 1] = (
                self.sources[index + 1],
                self.sources[index]
            )

            self.refresh_list()
            self.video_list.setCurrentRow(index + 1)

    def select_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu video",
            "final_video.mp4",
            "MP4 Video (*.mp4)"
        )

        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"

            self.output_path = path
            self.output_label.setText(path)

    def start_render(self):
        if not self.sources:
            QMessageBox.warning(
                self,
                "Thiếu video",
                "Hãy chọn ít nhất một video source."
            )
            return

        text = self.script_input.toPlainText().strip()

        if not text:
            QMessageBox.warning(
                self,
                "Thiếu nội dung",
                "Hãy nhập nội dung giọng đọc."
            )
            return

        if not self.output_path:
            QMessageBox.warning(
                self,
                "Thiếu đường dẫn",
                "Hãy chọn nơi lưu video."
            )
            return

        if Path(self.output_path).exists():
            reply = QMessageBox.question(
                self,
                "Ghi đè video",
                "File đã tồn tại. Bạn có muốn ghi đè?"
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        self.generate_btn.setEnabled(False)
        self.progress_bar.show()

        self.log.clear()
        self.status_label.setText("Đang xử lý...")

        self.worker = VideoWorker(
            sources=self.sources.copy(),
            text=text,
            output_path=self.output_path,
            voice=self.voice_combo.currentText(),
            orientation=self.orientation_combo.currentData()
        )

        self.worker.progress.connect(
            self.update_status
        )

        self.worker.done.connect(
            self.render_success
        )

        self.worker.failed.connect(
            self.render_failed
        )

        self.worker.start()

    def update_status(self, message):
        self.status_label.setText(message)
        self.log.appendPlainText(message)

    def render_success(self, path):
        self.progress_bar.hide()
        self.generate_btn.setEnabled(True)

        self.status_label.setText(
            "Hoàn thành!"
        )

        self.log.appendPlainText(
            f"Video đã lưu tại: {path}"
        )

        QMessageBox.information(
            self,
            "Thành công",
            f"Đã tạo video thành công:\n{path}"
        )

    def render_failed(self, error):
        self.progress_bar.hide()
        self.generate_btn.setEnabled(True)

        self.status_label.setText(
            "Có lỗi khi dựng video."
        )

        self.log.appendPlainText(error)

        QMessageBox.critical(
            self,
            "Lỗi xử lý",
            error
        )
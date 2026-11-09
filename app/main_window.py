from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.app_errors import PipelineError
from core.pipeline import build_video
from core.usage_store import get_usage_summary


THEME_COLORS = {
    "dark": {
        "window": "#0B1220",
        "surface": "#151F2E",
        "surface_alt": "#1B293A",
        "input": "#0F1927",
        "border": "#2B3A4D",
        "border_hover": "#42566E",
        "border_focus": "#34B887",
        "text": "#EDF3FA",
        "muted": "#A3B1C2",
        "subtle": "#718198",
        "accent": "#15966A",
        "accent_hover": "#1BAC7A",
        "accent_pressed": "#117B57",
        "accent_text": "#FFFFFF",
        "selection": "#214C40",
        "success_bg": "#173D32",
        "success_text": "#91E3BF",
        "busy_bg": "#49391D",
        "busy_text": "#FFDA91",
        "danger": "#F0787E",
        "scroll": "#3B4D63",
    },
    "light": {
        "window": "#F3F6FA",
        "surface": "#FFFFFF",
        "surface_alt": "#F7F9FC",
        "input": "#FFFFFF",
        "border": "#DCE4ED",
        "border_hover": "#B7C6D6",
        "border_focus": "#16845D",
        "text": "#172536",
        "muted": "#5F6F82",
        "subtle": "#8492A3",
        "accent": "#16845D",
        "accent_hover": "#11734F",
        "accent_pressed": "#0E6042",
        "accent_text": "#FFFFFF",
        "selection": "#DDF2E9",
        "success_bg": "#E5F5ED",
        "success_text": "#176B4D",
        "busy_bg": "#FFF2D9",
        "busy_text": "#8A5A08",
        "danger": "#B4232C",
        "scroll": "#C5D0DC",
    },
}


def build_stylesheet(theme: str) -> str:
    c = THEME_COLORS[theme]
    template = """
    QMainWindow, QWidget#root {
        background: $window;
        color: $text;
        font-family: "Segoe UI";
        font-size: 10pt;
    }
    QWidget { outline: none; }
    QScrollArea { border: none; background: transparent; }
    QWidget#scrollContent { background: transparent; }
    QFrame#topHeader, QFrame#footerCard, QFrame#card {
        background: $surface;
        border: 1px solid $border;
        border-radius: 15px;
    }
    QFrame#topHeader {
        border-top: 3px solid $accent;
    }
    QFrame#card {
        background: $surface;
    }
    QLabel#eyebrow {
        color: $accent;
        font-size: 8pt;
        font-weight: 800;
        letter-spacing: 1.4px;
    }
    QLabel#appTitle {
        color: $text;
        font-size: 23pt;
        font-weight: 800;
    }
    QLabel#appSubtitle, QLabel#helper, QLabel#muted {
        color: $muted;
    }
    QLabel#appSubtitle { font-size: 9.5pt; }
    QLabel#helper { font-size: 9pt; }
    QLabel#sectionTitle {
        color: $text;
        font-size: 11pt;
        font-weight: 750;
    }
    QLabel#fieldLabel {
        color: $text;
        font-weight: 700;
        padding-top: 3px;
    }
    QLabel#statusBadge {
        border-radius: 9px;
        padding: 8px 12px;
        font-size: 8pt;
        font-weight: 800;
        background: $success_bg;
        color: $success_text;
    }
    QLabel#statusBadge[state="processing"] {
        background: $busy_bg;
        color: $busy_text;
    }
    QLabel#statusMessage {
        color: $text;
        font-weight: 700;
    }
    QLabel#usageLabel { color: $text; font-size: 9.5pt; font-weight: 650; }
    QLabel#usageNote { color: $subtle; font-size: 8pt; }
    QListWidget, QPlainTextEdit, QLineEdit, QComboBox {
        background: $input;
        color: $text;
        border: 1px solid $border;
        border-radius: 10px;
        padding: 9px 11px;
        selection-background-color: $selection;
        selection-color: $text;
    }
    QListWidget { padding: 6px; }
    QListWidget::item {
        padding: 11px 10px;
        border-radius: 7px;
        margin: 2px 1px;
    }
    QListWidget::item:hover { background: $surface_alt; }
    QListWidget::item:selected {
        background: $selection;
        color: $text;
        border-left: 3px solid $accent;
    }
    QPlainTextEdit {
        padding: 12px;
        line-height: 1.4;
    }
    QLineEdit { min-height: 24px; }
    QLineEdit:read-only { color: $muted; }
    QComboBox { min-height: 26px; padding-right: 28px; }
    QComboBox::drop-down {
        border: none;
        width: 28px;
        subcontrol-origin: padding;
        subcontrol-position: center right;
    }
    QComboBox QAbstractItemView {
        background: $surface;
        color: $text;
        border: 1px solid $border;
        border-radius: 8px;
        padding: 5px;
        selection-background-color: $selection;
        outline: none;
    }
    QPushButton, QToolButton {
        background: $surface_alt;
        color: $text;
        border: 1px solid $border;
        border-radius: 9px;
        padding: 9px 13px;
        min-height: 22px;
        font-weight: 650;
    }
    QPushButton:hover, QToolButton:hover {
        background: $surface;
        border-color: $border_hover;
    }
    QPushButton:pressed, QToolButton:pressed {
        background: $selection;
        border-color: $border_focus;
    }
    QPushButton:disabled, QToolButton:disabled {
        color: $subtle;
        background: $surface_alt;
        border-color: $border;
    }
    QPushButton#primaryButton {
        color: $accent_text;
        background: $accent;
        border: 1px solid $accent;
        font-weight: 800;
        padding: 11px 18px;
        min-height: 25px;
    }
    QPushButton#primaryButton:hover {
        background: $accent_hover;
        border-color: $accent_hover;
    }
    QPushButton#primaryButton:pressed {
        background: $accent_pressed;
        border-color: $accent_pressed;
    }
    QPushButton#quietButton { background: transparent; }
    QPushButton#smallButton { padding: 8px 11px; }
    QProgressBar {
        background: $surface_alt;
        border: none;
        border-radius: 4px;
        height: 7px;
        text-align: center;
    }
    QProgressBar::chunk { background: $accent; border-radius: 4px; }
    QSplitter::handle { background: transparent; }
    QSplitter::handle:horizontal { width: 12px; }
    QSplitter::handle:vertical { height: 12px; }
    QScrollBar:vertical {
        background: transparent;
        width: 10px;
        margin: 3px 1px 3px 3px;
    }
    QScrollBar::handle:vertical {
        background: $scroll;
        min-height: 32px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover { background: $border_hover; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar:horizontal { height: 9px; background: transparent; }
    QScrollBar::handle:horizontal { background: $scroll; border-radius: 4px; }
    QToolTip {
        background: $surface;
        color: $text;
        border: 1px solid $border;
        padding: 6px 8px;
        border-radius: 6px;
    }
    """
    # Replace longer tokens first so keys such as "$border_hover" are not
    # partially consumed by the shorter "$border" token.
    for key, value in sorted(c.items(), key=lambda item: len(item[0]), reverse=True):
        template = template.replace(f"${key}", value)
    return template


class VideoWorker(QThread):
    progress = Signal(str)
    done = Signal(str)
    failed = Signal(object)

    def __init__(self, sources, text, output_path, voice, orientation, rate):
        super().__init__()
        self.sources = list(sources)
        self.text = text
        self.output_path = output_path
        self.voice = voice
        self.orientation = orientation
        self.rate = rate

    def run(self) -> None:
        try:
            result = build_video(
                sources=self.sources,
                text=self.text,
                output_path=self.output_path,
                voice_name=self.voice,
                orientation=self.orientation,
                rate=self.rate,
                progress_callback=self.progress.emit,
            )
            self.done.emit(str(result))
        except Exception as error:
            self.failed.emit(error)


class MainWindow(QMainWindow):
    RESPONSIVE_BREAKPOINT = 1060

    def __init__(self):
        super().__init__()
        self.settings = QSettings("AutoVideoLocal", "AutoVideoLocal")
        self.setWindowTitle("AutoVideoLocal")
        self.setMinimumSize(760, 640)
        self.resize(1180, 860)

        saved_geometry = self.settings.value("window/geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

        self.sources: list[str] = []
        self.output_path: str | None = None
        self.worker: VideoWorker | None = None
        self._interactive_widgets: list[QWidget] = []
        self._last_split_orientation: Qt.Orientation | None = None
        self._log_expanded = False

        self.init_ui()
        self._restore_preferences()
        self._update_responsive_layout(force=True)
        self.refresh_usage_label()

    def init_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        main = QVBoxLayout(root)
        main.setContentsMargins(20, 18, 20, 16)
        main.setSpacing(14)

        # Header: brand and appearance preference are separated from form fields.
        header = QFrame()
        header.setObjectName("topHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 17, 20, 17)
        header_layout.setSpacing(20)

        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(3)
        eyebrow = QLabel("VIDEO CREATION STUDIO  ·  VERSION 1.0.1")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("AutoVideoLocal")
        title.setObjectName("appTitle")
        subtitle = QLabel("Ghép video, tạo giọng đọc và phụ đề trong vài bước đơn giản.")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        brand_layout.addWidget(eyebrow)
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        header_layout.addLayout(brand_layout, 1)

        header_controls = QVBoxLayout()
        header_controls.setSpacing(5)
        theme_label = QLabel("Giao diện")
        theme_label.setObjectName("fieldLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Theo hệ thống", "system")
        self.theme_combo.addItem("Sáng", "light")
        self.theme_combo.addItem("Tối", "dark")
        self.theme_combo.setMinimumWidth(155)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        header_controls.addWidget(theme_label)
        header_controls.addWidget(self.theme_combo)
        header_layout.addLayout(header_controls)

        self.header_status = QLabel("SẴN SÀNG")
        self.header_status.setObjectName("statusBadge")
        self.header_status.setProperty("state", "ready")
        self.header_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.header_status, alignment=Qt.AlignmentFlag.AlignVCenter)
        main.addWidget(header)

        # Scrollable content prevents clipping on shorter or smaller windows.
        self.body_scroll = QScrollArea()
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body_content = QWidget()
        body_content.setObjectName("scrollContent")
        body_layout = QVBoxLayout(body_content)
        body_layout.setContentsMargins(1, 1, 1, 1)
        body_layout.setSpacing(12)

        self.body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.body_splitter.setChildrenCollapsible(False)
        self.body_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.body_splitter.setHandleWidth(10)

        self.left_panel = self._build_left_panel()
        self.right_panel = self._build_right_panel()
        self.body_splitter.addWidget(self.left_panel)
        self.body_splitter.addWidget(self.right_panel)
        self.body_splitter.setStretchFactor(0, 6)
        self.body_splitter.setStretchFactor(1, 4)
        body_layout.addWidget(self.body_splitter)
        self.body_scroll.setWidget(body_content)
        main.addWidget(self.body_scroll, 1)

        # Fixed footer keeps status and primary action visible during scrolling.
        footer = QFrame()
        footer.setObjectName("footerCard")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(17, 14, 17, 14)
        footer_layout.setSpacing(11)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Sẵn sàng tạo video.")
        self.status_label.setObjectName("statusMessage")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("muted")
        status_row.addWidget(self.progress_label)
        footer_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        footer_layout.addWidget(self.progress_bar)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.log_toggle_btn = QToolButton()
        self.log_toggle_btn.setText("Xem nhật ký xử lý  +")
        self.log_toggle_btn.setObjectName("quietButton")
        self.log_toggle_btn.clicked.connect(self.toggle_log)
        action_row.addWidget(self.log_toggle_btn)
        action_row.addStretch(1)

        self.open_folder_btn = QPushButton("Mở thư mục đầu ra")
        self.open_folder_btn.setObjectName("quietButton")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        action_row.addWidget(self.open_folder_btn)

        self.generate_btn = QPushButton("Xuất video")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setMinimumWidth(160)
        self.generate_btn.clicked.connect(self.start_render)
        action_row.addWidget(self.generate_btn)
        footer_layout.addLayout(action_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Nhật ký xử lý sẽ hiển thị tại đây.")
        self.log.setMinimumHeight(90)
        self.log.setMaximumHeight(145)
        self.log.hide()
        footer_layout.addWidget(self.log)
        main.addWidget(footer)

        self._interactive_widgets = [
            self.add_btn,
            self.remove_btn,
            self.up_btn,
            self.down_btn,
            self.video_list,
            self.script_input,
            self.voice_combo,
            self.rate_combo,
            self.orientation_combo,
            self.output_btn,
        ]
        self.setCentralWidget(root)
        self.apply_theme(self._resolved_theme())

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(0)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        source_card, source_layout = self._create_card(
            "01 · Video nguồn",
            "Thêm video và sắp xếp theo thứ tự muốn xuất.",
        )
        self.video_list = QListWidget()
        self.video_list.setMinimumHeight(190)
        self.video_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        source_layout.addWidget(self.video_list, 1)

        source_actions = QHBoxLayout()
        source_actions.setSpacing(7)
        self.add_btn = QPushButton("＋  Thêm video")
        self.add_btn.setObjectName("primaryButton")
        self.remove_btn = QPushButton("Xóa")
        self.up_btn = QPushButton("↑  Lên")
        self.down_btn = QPushButton("↓  Xuống")
        for button in (self.add_btn, self.remove_btn, self.up_btn, self.down_btn):
            button.setObjectName("smallButton" if button is not self.add_btn else "primaryButton")
            source_actions.addWidget(button)
        self.add_btn.clicked.connect(self.add_videos)
        self.remove_btn.clicked.connect(self.remove_video)
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn.clicked.connect(self.move_down)
        source_layout.addLayout(source_actions)
        layout.addWidget(source_card, 3)

        script_card, script_layout = self._create_card(
            "02 · Lời thoại",
            "Nhập nội dung tiếng Việt. Phụ đề sẽ được chia theo từng câu.",
        )
        self.script_input = QPlainTextEdit()
        self.script_input.setPlaceholderText(
            "Ví dụ: Xin chào! Hôm nay chúng ta sẽ cùng khám phá một chủ đề thú vị..."
        )
        self.script_input.setMinimumHeight(145)
        self.script_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        script_layout.addWidget(self.script_input, 1)
        layout.addWidget(script_card, 2)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(0)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        settings_card, settings_layout = self._create_card(
            "03 · Cấu hình video",
            "Chọn giọng đọc và định dạng phù hợp với nội dung.",
        )

        settings_layout.addWidget(self._field_label("Giọng đọc"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Nữ - Hoài My", "Nam - Minh"])
        settings_layout.addWidget(self.voice_combo)

        settings_layout.addWidget(self._field_label("Tốc độ đọc"))
        self.rate_combo = QComboBox()
        for label, value in [
            ("Chậm hơn · -10%", "-10%"),
            ("Mặc định · 0%", "+0%"),
            ("Nhanh hơn · +10%", "+10%"),
            ("Nhanh hơn · +20%", "+20%"),
        ]:
            self.rate_combo.addItem(label, value)
        self.rate_combo.setCurrentIndex(1)
        settings_layout.addWidget(self.rate_combo)

        settings_layout.addWidget(self._field_label("Tỷ lệ khung hình"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Video dọc · 9:16", "portrait")
        self.orientation_combo.addItem("Video ngang · 16:9", "landscape")
        settings_layout.addWidget(self.orientation_combo)

        audio_note = QLabel("Âm thanh gốc của video sẽ được tắt trong bản xuất.")
        audio_note.setObjectName("helper")
        audio_note.setWordWrap(True)
        settings_layout.addWidget(audio_note)
        layout.addWidget(settings_card)

        output_card, output_layout = self._create_card(
            "04 · File đầu ra",
            "Chọn vị trí và tên file MP4 sau khi hoàn tất.",
        )
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setMinimumWidth(0)
        self.output_edit.setPlaceholderText("Chưa chọn nơi lưu video")
        output_layout.addWidget(self.output_edit)
        self.output_btn = QPushButton("Chọn nơi lưu…")
        self.output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(self.output_btn)
        layout.addWidget(output_card)

        usage_card, usage_layout = self._create_card(
            "05 · Mức sử dụng giọng đọc",
            "Thống kê cục bộ trên thiết bị này.",
        )
        self.usage_label = QLabel()
        self.usage_label.setObjectName("usageLabel")
        self.usage_label.setWordWrap(True)
        usage_layout.addWidget(self.usage_label)
        self.usage_note = QLabel(
            "Số liệu này chỉ giúp theo dõi thói quen sử dụng, không phải hạn mức chính thức của Microsoft."
        )
        self.usage_note.setObjectName("usageNote")
        self.usage_note.setWordWrap(True)
        usage_layout.addWidget(self.usage_note)
        layout.addWidget(usage_card)
        layout.addStretch(1)
        return panel

    @staticmethod
    def _create_card(title_text: str, description: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(11)

        heading = QLabel(title_text)
        heading.setObjectName("sectionTitle")
        heading.setWordWrap(True)
        description_label = QLabel(description)
        description_label.setObjectName("helper")
        description_label.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(description_label)
        return card, layout

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _restore_preferences(self) -> None:
        saved_theme = self.settings.value("appearance/theme", "system")
        index = self.theme_combo.findData(saved_theme)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)

        saved_splitter = self.settings.value("layout/splitter")
        if saved_splitter:
            self.body_splitter.restoreState(saved_splitter)

    def _resolved_theme(self) -> str:
        selected = self.theme_combo.currentData() if hasattr(self, "theme_combo") else "system"
        if selected in THEME_COLORS:
            return selected
        palette = QApplication.palette()
        background = palette.color(QPalette.ColorRole.Window)
        return "dark" if background.lightness() < 128 else "light"

    def on_theme_changed(self) -> None:
        selected = self.theme_combo.currentData()
        self.settings.setValue("appearance/theme", selected)
        self.apply_theme(self._resolved_theme())

    def apply_theme(self, theme: str) -> None:
        self.setStyleSheet(build_stylesheet(theme))

    def _update_responsive_layout(self, force: bool = False) -> None:
        if not hasattr(self, "body_splitter"):
            return
        orientation = (
            Qt.Orientation.Horizontal
            if self.width() >= self.RESPONSIVE_BREAKPOINT
            else Qt.Orientation.Vertical
        )
        if not force and orientation == self._last_split_orientation:
            return
        self.body_splitter.setOrientation(orientation)
        self._last_split_orientation = orientation
        if orientation == Qt.Orientation.Horizontal:
            available_width = max(1, self.body_splitter.width() - self.body_splitter.handleWidth())
            left_size = int(available_width * 0.59)
            self.body_splitter.setSizes([left_size, available_width - left_size])
        else:
            self.body_splitter.setSizes([470, 500])

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_responsive_layout()

    def refresh_usage_label(self) -> None:
        summary = get_usage_summary()
        self.usage_label.setText(
            f"Hôm nay: {summary['requests']:,} yêu cầu · "
            f"{summary['characters']:,} ký tự đã gửi."
        )

    def add_videos(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn video nguồn",
            "",
            "Video (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
        )
        added = 0
        for file_path in files:
            resolved = str(Path(file_path).resolve())
            if resolved not in self.sources:
                self.sources.append(resolved)
                added += 1
        self.refresh_list()
        if added:
            self.append_log(f"Đã thêm {added} video nguồn.")

    def refresh_list(self) -> None:
        selected_row = self.video_list.currentRow()
        self.video_list.clear()
        for index, path in enumerate(self.sources):
            item = QListWidgetItem(f"{index + 1:02d}   {Path(path).name}")
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.video_list.addItem(item)
        if self.sources:
            self.video_list.setCurrentRow(max(0, min(selected_row, len(self.sources) - 1)))

    def remove_video(self) -> None:
        index = self.video_list.currentRow()
        if index < 0:
            return
        removed = self.sources.pop(index)
        self.refresh_list()
        self.append_log(f"Đã xóa {Path(removed).name} khỏi danh sách.")

    def move_up(self) -> None:
        index = self.video_list.currentRow()
        if index <= 0:
            return
        self.sources[index - 1], self.sources[index] = self.sources[index], self.sources[index - 1]
        self.refresh_list()
        self.video_list.setCurrentRow(index - 1)

    def move_down(self) -> None:
        index = self.video_list.currentRow()
        if index < 0 or index >= len(self.sources) - 1:
            return
        self.sources[index + 1], self.sources[index] = self.sources[index], self.sources[index + 1]
        self.refresh_list()
        self.video_list.setCurrentRow(index + 1)

    def select_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Chọn nơi lưu video",
            str(Path.home() / "Downloads" / "final_video.mp4"),
            "Video MP4 (*.mp4)",
        )
        if not path:
            return
        if not path.lower().endswith(".mp4"):
            path += ".mp4"
        self.output_path = str(Path(path).resolve())
        self.output_edit.setText(self.output_path)
        self.output_edit.setToolTip(self.output_path)

    def start_render(self) -> None:
        if not self.sources:
            self.show_validation_error(
                "Chưa có video nguồn",
                "Hãy thêm ít nhất một video trước khi xuất.",
            )
            return

        missing = [path for path in self.sources if not Path(path).is_file()]
        if missing:
            self.show_validation_error(
                "Không tìm thấy video nguồn",
                "Một hoặc nhiều video đã bị di chuyển hoặc xóa:\n\n"
                + "\n".join(Path(path).name for path in missing),
            )
            return

        script = self.script_input.toPlainText().strip()
        if not script:
            self.show_validation_error(
                "Chưa có lời thoại",
                "Hãy nhập nội dung tiếng Việt muốn chuyển thành giọng đọc.",
            )
            return

        if not self.output_path:
            self.show_validation_error(
                "Chưa chọn nơi lưu",
                "Hãy chọn tên file và thư mục lưu video đầu ra.",
            )
            return

        if Path(self.output_path).exists():
            answer = QMessageBox.question(
                self,
                "Xác nhận ghi đè",
                "File đầu ra đã tồn tại. Bạn có muốn thay thế file này "
                "khi video mới được kiểm tra thành công không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.set_processing(True)
        self.log.clear()
        self.open_folder_btn.setEnabled(False)
        self.status_label.setText("Đang chuẩn bị xử lý…")
        self.append_log("Bắt đầu quy trình xuất video.")

        self.worker = VideoWorker(
            sources=self.sources,
            text=script,
            output_path=self.output_path,
            voice=self.voice_combo.currentText(),
            orientation=self.orientation_combo.currentData(),
            rate=self.rate_combo.currentData(),
        )
        self.worker.progress.connect(self.update_status)
        self.worker.done.connect(self.render_success)
        self.worker.failed.connect(self.render_failed)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def set_processing(self, processing: bool) -> None:
        for widget in self._interactive_widgets:
            widget.setEnabled(not processing)
        self.generate_btn.setEnabled(not processing)
        self.progress_bar.setVisible(processing)
        self.header_status.setText("ĐANG XỬ LÝ" if processing else "SẴN SÀNG")
        self.header_status.setProperty("state", "processing" if processing else "ready")
        self.header_status.style().unpolish(self.header_status)
        self.header_status.style().polish(self.header_status)

    def update_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.append_log(message)
        self.refresh_usage_label()

    def append_log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def toggle_log(self) -> None:
        self._log_expanded = not self._log_expanded
        self.log.setVisible(self._log_expanded)
        self.log_toggle_btn.setText(
            "Ẩn nhật ký xử lý  −" if self._log_expanded else "Xem nhật ký xử lý  +"
        )

    def render_success(self, path: str) -> None:
        self.status_label.setText("Xuất video thành công.")
        self.append_log(f"Đã lưu video: {path}")
        self.open_folder_btn.setEnabled(True)
        self.refresh_usage_label()
        QMessageBox.information(
            self,
            "Xuất video thành công",
            f"Video đã được tạo và kiểm tra hợp lệ.\n\n{path}",
        )

    def render_failed(self, error: object) -> None:
        self.refresh_usage_label()
        if isinstance(error, PipelineError):
            self.status_label.setText(f"Thất bại tại công đoạn: {error.stage}.")
            self.append_log(f"Thất bại: {error.code} – {error.title}")
            details = (
                f"Công đoạn: {error.stage}\n"
                f"Mã lỗi: {error.code}\n\n"
                f"Chi tiết kỹ thuật:\n"
                f"{error.technical_detail or 'Không có chi tiết kỹ thuật bổ sung.'}"
            )
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(error.title)
            box.setText(error.message)
            box.setInformativeText("Hướng xử lý:\n" + error.recovery)
            box.setDetailedText(details)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()
        else:
            message = str(error) or error.__class__.__name__
            self.status_label.setText("Quá trình xuất video không hoàn thành.")
            self.append_log("Đã xảy ra lỗi ngoài dự kiến. Hãy mở chi tiết lỗi để kiểm tra.")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("Không thể xuất video")
            box.setText("Đã xảy ra lỗi ngoài dự kiến.")
            box.setInformativeText(
                "Hãy kiểm tra thư mục làm việc và gửi chi tiết kỹ thuật để được hỗ trợ."
            )
            box.setDetailedText(f"{error.__class__.__name__}: {message}")
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()

    def on_worker_finished(self) -> None:
        self.set_processing(False)
        self.refresh_usage_label()

    def show_validation_error(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def open_output_folder(self) -> None:
        if not self.output_path:
            return
        folder = Path(self.output_path).parent
        if folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Đang xuất video",
                "Video vẫn đang được xử lý. Vui lòng chờ công đoạn hiện tại hoàn tất trước khi đóng ứng dụng.",
            )
            event.ignore()
            return

        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("layout/splitter", self.body_splitter.saveState())
        self.settings.setValue("appearance/theme", self.theme_combo.currentData())
        event.accept()
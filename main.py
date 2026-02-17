import sys
import os
import subprocess
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QLineEdit, QProgressBar, QScrollArea, QGridLayout,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog, QMenu,
    QListWidget, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QAction, QPalette, QColor, QDragEnterEvent, QDropEvent

from clip_service import CLIPService
from cache_manager import CacheManager
from search_engine import SearchEngine


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


class EmbeddingWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, clip_service, cache_manager, images):
        super().__init__()
        self.clip_service = clip_service
        self.cache_manager = cache_manager
        self.images = images

    def run(self):
        try:
            self.clip_service.load()
            total = len(self.images)
            
            for i, img_path in enumerate(self.images):
                try:
                    embedding = self.clip_service.get_image_embedding(img_path)
                    self.cache_manager.save_embedding(img_path, embedding)
                except Exception as e:
                    print(f"Error: {e}")
                
                self.progress.emit(i + 1, total)
            
            self.finished.emit(total)
        except Exception as e:
            self.error.emit(str(e))


class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, search_engine, query, image_path):
        super().__init__()
        self.search_engine = search_engine
        self.query = query
        self.image_path = image_path

    def run(self):
        try:
            if self.image_path and os.path.exists(self.image_path):
                results = self.search_engine.search_by_image(self.image_path)
            else:
                results = self.search_engine.search(self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ImageSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.clip_service = CLIPService()
        self.cache_manager = CacheManager()
        self.search_engine = SearchEngine(self.cache_manager, self.clip_service)

        self.folders = set()
        self.model_loaded = False
        self.embedding = False
        self.drop_image_path = None
        
        self.embedding_worker = None
        self.search_worker = None

        self.current_theme = 'dark'
        
        self.setWindowTitle("CLIP Image Search")
        self.setGeometry(100, 100, 1000, 700)

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        top_group = QGroupBox("Folders to scan")
        top_layout = QHBoxLayout(top_group)
        
        self.folders_list = QListWidget()
        self.folders_list.setMaximumHeight(80)
        top_layout.addWidget(self.folders_list, 1)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)
        
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self._add_folder)
        btn_layout.addWidget(self.add_folder_btn)
        
        self.gen_embeddings_btn = QPushButton("Generate Embeddings")
        self.gen_embeddings_btn.clicked.connect(self._start_embedding)
        btn_layout.addWidget(self.gen_embeddings_btn)
        
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        btn_layout.addWidget(self.clear_cache_btn)
        
        self.toggle_theme_btn = QPushButton("Toggle Theme")
        self.toggle_theme_btn.clicked.connect(self._toggle_theme)
        btn_layout.addWidget(self.toggle_theme_btn)
        
        self.stats_label = QLabel("Cached: 0 images (0.0 MB)")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.stats_label)
        
        top_layout.addLayout(btn_layout)
        main_layout.addWidget(top_group)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        status_layout.addWidget(self.progress)
        
        main_layout.addWidget(status_group)

        search_group = QGroupBox("Search")
        search_layout = QHBoxLayout(search_group)
        
        search_layout.addWidget(QLabel("Query:"))
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Enter text to search...")
        self.search_entry.returnPressed.connect(self._start_search)
        search_layout.addWidget(self.search_entry, 1)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._start_search)
        search_layout.addWidget(self.search_btn)
        
        search_layout.addSpacing(10)
        
        self.drop_frame = DropFrame()
        self.drop_frame.setMinimumSize(200, 60)
        self.drop_frame.setMaximumSize(300, 80)
        self.drop_frame.image_dropped.connect(self._set_dropped_image)
        search_layout.addWidget(self.drop_frame)
        
        self.drop_label = QLabel("Drag image here\nor click to browse")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumSize(180, 50)
        self.drop_frame.set_widget(self.drop_label)
        
        self.browse_img_btn = QPushButton("Browse Image")
        self.browse_img_btn.clicked.connect(self._browse_image)
        search_layout.addWidget(self.browse_img_btn)
        
        self.clear_img_btn = QPushButton("Clear Image")
        self.clear_img_btn.clicked.connect(self._clear_dropped_image)
        search_layout.addWidget(self.clear_img_btn)
        
        main_layout.addWidget(search_group, 0)

        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.results_widget = QWidget()
        self.results_layout = QGridLayout(self.results_widget)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(5, 5, 5, 5)
        
        results_scroll.setWidget(self.results_widget)
        main_layout.addWidget(results_scroll, 1)

        self._update_stats()

    def _apply_theme(self):
        if self.current_theme == 'dark':
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
            dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
            dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
            dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
            dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
            dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
            dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            self.setPalette(dark_palette)
            
            self._set_stylesheet("dark")
        else:
            self.setPalette(QPalette())
            self._set_stylesheet("light")

    def _set_stylesheet(self, theme):
        if theme == "dark":
            ss = """
                QGroupBox {
                    color: white;
                    border: 1px solid #555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QListWidget {
                    background-color: #3C3C3C;
                    color: white;
                    border: 1px solid #555;
                }
                QLineEdit {
                    background-color: #3C3C3C;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #3C3C3C;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4C4C4C;
                }
                QPushButton:pressed {
                    background-color: #2C2C2C;
                }
                QLabel {
                    color: white;
                }
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #3C3C3C;
                }
                QProgressBar::chunk {
                    background-color: #0078D4;
                }
            """
        else:
            ss = """
                QGroupBox {
                    border: 1px solid #aaa;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """
        self.setStyleSheet(ss)

    def _toggle_theme(self):
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self._apply_theme()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folders.add(folder)
            self._update_folders_list()

    def _update_folders_list(self):
        self.folders_list.clear()
        for folder in self.folders:
            self.folders_list.addItem(folder)

    def _update_stats(self):
        stats = self.cache_manager.get_stats()
        size_mb = stats["cache_size_mb"]
        self.stats_label.setText(f"Cached: {stats['image_count']} images ({size_mb:.1f} MB)")

    def _get_images_from_folders(self):
        images = []
        for folder in self.folders:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        img_path = os.path.join(root, f)
                        if not self.cache_manager.has_embedding(img_path):
                            images.append(img_path)
        return images

    def _start_embedding(self):
        if not self.folders:
            QMessageBox.warning(self, "No folders", "Please add at least one folder to scan.")
            return
        
        if self.embedding:
            return
        
        images = self._get_images_from_folders()
        
        if not images:
            QMessageBox.information(self, "Done", "All images already have embeddings!")
            return
        
        self.embedding = True
        self.status_label.setText("Loading CLIP model...")
        self.progress.setVisible(True)
        self.progress.setMaximum(len(images))
        self.progress.setValue(0)
        
        self.gen_embeddings_btn.setEnabled(False)
        
        self.embedding_worker = EmbeddingWorker(self.clip_service, self.cache_manager, images)
        self.embedding_worker.progress.connect(self._on_embedding_progress)
        self.embedding_worker.finished.connect(self._on_embedding_done)
        self.embedding_worker.error.connect(self._on_embedding_error)
        self.embedding_worker.start()

    def _on_embedding_progress(self, current, total):
        self.progress.setValue(current)
        self.status_label.setText(f"Processing {current}/{total}...")

    def _on_embedding_done(self, total):
        self.embedding = False
        self.progress.setVisible(False)
        self.status_label.setText(f"Done! {total} images processed")
        self._update_stats()
        self.model_loaded = True
        self.gen_embeddings_btn.setEnabled(True)
        QMessageBox.information(self, "Done", f"Successfully processed {total} images!")

    def _on_embedding_error(self, error_msg):
        self.embedding = False
        self.progress.setVisible(False)
        self.status_label.setText("Error")
        self.gen_embeddings_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_msg)

    def _clear_cache(self):
        reply = QMessageBox.question(
            self, "Clear Cache", 
            "This will delete all cached embeddings. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cache_manager.clear_all()
            self.status_label.setText("Cache cleared")
            self._update_stats()

    def _start_search(self):
        query = self.search_entry.text().strip()
        has_text = bool(query)
        has_image = self.drop_image_path is not None and os.path.exists(self.drop_image_path)
        
        if not has_text and not has_image:
            QMessageBox.warning(self, "No input", "Please enter text or drop an image to search")
            return
        
        if not self.model_loaded:
            self.status_label.setText("Loading CLIP model...")
            self.clip_service.load()
            self.model_loaded = True
        
        if has_image:
            self.status_label.setText(f"Searching by image: {os.path.basename(self.drop_image_path)}")
        else:
            self.status_label.setText(f"Searching for: {query}")
        
        self.search_btn.setEnabled(False)
        
        self.search_worker = SearchWorker(self.search_engine, query, self.drop_image_path)
        self.search_worker.finished.connect(self._on_search_done)
        self.search_worker.error.connect(self._on_search_error)
        self.search_worker.start()

    def _on_search_done(self, results):
        self.search_btn.setEnabled(True)
        self._display_results(results)
        self.status_label.setText(f"Found {len(results)} results")

    def _on_search_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.status_label.setText("Error")
        QMessageBox.critical(self, "Error", error_msg)

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _display_results(self, results):
        self._clear_results()
        
        if not results:
            no_results = QLabel("No results found")
            no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.addWidget(no_results, 0, 0, 1, 4)
            return

        row = 0
        col = 0
        max_cols = 4

        for img_path, score in results:
            try:
                frame = QFrame()
                frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
                frame_layout = QVBoxLayout(frame)
                frame_layout.setSpacing(3)
                frame_layout.setContentsMargins(5, 5, 5, 5)
                
                img_label = QLabel()
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setCursor(Qt.CursorShape.PointingHandCursor)
                
                pixmap = QPixmap(img_path)
                if pixmap.isNull():
                    continue
                pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_label.setPixmap(pixmap)
                img_label.mousePressEvent = lambda e, p=img_path: self._open_image(p)
                img_label.contextMenuEvent = lambda e, p=img_path, w=frame: self._show_context_menu(e, p, w)
                
                frame_layout.addWidget(img_label)
                
                score_label = QLabel(f"{score:.3f}")
                score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                score_label.setStyleSheet("font-size: 8pt;")
                frame_layout.addWidget(score_label)
                
                filename = os.path.basename(img_path)
                name_label = QLabel(filename[:30] + "..." if len(filename) > 30 else filename)
                name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name_label.setStyleSheet("font-size: 7pt;")
                name_label.setWordWrap(True)
                name_label.setCursor(Qt.CursorShape.PointingHandCursor)
                name_label.mousePressEvent = lambda e, p=img_path: self._open_image(p)
                frame_layout.addWidget(name_label)
                
                self.results_layout.addWidget(frame, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            except Exception as e:
                print(f"Error displaying {img_path}: {e}")

    def _open_image(self, img_path):
        if os.path.exists(img_path):
            subprocess.run(["xdg-open", img_path])

    def _show_context_menu(self, event, img_path, widget):
        menu = QMenu(self)
        
        open_path_action = QAction("Open Path", self)
        open_path_action.triggered.connect(lambda: self._open_folder(img_path))
        menu.addAction(open_path_action)
        
        copy_path_action = QAction("Copy Path", self)
        copy_path_action.triggered.connect(lambda: self._copy_path(img_path))
        menu.addAction(copy_path_action)
        
        menu.exec(event.globalPos())

    def _open_folder(self, img_path):
        folder = os.path.dirname(img_path)
        if os.path.exists(folder):
            subprocess.run(["xdg-open", folder])

    def _copy_path(self, img_path):
        clipboard = QApplication.clipboard()
        clipboard.setText(img_path)

    def _browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", 
            "Image files (*.jpg *.jpeg *.png *.gif *.bmp *.webp)"
        )
        if file_path:
            self._set_dropped_image(file_path)

    def _set_dropped_image(self, image_path):
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self, "Invalid file", "Please drop an image file")
            return
        
        self.drop_image_path = image_path
        
        try:
            pixmap = QPixmap(image_path).scaled(180, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.drop_label.setPixmap(pixmap)
            self.drop_label.setText("")
        except Exception as e:
            print(f"Error loading preview: {e}")
            self.drop_label.setText(os.path.basename(image_path)[:30])
            self.drop_label.setPixmap(QPixmap())

    def _clear_dropped_image(self):
        self.drop_image_path = None
        self.drop_label.setPixmap(QPixmap())
        self.drop_label.setText("Drag image here\nor click to browse")


class DropFrame(QFrame):
    image_dropped = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setLineWidth(2)
        self._widget = None
        
    def set_widget(self, widget):
        self._widget = widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                self.image_dropped.emit(url.toLocalFile())
        event.acceptProposedAction()
    
    def mousePressEvent(self, event):
        if self._widget:
            self._widget.mousePressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ImageSearchApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

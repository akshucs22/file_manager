import sys
import os
import logging
import shutil
import subprocess
import webbrowser
from PyQt5.QtWidgets import(
    QApplication, QMainWindow, QTreeView, QFileSystemModel,
    QVBoxLayout, QWidget, QPushButton, QFileDialog, QMenu,
    QAction, QInputDialog, QMessageBox, QToolBar, QTextBrowser, QDockWidget,
    QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt, QDateTime, QObject, pyqtSignal

class Clipboard(QObject):
    copied = pyqtSignal(str)
    cut_file = pyqtSignal(str)
    pasted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._source_path = ""

    @property
    def source_path(self):
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        self._source_path = value

    def copy(self, source_path):
        self.source_path = source_path
        self.copied.emit(source_path)

    def cut(self, source_path):
        self.source_path = source_path
        self.cut_file.emit(source_path)

    def paste(self, destination_path):
        if not self.source_path:
            return False

        if os.path.exists(destination_path):
            destination_path = self.get_unique_name(destination_path)

        if os.path.isdir(self.source_path):
            shutil.copytree(self.source_path, destination_path)
        else:
            shutil.copy2(self.source_path, destination_path)

        self.pasted.emit(destination_path)
        return True

    def get_unique_name(self, path):
        base, ext = os.path.splitext(path)
        index = 1
        new_path = f"{base}_{index}{ext}"

        while os.path.exists(new_path):
            index += 1
            new_path = f"{base}_{index}{ext}"

        return new_path

class FileManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Manager")

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QHBoxLayout(self.central_widget)

        self.tree_view1 = QTreeView(self)
        self.layout.addWidget(self.tree_view1)

        self.tree_view2 = QTreeView(self)
        self.layout.addWidget(self.tree_view2)

        home_path = os.path.expanduser("~")
        self.model1 = QFileSystemModel()
        self.model1.setRootPath(home_path)
        self.tree_view1.setModel(self.model1)
        self.tree_view1.setContextMenuPolicy(Qt.CustomContextMenu)

        self.model2 = QFileSystemModel()
        self.model2.setRootPath(home_path)
        self.tree_view2.setModel(self.model2)
        self.tree_view2.setContextMenuPolicy(Qt.CustomContextMenu)

        self.tree_view1.doubleClicked.connect(self.open_item1)
        self.tree_view2.doubleClicked.connect(self.open_item2)
        self.tree_view1.customContextMenuRequested.connect(self.show_context_menu1)
        self.tree_view2.customContextMenuRequested.connect(self.show_context_menu2)

        self.setup_actions()
        self.setup_toolbar()
        self.setup_status_bar()

        self.open_button1 = QPushButton("Open Directory 1", self)
        self.open_button1.clicked.connect(self.open_directory1)
        self.layout.addWidget(self.open_button1)

        self.open_button2 = QPushButton("Open Directory 2", self)
        self.open_button2.clicked.connect(self.open_directory2)
        self.layout.addWidget(self.open_button2)

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        self.clipboard = Clipboard()
        self.clipboard.copied.connect(self.on_copied)
        self.clipboard.cut_file.connect(self.on_cut)
        self.clipboard.pasted.connect(self.on_pasted)

        self.logs_dock = QDockWidget("Logs", self)
        self.logs_browser = QTextBrowser()
        self.logs_dock.setWidget(self.logs_browser)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.logs_dock)

    def open_directory1(self):
        directory = QFileDialog.getExistingDirectory(self, "Open Directory", "")
        if directory:
            try:
                self.model1.setRootPath(directory)
                self.tree_view1.setRootIndex(self.model1.index(directory))
                self.log_action(f"Opened directory 1: {directory}")
            except Exception as e:
                self.log_action(f"Error opening directory 1: {e}")
                QMessageBox.warning(self, "Error", f"Error opening directory 1: {e}")

    def open_directory2(self):
        directory = QFileDialog.getExistingDirectory(self, "Open Directory", "")
        if directory:
            try:
                self.model2.setRootPath(directory)
                self.tree_view2.setRootIndex(self.model2.index(directory))
                self.log_action(f"Opened directory 2: {directory}")
            except Exception as e:
                self.log_action(f"Error opening directory 2: {e}")
                QMessageBox.warning(self, "Error", f"Error opening directory 2: {e}")

    def open_item1(self, index):
        self.open_item(index, self.model1, "directory 1")

    def open_item2(self, index):
        self.open_item(index, self.model2, "directory 2")

    def open_item(self, index, model, directory_name):
        try:
            file_path = model.filePath(index)
            if os.path.isfile(file_path):
                if sys.platform.startswith('linux'):
                    subprocess.Popen(["xdg-open", file_path])
                elif sys.platform.startswith('win'):
                    os.startfile(file_path)
                else:
                    webbrowser.open(file_path)
            elif os.path.isdir(file_path):
                model.setRootPath(file_path)
                self.log_action(f"Opened {directory_name}: {file_path}")
        except Exception as e:
            self.log_action(f"Error opening item: {e}")
            QMessageBox.warning(self, "Error", f"Error opening item: {e}")

    def show_context_menu1(self, point):
        self.show_context_menu(point, self.tree_view1, self.model1, "directory 1")

    def show_context_menu2(self, point):
        self.show_context_menu(point, self.tree_view2, self.model2, "directory 2")

    def show_context_menu(self, point, tree_view, model, directory_name):
        try:
            index = tree_view.indexAt(point)
            if index.isValid():
                menu = QMenu(self)

                actions = [self.copy_action, self.cut_action, self.paste_action,
                           self.delete_action, self.rename_action, self.properties_action]
                for action in actions:
                    menu.addAction(action)

                self.cut_action.setEnabled(index.isValid())
                self.paste_action.setEnabled(self.clipboard.source_path and index.isValid())
                self.rename_action.setEnabled(index.isValid())
                self.delete_action.setEnabled(index.isValid())

                menu.exec_(tree_view.mapToGlobal(point))
        except Exception as e:
            self.log_action(f"Error showing context menu: {e}")
            QMessageBox.warning(self, "Error", f"Error showing context menu: {e}")

    def setup_actions(self):
        try:
            self.copy_action = QAction("Copy", self)
            self.copy_action.setShortcut("Ctrl+C")
            self.copy_action.triggered.connect(self.copy_item)

            self.cut_action = QAction("Cut", self)
            self.cut_action.setShortcut("Ctrl+X")
            self.cut_action.triggered.connect(self.cut_item)

            self.paste_action = QAction("Paste", self)
            self.paste_action.setShortcut("Ctrl+V")
            self.paste_action.triggered.connect(self.paste_item)

            self.delete_action = QAction("Delete", self)
            self.delete_action.setShortcut("Delete")
            self.delete_action.triggered.connect(self.delete_item)

            self.rename_action = QAction("Rename", self)
            self.rename_action.setShortcut("F2")
            self.rename_action.triggered.connect(self.rename_item)

            self.properties_action = QAction("Properties", self)
            self.properties_action.setShortcut("Ctrl+P")
            self.properties_action.triggered.connect(self.show_properties)
        except Exception as e:
            self.log_action(f"Error setting up actions: {e}")
            QMessageBox.warning(self, "Error", f"Error setting up actions: {e}")

    def setup_toolbar(self):
        try:
            self.toolbar = QToolBar(self)
            self.addToolBar(self.toolbar)

            self.toolbar.addAction(self.copy_action)
            self.toolbar.addAction(self.cut_action)
            self.toolbar.addAction(self.paste_action)
            self.toolbar.addAction(self.delete_action)
            self.toolbar.addAction(self.rename_action)
            self.toolbar.addAction(self.properties_action)
        except Exception as e:
            self.log_action(f"Error setting up toolbar: {e}")
            QMessageBox.warning(self, "Error", f"Error setting up toolbar: {e}")

    def setup_status_bar(self):
        try:
            self.status_label = QLabel()
            self.statusBar().addWidget(self.status_label)
        except Exception as e:
            self.log_action(f"Error setting up status bar: {e}")
            QMessageBox.warning(self, "Error", f"Error setting up status bar: {e}")

    def copy_item(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                self.clipboard.copy(self.model1.filePath(index1))
            elif index2.isValid():
                self.clipboard.copy(self.model2.filePath(index2))
        except Exception as e:
            self.log_action(f"Error copying item: {e}")
            QMessageBox.warning(self, "Error", f"Error copying item: {e}")

    def cut_item(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                self.clipboard.cut(self.model1.filePath(index1))
            elif index2.isValid():
                self.clipboard.cut(self.model2.filePath(index2))
        except Exception as e:
            self.log_action(f"Error cutting item: {e}")
            QMessageBox.warning(self, "Error", f"Error cutting item: {e}")

    def paste_item(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                destination_path = self.model1.filePath(index1)
            elif index2.isValid():
                destination_path = self.model2.filePath(index2)
            else:
                return

            if self.clipboard.paste(destination_path):
                self.log_action(f"Pasted to: {destination_path}")
                if index1.isValid():
                    self.model1.setRootPath(self.model1.rootPath())
                    self.tree_view1.setRootIndex(self.model1.index(self.model1.rootPath()))
                elif index2.isValid():
                    self.model2.setRootPath(self.model2.rootPath())
                    self.tree_view2.setRootIndex(self.model2.index(self.model2.rootPath()))
        except Exception as e:
            self.log_action(f"Error pasting item: {e}")
            QMessageBox.warning(self, "Error", f"Error pasting item: {e}")

    def delete_item(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                file_path = self.model1.filePath(index1)
                self.perform_delete(file_path, "directory 1")
            elif index2.isValid():
                file_path = self.model2.filePath(index2)
                self.perform_delete(file_path, "directory 2")
        except Exception as e:
            self.log_action(f"Error deleting item: {e}")
            QMessageBox.warning(self, "Error", f"Error deleting item: {e}")

    def perform_delete(self, file_path, directory_name):
        try:
            if os.path.isdir(file_path):
                if os.path.basename(file_path).startswith("$"):
                    self.log_action(f"Skipped deletion of system directory: {file_path}")
                    return

                shutil.rmtree(file_path)
                self.log_action(f"Deleted from {directory_name}: {file_path}")
            elif os.path.isfile(file_path):
                os.remove(file_path)
                self.log_action(f"Deleted from {directory_name}: {file_path}")
        except PermissionError as e:
            self.log_action(f"PermissionError: {e}")
            QMessageBox.warning(self, "Permission Error", f"PermissionError: {e}")
        except Exception as e:
            self.log_action(f"Error performing delete: {e}")
            QMessageBox.warning(self, "Error", f"Error performing delete: {e}")

    def rename_item(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                index = index1
                model = self.model1
                directory_name = "directory 1"
            elif index2.isValid():
                index = index2
                model = self.model2
                directory_name = "directory 2"
            else:
                return

            old_path = model.filePath(index)
            new_name, ok = QInputDialog.getText(self, "Rename", "New Name:", text=os.path.basename(old_path))

            if ok and new_name:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                self.log_action(f"Renamed: {old_path} to {new_path}")
        except Exception as e:
            self.log_action(f"Error renaming item: {e}")
            QMessageBox.warning(self, "Error", f"Error renaming item: {e}")

    def show_properties(self):
        try:
            index1 = self.tree_view1.currentIndex()
            index2 = self.tree_view2.currentIndex()
            if index1.isValid():
                index = index1
                model = self.model1
            elif index2.isValid():
                index = index2
                model = self.model2
            else:
                return

            file_path = model.filePath(index)
            file_stats = os.stat(file_path)
            size = f"{file_stats.st_size / (1024 * 1024):.2f} MB"
            properties_str = f"Path: {file_path}\nSize: {size}\nLast Modified: {file_stats.st_mtime}"
            QMessageBox.information(self, "Properties", properties_str)
        except Exception as e:
            self.log_action(f"Error showing properties: {e}")
            QMessageBox.warning(self, "Error", f"Error showing properties: {e}")

    def log_action(self, action):
        try:
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            logging.info(f"{timestamp} - {action}")
            self.logs_browser.append(f"{timestamp} - {action}")
        except Exception as e:
            print(f"Error logging action: {e}")

    def update_status_bar(self, index):
        try:
            if index.isValid():
                file_path = self.model1.filePath(index) if self.tree_view1.currentIndex() == index else self.model2.filePath(index)
                self.status_label.setText(file_path)
            else:
                self.status_label.setText("")
        except Exception as e:
            self.log_action(f"Error updating status bar: {e}")

    def on_copied(self, path):
        try:
            self.log_action(f"Copied: {path}")
        except Exception as e:
            self.log_action(f"Error handling copy signal: {e}")

    def on_cut(self, path):
        try:
            self.log_action(f"Cut: {path}")
        except Exception as e:
            self.log_action(f"Error handling cut signal: {e}")

    def on_pasted(self, path):
        try:
            self.log_action(f"Pasted: {path}")
        except Exception as e:
            self.log_action(f"Error handling paste signal: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManagerApp()
    window.setGeometry(100, 100, 1200, 600)
    window.show()
    sys.exit(app.exec_())
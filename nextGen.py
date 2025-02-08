import sys
import yaml
import random
from itertools import product
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton, QTextEdit,
    QLabel, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt
import os

class CartesianProductApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cartesian Product GUI")
        self.setGeometry(100, 100, 800, 600)
        self.data = {}
        self.selected_items1 = []
        self.selected_items2 = []
        self.init_ui()
        self.load_yaml()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Horizontal layout for side-by-side QTreeWidgets
        h_layout = QHBoxLayout()

        # First QTreeWidget for selection
        self.tree_widget1 = QTreeWidget()
        self.tree_widget1.setHeaderLabel("Data Hierarchy 1")
        self.tree_widget1.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree_widget1.itemSelectionChanged.connect(self.handle_selection1)
        h_layout.addWidget(self.tree_widget1)

        # Second QTreeWidget for selection
        self.tree_widget2 = QTreeWidget()
        self.tree_widget2.setHeaderLabel("Data Hierarchy 2")
        self.tree_widget2.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree_widget2.itemSelectionChanged.connect(self.handle_selection2)
        h_layout.addWidget(self.tree_widget2)

        layout.addLayout(h_layout)

        # Slider for number of results
        slider_layout = QVBoxLayout()
        self.slider_label = QLabel("Number of results: 50")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 200)
        self.slider.setValue(50)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.valueChanged.connect(self.update_slider_label)
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.slider)
        layout.addLayout(slider_layout)

        # Compute Button
        compute_button = QPushButton("Generate Samples!")
        compute_button.clicked.connect(self.display_cartesian_product)
        layout.addWidget(compute_button)

        # TextEdit for displaying results
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

    def load_yaml(self):
        file_name = 'data.yaml'
        if not os.path.exists(file_name):
            QMessageBox.critical(self, "Error", f"File '{file_name}' not found in the current directory.")
            return

        try:
            with open(file_name, 'r') as file:
                self.data = yaml.safe_load(file)
            self.populate_tree(self.data, self.tree_widget1.invisibleRootItem())
            self.populate_tree(self.data, self.tree_widget2.invisibleRootItem())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load '{file_name}': {e}")

    def populate_tree(self, data, parent_item):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    item = QTreeWidgetItem([key])
                    parent_item.addChild(item)
                elif isinstance(value, dict):
                    item = QTreeWidgetItem([key])
                    parent_item.addChild(item)
                    self.populate_tree(value, item)

    def handle_selection1(self):
        selected_items = self.tree_widget1.selectedItems()
        self.selected_items1 = [item for item in selected_items if item.childCount() == 0]

    def handle_selection2(self):
        selected_items = self.tree_widget2.selectedItems()
        self.selected_items2 = [item for item in selected_items if item.childCount() == 0]

    def update_slider_label(self, value):
        self.slider_label.setText(f"Number of results: {value}")

    def display_cartesian_product(self):
        if len(self.selected_items1) != 1 or len(self.selected_items2) != 1:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one item from each hierarchy.")
            return

        try:
            list1 = self.get_item_path(self.selected_items1[0])
            list2 = self.get_item_path(self.selected_items2[0])

            if not isinstance(list1, list) or not isinstance(list2, list):
                QMessageBox.warning(self, "Selection Error", "Both selections must correspond to lists.")
                return

            total_combinations = len(list1) * len(list2)
            num_results = self.slider.value()

            if total_combinations > num_results:
                sampled_indices = random.sample(range(total_combinations), num_results)
                result = [divmod(index, len(list2)) for index in sampled_indices]
                result_pairs = [(list1[i], list2[j]) for i, j in result]
            else:
                result_pairs = list(product(list1, list2))

            self.result_text.clear()
            for item in result_pairs:
                self.result_text.append(f"{item}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def get_item_path(self, item):
        path = []
        while item is not None:
            path.insert(0, item.text(0))
            item = item.parent()
        data = self.data
        for key in path:
            data = data[key]
        return data

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CartesianProductApp()
    window.show()
    sys.exit(app.exec())

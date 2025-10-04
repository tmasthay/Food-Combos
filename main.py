import sys
import yaml
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QLabel, QHBoxLayout, QTextBrowser
)


def build_tree(parent, data):
    if isinstance(data, dict):
        for key, value in data.items():
            item = QTreeWidgetItem([key])
            parent.addChild(item)
            build_tree(item, value)
    elif isinstance(data, list):
        # Base unit, don't expand further
        pass


class ComboApp(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setWindowTitle("YAML Combo Generator")

        layout = QVBoxLayout()

        trees_layout = QHBoxLayout()
        self.tree1 = QTreeWidget()
        self.tree2 = QTreeWidget()
        self.tree1.setHeaderHidden(True)
        self.tree2.setHeaderHidden(True)

        # Fill trees
        build_tree(self.tree1.invisibleRootItem(), self.data)
        build_tree(self.tree2.invisibleRootItem(), self.data)

        trees_layout.addWidget(self.tree1)
        trees_layout.addWidget(self.tree2)

        layout.addLayout(trees_layout)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Number of results to generate")
        self.input_field.setText("50")

        self.button = QPushButton("Regenerate Random Combos")
        self.output = QTextBrowser()

        layout.addWidget(self.input_field)
        layout.addWidget(self.button)
        layout.addWidget(QLabel("Pairings:"))
        layout.addWidget(self.output)

        self.setLayout(layout)

        self.button.clicked.connect(self.generate_combos)

    def get_selected_list(self, tree):
        item = tree.currentItem()
        if not item:
            return None
        path = []
        while item:
            path.insert(0, item.text(0))
            item = item.parent()
        # Traverse dictionary using path
        d = self.data
        for p in path:
            d = d[p]
        if isinstance(d, list):
            return d
        return None

    def generate_combos(self):
        list1 = self.get_selected_list(self.tree1)
        list2 = self.get_selected_list(self.tree2)
        if not list1 or not list2:
            self.output.setHtml("Please select two valid list nodes.")
            return

        try:
            n = int(self.input_field.text())
        except ValueError:
            self.output.setHtml("Enter a valid number.")
            return

        wiki = '<a href="https://en.wikipedia.org/wiki/'
        seen = lambda x : 'Unreadable dish' if '%' in x else x
        max_len = max(len(str(x)) for x in [seen(x) for x in list1])
        combos = []
        for _ in range(n):
            a = random.choice(list1)
            b = random.choice(list2)

            
            seen_a = seen(a)
            seen_b = seen(b)
            
            num_spaces = max_len - len(seen_a) + 5
            spaces = ' ' * num_spaces

            a_html = f'{wiki}{a}">{seen_a}</a>{spaces}'
            b_html = f'{wiki}{b}">{seen_b}</a>'
            combos.append(f"{a_html}{b_html}") 

        self.output.setOpenExternalLinks(True)
        
        html = "<pre>" + "\n".join(combos) + "</pre>"
        self.output.setHtml(html)



if __name__ == "__main__":
    with open("data.yaml", "r") as f:
        data = yaml.safe_load(f)

    app = QApplication(sys.argv)
    window = ComboApp(data)
    window.show()
    sys.exit(app.exec())

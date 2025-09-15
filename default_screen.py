from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

class DefaultScreen(QWidget):
    def __init__(self, parent_window, top_margin=40, side_margin=40, spacing=30):
        super().__init__()
        self.parent_window = parent_window
        self.setStyleSheet("border: none; background-color: transparent;")  # ili transparent ako treba

        # Glavni layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(side_margin, top_margin, side_margin, top_margin)
        self.layout.setSpacing(spacing)
        self.layout.setAlignment(Qt.AlignTop)  # Svi elementi kreću od vrha

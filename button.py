# custom_button.py
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

class IconTextButton(QWidget):
    def __init__(self, text, icon_path, click_callback=None, parent=None, reverse=False, icon_size=24):
        super().__init__(parent)

        self.setStyleSheet("""
            QWidget {
                border: none;
            }
        """)
        
        layout = QHBoxLayout(self)
        # VAŽNO: Postavi margine i spacing na minimum
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)  # Malo spacing između ikone i teksta
        
        # Tekst
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.text_label.setFont(QFont("Arial", 14, 200))

        # Ikonica
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QPixmap(icon_path).scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        if reverse:
            layout.addWidget(self.icon_label)
            layout.addWidget(self.text_label)
        else:
            layout.addWidget(self.text_label)
            layout.addWidget(self.icon_label)

        # VAŽNO: Postavi size policy da se dugme ne razvlači nepotrebno
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self.click_callback = click_callback

    def mousePressEvent(self, event):
        if self.click_callback:
            self.click_callback()
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize
import os
from color import COLORS


class TopBar(QWidget):
    def __init__(self, parent=None, title=None, logo=True, show_back=False, on_back=None):
        super().__init__(parent)

        self.setFixedHeight(80)
        self.setStyleSheet("""
            TopBar {
                background-color: #ffffff;
            }
            QPushButton {
                border: none;
                background: transparent;
                font-size: 18px;
            }
        """)

        # --- Glavni HBox Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)

        # --- Leva zona ---
        self.left_container = QWidget()
        left_layout = QHBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        if show_back:
            icon_path = os.path.join("public", "icons", "back_arrow.png")
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)

                # Kreiraj dugme BEZ teksta i sa ikonicom
                self.back_button = QPushButton()
                self.back_button.setIcon(icon)
                self.back_button.setIconSize(QSize(48, 48))  # Podesi veličinu ikone
#                self.back_button.setFixedSize(40, 40)               # Podesi dimenzije dugmeta

                # Ako želiš ravan stil bez okvira
                self.back_button.setStyleSheet("border: none; background: transparent;")
            if on_back:
                self.back_button.clicked.connect(on_back)
            left_layout.addWidget(self.back_button, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        else:
            # Dodaj prazan prostor iste širine kao dugme
            spacer = QLabel()
            spacer.setFixedWidth(40)
            left_layout.addWidget(spacer)

        # Leva zona fiksna širina prema sadržaju
        self.left_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout.addWidget(self.left_container)

        # --- Središnja zona (Centrirani logo ili naslov) ---
        self.center_label = QLabel()
        self.center_label.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join("public", "graphs", "logo.png")
        if logo and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.center_label.setPixmap(pixmap.scaledToHeight(80, Qt.SmoothTransformation))
        elif title:
            self.center_label.setText(title)
            self.center_label.setFont(QFont("Inter", 24, QFont.Bold))
            self.center_label.setStyleSheet(f"color: {COLORS['main_color']}")

        # Centralna zona se širi da uzme sav preostali prostor
        self.center_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.center_label, alignment=Qt.AlignCenter)

        # --- Desna zona (isti "vizuelni" balans kao leva) ---
        self.right_container = QWidget()
        right_layout = QHBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Prazan placeholder širine 40px za balansiranje
        placeholder = QLabel()
        placeholder.setFixedWidth(40)
        right_layout.addWidget(placeholder)

        self.right_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout.addWidget(self.right_container)

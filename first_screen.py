from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import os
from botbar import BottomBar
from lang import LANG
from color import COLORS

class FirstScreen(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        screen_height = parent_window.screen_height

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: transparent;
            }
            #LowerSection {
                border-top: 2px solid #ddd;
                background-color: white;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)

        # --- Gornja sekcija ---
        upper_section = QFrame()
        upper_section.setFixedHeight(screen_height // 2)
        upper_layout = QVBoxLayout(upper_section)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_pixmap = QPixmap(os.path.join("public","graphs","logo.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(230, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo_label.setText("EIK HOTEL")
        upper_layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        # --- Donja sekcija ---
        lower_section = QFrame()
        lower_section.setObjectName("LowerSection")
        lower_section.setFixedHeight(screen_height // 2)
        

        lower_layout = QVBoxLayout(lower_section)
        lower_layout.setSpacing(20)

        title_label = QLabel(LANG["TITLE"])
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Inter", 28, QFont.Bold))
        title_label.setStyleSheet(f'color: {COLORS["main_color"]};')

        description_label = QLabel(LANG["DESC"])
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setFont(QFont("Arial", 14))
        description_label.setStyleSheet(f'color: {COLORS["black_1"]};')
        description_label.setWordWrap(True)

        chart_label = QLabel()
        chart_label.setAlignment(Qt.AlignCenter)
        chart_label.setFixedHeight(screen_height // 4)
        chart_pixmap = QPixmap(os.path.join("public","graphs","scancard.png"))
        if not chart_pixmap.isNull():
            chart_label.setPixmap(chart_pixmap.scaled(
                chart_label.width(), chart_label.height(), 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            chart_label.setText("SCAN CARD")

        bottom_bar = BottomBar(
            show_back=False
        )
        

        # Dodaj u layout
        lower_layout.addWidget(title_label)
        lower_layout.addWidget(description_label)
        lower_layout.addWidget(chart_label)
        lower_layout.addWidget(bottom_bar)

        layout.addWidget(upper_section)
        layout.addWidget(lower_section)


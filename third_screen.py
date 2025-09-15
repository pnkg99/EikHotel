from PyQt5.QtWidgets import QWidget, QGridLayout, QFrame, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import Qt
import os
from default_screen import DefaultScreen
from topbar import TopBar
from botbar import BottomBar
from color import COLORS
from msgmodal import CustomModal
from services.web import deactivate_nfc

class ThirdScreen(DefaultScreen):
    def __init__(self, parent_window):
        super().__init__(parent_window, top_margin=0, side_margin=0, spacing=0)
        self.parent_window = parent_window
        # --- Top Bar ---
        top_bar = TopBar()
        self.layout.addWidget(top_bar)

        # --- Centralni widget za grid ---
        center_widget = QWidget()
        grid_layout = QGridLayout(center_widget)
        grid_layout.setSpacing(30)
        grid_layout.setContentsMargins(20, 20, 20, 40) 
        grid_layout.setAlignment(Qt.AlignCenter)

        # Lista kocki sa nazivom i slikom
        restaurant_png = os.path.join("public", "graphs", "restaurant.png")
        parkingt_png = os.path.join("public", "graphs", "parking.png")
        history_png = os.path.join("public", "graphs", "history.png")
        decode_png = os.path.join("public", "graphs", "decode.png")
        
        boxes = [
            ("RESTORAN", restaurant_png, lambda: self.parent_window.screen_manager.show_screen("restaurant")),
            ("PARKING", parkingt_png, lambda: self.parent_window.screen_manager.show_screen("parking")),
            ("ISTORIJA", history_png, lambda: self.parent_window.screen_manager.show_screen("history")),
            ("DEKODIRAJ KARTICU", decode_png, lambda: self.process_decode_card()),
        ]

        for idx, (title, icon_path, action) in enumerate(boxes):
            row = idx // 2
            col = idx % 2

            # Okvir kocke
            box = QFrame()
            box.setFixedSize(360, 360)
            box.setStyleSheet("""
                QFrame {
                    border-radius: 20px;
                    background-color: rgb(250, 248, 245);
                }
            """)

            # --- Klik handler ---
            box.mousePressEvent = lambda event, act=action: act()

            # --- Senka ---
            shadow = QGraphicsDropShadowEffect(box)
            shadow.setBlurRadius(12)
            shadow.setXOffset(0)
            shadow.setYOffset(6)
            shadow.setColor(QColor(0, 0, 0, 35))
            box.setGraphicsEffect(shadow)

            # --- Slika ---
            pixmap = QPixmap(icon_path).scaled(
                300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            image_label = QLabel(box)
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("background: transparent;")
            image_label.setGeometry(0, 0, box.width(), box.height())

            # --- Tekst ---
            title_label = QLabel(title, box)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setFont(QFont("Inter", 24, QFont.Bold))
            title_label.setStyleSheet(f"color: {COLORS['vibrant']}; background: transparent;")
            title_label.setGeometry(0, 0, box.width(), box.height())

            grid_layout.addWidget(box, row, col, alignment=Qt.AlignCenter)

        # --- Dodaj centralni widget ---
        self.layout.addStretch()
        self.layout.addWidget(center_widget, alignment=Qt.AlignCenter)
        self.layout.addStretch()

        # --- Bottom Bar ---
        bottom_bar = BottomBar(
            show_back=True,
            on_back=self.cancel_form,
            variant=2
        )
        self.layout.addWidget(bottom_bar)
        
    def process_decode_card(self):
        modal = CustomModal(
            message="Da li ste sigurni da želite da dekodirate karticu?",
            modal_type="question"
        )
        modal.confirmed.connect(self.finish_decoding)
        modal.cancelled.connect(lambda: print("Abort decoding"))
        modal.show()


    def finish_decoding(self):
        deactivate_nfc(self.parent_window.screen_manager.token,self.parent_window.screen_manager.cvc)
        modal = CustomModal(message="Kartica Dekodirana")
        modal.show()
        self.parent_window.screen_manager.show_screen("home")

    def cancel_form(self):
        """Emituje signal za završetak narudžbe"""
        modal = CustomModal(
            message="Da li želite da izađete?", 
            modal_type="leave"
        )
        # Povezivanje sa funkcijama
        modal.confirmed.connect(lambda: self.parent_window.screen_manager.show_screen("home"))
        modal.cancelled.connect(lambda: print("Nothing"))
        modal.show()
        

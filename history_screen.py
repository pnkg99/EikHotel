from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QSizePolicy,QSpacerItem,
                             QLabel, QScrollArea, QFrame, QScroller,QScrollerProperties )
from PyQt5.QtGui import  QFont, QIcon
from PyQt5.QtCore import QSize, Qt
from default_screen import DefaultScreen
from topbar import TopBar
from botbar import BottomBar
import os
from msgmodal import CustomModal

class HistoryScreen(DefaultScreen):
    def __init__(self, parent_window):
        super().__init__(parent_window, top_margin=0, side_margin=0, spacing=0)

        # --- Top Bar ---
        top_bar = TopBar(show_back=True,logo=False,title="Istorija korišćenja kartice".upper(), on_back=(lambda: self.parent_window.screen_manager.show_screen("customer")))
        self.layout.addWidget(top_bar)

        # --- Scroll Area sa transakcijama ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)

        # Omogućavamo gestove za touch i drag
        for gesture in (
            QScroller.TouchGesture,
            QScroller.LeftMouseButtonGesture
        ):
            QScroller.grabGesture( self.scroll_area.viewport(), gesture)

        sc = QScroller.scroller(self.scroll_area.viewport())
        props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.AxisLockThreshold, 1.0)
        sc.setScrollerProperties(props)


        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(0)  # bez space između redova
        self.list_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area.setWidget(self.list_container)
        self.layout.addWidget(self.scroll_area)

        # --- Bottom Bar ---
        bottom_bar = BottomBar()
        self.layout.addWidget(bottom_bar)

    def update_history(self, transactions):
        """Popunjava listu transakcija"""

        # Očisti ceo layout (widgete, separatore i stretch)
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
            del item

        # Dodaj nove transakcije
        for transaction in transactions:
            item_widget = TransactionWidget(transaction)
            self.list_layout.addWidget(item_widget)

            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: #D5D5D5;")
            self.list_layout.addWidget(separator)

        # Stretch na kraju da gura sadržaj gore
        self.list_layout.addStretch()

    def clear_layout(self, layout):
        """Pomoćna metoda za čišćenje ugnježdenih layouta"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
            del item


class TransactionWidget(QWidget):
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.setup_ui()
        
    def get_transaction_type_name(self, transaction_type):
        """Vraća naziv transakcije na osnovu type-a"""
        type_names = {
            "1": "Aktivacija kartice",
            "2": "Parking",
            "3": "Ulazak u restoran",
            "4": "Ulazak u teretanu",
            "5": "Porudžbina iz restorana"
        }
        return type_names.get(transaction_type, f"Tip {transaction_type}")

    def setup_ui(self):
        self.setStyleSheet("""
            padding-top: 8px;
            padding-bottom: 8px;
            color:#292929;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(30)

        # Title
        title = QLabel(self.get_transaction_type_name(self.transaction["type"]))
        title.setFont(QFont("Inter", 12, 400))
        title.setFixedWidth(200)

        # Date
        date = QLabel(self.transaction["transation_date"])
        date.setFont(QFont("Inter", 12, 400))
        date.setFixedWidth(100)

        # Time
        time = QLabel(self.transaction["transation_time"])
        time.setFont(QFont("Inter", 12, 400))
        time.setFixedWidth(100)

        layout.addWidget(title)
        layout.addWidget(date)
        layout.addWidget(time)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Dugme za tip 5
        if self.transaction["type"] == "5":
            icon_path = os.path.join("public", "icons", "front_arrow.png")
            button = QPushButton()
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(26, 26))  # Prilagodi veličinu ikone
            button.setStyleSheet("QPushButton { border: none; padding: 0px; }")
            button.clicked.connect(self.open_modal)
            layout.addWidget(button)

    def open_modal(self):
        modal = CustomModal(modal_type="transaction", transaction=self.transaction)
        modal.show()


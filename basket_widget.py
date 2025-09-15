from PyQt5 import QtWidgets, QtCore, QtGui
from color import COLORS

# Boje
GRAY_COLOR = COLORS["grey"]

class BasketItemWidget(QtWidgets.QFrame):
    quantity_changed = QtCore.pyqtSignal(str, int)
    remove_item      = QtCore.pyqtSignal(str)
    add_to_cart      = QtCore.pyqtSignal(dict)

    def __init__(self, product_data: dict, quantity: int, parent=None):
        super().__init__(parent)
        self.product = product_data
        self.quantity = int(quantity)
        self._setup_ui()

    def _setup_ui(self):
        # Stil widgeta: donja linija i vertikalni padding
        self.setObjectName("basketItem")
        self.setStyleSheet(f"""
        QFrame#basketItem {{
            background-color: transparent;
            border: none;
            border-bottom: 1px solid #D5D5D5;
            padding: 8px;
        }}
        """)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # --- Gornji red: naziv | količina | ukupna cena ---
        top_layout = QtWidgets.QHBoxLayout()

        raw_name = self.product.get('title', 'Nepoznat proizvod')

        name_label = QtWidgets.QLabel()
        name_label.setStyleSheet("color: #242424;")
        name_label.setWordWrap(True)

        font = QtGui.QFont("Inter", 12, QtGui.QFont.Weight.Bold)
        name_label.setFont(font)

        # Postavi maksimalno 2 reda
        line_height = name_label.fontMetrics().height()
        name_label.setFixedHeight(int(line_height * 2.2))  # za dva reda

        # Ograniči širinu da QLabel zna kada da prelomi
        name_label.setFixedWidth(150)  # prilagodi svom layoutu

        # Ako ne staje u 2 reda, skrati i dodaj "..."
        fm = name_label.fontMetrics()
        elided_text = fm.elidedText(raw_name, QtCore.Qt.ElideRight, name_label.width() * 2)
        name_label.setText(elided_text)

        # Dodaj vertikalno centrirano
        top_layout.addWidget(name_label, alignment=QtCore.Qt.AlignVCenter)

        # --- Količina ---
        self.qty_label = QtWidgets.QLabel(f"*{self.quantity}")
        self.qty_label.setFont(QtGui.QFont("Inter", 12))
        self.qty_label.setStyleSheet(f"color: {GRAY_COLOR};")
        self.qty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.qty_label, alignment=QtCore.Qt.AlignVCenter)

        # --- Cena ---
        self.price_label = QtWidgets.QLabel(f"{self.get_product_price()*self.quantity} rsd")
        self.price_label.setFont(QtGui.QFont("Inter", 12, QtGui.QFont.Weight.Bold))
        self.price_label.setStyleSheet("color: #242424;")
        self.price_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(self.price_label, alignment=QtCore.Qt.AlignVCenter)

        main_layout.addLayout(top_layout)


        # --- Donji red: dugmići ---
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setContentsMargins(0,0,0,0)
        import os
        remove_png = os.path.join("public", "icons", "remove.png")
        minus_png = os.path.join("public", "icons", "minus.png")
        plus_png = os.path.join("public", "icons", "plus.png")
        # 1) Dugme za brisanje (X)
        btn_remove = QtWidgets.QToolButton()
        btn_remove.setIcon(QtGui.QIcon(remove_png))
        btn_remove.setIconSize(QtCore.QSize(48,48))
        btn_remove.setStyleSheet("background: transparent; border: none;")
        btn_remove.setAutoRaise(False)
        btn_remove.clicked.connect(lambda: self.remove_item.emit(str(self.product['id'])))
        bottom_layout.addWidget(btn_remove)

        bottom_layout.addStretch()

        # 2) Dugme za smanjenje količine (-)
        btn_minus = QtWidgets.QToolButton()
        btn_minus.setIcon(QtGui.QIcon(minus_png))
        btn_minus.setIconSize(QtCore.QSize(48,48))
        btn_minus.setStyleSheet("background: transparent; border: none;")
        btn_minus.setAutoRaise(True)
        btn_minus.clicked.connect(lambda: self._change_quantity(-1))
        bottom_layout.addWidget(btn_minus)

        bottom_layout.addStretch()

        # 3) Dugme za povećanje količine (+)
        btn_plus = QtWidgets.QToolButton()
        btn_plus.setIcon(QtGui.QIcon(plus_png))
        btn_plus.setIconSize(QtCore.QSize(48,48))
        btn_plus.setStyleSheet("background: transparent; border: none;")
        btn_plus.setAutoRaise(True)
        btn_plus.clicked.connect(lambda: self.add_to_cart.emit(self.product))

        bottom_layout.addWidget(btn_plus)

        main_layout.addLayout(bottom_layout)

    def get_product_price(self):
        return float(self.product.get('price',0))

    def _change_quantity(self, delta: int):
        new_qty = max(0, self.quantity + delta)
        if new_qty != self.quantity:
            self.quantity = new_qty
            # Emituj signal ka spoljnom kontroleru
            print(109, self.product['id'], new_qty )
            self.quantity_changed.emit(self.product['id'], new_qty)
            # Ažuriraj UI
            self.qty_label.setText(f"x{new_qty}")
            total = self.get_product_price() * new_qty
            self.price_label.setText(f"{total} rsd")


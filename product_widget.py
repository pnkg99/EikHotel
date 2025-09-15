from PyQt5 import QtWidgets, QtCore, QtGui
from image_cache import get_cached_image
from msgmodal import CustomModal
# Boje
ACCENT_COLOR = "#E1B10D"
GRAY_COLOR = "#808080"
RED_COLOR = "#f44336"
BORDER_COLOR = "#D5D5D5"

  
class ProductWidget(QtWidgets.QFrame):
    """Widget za prikaz jednog proizvoda"""
    add_to_cart = QtCore.pyqtSignal(dict)

    def __init__(self, product_data: dict, parent=None):
        super().__init__(parent)
        self.product = product_data
        self.setObjectName("productItemFrame")
        self.setup_ui()

    def setup_ui(self):
        # Stil
        self.setStyleSheet(f"""
        QFrame#productItemFrame {{
            background-color: transparent;
            border: none;
            border-bottom: 1px solid {BORDER_COLOR};
        }}
        """)
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(20)

        # Levi deo: slika, naziv, opis
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.img_label = QtWidgets.QLabel()
        self.img_label.setFixedSize(180, 120)
        self.img_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet(f"""
        QLabel {{
            background-color: white;
            border-radius: 8px;
        }}
        """)

        pm = get_cached_image(str(self.product.get("id", "")),
                              self.product.get("photo", ""),
                              QtCore.QSize(180, 120))
        if not pm.isNull():
            self.img_label.setPixmap(pm)
        else:
            self.img_label.setText("📦")
            
        # Kontejner za naziv i opis sa malim spacingom
        text_container = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)  # Mali spacing između naziva i opisa
        
        name_label = QtWidgets.QLabel(self.product.get('title', 'Nepoznat proizvod'))
        name_label.setFont(QtGui.QFont("Inter", 14, QtGui.QFont.Weight.Bold))
        name_label.setStyleSheet("color: #292929;")

        # Bolja provera opisa
        raw_desc = self.product.get('description')
        desc_text = str(raw_desc).strip() if raw_desc else ''
        if not desc_text or desc_text == "None":
            desc_text = 'Nema opisa'
        elif len(desc_text) > 60:
            desc_text = desc_text[:57] + '...'
        desc_label = QtWidgets.QLabel(desc_text)
        desc_label.setFont(QtGui.QFont("Inter", 11, 400))
        desc_label.setStyleSheet(f"color: #292929;")
        desc_label.setWordWrap(True)

        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)

        left_layout.addWidget(self.img_label)
        left_layout.addSpacing(8)  # Spacing između slike i teksta
        left_layout.addWidget(text_container)
        left_layout.addSpacing(20)  # Veći spacing do donjeg bordera
        left_layout.addStretch()
        
        main_layout.addLayout(left_layout)

        # Desni deo: cena, dugme "Dodaj", dugme "Više"
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        # Stretch gore da bi se elementi centrirali vertikalno
        right_layout.addStretch()

        # --- Price layout ---
        self.price = float(self.product.get('price', 0))
        price_value = QtWidgets.QLabel(f"{self.price:.2f}")
        price_value.setFont(QtGui.QFont("Inter", 16, QtGui.QFont.Weight.Bold))
        price_value.setStyleSheet(f"color: #EFA90F;")

        currency = QtWidgets.QLabel("rsd")
        currency.setFont(QtGui.QFont("Inter", 12, 600))
        currency.setStyleSheet("color: #606060;")

        price_layout = QtWidgets.QHBoxLayout()
        price_layout.setContentsMargins(0, 0, 0, 0)
        price_layout.setSpacing(4)
        price_layout.addWidget(price_value)
        price_layout.addWidget(currency)

        right_layout.addLayout(price_layout)

        # --- Add button ---
        add_btn = QtWidgets.QPushButton("Dodaj")
        add_btn.setFont(QtGui.QFont("Inter", 16, QtGui.QFont.Weight.Bold))
        add_btn.setStyleSheet(f"""
        QPushButton {{
            background: #C29A43;
            color: white;
            padding: 12px;
            border-radius: 8px;
        }}
        """)
        add_btn.clicked.connect(self.add_clicked)
        right_layout.addWidget(add_btn)
        
        right_layout.addSpacing(16)  # Veći spacing između "Dodaj" i "Više"

        # --- More button ---
        more_btn = QtWidgets.QPushButton("Više")
        more_btn.setFont(QtGui.QFont("Inter", 10,  500))
        more_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        more_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            text-decoration: underline;
            color:black;
            padding: 12px 6px;
        }}
        """)
        more_btn.clicked.connect(self.view_details)
        right_layout.addWidget(more_btn, alignment=QtCore.Qt.AlignRight)

        # Stretch dole da bi se elementi centrirali vertikalno
        right_layout.addStretch()

        main_layout.addLayout(right_layout) 
    
    def add_clicked(self):
        self.add_to_cart.emit(self.product)

    def view_details(self):
        modal = CustomModal(modal_type="product", transaction=self.product)
        modal.add_to_cart.connect(self.add_clicked)
        modal.show()

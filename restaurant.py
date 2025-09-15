from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QButtonGroup
from basket_widget import BasketItemWidget
from product_widget import ProductWidget
from topbar import TopBar
from msgmodal import CustomModal
from services.web import checkout_service

class Restaurant(QtWidgets.QMainWindow):
    order_action = QtCore.pyqtSignal(str, dict)  # emituje "finish" ili "cancel"

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.setWindowTitle("Restaurant")
        self.resize(900, 700)
        self.parent_window=parent_window
        
        # Inicijalizacija atributa
        self.basket_items = {}
        self.categories = []
        self.slug = None
        # Setup UI
        self._setup_ui()
        self._init_scrollers()
        self._setup_total_label()
        self._setup_action_buttons()

    def _setup_ui(self):
        """Kreira kompletan UI"""
        # Kreiramo centralni widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName('CatalogPage')
        
        # Glavni vertikalni layout
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        # --- Top Bar samo sa logom ---
        top_bar = TopBar(show_back=True, on_back=(lambda: self.parent_window.screen_manager.show_screen("customer")))

        main_layout.addWidget(top_bar)

        # -------------------- Gornji deo - Kategorije --------------------
        self.categoryScrollArea = QtWidgets.QScrollArea()
        self.categoryScrollArea.setObjectName("categoryScrollArea")
        self.categoryScrollArea.setFixedHeight(50)
        self.categoryScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.categoryScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.categoryScrollArea.setWidgetResizable(True)

        # Sadržaj scrola za kategorije
        category_content = QtWidgets.QWidget()
        self.cat_layout = QtWidgets.QHBoxLayout(category_content)
        self.cat_layout.setContentsMargins(20,5,20,5)
        self.cat_layout.setSpacing(12)
        self.cat_layout.addStretch()

        self.categoryScrollArea.setWidget(category_content)
        self.cat_contents = category_content
        main_layout.addWidget(self.categoryScrollArea)

        # -------------------- Glavni deo 60:40 --------------------
        main_horizontal = QtWidgets.QHBoxLayout()
        main_horizontal.setContentsMargins(0,0,0,0)
        main_horizontal.setSpacing(0)
        main_layout.addLayout(main_horizontal, 1)

        # Container za proizvode sa border-om
        product_container = QtWidgets.QWidget()
        product_container_layout = QtWidgets.QVBoxLayout(product_container)
        product_container_layout.setContentsMargins(0, 10, 0, 10)
        product_container_layout.setSpacing(0)

        # Proizvodi (60%)
        self.productScrollArea = QtWidgets.QScrollArea()
        self.productScrollArea.setObjectName("productScrollArea")
        self.productScrollArea.setWidgetResizable(True)
        self.productScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.productScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.productScrollArea.setStyleSheet("""
            QScrollArea#productScrollArea {
                border-right: 1px solid #D5D5D5;
                border-radius: 2px;
            }
        """)
        
        product_content = QtWidgets.QWidget()
        self.prod_layout = QtWidgets.QVBoxLayout(product_content)
        self.prod_layout.setContentsMargins(10,5,10,5)
        self.prod_layout.setSpacing(10)
        self.prod_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.productScrollArea.setWidget(product_content)
        self.prod_contents = product_content
        product_container_layout.addWidget(self.productScrollArea)
        main_horizontal.addWidget(product_container, 6)  # 60%

        # Korpa (40%)
        self.basketScrollArea = QtWidgets.QScrollArea()
        self.basketScrollArea.setObjectName("basketScrollArea")
        self.basketScrollArea.setWidgetResizable(True)
        self.basketScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.basketScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.basketScrollArea.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        basket_content = QtWidgets.QWidget()
        self.basket_layout = QtWidgets.QVBoxLayout(basket_content)
        
        # Margine za korpu
        vsb_width = self.basketScrollArea.verticalScrollBar().sizeHint().width()
        self.basket_layout.setContentsMargins(vsb_width, 10, vsb_width, 10)
        self.basket_layout.setSpacing(4)
        
        self.basketScrollArea.setWidget(basket_content)
        self.basket_contents = basket_content
        main_horizontal.addWidget(self.basketScrollArea, 4)  # 40%

        # -------------------- Footer --------------------
        footer = QtWidgets.QFrame()
        footer.setObjectName("footer")
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.setContentsMargins(16,16,16,16)
        footer_layout.setSpacing(16)
        main_layout.addWidget(footer, 0)

        # Dugmad
        self.cancelOrderButton = QtWidgets.QPushButton("Otkaži")
        self.cancelOrderButton.setObjectName("cancelOrderButton")
        self.cancelOrderButton.setMinimumHeight(64)
        self.cancelOrderButton.setStyleSheet("""
            QPushButton {
                background: #E11B1B;
                font-family: Inter;
                font-weight: 600;
                font-size: 20px;
                color: white;
                border-radius: 16px;
                border: none;
            }
        """)
        footer_layout.addWidget(self.cancelOrderButton, 3)

        self.finishOrderButton = QtWidgets.QPushButton("Završi račun")
        self.finishOrderButton.setObjectName("finishOrderButton")
        self.finishOrderButton.setMinimumHeight(64)
        self.finishOrderButton.setStyleSheet("""
            QPushButton {
                background: #EFA90F;
                font-family: Inter;
                font-weight: 600;
                font-size: 20px;
                color: white;
                border-radius: 16px;
                border: none;
            }
        """)
        footer_layout.addWidget(self.finishOrderButton, 7)

        # Postavljamo border za centralni widget
        self.setStyleSheet("border: none;")

    def update_slug(self, new_slug):
        """Ažurira slug kada se pročita NFC kartica"""
        self.slug = new_slug
        print(f"Restaurant slug updated to: {new_slug}")

    def _init_scrollers(self):
        """Inicijalizuje scroll areas sa touch gestures"""
        for scroll in (self.productScrollArea, self.basketScrollArea):
            # Isključujemo default scroll barove
            scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)

            vp = scroll.viewport()
            vp.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)

            # Omogućavamo gestove za touch i drag
            for gesture in (
                QtWidgets.QScroller.TouchGesture,
                QtWidgets.QScroller.LeftMouseButtonGesture
            ):
                QtWidgets.QScroller.grabGesture(vp, gesture)

            sc = QtWidgets.QScroller.scroller(vp)
            props = sc.scrollerProperties()
            props.setScrollMetric(QtWidgets.QScrollerProperties.AxisLockThreshold, 1.0)
            sc.setScrollerProperties(props)

    def _setup_total_label(self):
        """Kreira i dodaje total label u korpu"""
        self.total_label = QtWidgets.QLabel("0.00 rsd")
        self.total_label.setFont(QtGui.QFont("Inter", 18, QtGui.QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #292929;")
        self.total_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom)
        self.basket_layout.addWidget(self.total_label)

    def _setup_action_buttons(self):
        """Povezuje dugmad sa funkcijama"""
        self.finishOrderButton.clicked.connect(self._emit_finish)
        self.cancelOrderButton.clicked.connect(self._emit_cancel)
        print("[Restaurant] Action buttons connected")

    def _emit_finish(self):
        """Emituje signal za završetak narudžbe"""
        modal = CustomModal( "Da li želite da završite račun?", "confirmation", "question")
        # Povezivanje sa funkcijama
        modal.confirmed.connect(lambda: self.process_order())
        modal.cancelled.connect(lambda: print("Back to order"))

        modal.show()
        self.order_action.emit("finish", self.get_basket_items())

    def _emit_cancel(self):
        """Emituje signal za otkazivanje narudžbe"""
        self.clear_basket()
        self.parent_window.screen_manager.show_screen("customer")
    
    def process_order(self):
        print(self.basket_items)
        out = checkout_service(self.slug, self.basket_items)
        if out :
            modal = CustomModal("Uspešno ste izvršili kupovinu".upper(), "notification", "success")
            modal.show()
            self.clear_basket()
            self.parent_window.screen_manager.show_screen("home")
        else :
            modal = CustomModal("Greška".upper(), "notification", "error")
            modal.show()
    # -------------------------
    # Kategorije i proizvodi
    # -------------------------
    
    def update_categories(self, categories: list[dict]):
        self.categories = categories
        for i in reversed(range(self.cat_layout.count())):
            item = self.cat_layout.itemAt(i)
            if item:
                w = item.widget()
                if isinstance(w, QtWidgets.QPushButton):
                    self.cat_layout.takeAt(i)
                    w.deleteLater()

        # Button group
        self.button_group = QButtonGroup(self.cat_contents)
        self.button_group.setExclusive(True)

        first_button = None

        for cat in categories:
            btn = QtWidgets.QPushButton("#" + cat["name"], parent=self.cat_contents)
            btn.setMinimumSize(QtCore.QSize(80, 0))
            btn.setFont(QtGui.QFont("Inter", 12, QtGui.QFont.Weight.Bold))
            btn.setCheckable(True)
            self.button_group.addButton(btn)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #CEAE69;
                    padding: 8px 14px;
                    border-radius: 18px;
                    color: #CEAE69;
                    font-weight: 500;
                    background: transparent;
                }
                QPushButton:checked {
                    background-color: #CEAE69;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda _, prods=cat["pricelist_items"]: self.update_products(prods))
            self.cat_layout.insertWidget(self.cat_layout.count() - 1, btn)

            if first_button is None:
                first_button = (btn, cat["pricelist_items"])

        # Ako postoji prva kategorija - selektuj i učitaj proizvode
        if first_button:
            btn, prods = first_button
            btn.setChecked(True)
        self.update_products(prods)

    def update_products(self, products: list[dict]):
        """Ažurira listu proizvoda"""
        # Uklanjamo sve postojeće proizvode
        for i in reversed(range(self.prod_layout.count())):
            item = self.prod_layout.itemAt(i)
            if item:
                w = item.widget()
                if w:
                    self.prod_layout.takeAt(i)
                    w.deleteLater()

        # Dodajemo nove proizvode
        for prod in products:
            w = ProductWidget(prod, parent=self.prod_contents)
            w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            w.add_to_cart.connect(self.add_to_basket)
            self.prod_layout.addWidget(w)

    # -------------------------
    # Korpa
    # -------------------------
    
    def clear_basket(self):
        """Briše sve stavke iz korpe"""
        self.basket_items.clear()
        self.update_basket_display()

    def update_basket_display(self):
        """Ažurira prikaz korpe"""
        # Uklanjamo sve postojeće stavke osim total label-a
        for i in reversed(range(self.basket_layout.count())):
            item = self.basket_layout.itemAt(i)
            widget = item.widget()
            if widget and widget is not self.total_label:
                self.basket_layout.takeAt(i)
                widget.deleteLater()

        # Dodajemo nove stavke
        for product_id, item in self.basket_items.items():
            w = BasketItemWidget(item["product"], item["quantity"], parent=self.basket_contents)
            w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            w.quantity_changed.connect(self.update_item_quantity)
            w.remove_item.connect(self.remove_from_basket)
            w.add_to_cart.connect(self.add_to_basket)
            self.basket_layout.insertWidget(0, w)

        self.update_total()

    def add_to_basket(self, product: dict):
        """Dodaje proizvod u korpu"""
        product_id = str(product.get('id', product.get('name', '')))
        if product_id in self.basket_items:
            self.basket_items[product_id]["quantity"] += 1
        else:
            self.basket_items[product_id] = {"product": product, "quantity": 1}
        self.update_basket_display()

    def update_item_quantity(self, product_id: str, new_quantity: int):
        """Ažurira količinu stavke u korpi"""
        if new_quantity <= 0:
            self.remove_from_basket(product_id)
        else:
            if product_id in self.basket_items:
                self.basket_items[product_id]["quantity"] = new_quantity
                self.update_basket_display()

    def remove_from_basket(self, product_id: str):
        """Uklanja stavku iz korpe"""
        print(f"[DEBUG] remove_from_basket: trying to remove {product_id}")
        print(f"[DEBUG] basket_items keys: {list(self.basket_items.keys())}")

        if product_id in self.basket_items:
            print("[DEBUG] found item, deleting...")
            del self.basket_items[product_id]
            self.update_basket_display()
        else:
            print("[DEBUG] product_id NOT FOUND")

    def update_total(self):
        """Ažurira ukupnu cenu"""
        total = sum(float(item["product"].get('price', 0)) * int(item["quantity"])
                    for item in self.basket_items.values())
        self.total_label.setText(f"{total:.2f} rsd")

    def get_basket_items(self):
        """Vraća kopiju stavki iz korpe"""
        return self.basket_items.copy()

    def get_basket_total(self):
        """Vraća ukupnu cenu korpe"""
        return sum(float(item["product"].get('price', 0)) * int(item["quantity"])
                    for item in self.basket_items.values())

    def is_basket_empty(self):
        """Proverava da li je korpa prazna"""
        return len(self.basket_items) == 0
    
    


# Primer korišćenja
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    restaurant = Restaurant()
    restaurant.show()
    
    # Test podaci
    test_categories = [
        {
            "name": "Pica",
            "pricelist_items": [
                {"id": "1", "name": "Margarita", "price": 850},
                {"id": "2", "name": "Capricciosa", "price": 950}
            ]
        },
        {
            "name": "Burgeri", 
            "pricelist_items": [
                {"id": "3", "name": "Cheeseburger", "price": 650},
                {"id": "4", "name": "Chicken Burger", "price": 700}
            ]
        }
    ]
    
    restaurant.update_categories(test_categories)
    
    sys.exit(app.exec_())
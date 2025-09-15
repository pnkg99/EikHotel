from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
                             QApplication, QPushButton, QScrollArea, QScroller, QScrollerProperties, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal, QSize, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QPainter, QColor, QPixmap
from image_cache import get_cached_image
import os
from color import COLORS
from button import IconTextButton
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

class CustomModal(QWidget):
    # Signali za dugmad
    confirmed = pyqtSignal()
    cancelled = pyqtSignal()
    add_to_cart = pyqtSignal(dict)
    allocate_parking = pyqtSignal()
    
    def __init__(self, message="", modal_type="notification", icon_name="success", transaction=None, parent=None):
        """
        modal_type: 'notification', 'confirmation', 'leave', 'help'
        icon_name: 'success', 'error', 'warning', 'question'
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.modal_type = modal_type
        self.auto_close = modal_type == "notification"
        self.transaction = transaction
        self.parent_widget = parent

        screen = QApplication.desktop().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        screen_x = 0
        screen_y = 0

        # Postavi veličinu modala da pokriva parent/ekran
        self.resize(screen_width, screen_height)
        self.move(screen_x, screen_y)
        modal_width = 760
        modal_height = 420
        if modal_type == "notification":
            modal_height = 260
        elif modal_type == "transaction":
            pass
        elif modal_type == "product":
            modal_height = 600
        elif modal_type == "help":
            modal_width = 800
        elif modal_type == "parking":
            modal_height = 300
            pass
        else:
            modal_height = 200

        self.modal = QFrame(self)
        self.modal.setFixedSize(modal_width, modal_height)
        self.modal.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 32px;
            }
        """)

        # Pozicioniraj modal
        if modal_type == "help":
            # Help modal centriran po horizontali i poravnat na dno
            modal_x = (screen_width - modal_width) // 2
            modal_y_final = screen_height - modal_height
            modal_y_start = screen_height  # Početna pozicija ispod ekrana
            
            self.modal.move(modal_x, modal_y_start)
            self.modal_final_y = modal_y_final
            self.modal_start_y = modal_y_start
        else:
            # Ostali modali - centrirani po horizontali i vertikali
            modal_x = (screen_width - modal_width) // 2
            modal_y = (screen_height - modal_height) // 2
            self.modal.move(modal_x, modal_y)

        # Layout za modal
        layout = QVBoxLayout(self.modal)
        layout.setContentsMargins(40, 40, 40, 40)
        
        if modal_type == "notification":
            self._setup_notification_layout(layout, message, icon_name)
        elif modal_type == "transaction":
            self._setup_transaction_layout(layout)
        elif modal_type == "product":
            self._setup_product_layout(layout)
        elif modal_type == "help":
            self._setup_help_layout(layout) 
        elif modal_type == "parking":
            self._setup_parking_layout(layout)
        else:  # confirmation ili leave
            self._setup_confirmation_layout(layout, message)

        # Animacija
        if modal_type == "help":
            # Help modal - slide up animacija
            self.setWindowOpacity(0)
            
            # Fade in animacija
            self.fade_in = QPropertyAnimation(self, b"windowOpacity")
            self.fade_in.setDuration(150)
            self.fade_in.setStartValue(0)
            self.fade_in.setEndValue(1)
            
            # Slide up animacija
            self.slide_in = QPropertyAnimation(self.modal, b"geometry")
            self.slide_in.setDuration(300)
            self.slide_in.setStartValue(QRect(modal_x, modal_y_start, modal_width, modal_height))
            self.slide_in.setEndValue(QRect(modal_x, modal_y_final, modal_width, modal_height))
            self.slide_in.setEasingCurve(QEasingCurve.OutCubic)
            
            # Pokreni animacije
            self.fade_in.start()
            self.slide_in.start()
        else:
            # Ostali modali - obična fade animacija
            self.setWindowOpacity(0)
            self.fade_in = QPropertyAnimation(self, b"windowOpacity")
            self.fade_in.setDuration(200)
            self.fade_in.setStartValue(0)
            self.fade_in.setEndValue(1)
            self.fade_in.start()

        # Auto-zatvaranje samo za notification
        if self.auto_close:
            QTimer.singleShot(2000, self.close_with_fade)

    def _setup_parking_layout(self, layout):
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Gornji deo (naslov + opis)
        top_layout = QVBoxLayout()
        top_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        title = QLabel(self.transaction.get("name", "PARKING NUMBER"))
        title.setFont(QFont("Inter", 18, QFont.Bold))
        title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title.setStyleSheet("color: #242424;")
        top_layout.addWidget(title)

        description = QLabel(self.transaction.get("message", "Parking..."))
        description.setFont(QFont("Inter", 14))
        description.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        description.setWordWrap(True)
        description.setStyleSheet("color: #242424; margin-top: 8px; margin-bottom: 16px;")
        top_layout.addWidget(description)

        layout.addLayout(top_layout)

        # Srednji deo (tablice)
        plates_container = QHBoxLayout()
        plates_container.setSpacing(20)
        plates_container.setAlignment(Qt.AlignCenter)

        def create_plate_box(plate_text):
            plate_frame = QFrame()
            plate_frame.setFixedSize(200, 84)
            plate_frame.setStyleSheet("""
                QFrame {
                    border: 2px dashed #292929;
                    border-radius: 16px;
                    background-color: transparent;
                }
            """)
            plate_layout = QHBoxLayout(plate_frame)
            plate_layout.setContentsMargins(0, 0, 0, 0)
            plate_layout.setAlignment(Qt.AlignCenter)

            plate_label = QLabel(plate_text)
            plate_label.setFont(QFont("Inter", 20, QFont.Bold))
            plate_label.setStyleSheet("color: #C29A43; border: none; background: transparent;")
            plate_layout.addWidget(plate_label)

            return plate_frame

        for plate in self.transaction["plates"]:
            plates_container.addWidget(create_plate_box(plate))

        layout.addStretch(1)  # gura tablice ka sredini
        layout.addLayout(plates_container)
        layout.addStretch(1)

        # Donji deo (dugme)
        allocated = self.transaction.get("allocated", False)
        if self.transaction.get("status") == "current" :
            if not allocated :
                assign_button = QPushButton("Dodeli parking mesto kartici")
                assign_button.setFont(QFont("Inter", 14, QFont.Medium))
                assign_button.setFixedHeight(50)
                assign_button.setStyleSheet("""
                    QPushButton {
                        background-color: #C29A43;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 8px 16px;
                    }
                    QPushButton:hover {
                        background-color: #a88436;
                    }
                """)
                assign_button.clicked.connect(self.allocate_parking.emit)
                layout.addWidget(assign_button, alignment=Qt.AlignHCenter | Qt.AlignBottom)

    def _setup_help_layout(self, layout):
        """Jednostavan help layout - naslov, opis, dugme u donjem levom uglu"""
        
        self.modal.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top-left-radius: 32px;
                border-top-right-radius: 32px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)    
        # Naslov
        title = QLabel("POMOĆ")
        title.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        title.setFont(QFont("Inter", 24, QFont.Bold))
        title.setStyleSheet("color: #C29A43; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Opis
        description = QLabel(
            "Ako imate bilo kakvu poteškoću prilikom korišćenja softvera, "
            "slobodno nas kontaktirajte putem mejla ili nas pozovite.\n\n"
        )
        
        description.setFont(QFont("Inter", 14))
        description.setStyleSheet("color: #242424;")  # bez line-height
        description.setMaximumWidth(420)
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(description, 0, Qt.AlignHCenter)

        contacts = {
            "+381-65-111-2222": os.path.join("public", "icons", "call.png"),
            "support@example.com": os.path.join("public", "icons", "mail.png")
        }

        for text, icon_path in contacts.items():
            # Horizontalni layout za jednu liniju
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignCenter)  # centriraj ceo red
            row_layout.setSpacing(8)

            # Ikonica
            icon_label = QLabel()
            pixmap = QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignCenter)

            # Tekst
            text_label = QLabel(text)
            text_label.setFont(QFont("Inter", 14, 600))
            text_label.setStyleSheet("color: #242424;")
            text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            # Dodaj u red
            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)

            # Dodaj red u glavni layout
            layout.addLayout(row_layout)

        layout.setSpacing(10)
        
        # Stretch da gurne dugme na dno
        layout.addStretch()
        
        # Container za dugme u donjem levom uglu
        button_container = QHBoxLayout()
        button_container.setContentsMargins(0, 0, 0, 0)
        
        # Nazad dugme
        back_button = IconTextButton(
            "Nazad",
            os.path.join("public", "icons", "back_arrow.png"),
            click_callback=self._on_cancel,
            reverse=True,
            icon_size=46
        )
        
        # Dodaj dugme u levi ugao
        button_container.addWidget(back_button)
        button_container.addStretch()  # Gurne dugme u levi ugao
        
        layout.addLayout(button_container)
        
    def _setup_notification_layout(self, layout, message, icon_name):
        """Layout za notification modal - ikonica gore, tekst dole"""
        self.icon_label = QLabel()
        icon_path = os.path.join("public", "icons", f"{icon_name}.png")
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path).scaled(116, 116, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignHCenter)
        
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Inter", 22, QFont.Bold))
        self.label.setStyleSheet(f"color: {COLORS['main_color']};")
        self.label.setWordWrap(True)
        
        layout.addWidget(self.icon_label)
        layout.addSpacing(6)
        layout.addWidget(self.label)

    def _setup_confirmation_layout(self, layout, message):
        """Layout za confirmation/leave modal - tekst gore, dugmad dole"""
        
        # Tekst poruke
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.label.setFont(QFont("Inter", 20, QFont.Bold))
        self.label.setStyleSheet(f"color: #292929;")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        layout.addSpacing(8)
        
        # Dugmad direktno na dnu, bez stretch
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        # Ne dugme
        self.no_button = QPushButton("Odustani")
        self.no_button.setFont(QFont("Inter", 14, QFont.Medium))
        self.no_button.setFixedSize(280, 64)
        self.no_button.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: #EFA90F;
                border: 2px solid #EFA90F;
                border-radius: 16px;
                padding: 8px 16px;
            }}
        """)
        self.no_button.clicked.connect(self._on_cancel)
        
        # Da dugme - tekst se menja na osnovu tipa
        confirm_text = "Potvrdi?"
        if self.modal_type == "leave":
            confirm_text = "Izađi"
        elif self.modal_type == "question":
            confirm_text = "Dekodiraj karticu"
        elif self.modal_type == "confirmation":
            confirm_text = "Završi račun"
        self.yes_button = QPushButton(confirm_text)
        self.yes_button.setFont(QFont("Inter", 14, QFont.Medium))
        self.yes_button.setFixedSize(280, 64)
        self.yes_button.setStyleSheet("""
            QPushButton {
                background-color: #EFA90F;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
            }
        """)
        self.yes_button.clicked.connect(self._on_confirm)
        
        # Poravnaj dugmad na centar
        button_layout.addStretch()
        button_layout.addWidget(self.no_button)
        button_layout.addWidget(self.yes_button)
        button_layout.addStretch()
        
        # Dodaj dugmad na kraj layout-a
        layout.addLayout(button_layout)

    def _setup_product_layout(self, layout):
        product = self.transaction
        if not product:
            return

        layout.setAlignment(Qt.AlignTop)

        # --- Naziv ---
        title = QLabel(product.get('title', 'Nepoznat proizvod'))
        title.setFont(QFont('Inter', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: black;")
        layout.addWidget(title)
        layout.addSpacing(8)  # ← spacing između title i slike

        # --- Slika ---
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        pm = get_cached_image(
            str(product.get("id", "")),
            product.get("image_url", ""),
            QSize(360, 240)
        )
        if not pm.isNull():
            image_label.setPixmap(pm)
        else:
            image_label.setText("📦")
            image_label.setFont(QFont("Inter", 48))
        layout.addWidget(image_label)
        layout.addSpacing(8)  # ← spacing između slike i opisa

        # --- Opis ---
        desc = QLabel(product.get('description', 'Nema opisa'))
        desc.setWordWrap(True)
        desc.setFont(QFont('Inter', 14))
        desc.setStyleSheet("color: #292929;")
        layout.addWidget(desc)

        # --- Stretch pre cene i dugmeta da ih gurne skroz dole ---
        layout.addStretch()

        # --- Cena i dugme zajedno ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(16)

        # Cena (vrednost + valuta)
        price_container = QHBoxLayout()
        price_container.setSpacing(4)

        price_value = QLabel(f"{float(product.get('price', 0)):.2f}")
        price_value.setFont(QFont("Inter", 20, QFont.Bold))
        price_value.setStyleSheet("color: #EFA90F;")

        currency = QLabel("rsd")
        currency.setFont(QFont("Inter", 14, 600))
        currency.setStyleSheet("color: #606060;")

        price_container.addWidget(price_value)
        price_container.addWidget(currency)

        # Omotaj cenu u widget da bi mogla da se doda u HBox
        price_widget = QWidget()
        price_widget.setLayout(price_container)

        # Dugme
        add_btn = QPushButton("Dodaj u korpu")
        add_btn.setFont(QFont("Inter", 16, QFont.Bold))
        add_btn.setFixedHeight(50)
        add_btn.setMinimumWidth(150)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #C29A43;
                color: white;
                border-radius: 8px;
                padding: 6px 16px;
            }
        """)
        add_btn.clicked.connect(lambda: self._on_add_to_cart(product))
        # Dodavanje u layout
        bottom_layout.addWidget(price_widget)
        bottom_layout.addStretch()
        bottom_layout.addWidget(add_btn)

        layout.addLayout(bottom_layout)

    def _on_add_to_cart(self, product):
        print("Dodato u korpu:", product)
        self.add_to_cart.emit(product)
        self.close_with_fade()

    def _on_confirm(self):
        """Kada se klikne Da"""
        self.confirmed.emit()
        self.close_with_fade()
    
    def _on_cancel(self):
        """Kada se klikne Ne"""
        self.cancelled.emit()
        self.close_with_fade()

    def paintEvent(self, event):
        """Nacrtaj tamnu pozadinu direktno"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Tamna pozadina preko celog widget-a
        overlay_color = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay_color)

    def close_with_fade(self):
        """Zatvori modal sa fade animacijom ili slide down za help"""
        if self.modal_type == "help":
            # Help modal - slide down animacija
            self.fade_out = QPropertyAnimation(self, b"windowOpacity")
            self.fade_out.setDuration(500)
            self.fade_out.setStartValue(1)
            self.fade_out.setEndValue(0)
            
            # Slide down animacija
            current_rect = self.modal.geometry()
            self.slide_out = QPropertyAnimation(self.modal, b"geometry")
            self.slide_out.setDuration(400)
            self.slide_out.setStartValue(current_rect)
            self.slide_out.setEndValue(QRect(
                current_rect.x(), 
                self.modal_start_y,  # Spusti nazad dole
                current_rect.width(), 
                current_rect.height()
            ))
            self.slide_out.setEasingCurve(QEasingCurve.InCubic)
            
            # Kada se animacija završi, zatvori modal
            self.slide_out.finished.connect(self.close)
            
            # Pokreni animacije
            #self.fade_out.start()
            self.slide_out.start()
        else:
            # Ostali modali - obična fade animacija
            self.fade_out = QPropertyAnimation(self, b"windowOpacity")
            self.fade_out.setDuration(300)
            self.fade_out.setStartValue(1)
            self.fade_out.setEndValue(0)
            self.fade_out.finished.connect(self.close)
            self.fade_out.start()

    def mousePressEvent(self, event):
        """Zatvara modal ako korisnik klikne van modalnog okvira."""
        if not self.modal.geometry().contains(event.pos()):
            if self.modal_type in ["transaction", "product", "help", "parking"]:
                self._on_cancel()
    
    def _setup_transaction_layout(self, layout):
        if not self.transaction:
            return

        # --- GORNJI RED: Datum | Račun | Vreme ---
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20,0,20,0)
        date_label = QLabel(self.transaction.get("transation_date", ""))
        date_label.setFont(QFont("Inter", 12))
        date_label.setStyleSheet("color: #606060;")

        title_label = QLabel("Račun")
        title_label.setFont(QFont("Inter", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #C29A43;")

        time_label = QLabel(self.transaction.get("transation_time", ""))
        time_label.setFont(QFont("Inter", 12))
        time_label.setStyleSheet("color: #606060;")
        time_label.setAlignment(Qt.AlignRight)

        top_layout.addWidget(date_label, alignment=Qt.AlignLeft)
        top_layout.addStretch()
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(time_label, alignment=Qt.AlignRight)

        layout.addLayout(top_layout)

        # --- SREDINA: Lista proizvoda ---
        products = self.transaction.get("products_in_transation", [])
        self.itemArea = QScrollArea()
        self.itemArea.setWidgetResizable(True)
        self.itemArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.itemArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.itemArea.viewport().setStyleSheet("background-color: white;")
        self.itemArea.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)

        # Omogućavamo gestove za touch i drag
        for gesture in (
            QScroller.TouchGesture,
            QScroller.LeftMouseButtonGesture
        ):
            QScroller.grabGesture( self.itemArea.viewport(), gesture)

        sc = QScroller.scroller(self.itemArea.viewport())
        props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.AxisLockThreshold, 1.0)
        sc.setScrollerProperties(props)

        # Widget koji će sadržati listu proizvoda
        container = QWidget()
        container.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: none;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        # REŠENJE 1: Koristi QFrame umesto QHBoxLayout za svaki proizvod
        for item in products:
            # Kreiraj frame za svaki proizvod
            product_frame = QFrame()
            product_frame.setFixedHeight(40)  # Fiksna visina za konzistentnost
            product_frame.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                }
            """)
            
            # Kreiraj layout za frame
            product_layout = QHBoxLayout(product_frame)
            product_layout.setContentsMargins(20, 5, 20, 5)
            product_layout.setSpacing(0)

            name_qty = f"{item['name']} x {item['quantity']}"
            total_price = f"{item['total']} rsd"

            left_label = QLabel(name_qty)
            left_label.setFont(QFont("Inter", 14))
            left_label.setStyleSheet("color: #292929;")
            left_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            right_label = QLabel(total_price)
            right_label.setFont(QFont("Inter", 14))
            right_label.setStyleSheet("color: black;")
            right_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            product_layout.addWidget(left_label)
            product_layout.addStretch()
            product_layout.addWidget(right_label)

            # Dodaj frame u kontejner
            container_layout.addWidget(product_frame)

        # Dodaj stretch na kraj da gurne sve gore ako ima manje proizvoda
        container_layout.addStretch()

        # Postavi container widget u scroll area
        self.itemArea.setWidget(container)
        
        # Dodaj scroll area u glavni layout
        layout.addWidget(self.itemArea)

        # --- DONJI RED: Ukupno ---
        total_sum = sum(float(item["total"]) for item in products)
        price_value = QLabel(f"{total_sum:.2f}")
        price_value.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        price_value.setStyleSheet(f"color: #EFA90F;")

        currency = QLabel("rsd")
        currency.setFont(QFont("Inter", 12, 600))
        currency.setStyleSheet("color: #606060;")

        price_layout = QHBoxLayout()
        price_layout.setContentsMargins(0, 0, 0, 0)
        price_layout.setSpacing(4)
        price_layout.addWidget(price_value)
        price_layout.addWidget(currency)
        price_layout.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addLayout(price_layout)
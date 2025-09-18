from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QFrame, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from default_screen import DefaultScreen
from msgmodal import CustomModal
from topbar import TopBar
from botbar import BottomBar
from color import COLORS  # uvoz boja
from services.web import register_guest 
from virtual_keyboard import KeyboardLineEdit  # Nova import
import random
label_1_style=f"""    
font-family: Inter;
font-weight: 600;
font-style: Semi Bold;
font-size: 14px;
line-height: 20px;
letter-spacing: 0%;
text-transform: uppercase;
color: {COLORS["black_1"]} 
"""

button_enabled_style = f"""
    QPushButton {{
        background-color: rgb(239, 169, 15);
        color: white;
        border-radius: 16px;
    }}
"""
button_disabled_style=f"""
    QPushButton {{
        background-color: rgba(239, 169, 15, 61);
        color: white;
        border-radius: 16px;
    }}
"""

class SecondScreen(DefaultScreen):
    def __init__(self, parent_window):
        super().__init__(parent_window, top_margin=0, side_margin=0, spacing=0)
        self.parent_window = parent_window 
        self.current_keyboard_input = None  # Track koji input trenutno koristi tastaturu
        
        # --- Top Bar samo sa logom ---
        top_bar = TopBar()
        self.layout.addWidget(top_bar)
        self.layout.addSpacing(60) 
        
        # --- Centrirani okvir za formu ---
        form_container = QFrame()
        self.form_layout = QVBoxLayout(form_container)  # Čuvamo referencu na layout
        self.form_layout.setContentsMargins(0, 40, 0, 0)  # Odmak od top bara
        self.form_layout.setSpacing(30)
        form_container.setMinimumWidth(600)
        form_container.setStyleSheet("background-color: transparent;")
        form_container.setSizePolicy(form_container.sizePolicy().Expanding, form_container.sizePolicy().Preferred)

        # --- Input: Broj sobe ---
        self.room_title = QLabel("Broj Sobe")
        self.room_title.setStyleSheet(label_1_style)
        self.room_input = KeyboardLineEdit("numeric", self)
        self.room_input.setFont(QFont("Arial", 16))
        self.room_input.setFixedHeight(40)
        self.room_input.setAlignment(Qt.AlignCenter)
        self.room_input.set_container_layout(self.form_layout)  # Postavlja gde će se pojaviti tastatura
        self.room_input.mousePressEvent = lambda event: self.handle_input_focus(self.room_input, event)
        self.room_input.textChanged.connect(self.validate_form)
        self.form_layout.addWidget(self.room_title, alignment=Qt.AlignHCenter)
        self.form_layout.addWidget(self.room_input)

        # --- Input: Ime i Prezime ---
        self.name_title = QLabel("Ime i Prezime")
        self.name_title.setStyleSheet(label_1_style)
        self.name_input = KeyboardLineEdit("alphanumeric", self)
        self.name_input.setFont(QFont("Arial", 16))
        self.name_input.setFixedHeight(40)
        self.name_input.setAlignment(Qt.AlignCenter)
        self.name_input.set_container_layout(self.form_layout)  # Postavlja gde će se pojaviti tastatura
        self.name_input.mousePressEvent = lambda event: self.handle_input_focus(self.name_input, event)
        self.name_input.textChanged.connect(self.validate_form)
        self.form_layout.addWidget(self.name_title, alignment=Qt.AlignHCenter)
        self.form_layout.addWidget(self.name_input)

        # --- Dugme Submit ---
        self.submit_button = QPushButton("Registruj novog gosta >")
        self.submit_button.setFixedHeight(64)
        self.submit_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.submit_button.setStyleSheet(button_disabled_style)  # start disabled
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self.submit_form)
        self.form_layout.addWidget(self.submit_button)

        # --- Dodaj formu centriranu ---
        self.layout.addWidget(form_container, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.layout.addStretch()

        # --- Bottom Bar sa Cancel i Help ---
        bottom_bar = BottomBar(
            show_back=True,
            on_back=self.cancel_form,
            variant=1
        )
        self.layout.addWidget(bottom_bar)

    def handle_input_focus(self, input_widget, event):
        """Upravlja fokusiranjem inputa i prikazom tastature"""
        # Sakrij tastaturu sa prethodnog inputa
        if self.current_keyboard_input and self.current_keyboard_input != input_widget:
            self.current_keyboard_input.hide_keyboard()
        
        # Postavi trenutni input i prikaži tastaturu
        self.current_keyboard_input = input_widget
        input_widget.show_keyboard()
        
        # Pozovi original mousePressEvent
        KeyboardLineEdit.mousePressEvent(input_widget, event)

    def cancel_form(self):
        """Cancel vraća na prvi ekran"""
        # Sakrij tastaturu pre prelaska
        if self.current_keyboard_input:
            self.current_keyboard_input.hide_keyboard()
        self.parent_window.screen_manager.show_screen("home")

    def submit_form(self):
        room_number = self.room_input.text().strip()
        name = self.name_input.text().strip()

        print(f"SUBMIT -> Soba: {room_number}, Gost: {name}")

        # Sakrij tastaturu pre submit-a
        if self.current_keyboard_input:
            self.current_keyboard_input.hide_keyboard()
            
        randint = random.randint(1, 1000000000)
        randint2 = random.randint(1, 1000000000)
        self.parent_window.screen_manager.token = randint
        print(self.parent_window.screen_manager.last_uid, 6, randint)
        out = self.parent_window.screen_manager.nfc_reader.write_block(self.parent_window.screen_manager.last_uid, 6, str(randint))
        out2 = self.parent_window.screen_manager.nfc_reader.write_block(self.parent_window.screen_manager.last_uid, 7, str(randint))
        if out and out2 :
            register = register_guest(room_number, name, self.parent_window.screen_manager.last_uid, str(randint), str(randint2))
            if register :            
                # Prikaz custom modala
                modal = CustomModal("Uspešno ste dodali gosta".upper(), "notification", "success")
                modal.show()
                self.parent_window.screen_manager.show_screen("home")
            else : 
                
                modal = CustomModal("Greška!", "notification", "error")
                modal.show()

            
        # Reset forme
        self.room_input.clear()
        self.name_input.clear()
        self.current_keyboard_input = None
        self.validate_form()

    def validate_form(self):
        room_filled = bool(self.room_input.text().strip())
        name_filled = bool(self.name_input.text().strip())

        if room_filled and name_filled:
            self.submit_button.setStyleSheet(button_enabled_style)
            self.submit_button.setEnabled(True)
        else:
            self.submit_button.setStyleSheet(button_disabled_style)
            self.submit_button.setEnabled(False)
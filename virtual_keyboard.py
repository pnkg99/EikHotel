from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QGridLayout, QLineEdit, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from color import COLORS

class VirtualKeyboard(QWidget):
    textChanged = pyqtSignal(str)  # Signal za slanje unetog teksta
    
    def __init__(self, keyboard_type="numeric", parent=None):
        super().__init__(parent)
        self.keyboard_type = keyboard_type
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border-radius: 12px;
            }}
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Keyboard layout
        if self.keyboard_type == "numeric":
            keyboard_layout = self.create_numeric_layout()
        else:  # alphanumeric
            keyboard_layout = self.create_alphanumeric_layout()
            
        layout.addLayout(keyboard_layout)
        
        self.setLayout(layout)
        
    def create_numeric_layout(self):
        """Kreira kompaktnu numeričku tastaturu 3x4"""
        layout = QGridLayout()
        layout.setSpacing(12)  # Veći spacing između redova
        
        # Brojevi u 3 kolone sa C i CC pored nule
        numbers = [
            ['1', '2', '3'],
            ['4', '5', '6'], 
            ['7', '8', '9'],
            ['C', '0', 'CC']  # C i CC pored nule
        ]
        
        for row, number_row in enumerate(numbers):
            for col, number in enumerate(number_row):
                btn = QPushButton(number)
                if number in ['C', 'CC']:
                    # Specijalni dugmići za brisanje
                    if number == 'C':
                        btn.clicked.connect(lambda checked: self.backspace())
                        btn.setStyleSheet(self.get_special_button_style())
                    else:  # CC
                        btn.clicked.connect(lambda checked: self.clear_all())
                        btn.setStyleSheet(self.get_special_button_style())
                else:
                    # Običan broj
                    btn.clicked.connect(lambda checked, n=number: self.add_character(n))
                    btn.setStyleSheet(self.get_text_key_style())
                
                btn.setFixedSize(100, 100)  # Veći dugmići za touchscreen
                if number in ['C', 'CC']:
                    btn.setFont(QFont("Arial", 16, QFont.Bold))  # Manji font za C/CC
                else:
                    btn.setFont(QFont("Arial", 24, QFont.Bold))  # Veći font za brojeve
                    
                layout.addWidget(btn, row, col)
        
        
        
        # Centriraj layout
        container_layout = QHBoxLayout()
        container_layout.addStretch()
        
        container_widget = QWidget()
        container_widget.setLayout(layout)
        container_layout.addWidget(container_widget)
        container_layout.addStretch()
        return container_layout

    def create_alphanumeric_layout(self):
        """Kreira kompaktnu alfanumeričku tastaturu"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        rows = [
            ['Q', 'W', 'E', 'R', 'T', 'Z', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Y', 'X', 'C', 'V', 'B', 'N', 'M']
        ]
        
        for row_chars in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)
            row_layout.addStretch()
            for char in row_chars:
                btn = QPushButton(char)
                btn.clicked.connect(lambda checked, c=char: self.add_character(c))
                btn.setFixedSize(64, 64)
                btn.setFont(QFont("Arial", 16, QFont.Bold))
                btn.setStyleSheet(self.get_key_button_style())
                row_layout.addWidget(btn)
            row_layout.addStretch()
            layout.addLayout(row_layout)
        
        # Srpska slova
        serbian_layout = QHBoxLayout()
        serbian_layout.addStretch()
        for char in ['Š', 'Đ', 'Č', 'Ć', 'Ž']:
            btn = QPushButton(char)
            btn.clicked.connect(lambda checked, c=char: self.add_character(c))
            btn.setFixedSize(64, 64)
            btn.setFont(QFont("Arial", 16, QFont.Bold))
            btn.setStyleSheet(self.get_key_button_style())
            serbian_layout.addWidget(btn)
        serbian_layout.addStretch()
        layout.addLayout(serbian_layout)

        # Space + Erase + Enter
        space_layout = QHBoxLayout()
        space_layout.addStretch()

        # Erase dugme
        erase_btn = QPushButton("Obriši")
        erase_btn.clicked.connect(self.backspace)
        erase_btn.setFixedSize(150, 64)
        erase_btn.setFont(QFont("Arial", 16, QFont.Bold))
        erase_btn.setStyleSheet(self.get_key_button_style())
        space_layout.addWidget(erase_btn)

        # Space dugme
        space_btn = QPushButton("RAZMAK")
        space_btn.clicked.connect(lambda: self.add_character(" "))
        space_btn.setFixedSize(300, 64)
        space_btn.setFont(QFont("Arial", 16, QFont.Bold))
        space_btn.setStyleSheet(self.get_key_button_style())
        space_layout.addWidget(space_btn)

        # Enter dugme (zatvara tastaturu)
        enter_btn = QPushButton("Unesi")
        enter_btn.clicked.connect(lambda: self.parent().hide_keyboard() if hasattr(self.parent(), 'hide_keyboard') else None)
        enter_btn.setFixedSize(150, 64)
        enter_btn.setFont(QFont("Arial", 16, QFont.Bold))
        enter_btn.setStyleSheet(self.get_key_button_style())
        space_layout.addWidget(enter_btn)

        space_layout.addStretch()
        layout.addLayout(space_layout)
        
        return layout

    def get_special_button_style(self):
        return f"""
            QPushButton {{
                background-color: #f5f5f5;
                border: none;
                border-radius: 8px;
                color: #666666;
            }}
            QPushButton:pressed {{
                background-color: #e0e0e0;
                color: #333333;
            }}
        """
    
    def get_text_key_style(self):
        return f"""
        QPushButton {{
            background-color: white;
            border: none;
            border-radius: 6px;
            color: {COLORS.get('black_1', 'black')};
        }}
        QPushButton:pressed {{
            background-color: {COLORS.get('main_color', '#EFA90F')};
            color: white;
        }}
    """
    
    def get_key_button_style(self):
        return f"""
            QPushButton {{
                background-color: white;
                border: none;
                border-radius: 8px;
                color: {COLORS.get('black_1', 'black')};
            }}
            QPushButton:pressed {{
                background-color: #d4950c;
                color: white;
            }}
        """
    
    def get_control_button_style(self, bg_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 15px;
            }}
        """

    def mouseReleaseEvent(self, event):
        # Vrati na normalno stanje sa kratkim delay-em
        QTimer.singleShot(300, lambda: print("hehe"))
        super().mouseReleaseEvent(event)

    def add_character(self, char):
        """Dodaje karakter i emituje signal"""
        if self.keyboard_type == "numeric":
            if char.isdigit():
                self.textChanged.emit(char)
        else:
            self.textChanged.emit(char)
    
    def backspace(self):
        """Emituje backspace signal"""
        self.textChanged.emit("BACKSPACE")
    
    def clear_all(self):
        """Emituje clear signal"""
        self.textChanged.emit("CLEAR")


class KeyboardLineEdit(QLineEdit):
    """Custom QLineEdit sa integrisanom virtuelnom tastaturom"""
    
    def __init__(self, keyboard_type="numeric", parent=None):
        super().__init__(parent)
        self.keyboard_type = keyboard_type
        self.keyboard = None
        self.container_layout = None
        
        # Sprečava fizičku tastaturu
        self.setReadOnly(True)
        
        # Style
        self.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                border-bottom: 1px solid {COLORS.get('main_color', '#EFA90F')};
                padding: 5px;
            }}
            QLineEdit:focus {{
                border-bottom: 2px solid {COLORS.get('main_color', '#EFA90F')};
            }}
        """)
    
    def set_container_layout(self, layout):
        """Postavlja layout kontejner gde će se dodati tastatura"""
        self.container_layout = layout
    
    def mousePressEvent(self, event):
        """Prikazuje tastaturu kada se klikne na input"""
        if not self.keyboard and self.container_layout:
            self.show_keyboard()
        super().mousePressEvent(event)
    
    def show_keyboard(self):
        """Prikazuje tastaturu ispod inputa"""
        if not self.keyboard:
            self.keyboard = VirtualKeyboard(self.keyboard_type, self.parent())
            self.keyboard.textChanged.connect(self.handle_keyboard_input)
            
            # Dodaj tastaturu u container layout
            self.container_layout.addWidget(self.keyboard)
            
            # Fokusiraj na input
            self.setFocus()
    
    def hide_keyboard(self):
        """Sakriva tastaturu"""
        if self.keyboard:
            self.container_layout.removeWidget(self.keyboard)
            self.keyboard.deleteLater()
            self.keyboard = None
    
    def handle_keyboard_input(self, char):
        """Obrađuje unos sa tastature"""
        current = self.text()
        
        if char == "BACKSPACE":
            if current:
                self.setText(current[:-1])
        elif char == "CLEAR":
            self.clear()
        elif char == " ":
            # Space handling za imena
            if self.keyboard_type != "numeric" and current and not current.endswith(" "):
                if len(current) < 50:
                    self.setText(current + char)
        else:
            # Dodaj karakter
            if self.keyboard_type == "numeric":
                if len(current) < 10:
                    self.setText(current + char)
            else:
                if len(current) < 50:
                    # Capitalize handling
                    if not current or current.endswith(" "):
                        char = char.upper()
                    else:
                        char = char.lower()
                    self.setText(current + char)
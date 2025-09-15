from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QSizePolicy, QSpacerItem,
                             QLabel, QScrollArea, QFrame, QScroller, QScrollerProperties,
                             QGridLayout, QButtonGroup)
from PyQt5.QtGui import QFont, QIcon, QPalette
from PyQt5.QtCore import QSize, Qt
from default_screen import DefaultScreen
from topbar import TopBar
from botbar import BottomBar
import os
from msgmodal import CustomModal
from parking_manager import ParkingManager  # Import našeg manager-a
from services.web import parking_allocate

class ParkingSpotButton(QPushButton):
    def __init__(self, spot_number, status):
        super().__init__(spot_number)
        self.spot_number = spot_number
        self.status = status
        self.setFixedSize(64, 64)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.set_status(status)
    
        
    def set_status(self, status):
        self.status = status
        if status == 'free':
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4BC243;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-weight: bold;
                }
            """)
        elif status == 'occupied':
            self.setStyleSheet("""
                QPushButton {
                    background-color: #E11B1B;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-weight: bold;
                }
            """)
        else:  # current
            self.setStyleSheet("""
                QPushButton {
                    background-color: #606060;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-weight: bold;
                }
            """)

class ParkingScreen(DefaultScreen):
    def __init__(self, parent_window):
        super().__init__(parent_window, top_margin=0, side_margin=0, spacing=0)
        self.parent_window = parent_window
        # Koristi ParkingManager singleton
        self.parking_manager = ParkingManager()
        self.spots_buttons = {}  # (parking_type, level, section, spot_number) -> ParkingSpotButton

        # --- Top Bar ---
        top_bar = TopBar(show_back=True, logo=False, title="PARKING", 
                        on_back=(lambda: self.parent_window.screen_manager.show_screen("customer")))
        self.layout.addWidget(top_bar)

        # --- Main Content Area ---
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignTop)

        # Dobij strukturu parkinga iz manager-a
        self.parking_data = self.parking_manager.get_parking_structure()

        self.selected_parking = 'unutrasnji'
        self.selected_level = 1

        # Create UI components
        self.create_parking_type_buttons(main_layout)
        self.create_level_buttons(main_layout)
        self.create_parking_spots_area(main_layout)

        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_area.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)

        # Omogućavamo gestove za touch i drag
        for gesture in (
            QScroller.TouchGesture,
            QScroller.LeftMouseButtonGesture
        ):
            QScroller.grabGesture( scroll_area.viewport(), gesture)

        sc = QScroller.scroller(scroll_area.viewport())
        props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.AxisLockThreshold, 1.0)
        sc.setScrollerProperties(props)
        
        scroll_area.setWidget(main_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Enable touch scrolling
        QScroller.grabGesture(scroll_area, QScroller.LeftMouseButtonGesture)

        self.layout.addWidget(scroll_area)

        # --- Bottom Bar ---
        bottom_bar = BottomBar()
        self.layout.addWidget(bottom_bar)

    def create_parking_type_buttons(self, layout):
        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)  # razmak između dugmadi
        buttons_layout.setAlignment(Qt.AlignHCenter)  # centriraj dugmad horizontalno

        self.parking_type_group = QButtonGroup()

        # Unutrasnji button
        self.btn_unutrasnji = QPushButton("Unutrašnji")
        self.btn_unutrasnji.setFixedSize(352, 64)
        self.btn_unutrasnji.setFont(QFont("Arial", 14, QFont.Bold))
        self.btn_unutrasnji.clicked.connect(lambda: self.select_parking_type('unutrasnji'))
        self.parking_type_group.addButton(self.btn_unutrasnji)

        # Spoljasnji button
        self.btn_spoljasnji = QPushButton("Spoljašnji")
        self.btn_spoljasnji.setFixedSize(352, 64)
        self.btn_spoljasnji.setFont(QFont("Arial", 14, QFont.Bold))
        self.btn_spoljasnji.clicked.connect(lambda: self.select_parking_type('spoljasnji'))
        self.parking_type_group.addButton(self.btn_spoljasnji)

        # Dodaj dugmad u layout
        buttons_layout.addWidget(self.btn_unutrasnji)
        buttons_layout.addWidget(self.btn_spoljasnji)

        layout.addWidget(buttons_container)

        # Inicijalni update stanja
        self.update_parking_type_buttons()
    
    def create_level_buttons(self, layout):
        # Levels container
        self.levels_container = QWidget()
        self.levels_layout = QHBoxLayout(self.levels_container)
        self.levels_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.levels_container)
        
        self.level_buttons = {}
        self.level_group = QButtonGroup()
        
        self.update_level_buttons()

    def create_parking_spots_area(self, layout):
        # Parking spots container
        self.spots_container = QWidget()
        self.spots_layout = QVBoxLayout(self.spots_container)
        self.spots_layout.setContentsMargins(0, 0, 0, 0)
        self.spots_layout.setSpacing(15)

        layout.addWidget(self.spots_container)
        
        self.update_parking_spots()

    def select_parking_type(self, parking_type):
        self.selected_parking = parking_type
        self.selected_level = 1
        self.update_parking_type_buttons()
        self.update_level_buttons()
        self.update_parking_spots()

    def select_level(self, level):
        self.selected_level = level
        self.update_level_buttons()
        self.update_parking_spots()

    def update_parking_type_buttons(self):
        # Style for selected button
        selected_style = """
            QPushButton {
                background-color: #C29A43;
                color: white;
                border: 2px solid #C29A43;
                border-radius: 16px;
                padding: 10px;
                font-weight: bold;
            }
        """        
        # Style for unselected button
        unselected_style = """
            QPushButton {
                background-color: transparent;
                color: #C29A43;
                border: none;
                border-radius: 16px;
                padding: 10px;
                font-weight: bold;
            }
        """
        
        if self.selected_parking == 'unutrasnji':
            self.btn_unutrasnji.setStyleSheet(selected_style)
            self.btn_spoljasnji.setStyleSheet(unselected_style)
        else:
            self.btn_unutrasnji.setStyleSheet(unselected_style)
            self.btn_spoljasnji.setStyleSheet(selected_style)

    def update_level_buttons(self):
        # Clear existing buttons
        for button in self.level_buttons.values():
            button.setParent(None)
        self.level_buttons.clear()

        # Get levels
        levels = self.parking_data[self.selected_parking]['levels']
        
        for level in levels:
            btn = QPushButton(f"Nivo {level}")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(48)
            btn.setFont(QFont("Arial", 12, QFont.Bold))
            btn.clicked.connect(lambda checked, l=level: self.select_level(l))
            
            self.level_buttons[level] = btn
            self.level_group.addButton(btn)
            self.levels_layout.addWidget(btn)

        self.update_level_button_styles()
        
    def update_level_button_styles(self):
        selected_style = """
            QPushButton {
                background-color: transparent;
                color: #C29A43;
                border-bottom: 2px solid #C29A43;;
                font-weight: bold;
                padding: 12px 0;
            }
        """
        unselected_style = """
            QPushButton {
                background-color: transparent;
                color: #C29A43;
                border: none;
                font-weight: bold;
                padding: 12px 0;
            }
        """

        for level, button in self.level_buttons.items():
            if level == self.selected_level:
                button.setStyleSheet(selected_style)
            else:
                button.setStyleSheet(unselected_style)

    def update_parking_spots(self):
        # Clear existing spots
        for i in reversed(range(self.spots_layout.count())):
            widget = self.spots_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Get sections for current selection
        sections = self.parking_data[self.selected_parking]['sections'][self.selected_level]

        # Create section widgets
        for section in sections:
            section_widget = self.create_section_widget(section)
            self.spots_layout.addWidget(section_widget)

    def create_section_widget(self, section):
        # Container bez border-a
        section_frame = QWidget()
        section_layout = QHBoxLayout(section_frame)
        section_layout.setContentsMargins(10, 5, 10, 5)
        section_layout.setSpacing(15)

        # Levo: labela "A", "B", itd.
        section_label = QLabel(section)
        section_label.setFont(QFont("Inter", 14, 600))
        section_label.setStyleSheet("color: #606060;") 
        section_label.setContentsMargins(0, 20, 20, 0)
        section_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        section_layout.addWidget(section_label)

        # Desno: grid sa mestima
        spots_widget = QWidget()
        spots_grid = QGridLayout(spots_widget)
        spots_grid.setSpacing(5) 

        # Dobij mesta iz ParkingManager-a umesto generisanja
        spots = self.parking_manager.get_spots_for_section(
            self.selected_parking, 
            self.selected_level, 
            section
        )

        spots_per_row = 10
        
        for i, spot in enumerate(spots):
            spot_button = ParkingSpotButton(spot.spot_number, spot.status)
            spot_button.clicked.connect(
                lambda checked, s=spot: self.on_spot_clicked(s)
            )
            
            # Koristi punu putanju kao ključ
            key = (spot.parking_type, spot.level, spot.section, spot.spot_number)
            self.spots_buttons[key] = spot_button

            row = i // spots_per_row
            col = i % spots_per_row
            spots_grid.addWidget(spot_button, row, col)

        section_layout.addWidget(spots_widget, stretch=1)
        return section_frame

    def on_spot_clicked(self, spot):
        """Klik na parking mesto - spot je ParkingSpot objekat"""
        print(f"Clicked on parking spot: {spot.spot_number}, status: {spot.status}")

        if spot.status == "free":
            transaction = {
                "name": f"Parking mesto {spot.spot_number}",
                "message": "Slobodno parking mesto.",
                "plates": [],
                "status": "free",
                "spot": spot  # Dodaj spot objekat za pristup
            }
        elif spot.status == "occupied":
            plates = [spot.license_plate] if spot.license_plate else []
            if spot.room_number:
                plates.append(spot.room_number)
            
            transaction = {
                "name": f"Zauzeto parking mesto {spot.spot_number}",
                "message": "Na označenom mestu se nalazi vozilo sa registracijom gosta koji je u sobi:",
                "plates": plates,
                "status": "occupied",
                "spot": spot
            }
        else:  # current
            spot.license_plate = "999 KG"
            transaction = {
                "name": f"Parking mesto {spot.spot_number}",
                "message": "Na označenom mestu se nalazi vozilo sa registracijom:",
                "plates": [spot.license_plate],
                "status": "current",
                "spot": spot,
                "allocated" : self.parent_window.screen_manager.parking_allocated
            }

        modal = CustomModal(modal_type="parking", transaction=transaction)
        
        # Povezivanje sa signalom za promenu statusa
        modal.allocate_parking.connect(lambda: self._allocate_parking(spot))
        
        modal.show()
        
    def _allocate_parking(self, spot):
        resp = parking_allocate(self.parent_window.screen_manager.number, self.parent_window.screen_manager.cvc, spot.spot_number, spot.license_plate)
        if resp and resp["status"] == 1 :
            modal = CustomModal(message="Alocirano parking mesto")
        elif resp["status"] == 2: 
            modal = CustomModal(message="Greška pri alociranju parking mesta")
        modal.show()
        self.parent_window.screen_manager.show_screen("customer")
    
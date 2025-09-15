import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QCursor
from screen import ScreenManager
from services.web import get_info

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hotel_info =  get_info()
        
        self.setWindowTitle("Eik Hotel")

        # Shortcut za ESC izlaz
        esc_shortcut = QShortcut(Qt.Key_Escape, self)
        esc_shortcut.activated.connect(self.close)

        # Dimenzije ekrana
        screen_geometry = QApplication.primaryScreen().geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

        max_width = 800

        if self.screen_width <= max_width:
            # Ako je ekran manji ili jednak 800px → full width
            self.setGeometry(0, 0, self.screen_width, self.screen_height)
        else:
            # Ako je ekran širi → centriraj prozor sa max 800px
            x = (self.screen_width - max_width) // 2
            self.setGeometry(x, 0, max_width, self.screen_height)
            self.setMaximumWidth(max_width) 

        # Screen manager kao centralni widget
        self.screen_manager = ScreenManager()
        self.setCentralWidget(self.screen_manager)

        # Dodaj ekrane
        from first_screen import FirstScreen
        from second_screen import SecondScreen
        from third_screen import ThirdScreen
        from restaurant import Restaurant
        from history_screen import HistoryScreen
        from parking_screen import ParkingScreen
        
        self.screen_manager.add_screen("home", FirstScreen(self))
        self.screen_manager.add_screen("register", SecondScreen(self))
        self.screen_manager.add_screen("customer", ThirdScreen(self))
        
        self.restaurant = Restaurant(self)
        self.restaurant.update_categories(self.hotel_info.get("products_for_restaurant", []))
        
        self.screen_manager.add_screen("restaurant", self.restaurant)
        self.history = HistoryScreen(self)
        self.screen_manager.add_screen("history", self.history)
        self.parking = ParkingScreen(self)
        self.screen_manager.add_screen("parking", self.parking)
        
        self.screen_manager.show_screen("home")        
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Sakrivanje kursora
    transparent_cursor = QCursor(QPixmap(10, 10)) 
    app.setOverrideCursor(transparent_cursor)

    # Pokretanje prozoras
    window = MainWindow()
    window.setWindowFlags(Qt.FramelessWindowHint)
    window.show()
    sys.exit(app.exec_())
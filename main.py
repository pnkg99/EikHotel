import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QCursor, QKeySequence 
from screen import ScreenManager
from services.web import get_info

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        print("🚀 Pokretanje Eik Hotel aplikacije...")
        
        # Učitaj hotel info
        try:
            self.hotel_info = get_info()
            print("✅ Hotel info učitan")
        except Exception as e:
            print(f"❌ Greška pri učitavanju hotel info: {e}")
            self.hotel_info = {}
        
        self.setWindowTitle("Eik Hotel")
        
        # Setup prozora
        self._setup_window()
        
        # Kreiraj screen manager
        self.screen_manager = ScreenManager()
        self.setCentralWidget(self.screen_manager)
        
        # Setup screen-ovi
        self._setup_screens()
        
        # Pokretanje na home screen (automatski pokretanje NFC polling-a)
        print("🏠 Prelazim na home screen...")
        self.screen_manager.show_screen("home")
        
        # Debug timer (opciono)
        self._setup_debug_timer()
        
        print("✅ Aplikacija pokrenuta uspešno!")

    def _setup_window(self):
        """Setup dimenzija i geometrije prozora"""
        try:
            # Dimenzije ekrana
            screen_geometry = QApplication.primaryScreen().geometry()
            self.screen_width = screen_geometry.width()
            self.screen_height = screen_geometry.height()
            
            print(f"📺 Rezolucija ekrana: {self.screen_width}x{self.screen_height}")

            max_width = 800

            if self.screen_width <= max_width:
                # Ako je ekran manji ili jednak 800px → full width
                self.setGeometry(0, 0, self.screen_width, self.screen_height)
                print("📱 Koristim full screen mode")
            else:
                # Ako je ekran širi → centriraj prozor sa max 800px
                x = (self.screen_width - max_width) // 2
                self.setGeometry(x, 0, max_width, self.screen_height)
                self.setMaximumWidth(max_width)
                print(f"🖥️ Centriram prozor: {max_width}px širina")
                
        except Exception as e:
            print(f"❌ Greška pri setup-u prozora: {e}")
            # Fallback na full screen
            self.showFullScreen()

    def _setup_screens(self):
        """Setup svih screen-ova"""
        try:
            print("📱 Kreiram screen-ove...")
            
            # Import screen-ova
            from first_screen import FirstScreen
            from second_screen import SecondScreen
            from third_screen import ThirdScreen
            from restaurant import Restaurant
            from history_screen import HistoryScreen
            from parking_screen import ParkingScreen
            
            # Dodaj osnovne screen-ove
            self.screen_manager.add_screen("home", FirstScreen(self))
            self.screen_manager.add_screen("register", SecondScreen(self))
            self.screen_manager.add_screen("customer", ThirdScreen(self))
            
            # Restaurant screen sa kategorijama
            self.restaurant = Restaurant(self)
            restaurant_products = self.hotel_info.get("products_for_restaurant", [])
            self.restaurant.update_categories(restaurant_products)
            self.screen_manager.add_screen("restaurant", self.restaurant)
            
            # History i parking screen-ovi
            self.history = HistoryScreen(self)
            self.screen_manager.add_screen("history", self.history)
            
            self.parking = ParkingScreen(self)
            self.screen_manager.add_screen("parking", self.parking)
            
            print("✅ Svi screen-ovi kreirani")
            
        except Exception as e:
            print(f"❌ Greška pri kreiranju screen-ova: {e}")
            raise

    def _setup_debug_timer(self):
        """Setup debug timer za praćenje stanja (opciono)"""
        if __name__ == "__main__":  # Samo u debug mode
            self.debug_timer = QTimer()
            self.debug_timer.timeout.connect(self._debug_status)
            self.debug_timer.start(10000)  # Svakih 10 sekundi

    def _debug_status(self):
        """Debug funkcija - prikazuje status aplikacije"""
        try:
            status = self.screen_manager.get_card_status()
            current_screen = None
            
            # Pronađi trenutni screen
            for name, widget in self.screen_manager.screens.items():
                if widget == self.screen_manager.currentWidget():
                    current_screen = name
                    break
            
            print(f"\n=== DEBUG STATUS ===")
            print(f"📱 Trenutni screen: {current_screen}")
            print(f"💳 Kartica aktivna: {status['card_active']}")
            if status['uid']:
                print(f"🔍 UID: {status['uid']}")
            if status['token']:
                print(f"🎫 Token: {status['token'][:10]}...")
            print(f"🍽️ Restoran: {status['restaurant_entered']}")
            print(f"💪 Teretana: {status['gym_entered']}")
            print(f"🅿️ Parking: {status['parking_allocated']}")
            print("==================\n")
            
        except Exception as e:
            print(f"❌ Debug greška: {e}")

    def keyPressEvent(self, event):
        """Handler za pritiske tastature"""
        try:
            if event.key() == Qt.Key_Escape:
                print("🚪 ESC pritisnut - zatvaranje aplikacije...")
                self.close_application()
            elif event.key() == Qt.Key_F1:
                # Debug - manual card check
                print("🔍 F1 - ručna provera kartice...")
                self.screen_manager.manual_card_check()
            elif event.key() == Qt.Key_F2:
                # Debug - status
                self._debug_status()
            elif event.key() == Qt.Key_F3:
                # Debug - restart NFC polling
                print("🔄 F3 - restart NFC polling...")
                self.screen_manager.stop_nfc_polling()
                time.sleep(0.5)
                self.screen_manager.start_nfc_polling()
            else:
                super().keyPressEvent(event)
        except Exception as e:
            print(f"❌ Greška u keyPressEvent: {e}")

    def close_application(self):
        """Bezbedan način zatvaranja aplikacije"""
        try:
            print("🔄 Zatvaranje aplikacije...")
            
            # Zaustavi NFC polling
            if hasattr(self.screen_manager, 'stop_nfc_polling'):
                self.screen_manager.stop_nfc_polling()
            
            # Kratka pauza da se sve završi
            time.sleep(0.3)
            
            print("✅ Aplikacija zatvorena")
            QApplication.quit()
            
        except Exception as e:
            print(f"❌ Greška pri zatvaranju: {e}")
            # Force quit ako se nešto zaglavi
            import os
            os._exit(0)

    def closeEvent(self, event):
        """Qt closeEvent"""
        try:
            print("🚪 CloseEvent pozvan...")
            self.close_application()
            event.accept()
        except Exception as e:
            print(f"❌ Greška u closeEvent: {e}")
            event.accept()

    # Metode koje screen-ovi možda pozivaju
    def get_screen_manager(self):
        """Vraća screen manager za pristup iz drugih screen-ova"""
        return self.screen_manager

    def get_hotel_info(self):
        """Vraća hotel info"""
        return self.hotel_info

    def restart_nfc_polling(self):
        """Restart NFC polling (za dugmad u UI)"""
        try:
            print("🔄 Restartovanje NFC polling-a...")
            self.screen_manager.stop_nfc_polling()
            time.sleep(0.2)
            self.screen_manager.start_nfc_polling()
            print("✅ NFC polling restartovan")
        except Exception as e:
            print(f"❌ Greška pri restartu NFC: {e}")


if __name__ == "__main__":
    try:
        print("🎬 Pokretanje PyQt aplikacije...")
        app = QApplication(sys.argv)

        # Sakrivanje kursora
        try:
            transparent_cursor = QCursor(QPixmap(1, 1))  # Minimalni transparentni kursor
            app.setOverrideCursor(transparent_cursor)
            print("🖱️ Kursor sakriven")
        except Exception as e:
            print(f"⚠️ Ne mogu sakriti kursor: {e}")

        # Kreiraj glavni prozor
        window = MainWindow()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.show()

        print("🎯 Ulazim u Qt event loop...")
        
        # Pokretanje aplikacije
        exit_code = app.exec_()
        
        print(f"🏁 Aplikacija završena sa kodom: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"💥 KRITIČNA GREŠKA u main aplikaciji: {e}")
        import traceback
        traceback.print_exc()
        
        # Force exit
        try:
            QApplication.quit()
        except:
            pass
        import os
        os._exit(1)
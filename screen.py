from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QTimer
from services.pn532 import SimpleUltralightReader
from services.web import read_nfc_card, get_card_history, enter_restaurant, enter_gym
import time

# Klasa za upravljanje NFC funkcionalnostima
class NFCManager(QObject):
    card_detected = pyqtSignal(bytes)  # Signal za detektovanu karticu

    def __init__(self):
        super().__init__()
        self.nfc_reader = SimpleUltralightReader()
        self.nfc_thread = NFCPollingThread(self.nfc_reader)
        self.nfc_thread.card_detected.connect(self.card_detected.emit)
        self.token_block_number = 6
        self.cvc_block_number = 7

    def start_polling(self):
        """Pokretanje NFC polling-a"""
        if not self.nfc_thread.isRunning():
            print("Pokretam NFC polling...")
            self.nfc_thread.start()
        else:
            print("NFC polling je već pokrenut")

    def stop_polling(self):
        """Zaustavljanje NFC polling-a"""
        if self.nfc_thread.isRunning():
            print("Zaustavljam NFC polling...")
            self.nfc_thread.stop()
        else:
            print("NFC polling nije pokrenut")

    def read_block(self, block_number):
        """Čita blok sa NFC kartice"""
        try:
            self.nfc_reader.simple_debug_read(6)
            return self.nfc_reader.read_block(block_number)
        except Exception as e:
            print(f"Greška pri čitanju bloka {block_number}: {e}")
            return None

    def write_block(self, block_number, data):
        """Upisuje podatke u blok na NFC kartici"""
        try:
            return self.nfc_reader.write_block(block_number, data)
        except Exception as e:
            print(f"Greška pri upisu u blok {block_number}: {e}")
            return False

    def cleanup(self):
        """Cleanup NFC resursa"""
        self.stop_polling()

class NFCPollingThread(QThread):
    """Thread za NFC polling koji je kompatibilan sa PyQt5"""
    card_detected = pyqtSignal(bytes)  # Signal za detektovanu karticu
    
    def __init__(self, nfc_reader):
        super().__init__()
        self.nfc_reader = nfc_reader
        self.is_running = False
        self.check_interval = 0.5
        self.last_uid = None
    
    def run(self):
        """Glavni loop za polling"""
        self.is_running = True
        
        while self.is_running:
            try:
                uid = self.nfc_reader.read_card_once(timeout=0.1)
                
                if uid:
                    uid_hex = ''.join(f"{b:02X}" for b in uid)
                    if self.last_uid != uid_hex:
                        self.card_detected.emit(bytes(uid))
                        self.last_uid = uid_hex
                else:
                    if self.last_uid is not None:
                        self.last_uid = None
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"NFC polling greška: {e}")
                time.sleep(1)
    
    def stop(self):
        """Zaustavlja polling"""
        self.is_running = False
        self.wait()

class ScreenManager(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.screens = {}
        self.nfc_manager = NFCManager()
        self.nfc_manager.card_detected.connect(self._handle_read_card)
        
        self.token = None
        self.uid = None
        self.cvc = None
        self.card_active = False
        self.restaurant_entered = False
        self.gym_entered = False
        self.parking_space = None
        self.reg_car_number = None
        self.parking_allocated = False

    def _update_history(self):
        """Ažurira istoriju transakcija"""
        resp = get_card_history(self.token, self.cvc)
        if resp:
            self.transactions = resp.get("transations", [])
            if "history" in self.screens:
                self.screens["history"].update_history(self.transactions)
            
            self.parking_space = resp.get("parking", {}).get("parking_space", None)
            if self.parking_space == "null":
                self.parking_space = None
            
            self.reg_car_number = resp.get("parking", {}).get("reg_car_number", None)
            if self.reg_car_number == "null":
                self.reg_car_number = None
            
            if self.reg_car_number and self.parking_space:
                self.parking_allocated = True
            else:
                self.parking_allocated = False
                
            print(f"Parking allocated: {self.parking_allocated}")

    def _handle_read_card(self, uid):
        """Handler za čitanje NFC kartice"""
        try:
            self.uid = uid
            uid_hex = ''.join(f"{b:02X}" for b in uid)
            print(f"Kartica detektovana: {uid_hex}")
            self.token = self.nfc_manager.read_block(self.nfc_manager.token_block_number)
            self.cvc = self.nfc_manager.read_block(self.nfc_manager.cvc_block_number)
            print(f"Token pročitan: {self.token}")
            print(f"CVC pročitan: {self.cvc}")
            if self.token and self.cvc:
                resp = read_nfc_card(self.token, self.cvc)
                print(f"Web response: {resp}")
                
                if resp:
                    if resp["status"] == 2:
                        self.show_screen("register")
                    elif resp["status"] == 1:
                        data = resp.get("data", {})
                        self.slug = data.get("slug")
                        
                        if "restaurant" in self.screens and self.slug:
                            self.screens["restaurant"].update_slug(self.slug)
                        
                        self.show_screen("customer")
                        self.card_active = True
                        self.restaurant_entered = False
                        self.gym_entered = False
                    else:
                        print(f"Neočekivan status: {resp['status']}")
                else:
                    print("Nema odgovora od web servisa")
            else:
                print("Token nije pročitan sa kartice")
                self.show_screen("register")
                
        except Exception as e:
            print(f"Greška pri obradi kartice: {e}")

    def add_screen(self, name, widget):
        """Dodaje novi screen"""
        self.screens[name] = widget
        self.addWidget(widget)

    def show_screen(self, name):
        """Prikazuje određeni screen"""
        if name in self.screens:
            if name == "home":
                self.nfc_manager.start_polling()
            else:
                self.nfc_manager.stop_polling()

            if (self.card_active and 
                name == "restaurant" and 
                not self.restaurant_entered and 
                self.token):
                try:
                    enter_restaurant(self.token, self.cvc)
                    self.restaurant_entered = True
                    print("Uspešan ulazak u restoran")
                except Exception as e:
                    print(f"Greška pri ulasku u restoran: {e}")

            if (self.card_active and 
                name == "gym" and 
                not self.gym_entered and 
                self.token):
                try:
                    enter_gym(self.token, self.cvc)
                    self.gym_entered = True
                    print("Uspešan ulazak u teretanu")
                except Exception as e:
                    print(f"Greška pri ulasku u teretanu: {e}")

            if name == "customer":
                self._update_history()

            self.setCurrentWidget(self.screens[name])
            print(f"Prebačeno na screen: {name}")

    def write_token(self, token):
        """Upisuje token na NFC karticu"""
        return self.nfc_manager.write_block(self.nfc_manager.token_block_number, token)

    def write_cvc(self, cvc):
        """Upisuje CVC na NFC karticu"""
        return self.nfc_manager.write_block(self.nfc_manager.cvc_block_number, cvc)

    def closeEvent(self, event):
        """Cleanup pri zatvaranju aplikacije"""
        print("Zatvaranje aplikacije - cleanup NFC...")
        self.nfc_manager.cleanup()
        super().closeEvent(event)

    def __del__(self):
        """Destruktor - cleanup"""
        if hasattr(self, 'nfc_manager'):
            self.nfc_manager.cleanup()
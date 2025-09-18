from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QTimer
from services.pn532 import SimpleNFCReader
from services.web import read_nfc_card, get_card_history, enter_restaurant, enter_gym
import time
import random

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
                    
                    # Emituj signal samo za nove kartice
                    if self.last_uid != uid_hex:
                        self.card_detected.emit(bytes(uid))  # originalni UID u bytes
                        self.last_uid = uid_hex
                else:
                    # Resetuj UID ako nema kartice
                    if self.last_uid is not None:
                        self.last_uid = None
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"NFC polling greška: {e}")
                time.sleep(1)
    
    def stop(self):
        """Zaustavlja polling"""
        self.is_running = False
        self.wait()  # Čeka da se thread završi

class ScreenManager(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.screens = {}
        
        # Kreiraj NFC čitač bez callback-a jer ćemo koristiti thread
        self.nfc_reader = SimpleNFCReader()
        
        # Kreiraj polling thread
        self.nfc_thread = NFCPollingThread(self.nfc_reader)
        self.nfc_thread.card_detected.connect(self._handle_read_card)
        
        self.pin = "123456"
        self.token = None
        self.uid = None
        self.cvc = None

        self.card_active = False  
        self.restaurant_entered = False
        self.gym_entered = False
        
        self.parking_space = None
        self.reg_car_number = None
        self.parking_allocated = False

    def _updage_history(self):
        """Ažurira istoriju transakcija"""
        resp = get_card_history(self.token, self.cvc)
        if resp:
            # update history transactions
            self.transactions = resp.get("transations", [])
            if "history" in self.screens:
                self.screens["history"].update_history(self.transactions)
            
            # update parking status 
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
            self.last_uid = uid_hex
            # Čitaj token iz bloka 6
            self.token = self.nfc_reader.read_block(uid, 6)
            self.cvc = self.nfc_reader.read_block(uid, 7)
            print(f"Token pročitan: {self.token}")
            print(f"CVC pročitan: {self.token}")
            if self.token and self.cvc:
                resp = read_nfc_card(self.token, self.cvs)
                print(f"Web response: {resp}")
                
                if resp:
                    if resp["status"] == 2:
                        self.show_screen("register")
                    elif resp["status"] == 1:
                        # Izvuci slug iz response-a
                        data = resp.get("data", {})
                        self.slug = data.get("slug")
                        
                        if "restaurant" in self.screens and self.slug:
                            self.screens["restaurant"].update_slug(self.slug)
                        
                        self.show_screen("customer")
                        
                        # Resetuj slotove pri novom očitavanju kartice
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
            # Upravljanje NFC polling-om
            if name == "home":
                self.start_nfc_polling()
            else:
                self.stop_nfc_polling()

            # Provera za ulazak u restoran
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

            # Provera za ulazak u teretanu
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

            # Ažuriraj istoriju kada se ide na customer screen
            if name == "customer":
                self._updage_history()

            # Prikaži screen
            self.setCurrentWidget(self.screens[name])
            print(f"Prebačeno na screen: {name}")

    def start_nfc_polling(self):
        """Pokretanje NFC polling-a"""
        if not self.nfc_thread.isRunning():
            print("Pokretam NFC polling...")
            self.nfc_thread.start()
        else:
            print("NFC polling je već pokrenut")

    def stop_nfc_polling(self):
        """Zaustavljanje NFC polling-a"""
        if self.nfc_thread.isRunning():
            print("Zaustavljam NFC polling...")
            self.nfc_thread.stop()
        else:
            print("NFC polling nije pokrenut")

    def write_token_to_card(self, token: str, timeout: float = 5.0) -> bool:
        """
        Upisuje token u karticu koja se trenutno drži na čitaču
        :param token: Token za upis
        :param timeout: Maksimalno vreme čekanja kartice
        :return: True ako je upis uspešan
        """
        print(f"Čekam karticu za upis tokena: {token}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                uid = self.nfc_reader.read_card_once(timeout=0.5)
                if uid:
                    uid_hex = ''.join(f"{b:02X}" for b in uid)
                    print(f"Kartica za upis detektovana: {uid_hex}")
                    
                    # Pokušaj upis
                    if self.nfc_reader.write_block(uid, 6, token):
                        print(f"Token '{token}' uspešno upisan!")
                        return True
                    else:
                        print("Greška pri upisu tokena")
                        return False
                        
            except Exception as e:
                print(f"Greška pri upisu: {e}")
                
            time.sleep(0.1)
        
        print("Timeout - kartica nije detektovana za upis")
        return False

    def closeEvent(self, event):
        """Cleanup pri zatvaranju aplikacije"""
        print("Zatvaranje aplikacije - cleanup NFC...")
        self.stop_nfc_polling()
        super().closeEvent(event)

    def __del__(self):
        """Destruktor - cleanup"""
        if hasattr(self, 'nfc_thread'):
            self.stop_nfc_polling()
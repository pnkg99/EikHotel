from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import QObject, pyqtSignal
from services.pn532 import SimpleUltralightReader
from services.web import read_nfc_card, get_card_history, enter_restaurant, enter_gym

class NFCManager(QObject):
    """Jednostavan NFC Manager - samo osnovne read/write funkcije"""
    
    def __init__(self):
        super().__init__()
        # Kreiraj jedan reader koji će se koristiti za sve operacije
        self.nfc_reader = SimpleUltralightReader()
        self.token_block_number = 5
        self.cvc_block_number = 6
        print("✓ NFCManager inicijalizovan - bez polling-a")

    def is_card_present(self):
        """Proverava da li je kartica prisutna"""
        try:
            uid = self.nfc_reader.read_card_once(timeout=0.5)
            return uid is not None
        except Exception as e:
            print(f"Greška pri proveri kartice: {e}")
            return False

    def get_card_uid(self):
        """Čita UID kartice ako je prisutna"""
        try:
            uid = self.nfc_reader.read_card_once(timeout=1.0)
            if uid:
                return bytes(uid)
            return None
        except Exception as e:
            print(f"Greška pri čitanju UID: {e}")
            return None

    def read_block(self, block_number):
        """Čita blok sa NFC kartice"""
        try:
            # Prvo proverava da li je kartica tu
            if not self.is_card_present():
                print(f"Kartica nije prisutna za čitanje bloka {block_number}")
                return None
                
            return self.nfc_reader.read_block(block_number)
        except Exception as e:
            print(f"Greška pri čitanju bloka {block_number}: {e}")
            return None

    def write_block(self, block_number, data):
        """Upisuje podatke u blok na NFC kartici"""
        try:
            # Prvo proverava da li je kartica tu
            if not self.is_card_present():
                print(f"Kartica nije prisutna za upis u blok {block_number}")
                return False
                
            return self.nfc_reader.write_block(block_number, data)
        except Exception as e:
            print(f"Greška pri upisu u blok {block_number}: {e}")
            return False

    def read_card_data(self):
        """Čita token i CVC sa kartice"""
        try:
            if not self.is_card_present():
                print("Kartica nije prisutna za čitanje podataka")
                return None, None, None
                
            uid = self.get_card_uid()
            token = self.read_block(self.token_block_number)
            cvc = self.read_block(self.cvc_block_number)
            
            return uid, token, cvc
        except Exception as e:
            print(f"Greška pri čitanju podataka kartice: {e}")
            return None, None, None


class ScreenManager(QStackedWidget):
    """Screen Manager koji koristi SimpleUltralightReader polling"""
    
    def __init__(self):
        super().__init__()
        self.screens = {}
        
        # Kreiraj NFC Manager (bez polling-a)
        self.nfc_manager = NFCManager()
        
        # Kreiraj glavni NFC reader sa polling-om
        self.main_nfc_reader = SimpleUltralightReader(on_card_read=self._handle_card_detected)
        
        # App state
        self.token = None
        self.uid = None
        self.cvc = None
        self.slug = None
        self.card_active = False
        self.restaurant_entered = False
        self.gym_entered = False
        self.parking_space = None
        self.reg_car_number = None
        self.parking_allocated = False
        self.transactions = []
        
        print("✓ ScreenManager inicijalizovan")

    def _handle_card_detected(self, uid):
        """Handler koji poziva SimpleUltralightReader kada detektuje karticu"""
        try:
            self.uid = bytes(uid)
            uid_hex = ''.join(f"{b:02X}" for b in uid)
            print(f"🔍 Kartica detektovana: {uid_hex}")
            
            # Koristi NFCManager za čitanje podataka (ne main_nfc_reader)
            _, token, cvc = self.nfc_manager.read_card_data()
            
            self.token = token
            self.cvc = cvc
            
            print(f"📖 Token: '{self.token}'")
            print(f"📖 CVC: '{self.cvc}'")
            
            if self.token and self.cvc:
                # Pozovi web servis
                resp = read_nfc_card(self.token, self.cvc)
                print(f"🌐 Web response: {resp}")
                
                if resp:
                    if resp["status"] == 2:
                        # Neregistrovana kartica
                        print("📝 Kartica nije registrovana - prelazim na register")
                        self.show_screen("register")
                    elif resp["status"] == 1:
                        # Registrovana kartica
                        data = resp.get("data", {})
                        self.slug = data.get("slug")
                        
                        if "restaurant" in self.screens and self.slug:
                            self.screens["restaurant"].update_slug(self.slug)
                        
                        print("✅ Kartica je registrovana - prelazim na customer")
                        self.show_screen("customer")
                        self.card_active = True
                        self.restaurant_entered = False
                        self.gym_entered = False
                    else:
                        print(f"⚠️ Neočekivan status: {resp['status']}")
                else:
                    print("❌ Nema odgovora od web servisa")
            else:
                print("📝 Token/CVC nije pročitan - prelazim na register")
                self.show_screen("register")
                
        except Exception as e:
            print(f"❌ Greška pri obradi kartice: {e}")

    def _update_history(self):
        """Ažurira istoriju transakcija"""
        try:
            resp = get_card_history(self.token, self.cvc)
            if resp:
                self.transactions = resp.get("transations", [])
                if "history" in self.screens:
                    self.screens["history"].update_history(self.transactions)
                
                parking = resp.get("parking", {})
                self.parking_space = parking.get("parking_space", None)
                self.reg_car_number = parking.get("reg_car_number", None)
                
                # Handle "null" strings from API
                if self.parking_space == "null":
                    self.parking_space = None
                if self.reg_car_number == "null":
                    self.reg_car_number = None
                
                self.parking_allocated = bool(self.reg_car_number and self.parking_space)
                
                print(f"🅿️ Parking allocated: {self.parking_allocated}")
                print(f"🅿️ Space: {self.parking_space}, Car: {self.reg_car_number}")
        except Exception as e:
            print(f"❌ Greška pri ažuriranju istorije: {e}")

    def start_nfc_polling(self):
        """Pokretanje glavnog NFC polling-a"""
        try:
            print("🔄 Pokretam NFC polling...")
            self.main_nfc_reader.start_polling()
        except Exception as e:
            print(f"❌ Greška pri pokretanju polling-a: {e}")

    def stop_nfc_polling(self):
        """Zaustavljanje glavnog NFC polling-a"""
        try:
            print("⏹️ Zaustavljam NFC polling...")
            self.main_nfc_reader.stop_polling()
        except Exception as e:
            print(f"❌ Greška pri zaustavljanju polling-a: {e}")

    def add_screen(self, name, widget):
        """Dodaje novi screen"""
        self.screens[name] = widget
        self.addWidget(widget)
        print(f"📱 Dodat screen: {name}")

    def show_screen(self, name):
        """Prikazuje određeni screen"""
        if name not in self.screens:
            print(f"❌ Screen '{name}' ne postoji!")
            return
            
        try:
            # Upravljanje polling-om
            if name == "home":
                self.start_nfc_polling()
            else:
                self.stop_nfc_polling()

            # Logika za ulazak u restoran
            if (self.card_active and 
                name == "restaurant" and 
                not self.restaurant_entered and 
                self.token):
                try:
                    enter_restaurant(self.token, self.cvc)
                    self.restaurant_entered = True
                    print("🍽️ Uspešan ulazak u restoran")
                except Exception as e:
                    print(f"❌ Greška pri ulasku u restoran: {e}")

            # Logika za ulazak u teretanu
            if (self.card_active and 
                name == "gym" and 
                not self.gym_entered and 
                self.token):
                try:
                    enter_gym(self.token, self.cvc)
                    self.gym_entered = True
                    print("💪 Uspešan ulazak u teretanu")
                except Exception as e:
                    print(f"❌ Greška pri ulasku u teretanu: {e}")

            # Ažuriraj istoriju za customer screen
            if name == "customer":
                self._update_history()

            # Prikaži screen
            self.setCurrentWidget(self.screens[name])
            print(f"📱 Prebačeno na screen: {name}")
            
        except Exception as e:
            print(f"❌ Greška pri prikazivanju screen-a {name}: {e}")

    def write_token(self, token):
        """Upisuje token na NFC karticu"""
        try:
            print(f"✍️ Upisujem token: '{token}'")
            return self.nfc_manager.write_block(self.nfc_manager.token_block_number, token)
        except Exception as e:
            print(f"❌ Greška pri upisu tokena: {e}")
            return False

    def write_cvc(self, cvc):
        """Upisuje CVC na NFC karticu"""
        try:
            print(f"✍️ Upisujem CVC: '{cvc}'")
            return self.nfc_manager.write_block(self.nfc_manager.cvc_block_number, cvc)
        except Exception as e:
            print(f"❌ Greška pri upisu CVC: {e}")
            return False

    def manual_card_check(self):
        """Ručna provera kartice (za dugmad u UI)"""
        try:
            print("🔍 Ručna provera kartice...")
            uid, token, cvc = self.nfc_manager.read_card_data()
            
            if uid:
                print(f"✅ Kartica pronađena: {uid.hex()}")
                self._handle_card_detected(uid)
                return True
            else:
                print("❌ Kartica nije pronađena")
                return False
        except Exception as e:
            print(f"❌ Greška pri ručnoj proveri: {e}")
            return False

    def get_card_status(self):
        """Vraća status trenutne kartice"""
        return {
            'uid': self.uid.hex() if self.uid else None,
            'token': self.token,
            'cvc': self.cvc,
            'card_active': self.card_active,
            'restaurant_entered': self.restaurant_entered,
            'gym_entered': self.gym_entered,
            'parking_allocated': self.parking_allocated,
            'parking_space': self.parking_space,
            'reg_car_number': self.reg_car_number
        }

    def closeEvent(self, event):
        """Cleanup pri zatvaranju aplikacije"""
        print("🔄 Zatvaranje aplikacije - cleanup NFC...")
        try:
            self.stop_nfc_polling()
            # Kratka pauza da se polling završi
            import time
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Greška pri cleanup-u: {e}")
        super().closeEvent(event)

    def __del__(self):
        """Destruktor - cleanup"""
        try:
            if hasattr(self, 'main_nfc_reader'):
                self.stop_nfc_polling()
        except:
            pass
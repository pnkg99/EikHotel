from PyQt5.QtWidgets import QStackedWidget
from services.pn532 import create_nfc_reader
from services.web import read_nfc_card, get_card_history, enter_restaurant, enter_gym
class ScreenManager(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.screens = {}
        self.nfc_reader = create_nfc_reader(self._handle_read_card)
        self.pin = "123456"
        self.number = None
        self.cvc = None
        self.uid = None

        self.card_active = False  
        self.restaurant_entered = False
        self.gym_entered = False
        
        self.parking_space = None
        self.reg_car_number = None
        self.parking_allocated = False

    def _updage_history(self):
        resp = get_card_history(self.number, self.cvc)
        if resp:
            # update history transactions
            self.transactions = resp.get("transations", [])
            self.screens["history"].update_history(self.transactions)
            # update parking status 
            self.parking_space = resp.get("parking", {}).get("parking_space", None)
            if self.parking_space == "null" : self.parking_space = None
            self.reg_car_number = resp.get("parking", {}).get("reg_car_number", None)
            if self.reg_car_number == "null" : self.reg_car_number = None
            if self.reg_car_number and self.parking_space : self.parking_allocated = True
            print(self.parking_allocated)
          
    def _handle_read_card(self, uid, uuid):
        self.uid = uid
        self.token = self.nfc_reader.read_block_simple(uid)

        if self.token :
            resp = read_nfc_card(self.token, "8888888")
            print(resp)
            if resp:
                if resp["status"] == 2:
                    self.show_screen("register")
                elif resp["status"] == 1:
                    self.slug = resp.get("data").get("slug")
                    self.screens["restaurant"].update_slug(self.slug)
                    self.show_screen("customer")
                    # Resetuj slotove pri novom očitavanju kartice
                    self.card_active = True
                    self.restaurant_entered = False
                    self.gym_entered = False

    def add_screen(self, name, widget):
        self.screens[name] = widget
        self.addWidget(widget)

    def show_screen(self, name):
        if name in self.screens:
            if name == "home":
                self.nfc_reader.start()
            else:
                self.nfc_reader.stop()

            # Provera za ulazak u restoran
            if self.card_active and name == "restaurant" and not self.restaurant_entered:
                enter_restaurant(self.number, self.cvc)
                self.restaurant_entered = True

            if name == "customer" :
                self._updage_history()

            self.setCurrentWidget(self.screens[name])


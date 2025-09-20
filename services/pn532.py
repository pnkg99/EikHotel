import time
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_ULTRALIGHT
import busio
import board

class SimpleUltralightReader:
    """Klasa za čitanje i pisanje MIFARE Ultralight kartica koristeći Adafruit PN532 preko I2C."""

    def __init__(self, i2c=None):
        """Inicijalizacija PN532 čitača preko I2C interfejsa."""
        try:
            # Ako I2C nije prosleđen, koristi podrazumevani I2C bus
            if i2c is None:
                i2c = busio.I2C(board.SCL, board.SDA)
            
            # Inicijalizacija PN532 preko I2C
            self.pn532 = PN532_I2C(i2c, debug=False)
            
            # Inicijalizacija firmvera i konfiguracija za MIFARE kartice
            self.pn532.SAM_configuration()
            print("PN532 čitač inicijalizovan preko I2C.")
        except Exception as e:
            print(f"Greška pri inicijalizaciji PN532: {e}")
            raise

    def read_card_once(self, timeout=0.1):
        """Čita UID kartice jednom, vraća bytes ili None ako nema kartice."""
        try:
            # Čitanje UID-a kartice sa zadatim timeout-om (u milisekundama)
            uid = self.pn532.read_passive_target(timeout=int(timeout * 1000))
            return uid if uid else None
        except Exception as e:
            print(f"Greška pri čitanju UID-a kartice: {e}")
            return None

    def read_block(self, block_number):
        """Čita podatke iz specificiranog bloka na MIFARE Ultralight kartici."""
        try:
            # Provera da li je kartica prisutna
            uid = self.read_card_once(timeout=0.1)
            if not uid:
                print("Nema detektovane kartice.")
                return None

            # Čitanje bloka (MIFARE Ultralight blokovi su 4 bajta)
            data = self.pn532.mifareultralight_read_block(block_number)
            if data is None:
                print(f"Greška pri čitanju bloka {block_number}.")
                return None
            
            # Vraća podatke kao hex string, kompatibilno sa NFCManager
            return data.hex().upper()
        except Exception as e:
            print(f"Greška pri čitanju bloka {block_number}: {e}")
            return None

    def write_block(self, block_number, data):
        """Upisuje podatke u specificirani blok na MIFARE Ultralight kartici."""
        try:
            # Provera da li je kartica prisutna
            uid = self.read_card_once(timeout=0.1)
            if not uid:
                print("Nema detektovane kartice.")
                return False

            # Priprema podataka (MIFARE Ultralight blokovi su 4 bajta)
            if isinstance(data, str):
                # Ako je data string, pretvori u bajtove (npr. hex string)
                data = bytes.fromhex(data)
            if len(data) != 4:
                print(f"Podaci moraju biti tačno 4 bajta za blok {block_number}.")
                return False

            # Upisivanje bloka
            success = self.pn532.mifareultralight_write_block(block_number, data)
            if not success:
                print(f"Greška pri upisu u blok {block_number}.")
                return False
            
            return True
        except Exception as e:
            print(f"Greška pri upisu u blok {block_number}: {e}")
            return False

    def cleanup(self):
        """Cleanup resursa pri gašenju."""
        print("Zatvaranje PN532 čitača.")
        # PN532_I2C ne zahteva eksplicitno zatvaranje I2C veze, ali osiguravamo čist izlaz
        self.pn532.power_down()
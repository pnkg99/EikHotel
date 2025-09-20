import time
import logging
from typing import Optional, Callable
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B, MIFARE_CMD_AUTH_A

class SimpleNFCReader:
    """
    Pojednostavljen NFC čitač za Raspberry Pi preko PN532 (I2C)
    """
    
    def __init__(self, on_card_read: Optional[Callable[[bytes], None]] = None):
        """
        :param on_card_read: Callback funkcija koja se poziva kada se detektuje kartica
        """
        self.on_card_read = on_card_read
        self.pn532 = None
        self.is_running = False
        self.default_key = [0xFF] * 6  # Default MIFARE ključ
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - [NFC] - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('NFC')
        
        # Inicijalizuj čitač
        self._init_reader()
    
    def _init_reader(self) -> bool:
        """Inicijalizuje PN532 čitač"""
        try:
            self.logger.info("Inicijalizujem NFC čitač...")
            i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(i2c, debug=False)
            self.pn532.SAM_configuration()
            
            # Proveri firmware
            ic, ver, rev, support = self.pn532.firmware_version
            self.logger.info(f"PN532 Firmware: {ver}.{rev}")
            return True
            
        except Exception as e:
            self.logger.error(f"Greška pri inicijalizaciji: {e}")
            return False
    
    def start_polling(self, check_interval: float = 0.5):
        """
        Pokreće kontinuirano čitanje kartica
        :param check_interval: Interval provere u sekundama
        """
        if not self.pn532:
            self.logger.error("NFC čitač nije inicijalizovan!")
            return
        
        self.is_running = True
        self.logger.info("Pokretam polling...")
        
        last_uid = None
        
        while self.is_running:
            try:
                uid = self.pn532.read_passive_target(timeout=0.1)
    # Ako je bytearray, pretvori u bytes

                if uid:
                    if isinstance(uid, bytearray):
                        uid = bytes(uid)
                    uid_hex = ''.join(f"{b:02X}" for b in uid)
                    
                    # Pozovi callback samo za nove kartice
                    if last_uid != uid_hex:
                        self.logger.info(f"Nova kartica: {uid_hex}")
                        if self.on_card_read:
                            self.on_card_read(uid)
                        last_uid = uid_hex
                else:
                    # Resetuj UID ako nema kartice
                    if last_uid is not None:
                        self.logger.info("Kartica uklonjena")
                        last_uid = None
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Prekidam polling (Ctrl+C)")
                break
            except Exception as e:
                self.logger.error(f"Greška tokom polling-a: {e}")
                time.sleep(1)  # Kratka pauza pre ponovnog pokušaja
    
    def stop_polling(self):
        """Zaustavlja polling"""
        self.is_running = False
        self.logger.info("Polling zaustavljen")
    
    def read_card_once(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Čita karticu jednom
        :param timeout: Timeout u sekundama
        :return: UID kartice ili None
        """
        if not self.pn532:
            self.logger.error("NFC čitač nije inicijalizovan!")
            return None
        
        try:
            uid = self.pn532.read_passive_target(timeout=timeout)
            if uid:
                uid_hex = ''.join(f"{b:02X}" for b in uid)
                self.logger.info(f"Kartica detektovana: {uid_hex}")
            return uid
        except Exception as e:
            self.logger.error(f"Greška pri čitanju: {e}")
            return None
    
    def authenticate_block(self, uid: bytes, block: int) -> bool:
        """
        Autentifikuje blok za čitanje/pisanje
        :param uid: UID kartice
        :param block: Broj bloka
        :return: True ako je autentifikacija uspešna
        """
        try:
            return self.pn532.mifare_classic_authenticate_block(
                uid, block, MIFARE_CMD_AUTH_B, self.default_key
            )
        except Exception as e:
            self.logger.error(f"Greška pri autentifikaciji bloka {block}: {e}")
            return False
    
    def read_block(self, uid: bytes, block: int, key: bytes = b"\xFF\xFF\xFF\xFF\xFF\xFF"):
        try:
            uid_list = [b for b in uid]  # PN532 traži listu intova

            # Autentifikacija
            if not self.authenticate_block(uid, block):# self.pn532.mifare_classic_authenticate_block(uid_list, block, MIFARE_CMD_AUTH_A, key):
                self.logger.error(f"Autentifikacija neuspešna za blok {block} (key={key.hex()})")
                return None

            # Čitaj podatke
            data = self.pn532.mifare_classic_read_block(block)
            if not data:
                self.logger.error(f"Čitanje bloka {block} neuspešno")
                return None

            # Konverzija u string
            text = bytes(data).rstrip(b"\x00").decode("utf-8", errors="ignore")
            self.logger.info(f"Blok {block} pročitan: '{text}'")
            return text

        except Exception as e:
            self.logger.error(f"Greška pri čitanju bloka {block}: {e}")
            return None

    def write_block(self, uid: bytes, block: int, data: str):
        try:          
            # Pripremi podatke (16 bajtova sa padding)
            block_data = list(data.encode('utf-8'))[:16]
            block_data += [0x00] * (16 - len(block_data))
            
            # Upiši podatke
            self.pn532.mifare_classic_write_block(block, block_data)
            self.logger.info(f"Blok {block} upisan: '{data}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Greška pri upisu u blok {block}: {e}")
            return False
    
    def read_write_demo(self, block: int = 6):
        """
        Demo funkcija koja čeka karticu i demonstrira čitanje/pisanje
        :param block: Blok za testiranje (default 6)
        """
        print(f"\nDemo čitanje/pisanje bloka {block}")
        print("Postavite karticu na čitač...")
        
        while True:
            try:
                uid = self.read_card_once(timeout=0.5)
                if uid:
                    uid_hex = ''.join(f"{b:02X}" for b in uid)
                    print(f"\nKartica detektovana: {uid_hex}")
                    
                    # Čitaj postojeće podatke
                    existing_data = self.read_block(uid, block)
                    print(f"Postojeći podaci: '{existing_data}'")
                    
                    # Upiši nove podatke
                    new_data = f"Test-{int(time.time())}"
                    if self.write_block(uid, block, new_data):
                        print(f"Upisano: '{new_data}'")
                        
                        # Verifikuj upis
                        verified_data = self.read_block(uid, block)
                        print(f"Verifikacija: '{verified_data}'")
                        
                        if verified_data == new_data:
                            print("✓ Upis uspešan!")
                        else:
                            print("✗ Greška pri verifikaciji")
                    
                    print("\nUklonite karticu i postavite drugu za novi test...")
                    
                    # Čekaj da se kartica ukloni
                    while self.read_card_once(timeout=0.1):
                        time.sleep(0.1)
                    
                    print("Kartica uklonjena. Postavite sledeću...")
                
            except KeyboardInterrupt:
                print("\nDemo završen!")
                break
            except Exception as e:
                self.logger.error(f"Greška tokom demo: {e}")
                time.sleep(1)


class SimpleUltralightReader:
    """
    Pojednostavljen NFC čitač za Raspberry Pi preko PN532 (I2C)
    Samo za MIFARE Ultralight (stranice od 4 bajta, bez autentifikacije)
    """

    def __init__(self, on_card_read: Optional[Callable[[bytes], None]] = None):
        self.on_card_read = on_card_read
        self.pn532 = None
        self.is_running = False

        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - [NFC] - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('NFC')

        # Inicijalizuj čitač
        self._init_reader()

    def _init_reader(self) -> bool:
        try:
            self.logger.info("Inicijalizujem NFC čitač (Ultralight)...")
            i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(i2c, debug=False)
            self.pn532.SAM_configuration()

            ic, ver, rev, support = self.pn532.firmware_version
            self.logger.info(f"PN532 Firmware: {ver}.{rev}")
            return True
        except Exception as e:
            self.logger.error(f"Greška pri inicijalizaciji: {e}")
            return False

    def start_polling(self, check_interval: float = 0.5):
        if not self.pn532:
            self.logger.error("NFC čitač nije inicijalizovan!")
            return

        self.is_running = True
        self.logger.info("Pokrećem polling...")

        last_uid = None

        while self.is_running:
            try:
                uid = self.pn532.read_passive_target(timeout=0.1)
                if uid:
                    if isinstance(uid, bytearray):
                        uid = bytes(uid)
                    uid_hex = ''.join(f"{b:02X}" for b in uid)

                    if last_uid != uid_hex:
                        self.logger.info(f"Nova kartica: {uid_hex}")
                        if self.on_card_read:
                            self.on_card_read(uid)
                        last_uid = uid_hex
                else:
                    if last_uid is not None:
                        self.logger.info("Kartica uklonjena")
                        last_uid = None

                time.sleep(check_interval)

            except KeyboardInterrupt:
                self.logger.info("Prekidam polling (Ctrl+C)")
                break
            except Exception as e:
                self.logger.error(f"Greška tokom polling-a: {e}")
                time.sleep(1)

    def stop_polling(self):
        self.is_running = False
        self.logger.info("Polling zaustavljen")

    def read_card_once(self, timeout: float = 1.0) -> Optional[bytes]:
        try:
            uid = self.pn532.read_passive_target(timeout=timeout)
            if uid:
                uid_hex = ''.join(f"{b:02X}" for b in uid)
                self.logger.info(f"Kartica detektovana: {uid_hex}")
            return uid
        except Exception as e:
            self.logger.error(f"Greška pri čitanju: {e}")
            return None

    def read_page(self, page: int) -> Optional[str]:
        """Čita jednu Ultralight stranicu (4 bajta)"""
        try:
            data = self.pn532.mifare_ultralight_read_page(page)
            if not data:
                self.logger.error(f"Čitanje stranice {page} neuspešno")
                return None

            text = bytes(data).decode("utf-8", errors="ignore")
            self.logger.info(f"Stranica {page} pročitana: HEX={bytes(data).hex()} TEXT='{text}'")
            return text
        except Exception as e:
            self.logger.error(f"Greška pri čitanju stranice {page}: {e}")
            return None

    def write_page(self, page: int, data: str) -> bool:
        """Upisuje do 4 bajta na Ultralight stranicu"""
        try:
            raw = list(data.encode("utf-8"))[:4]
            raw += [0x00] * (4 - len(raw))
            self.pn532.mifare_ultralight_write_page(page, raw)
            self.logger.info(f"Stranica {page} upisana: '{data}'")
            return True
        except Exception as e:
            self.logger.error(f"Greška pri upisu stranice {page}: {e}")
            return False

    def read_write_demo(self, page: int = 4):
        """
        Demo funkcija za čitanje/pisanje Ultralight stranica
        :param page: Stranica za test (default 4 jer 0-3 su UID i OTP)
        """
        print(f"\nDemo čitanje/pisanje stranice {page}")
        print("Postavite Ultralight karticu na čitač...")

        while True:
            try:
                uid = self.read_card_once(timeout=0.5)
                if uid:
                    uid_hex = ''.join(f"{b:02X}" for b in uid)
                    print(f"\nKartica detektovana: {uid_hex}")

                    # Čitaj postojeće podatke
                    existing_data = self.read_page(page)
                    print(f"Postojeći podaci: '{existing_data}'")

                    # Upis novih podataka
                    new_data = f"T{int(time.time())}"[:4]  # max 4 bajta
                    if self.write_page(page, new_data):
                        print(f"Upisano: '{new_data}'")

                        # Verifikacija
                        verified_data = self.read_page(page)
                        print(f"Verifikacija: '{verified_data}'")

                        if verified_data.strip("\x00") == new_data:
                            print("✓ Upis uspešan!")
                        else:
                            print("✗ Greška pri verifikaciji")

                    print("\nUklonite karticu i postavite drugu za novi test...")

                    while self.read_card_once(timeout=0.1):
                        time.sleep(0.1)

                    print("Kartica uklonjena. Postavite sledeću...")

            except KeyboardInterrupt:
                print("\nDemo završen!")
                break
            except Exception as e:
                self.logger.error(f"Greška tokom demo: {e}")
                time.sleep(1)


if __name__ == "__main__":
    def card_detected(uid):
        uid_hex = ''.join(f"{b:02X}" for b in uid)
        print(f"Callback: Kartica {uid_hex} detektovana!")

    reader = SimpleUltralightReader(on_card_read=card_detected)

    try:
        reader.read_write_demo()
    except KeyboardInterrupt:
        print("Program završen!")
    finally:
        reader.stop_polling()

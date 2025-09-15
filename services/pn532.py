import time
import logging
from typing import Optional, Callable
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B

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
    
    def read_block(self, uid: bytes, block: int) -> Optional[str]:
        """
        Čita podatke iz bloka
        :param uid: UID kartice
        :param block: Broj bloka
        :return: String podataka ili None
        """
        try:
            # Autentifikuj blok
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija bloka {block} neuspešna")
                return None
            
            # Čitaj podatke
            data = self.pn532.mifare_classic_read_block(block)
            if not data:
                self.logger.error(f"Čitanje bloka {block} neuspešno")
                return None
            
            # Konvertuj u string (ukloni padding)
            text = ''.join(chr(b) for b in data if 32 <= b <= 126).rstrip('\x00')
            self.logger.info(f"Blok {block} pročitan: '{text}'")
            return text
            
        except Exception as e:
            self.logger.error(f"Greška pri čitanju bloka {block}: {e}")
            return None
    
    def write_block(self, uid: bytes, block: int, data: str) -> bool:
        """
        Upisuje podatke u blok
        :param uid: UID kartice
        :param block: Broj bloka
        :param data: String podataka (max 16 karaktera)
        :return: True ako je upis uspešan
        """
        try:
            # Autentifikuj blok
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija bloka {block} neuspešna")
                return False
            
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

# Primer korišćenja
if __name__ == "__main__":
    def card_detected(uid):
        uid_hex = ''.join(f"{b:02X}" for b in uid)
        print(f"Callback: Kartica {uid_hex} detektovana!")
    
    # Kreiraj čitač
    reader = SimpleNFCReader(on_card_read=card_detected)
    
    try:
        # Pokretni demo
        reader.read_write_demo()
        
        # Ili pokreni kontinuirani polling
        # reader.start_polling(check_interval=0.3)
        
    except KeyboardInterrupt:
        print("Program završen!")
    finally:
        reader.stop_polling()
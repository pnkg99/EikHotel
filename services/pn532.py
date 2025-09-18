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
    
    def _init_reader(self) :
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
    
    def read_card_once(self, timeout: float = 1.0):
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
    
    def authenticate_block(self, uid: bytes, block: int):
        try:
            if self.pn532.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_A, self.default_key):
                return True
            if self.pn532.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_B, self.default_key):
                return True
            return False
        except Exception as e:
            self.logger.error(f"Greška pri autentifikaciji bloka {block}: {e}")
            return False

    
    def read_block(self, uid: bytes, block: int):
        try:
            # Autentifikacija
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija neuspešna za blok {block} (key={self.default_key.hex()})")
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
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija neuspešna za blok {block}")
                return False

            block_data = list(data.encode('utf-8'))[:16]
            block_data += [0x00] * (16 - len(block_data))
            
            self.pn532.mifare_classic_write_block(block, block_data)
            self.logger.info(f"Blok {block} upisan: '{data[:16]}'")
            return True

        except Exception as e:
            self.logger.error(f"Greška pri upisu u blok {block}: {e}")
            return False

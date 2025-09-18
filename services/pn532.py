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
        self.default_key = bytes([0xFF] * 6)  # Default MIFARE ključ
        self.alternative_keys = [
            bytes([0x00] * 6),  # Null ključ
            bytes([0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]),  # MAD ključ
            bytes([0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]),  # NFC Forum ključ
        ]
        self.last_successful_key = {}  # Keš za uspešne ključeve po sektoru
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - [NFC] - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('NFC')
        
        # Inicijalizuj čitač
        self._init_reader()
    
    def _init_reader(self):
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
                time.sleep(1)
    
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
    
    def get_sector_trailer_block(self, block: int):
        """Vraća broj bloka sector trailer-a za dati blok"""
        sector = block // 4
        return sector * 4 + 3

    def authenticate_block(self, uid: bytes, block: int):
        """Autentifikacija bloka sa keširanjem ključeva"""
        sector = block // 4
        # Proveri keširani ključ za sektor
        if sector in self.last_successful_key:
            key, auth_cmd = self.last_successful_key[sector]
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, block, auth_cmd, key):
                    self.logger.info(f"Autentifikacija uspešna za blok {block} sa keširanim ključem {key.hex()}")
                    return True
            except Exception as e:
                self.logger.debug(f"Keširani ključ neuspešan za blok {block}: {e}")
        
        # Pokušaj default ključ sa AUTH_A prvo (jer je kartica formatirana)
        try:
            if self.pn532.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_A, self.default_key):
                self.logger.info(f"Autentifikacija uspešna za blok {block} sa default ključem {self.default_key.hex()}")
                self.last_successful_key[sector] = (self.default_key, MIFARE_CMD_AUTH_A)
                return True
        except Exception as e:
            self.logger.debug(f"Default ključ neuspešan za blok {block}: {e}")
        
        # Pokušaj preko sector trailer-a
        trailer_block = self.get_sector_trailer_block(block)
        if block != trailer_block:
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, trailer_block, MIFARE_CMD_AUTH_A, self.default_key):
                    self.logger.info(f"Autentifikacija uspešna preko trailer bloka {trailer_block} za blok {block}")
                    self.last_successful_key[sector] = (self.default_key, MIFARE_CMD_AUTH_A)
                    return True
            except Exception as e:
                self.logger.debug(f"Trailer autentifikacija neuspešna za blok {trailer_block}: {e}")
        
        # Pokušaj alternativne ključeve
        keys_to_try = self.alternative_keys
        auth_commands = [MIFARE_CMD_AUTH_A, MIFARE_CMD_AUTH_B]
        
        for key in keys_to_try:
            for auth_cmd in auth_commands:
                try:
                    self.logger.debug(f"Pokušavam autentifikaciju bloka {block} sa ključem {key.hex()} i komandom {auth_cmd}")
                    if self.pn532.mifare_classic_authenticate_block(uid, block, auth_cmd, key):
                        self.logger.info(f"Autentifikacija uspešna za blok {block} sa ključem {key.hex()}")
                        self.last_successful_key[sector] = (key, auth_cmd)
                        return True
                except Exception as e:
                    self.logger.debug(f"Autentifikacija neuspešna za blok {block}: {e}")
                    continue
        
        self.logger.error(f"Sve autentifikacije neuspešne za blok {block}")
        return False

    def read_block(self, uid: bytes, block: int):
        """Čitanje bloka sa proverom access bits-a"""
        try:
            # Proveri da li je blok sector trailer
            if block % 4 == 3:
                self.logger.error(f"Blok {block} je sector trailer - koristi read_sector_trailer!")
                return None
            
            # Proveri access bits pre čitanja
            trailer_block = self.get_sector_trailer_block(block)
            trailer_data = self.read_sector_trailer(uid, block // 4)
            if trailer_data:
                access_bits = trailer_data[6:10]
                expected_access_bits = bytes([0xFF, 0x07, 0x80, 0x69])
                if access_bits != expected_access_bits:
                    self.logger.warning(f"Nestandardni access bits u sektoru {block // 4}: {access_bits.hex()}")
            
            # Pokušaj čitanje bez ponovne autentifikacije
            try:
                data = self.pn532.mifare_classic_read_block(block)
                if data:
                    text = bytes(data).rstrip(b"\x00").decode("utf-8", errors="ignore")
                    self.logger.info(f"Blok {block} pročitan (bez ponovne autentifikacije): '{text}'")
                    return text
            except:
                pass
            
            # Autentifikuj ako je potrebno
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija neuspešna za blok {block}")
                return None
            
            # Čitaj podatke
            time.sleep(0.2)  # Pauza za stabilnost
            data = self.pn532.mifare_classic_read_block(block)
            if not data:
                self.logger.error(f"Čitanje bloka {block} neuspešno")
                return None
            
            text = bytes(data).rstrip(b"\x00").decode("utf-8", errors="ignore")
            self.logger.info(f"Blok {block} pročitan: '{text}'")
            return text
        
        except Exception as e:
            self.logger.error(f"Greška pri čitanju bloka {block}: {str(e)}")
            return None

    def write_block(self, uid: bytes, block: int, data: str):
        """Upisivanje u blok sa proverom access bits-a"""
        try:
            # Proveri da li je blok sector trailer
            if block % 4 == 3:
                self.logger.error(f"Blok {block} je sector trailer - upis nije dozvoljen!")
                return False
            
            # Proveri access bits pre upisa
            trailer_block = self.get_sector_trailer_block(block)
            trailer_data = self.read_sector_trailer(uid, block // 4)
            if trailer_data:
                access_bits = trailer_data[6:10]
                expected_access_bits = bytes([0xFF, 0x07, 0x80, 0x69])
                if access_bits != expected_access_bits:
                    self.logger.warning(f"Nestandardni access bits u sektoru {block // 4}: {access_bits.hex()}. Upis možda neće raditi.")
            
            # Autentifikuj
            if not self.authenticate_block(uid, block):
                self.logger.error(f"Autentifikacija neuspešna za blok {block}")
                return False
            
            # Pripremi podatke za upis
            block_data = list(data.encode('utf-8'))[:16]
            block_data += [0x00] * (16 - len(block_data))
            
            # Upis podataka
            self.pn532.mifare_classic_write_block(block, block_data)
            self.logger.info(f"Blok {block} upisan: '{data[:16]}'")
            time.sleep(0.2)  # Pauza za stabilnost
            
            # Verifikacija upisa
            verification = self.read_block(uid, block)
            if verification and verification.strip() == data.strip():
                self.logger.info(f"Verifikacija uspešna za blok {block}")
                return True
            else:
                self.logger.warning(f"Verifikacija neuspešna za blok {block}")
                return False
        
        except Exception as e:
            self.logger.error(f"Greška pri upisu u blok {block}: {str(e)}")
            return False

    def format_card_sector(self, uid: bytes, sector: int):   
        """Formatira sektor sa default ključevima (OPASNO!)"""
        try:
            trailer_block = sector * 4 + 3
            access_bits = [0xFF, 0x07, 0x80, 0x69]
            trailer_data = list(self.default_key) + access_bits + list(self.default_key)
            
            if self.authenticate_block(uid, trailer_block):
                self.pn532.mifare_classic_write_block(trailer_block, trailer_data)
                self.logger.info(f"Sektor {sector} formatiran")
                return True
                
        except Exception as e:
            self.logger.error(f"Greška pri formatiranju sektora {sector}: {e}")
            return False

    def read_sector_trailer(self, uid: bytes, sector: int):
        """Čita sector trailer za proveru ključeva i access bits-a"""
        trailer_block = sector * 4 + 3
        if self.authenticate_block(uid, trailer_block):
            data = self.pn532.mifare_classic_read_block(trailer_block)
            if data:
                key_a = data[0:6]
                access_bits = data[6:10]
                key_b = data[10:16]
                self.logger.info(f"Sector {sector} trailer: KeyA={key_a.hex()}, AccessBits={access_bits.hex()}, KeyB={key_b.hex()}")
                return data
        self.logger.error(f"Neuspešno čitanje sector trailer-a {sector}")
        return None

# Testni kod za upis i čitanje blokova 12 i 13
if __name__ == "__main__":
    def on_card_read(uid):
        print(f"Kartica detektovana: {''.join(f'{b:02X}' for b in uid)}")
    
    nfc = SimpleNFCReader(on_card_read=on_card_read)
    
    # Čekaj karticu
    uid = nfc.read_card_once(timeout=5.0)
    if not uid:
        print("Nema kartice!")
        exit()
    
    # Pročitaj sector trailer sektora 3 (blokovi 12 i 13)
    nfc.read_sector_trailer(uid, 3)
    
    # Upis i čitanje blokova 12 i 13
    blocks = [12, 13]
    test_data = "12345"  # Promeni po potrebi
    for block in blocks:
        if nfc.write_block(uid, block, test_data):
            print(f"Upis uspešan u blok {block}: {test_data}")
            read_data = nfc.read_block(uid, block)
            print(f"Pročitano iz bloka {block}: {read_data}")
        else:
            print(f"Upis neuspešan za blok {block}")
    
    nfc.stop_polling()
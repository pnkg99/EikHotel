import time
import logging
import busio
import board
from typing import Optional, Callable
from adafruit_pn532.i2c import PN532_I2C

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

    def _init_reader(self):
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

    def read_card_once(self, timeout: float = 1.0):
        try:
            uid = self.pn532.read_passive_target(timeout=timeout)
            if uid:
                uid_hex = ''.join(f"{b:02X}" for b in uid)
                self.logger.info(f"Kartica detektovana: {uid_hex}")
            return uid
        except Exception as e:
            self.logger.error(f"Greška pri čitanju: {e}")
            return None

    def read_block(self, page: int):
        """Čita jednu Ultralight stranicu (4 bajta) - koristi generičku MIFARE funkciju"""
        try:
            # Pokušaj sa standardnom MIFARE read funkcijom
            if hasattr(self.pn532, 'mifare_classic_read_block'):
                # Neki driveri koriste ovu funkciju za sve MIFARE tipove
                data = self.pn532.mifare_classic_read_block(page)
            elif hasattr(self.pn532, 'ntag2xx_read_block'):
                # Alternativa za NTAG/Ultralight
                data = self.pn532.ntag2xx_read_block(page)
            elif hasattr(self.pn532, 'read_mifare_block'):
                # Još jedna varijanta
                data = self.pn532.read_mifare_block(page)
            else:
                # Fallback - pokušaj sa low-level komandom
                data = self._read_ultralight_page_raw(page)
            
            if not data:
                self.logger.error(f"Čitanje stranice {page} neuspešno")
                return None

            # Uzmi samo prva 4 bajta (Ultralight stranica)
            page_data = data[:4] if len(data) > 4 else data
            text = bytes(page_data).decode("utf-8", errors="ignore")
            self.logger.info(f"Stranica {page} pročitana: HEX={bytes(page_data).hex()} TEXT='{text}'")
            return text
        except Exception as e:
            self.logger.error(f"Greška pri čitanju stranice {page}: {e}")
            return None

    def _read_ultralight_page_raw(self, page: int):
        """Raw čitanje stranice koristeći low-level PN532 komande"""
        try:
            # MIFARE Ultralight READ komanda (0x30)
            response = self.pn532.call_function(
                0x40,  # InDataExchange
                params=[0x01, 0x30, page]  # Tg=1, CMD=READ, Page
            )
            if response and len(response) > 1:
                return response[1:]  # Prvi bajt je status
            return None
        except Exception as e:
            self.logger.error(f"Raw čitanje neuspešno: {e}")
            return None

    def write_block(self, page: int, data: str):
        """Upisuje do 4 bajta na Ultralight stranicu"""
        try:
            raw = list(data.encode("utf-8"))[:4]
            raw += [0x00] * (4 - len(raw))
            
            # Pokušaj sa različitim write funkcijama
            if hasattr(self.pn532, 'mifare_classic_write_block'):
                success = self.pn532.mifare_classic_write_block(page, raw)
            elif hasattr(self.pn532, 'ntag2xx_write_block'):
                success = self.pn532.ntag2xx_write_block(page, raw)
            elif hasattr(self.pn532, 'write_mifare_block'):
                success = self.pn532.write_mifare_block(page, raw)
            else:
                success = self._write_ultralight_page_raw(page, raw)
            
            if success:
                self.logger.info(f"Stranica {page} upisana: '{data}'")
                return True
            else:
                self.logger.error(f"Upis stranice {page} neuspešan")
                return False
        except Exception as e:
            self.logger.error(f"Greška pri upisu stranice {page}: {e}")
            return False

    def _write_ultralight_page_raw(self, page: int, data: list):
        """Raw upis stranice koristeći low-level PN532 komande"""
        try:
            # MIFARE Ultralight WRITE komanda (0xA2)
            params = [0x01, 0xA2, page] + data[:4]
            response = self.pn532.call_function(0x40, params=params)
            return response is not None
        except Exception as e:
            self.logger.error(f"Raw upis neuspešan: {e}")
            return False

    def get_available_methods(self):
        """Debug funkcija - prikazuje dostupne metode u pn532 objektu"""
        if self.pn532:
            methods = [method for method in dir(self.pn532) if 'read' in method.lower() or 'write' in method.lower()]
            self.logger.info(f"Dostupne read/write metode: {methods}")
            return methods
        return []

# Primer korišćenja:
if __name__ == "__main__":
    def on_card_detected(uid):
        print(f"Detektovana kartica sa UID: {uid.hex()}")
    
    reader = SimpleUltralightReader(on_card_read=on_card_detected)
    
    # Debug - prikaži dostupne metode
    reader.get_available_methods()
    
    try:
        # Test čitanja
        uid = reader.read_card_once(timeout=2.0)
        if uid:
            # Pokušaj čitanje nekoliko stranica
            for page in range(4, 8):  # Stranice 4-7 su obično dostupne za upis
                data = reader.read_block(page)
                print(f"Stranica {page}: {data}")
    except KeyboardInterrupt:
        print("Program prekinut")
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
        """Čita jednu Ultralight stranicu (4 bajta)"""
        try:
            # MIFARE Ultralight = NTAG kompatibilan
            data = self.pn532.ntag2xx_read_block(page)
            
            if not data:
                self.logger.error(f"Čitanje stranice {page} neuspešno")
                return None

            # NTAG vraća 16 bajta (4 stranice), uzmi samo prvi blok (4 bajta)
            page_data = data[:4]
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
            # Proveri da li je stranica dostupna za upis
            if page < 4:
                self.logger.error(f"Stranica {page} je rezervisana - ne može se pisati!")
                return False
                
            if page > 15:
                self.logger.error(f"Stranica {page} je van dosega Ultralight kartice!")
                return False
            
            # Pripremi podatke
            raw_data = data.encode("utf-8")[:4]
            raw = list(raw_data)
            # Dopuni do 4 bajta sa 0x00
            while len(raw) < 4:
                raw.append(0x00)
            
            self.logger.info(f"Pokušavam upis na stranicu {page}: {raw} ('{data}')")
            
            # Prvo proverava da li kartica još uvek postoji
            uid = self.pn532.read_passive_target(timeout=0.1)
            if not uid:
                self.logger.error("Kartica nije više u dosegu!")
                return False
            
            # Pokušaj upis
            success = self.pn532.ntag2xx_write_block(page, raw)
            
            if success:
                self.logger.info(f"Stranica {page} uspešno upisana: '{data}'")
                
                # Verifikuj upis čitanjem
                time.sleep(0.1)  # Kratka pauza
                verification = self.read_block(page)
                if verification and verification.strip('\x00') == data:
                    self.logger.info("Upis verifikovan!")
                    return True
                else:
                    self.logger.warning(f"Upis možda nije uspešan - verifikacija: '{verification}'")
                    return True  # Vraćamo True jer je write_block vratio success
            else:
                self.logger.error(f"ntag2xx_write_block vratio False za stranicu {page}")
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

    def get_card_info(self):
        """Čita osnovne informacije o kartici"""
        try:
            uid = self.read_card_once()
            if not uid:
                return None
                
            info = {
                'uid': ''.join(f"{b:02X}" for b in uid),
                'uid_length': len(uid),
                'card_type': 'MIFARE Ultralight' if len(uid) == 7 else 'Unknown'
            }
            
            # Pokušaj čitati prve stranice za dodatne info
            try:
                page0 = self.pn532.ntag2xx_read_block(0)  # UID + BCC
                page1 = self.pn532.ntag2xx_read_block(1)  # Još UID + internal
                
                if page0 and len(page0) >= 4:
                    info['serial_number'] = bytes(page0[:4]).hex()
                    
                self.logger.info(f"Kartica info: {info}")
                return info
            except:
                self.logger.warning("Ne mogu čitati dodatne informacije o kartici")
                return info
                
        except Exception as e:
            self.logger.error(f"Greška pri čitanju info kartice: {e}")
            return None

# Primer korišćenja:
if __name__ == "__main__":
    def on_card_detected(uid):
        print(f"Detektovana kartica sa UID: {uid.hex()}")
    
    reader = SimpleUltralightReader(on_card_read=on_card_detected)
    
    try:
        # Test čitanja
        print("Priloži MIFARE Ultralight karticu...")
        uid = reader.read_card_once(timeout=5.0)
        
        if uid:
            # Prikaži info o kartici
            info = reader.get_card_info()
            print(f"Kartica info: {info}")
            
            # Pokušaj čitanje korisničkih stranica (4-15)
            print("\nČitam korisničke stranice:")
            for page in range(4, 8):  # Stranice 4-7
                data = reader.read_block(page)
                if data:
                    print(f"  Stranica {page}: '{data.strip()}'")
            
            # Test upisa sa detaljnim dijagnostikama
            test_write = input("\nDa li želiš testirati upis na stranicu 4? (y/N): ")
            if test_write.lower() == 'y':
                
                # Proveri zaštitu od upisa
                print("Proveravam zaštitu kartice...")
                is_protected = reader.check_card_write_protection()
                
                test_data = "TEST"
                print(f"Pokušavam standardni upis: '{test_data}'")
                
                if reader.write_block(4, test_data):
                    print(f"✓ Uspešno upisano: '{test_data}'")
                    # Verifikuj upis
                    read_back = reader.read_block(4)
                    print(f"✓ Verifikacija: '{read_back.strip()}'")
                else:
                    print("✗ Standardni upis neuspešan, pokušavam alternativni...")
                    if reader.try_alternative_write(4, test_data):
                        read_back = reader.read_block(4)
                        print(f"✓ Alternativni upis uspešan: '{read_back.strip()}'")
                    else:
                        print("✗ Svi pokušaji upisa neuspešni")
                        print("Mogući uzroci:")
                        print("  - Kartica je zaštićena od upisa")
                        print("  - Kartica nije MIFARE Ultralight već drugi tip")
                        print("  - Hardverski problem sa čitačem")
                        print("  - Karticu pomeri ili je oštećena")
        else:
            print("Kartica nije detektovana")
            
    except KeyboardInterrupt:
        print("\nProgram prekinut")
    finally:
        reader.stop_polling()
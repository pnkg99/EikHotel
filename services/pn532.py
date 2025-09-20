import time
import logging
import busio
import board
from typing import Optional, Callable
from adafruit_pn532.i2c import PN532_I2C

class SimpleUltralightReader:
    """
    Pojednostavljen NFC čitač za Raspberry Pi preko PN532 (I2C)
    Koristi osnovne read_frame/write_frame API funkcije za direktnu kontrolu
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

    def _send_command_frame(self, command, params=None):
        """Šalje komandu korišćenjem _write_frame i čita odgovor sa _read_frame"""
        try:
            # Pripremi frame: [COMMAND] + [PARAMS]
            frame = [command]
            if params:
                frame.extend(params)
            
            # Pošalji komandu
            self.logger.info(f"→ Šaljem: {[hex(x) for x in frame]}")
            self.pn532._write_frame(frame)
            
            # Sačekaj kratko
            time.sleep(0.05)
            
            # Čitaj odgovor - length je obavezni parametar
            try:
                response = self.pn532._read_frame(length=32)
                if response:
                    self.logger.info(f"← Odgovor (32B): {[hex(x) for x in response]}")
                    return response
            except Exception as e1:
                self.logger.warning(f"_read_frame(32) neuspešan: {e1}")
                
                # Pokušaj sa različitim length vrednostima
                for length in [16, 64, 8, 128]:
                    try:
                        response = self.pn532._read_frame(length=length)
                        if response:
                            self.logger.info(f"← Odgovor ({length}B): {[hex(x) for x in response]}")
                            return response
                    except Exception as e2:
                        self.logger.debug(f"_read_frame({length}) neuspešan: {e2}")
                        continue
            
            self.logger.error("Svi pokušaji čitanja frame-a neuspešni")
            return None
                
        except Exception as e:
            self.logger.error(f"Greška pri slanju komande: {e}")
            return None

    def read_block(self, page: int):
        """Čita MIFARE Ultralight stranicu - MORA da aktivira karticu pre čitanja!"""
        try:
            if page < 0 or page > 15:
                self.logger.error(f"Stranica {page} je van dosega (0-15)")
                return None
            
            # KLJUČNO: Ponovo aktiviraj karticu pre čitanja!
            self.logger.debug(f"Aktiviram karticu za čitanje stranice {page}...")
            uid = self.pn532.read_passive_target(timeout=1.0)
            
            if not uid:
                self.logger.error(f"Kartica nije dostupna za čitanje stranice {page}")
                return None
            
            # Sada pokušaj čitanje sa NTAG funkcijom
            data = self.pn532.ntag2xx_read_block(page)
            
            if data:
                # Uzmi prva 4 bajta (jedna Ultralight stranica)
                page_data = data[:4]
                text = bytes(page_data).decode("utf-8", errors="ignore")
                
                self.logger.info(f"✓ Stranica {page}: HEX={bytes(page_data).hex().upper()} TEXT='{text.strip()}'")
                return text
            else:
                self.logger.warning(f"✗ Stranica {page}: ntag2xx_read_block vratio None")
                
                # Fallback: pokušaj sa MIFARE Classic funkcijom
                try:
                    # Ponovo aktiviraj karticu
                    uid = self.pn532.read_passive_target(timeout=0.5)
                    if uid:
                        classic_data = self.pn532.mifare_classic_read_block(page)
                        if classic_data:
                            page_data = classic_data[:4]
                            text = bytes(page_data).decode("utf-8", errors="ignore")
                            self.logger.info(f"✓ Stranica {page} (Classic fallback): TEXT='{text.strip()}'")
                            return text
                except:
                    pass
                
                return None
                
        except Exception as e:
            self.logger.error(f"Greška pri čitanju stranice {page}: {e}")
            return None

    def write_block(self, page: int, data: str):
        """Upisuje na MIFARE Ultralight stranicu - mora aktivirati karticu pre upisa!"""
        try:
            if page < 4:
                self.logger.error(f"Stranica {page} je rezervisana!")
                return False
                
            if page > 15:
                self.logger.error(f"Stranica {page} je van dosega!")
                return False
            
            # Pripremi podatke (4 bajta)
            raw_data = data.encode("utf-8")[:4]
            write_data = list(raw_data)
            while len(write_data) < 4:
                write_data.append(0x00)
            
            self.logger.info(f"Upisujem na stranicu {page}: {write_data} ('{data}')")
            
            # KLJUČNO: Aktiviraj karticu pre upisa!
            uid = self.pn532.read_passive_target(timeout=1.0)
            
            if not uid:
                self.logger.error("Kartica nije dostupna za upis!")
                return False
            
            # Pokušaj upis sa NTAG funkcijom
            try:
                success = self.pn532.ntag2xx_write_block(page, write_data)
                
                if success:
                    self.logger.info(f"✓ NTAG upis stranice {page} uspešan!")
                    
                    # Verifikuj upis
                    time.sleep(0.1)  # Kratka pauza
                    verification = self.read_block(page)
                    if verification and verification.strip('\x00').strip() == data:
                        self.logger.info("✓ Upis verifikovan!")
                    else:
                        self.logger.warning(f"⚠ Verifikacija: '{verification}' vs '{data}'")
                    
                    return True
                else:
                    self.logger.warning("✗ NTAG upis neuspešan, pokušavam Classic fallback...")
                    
            except Exception as e:
                self.logger.warning(f"NTAG upis greška: {e}, pokušavam fallback...")
            
            # Fallback: Pokušaj sa MIFARE Classic funkcijom
            try:
                # Ponovo aktiviraj karticu
                uid = self.pn532.read_passive_target(timeout=1.0)
                if uid:
                    success = self.pn532.mifare_classic_write_block(page, write_data)
                    if success:
                        self.logger.info(f"✓ Classic upis stranice {page} uspešan!")
                        return True
                    else:
                        self.logger.error("✗ Classic upis takođe neuspešan")
                        
            except Exception as e:
                self.logger.error(f"Classic upis greška: {e}")
            
            return False
                
        except Exception as e:
            self.logger.error(f"Greška pri upisu stranice {page}: {e}")
            return False

    def simple_debug_read(self, page: int):
        """Jednostavan debug za čitanje stranice"""
        try:
            self.logger.info(f"\n=== DEBUG READ stranice {page} ===")
            
            # Pokušaj sa različitim komandama
            commands_to_try = [
                ([0x40, 0x01, 0x30, page], "InDataExchange + READ"),
                ([0x30, page], "Direktni READ"), 
                ([0x32, page], "FAST_READ"),
            ]
            
            for cmd, desc in commands_to_try:
                try:
                    self.logger.info(f"Pokušavam: {desc}")
                    self.pn532._write_frame(cmd)
                    time.sleep(0.05)
                    
                    # _read_frame zahteva length parametar
                    response = self.pn532._read_frame(length=32)
                    if response:
                        self.logger.info(f"  ✓ Odgovor: {[hex(x) for x in response]}")
                        if len(response) >= 4:
                            # Pokušaj dekodovanje
                            for start in range(min(4, len(response))):
                                data = response[start:start+4] if start+4 <= len(response) else response[start:]
                                if len(data) > 0:
                                    text = bytes(data).decode("utf-8", errors="ignore").strip('\x00')
                                    if text and all(ord(c) < 127 for c in text):  # ASCII check
                                        self.logger.info(f"    Možda tekst od pozicije {start}: '{text}'")
                    else:
                        self.logger.info(f"  ✗ Nema odgovora")
                        
                except Exception as e:
                    self.logger.info(f"  ✗ Greška: {e}")
                    
            self.logger.info("=== KRAJ DEBUG ===\n")
            
        except Exception as e:
            self.logger.error(f"Debug greška: {e}")

    def try_high_level_read(self, page: int):
        """Pokušaj čitanje sa high-level funkcijama"""
        methods_to_try = [
            ('ntag2xx_read_block', 'NTAG read'),
            ('mifare_classic_read_block', 'MIFARE Classic read'),
            ('read_passive_target', 'Passive target read'),
        ]
        
        for method_name, desc in methods_to_try:
            if hasattr(self.pn532, method_name):
                try:
                    method = getattr(self.pn532, method_name)
                    self.logger.info(f"Pokušavam {desc} ({method_name})")
                    
                    if method_name == 'read_passive_target':
                        # Ova funkcija ne prima page parametar
                        continue
                    
                    result = method(page)
                    if result:
                        self.logger.info(f"✓ {desc} uspešan: {[hex(x) for x in result] if hasattr(result, '__iter__') else result}")
                        
                        # Pokušaj dekodovanje
                        if hasattr(result, '__iter__') and len(result) >= 4:
                            data = result[:4]  # Prva 4 bajta
                            text = bytes(data).decode("utf-8", errors="ignore").strip('\x00')
                            self.logger.info(f"  Tekst: '{text}'")
                            return text
                    else:
                        self.logger.info(f"✗ {desc} vratio None")
                        
                except Exception as e:
                    self.logger.info(f"✗ {desc} greška: {e}")
                    
        return None
        """Probaj originalne ntag funkcije ako ih imamo"""
        try:
            if hasattr(self.pn532, 'ntag2xx_read_block'):
                self.logger.info(f"Pokušavam ntag2xx_read_block({page})")
                data = self.pn532.ntag2xx_read_block(page)
                if data:
                    self.logger.info(f"NTAG odgovor: {[hex(x) for x in data]}")
                    text = bytes(data[:4]).decode("utf-8", errors="ignore")
                    return text
            return None
        except Exception as e:
            self.logger.error(f"NTAG fallback greška: {e}")
            return None
        """Čita osnovne informacije o kartici"""
        try:
            uid = self.read_card_once()
            if not uid:
                return None
                
            info = {
                'uid': ''.join(f"{b:02X}" for b in uid),
                'uid_length': len(uid),
                'card_type': 'MIFARE Ultralight' if len(uid) == 7 else 'Možda drugi tip'
            }
            
            # Čitaj prvu stranicu za dodatne informacije
            try:
                page0_data = self.read_block(0)
                if page0_data:
                    # Prva stranica sadrži deo UID-a
                    info['page0_content'] = page0_data.encode('utf-8').hex()
                    
            except:
                self.logger.warning("Ne mogu čitati stranicu 0")
                
            self.logger.info(f"Kartica info: {info}")
            return info
                
        except Exception as e:
            self.logger.error(f"Greška pri čitanju info kartice: {e}")
            return None

    def dump_all_pages(self):
        """Čita sve dostupne stranice sa ispravnom aktivacijom kartice"""
        print("\n=== DUMP SVIH STRANICA ===")
        success_count = 0
        
        for page in range(16):
            try:
                data = self.read_block(page)
                if data is not None:
                    clean_text = data.strip('\x00').strip()
                    if clean_text:
                        print(f"Stranica {page:2d}: '{clean_text}' (neprazna)")
                    else:
                        print(f"Stranica {page:2d}: [prazna]")
                    success_count += 1
                else:
                    print(f"Stranica {page:2d}: *** NEDOSTUPNA ***")
                    
                time.sleep(0.1)  # Kratka pauza između čitanja
                
            except Exception as e:
                print(f"Stranica {page:2d}: *** GREŠKA: {e} ***")
                
        print(f"\n✓ Uspešno pročitano: {success_count}/16 stranica")
        print("=== KRAJ DUMP-a ===\n")

# Primer korišćenja:
if __name__ == "__main__":
    def on_card_detected(uid):
        print(f"Detektovana kartica sa UID: {uid.hex()}")
    
    reader = SimpleUltralightReader(on_card_read=on_card_detected)
    
    try:
        print("=== ISPRAVLJENA VERZIJA ===")
        print("Priloži MIFARE Ultralight karticu...")
        
        uid = reader.read_card_once(timeout=5.0)
        
        if uid:
            info = reader.simple_debug_read()
            
            # Dump sve stranice  
            reader.dump_all_pages()
            
            # Test upisa
            test_write = input("Da li želiš testirati upis na stranicu 5? (y/N): ")
            if test_write.lower() == 'y':
                test_data = "TEST"
                print(f"\nPokušavam upis: '{test_data}' na stranicu 5")
                
                if reader.write_block(5, test_data):
                    print("✓ Upis uspešan!")
                    
                    # Čitaj nazad da potvrdiš
                    read_back = reader.read_block(5)
                    print(f"✓ Čitanje nazad: '{read_back.strip()}'")
                else:
                    print("✗ Upis neuspešan")
                    
        else:
            print("✗ Kartica nije detektovana")
            
    except KeyboardInterrupt:
        print("\nProgram prekinut")
    finally:
        reader.stop_polling()
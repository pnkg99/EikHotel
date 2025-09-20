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
        """Čita MIFARE Ultralight stranicu direktno preko frame API"""
        try:
            if page < 0 or page > 15:
                self.logger.error(f"Stranica {page} je van dosega (0-15)")
                return None
            
            # MIFARE Ultralight READ komanda = 0x30
            # Format: [0x40, 0x01, 0x30, PAGE]
            # 0x40 = InDataExchange, 0x01 = target, 0x30 = READ, PAGE = stranica
            response = self._send_command_frame(0x40, [0x01, 0x30, page])
            
            if response and len(response) >= 1:
                self.logger.info(f"Analiziram odgovor za stranicu {page}: {[hex(x) for x in response]}")
                
                # Različiti formati odgovora:
                # Format 1: [STATUS, DATA...]
                # Format 2: [0xD5, 0x41, STATUS, DATA...]
                # Format 3: [LENGTH, DATA...]
                
                data_start = 0
                status = None
                
                if len(response) >= 3 and response[0] == 0xD5 and response[1] == 0x41:
                    # Format sa prefiksom 0xD5, 0x41
                    status = response[2]
                    data_start = 3
                    self.logger.info(f"Format sa prefiksom, status: 0x{status:02X}")
                elif len(response) >= 2 and response[0] in [0x00, 0x01, 0x02]:
                    # Možda je prvi bajt status
                    status = response[0] 
                    data_start = 1
                    self.logger.info(f"Možda status: 0x{status:02X}")
                else:
                    # Možda su podaci odmah na početku
                    data_start = 0
                    self.logger.info("Pokušavam direktno čitanje podataka")
                
                if status is not None and status != 0x00:
                    self.logger.error(f"READ neuspešan, status: 0x{status:02X}")
                    return None
                
                # Uzmi podatke
                if len(response) >= data_start + 4:
                    data = response[data_start:data_start + 4]
                    text = bytes(data).decode("utf-8", errors="ignore")
                    
                    self.logger.info(f"✓ Stranica {page}: HEX={bytes(data).hex()} TEXT='{text.strip()}'")
                    return text
                else:
                    self.logger.error(f"Nedovoljno podataka u odgovoru (trebam {data_start + 4}, imam {len(response)})")
                    # Pokušaj sa celim odgovorom
                    if len(response) >= 4:
                        data = response[:4]
                        text = bytes(data).decode("utf-8", errors="ignore")
                        self.logger.warning(f"⚠ Pokušavam sa početkom: TEXT='{text.strip()}'")
                        return text
                    return None
            else:
                self.logger.error(f"Prazan ili neispravan odgovor za stranicu {page}")
                return None
                
        except Exception as e:
            self.logger.error(f"Greška pri čitanju stranice {page}: {e}")
            return None

    def write_block(self, page: int, data: str):
        """Upisuje na MIFARE Ultralight stranicu direktno preko frame API"""
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
            
            # MIFARE Ultralight WRITE komanda = 0xA2
            # Format: [0x40, 0x01, 0xA2, PAGE, DATA0, DATA1, DATA2, DATA3]
            params = [0x01, 0xA2, page] + write_data
            response = self._send_command_frame(0x40, params)
            
            if response and len(response) >= 1:
                status = response[0]
                if status == 0x00:  # Success
                    self.logger.info(f"✓ Stranica {page} uspešno upisana!")
                    
                    # Verifikuj upis
                    time.sleep(0.05)  # Kratka pauza
                    verification = self.read_block(page)
                    if verification and verification.strip('\x00').strip() == data:
                        self.logger.info("✓ Upis verifikovan!")
                    else:
                        self.logger.warning(f"⚠ Verifikacija drugačija: '{verification}'")
                    
                    return True
                else:
                    self.logger.error(f"✗ WRITE neuspešan, status: 0x{status:02X}")
                    return False
            else:
                self.logger.error("✗ Neispravan odgovor za WRITE")
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
        """Debug funkcija - čita sve stranice 0-15"""
        print("\n=== DUMP SVIH STRANICA ===")
        for page in range(16):
            try:
                print(f"\n--- Stranica {page} ---")
                
                # Prvo probaj običan read
                data = self.read_block(page)
                if data:
                    clean_text = data.strip('\x00').strip()
                    print(f"  Obično čitanje: '{clean_text}'")
                else:
                    print(f"  ✗ Obično čitanje neuspešno")
                
                # Onda probaj debug read
                self.simple_debug_read(page)
                
                # Onda probaj ntag fallback
                ntag_data = self.try_ntag_fallback(page)
                if ntag_data:
                    print(f"  NTAG fallback: '{ntag_data.strip()}'")
                
                time.sleep(0.1)  # Pauza između čitanja
                
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                
        print("=== KRAJ DUMP-a ===\n")

# Primer korišćenja:
if __name__ == "__main__":
    def on_card_detected(uid):
        print(f"Detektovana kartica sa UID: {uid.hex()}")
    
    reader = SimpleUltralightReader(on_card_read=on_card_detected)
    
    try:
        print("Priloži MIFARE Ultralight karticu...")
        uid = reader.read_card_once(timeout=5.0)
        
        if uid:
            # Prikaži info o kartici
            info = reader.get_card_info()
            print(f"Kartica info: {info}")
            
            # Test sa JEDNOM stranicom prvo
            test_page = 4  # Obično je dostupna za čitanje/pisanje
            print(f"\n=== TEST STRANICE {test_page} ===")
            
            # Pokušaj različite metode
            print("1. Standardni read_block:")
            data1 = reader.read_block(test_page)
            print(f"   Rezultat: '{data1}'" if data1 else "   ✗ Neuspešno")
            
            print("2. High-level metode:")
            data2 = reader.try_high_level_read(test_page)  
            print(f"   Rezultat: '{data2}'" if data2 else "   ✗ Neuspešno")
            
            print("3. Debug čitanje:")
            reader.simple_debug_read(test_page)
            
            # Ako bilo koji radi, nastavi sa dump-om
            if data1 or data2:
                print("\n✓ Našli smo radnu metodu! Nastavljamo sa dump-om...")
                reader.dump_all_pages()
            else:
                print("\n✗ Nijedna metoda ne radi. Moguće uzroci:")
                print("   - Kartica nije MIFARE Ultralight")  
                print("   - Problem sa PN532 komunikacijom")
                print("   - Kartica nije pravilno detektovana")
            
            # Test upisa samo ako čitanje radi
            test_write = input("Da li želiš testirati upis na stranicu 4? (y/N): ")
            if test_write.lower() == 'y':
                test_data = "TEST"
                print(f"\nPokušavam upis: '{test_data}'")
                
                if reader.write_block(4, test_data):
                    print("✓ Upis uspešan!")
                else:
                    print("✗ Upis neuspešan")
                    print("\nMogući uzroci:")
                    print("  - Kartica nije MIFARE Ultralight")
                    print("  - Kartica je zaštićena od upisa")
                    print("  - Kartica se pomerila tokom upisa")
                    
        else:
            print("Kartica nije detektovana")
            
    except KeyboardInterrupt:
        print("\nProgram prekinut")
    finally:
        reader.stop_polling()
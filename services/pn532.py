from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QWidget
import time
import logging
import traceback
from enum import Enum
from typing import Optional, Callable, Tuple, List
import sys
import platform

IS_WINDOWS = platform.system() == "Windows"
if not IS_WINDOWS:
    import board
    import busio
    from digitalio import DigitalInOut
    from adafruit_pn532.i2c import PN532_I2C
    from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B

else:
    # Dummy classes for development on Windows
    class PN532_I2C:
        def __init__(self, *args, **kwargs): pass
        def get_firmware_version(self): return [1, 2, 3, 4]
        def SAM_configuration(self): pass
        def read_passive_target(self): return b'\x01\x02\x03\x04'
        def mifare_classic_authenticate_block(self, uid, block, cmd, key): return True
        def mifare_classic_read_block(self, block): return b'\x00' * 16
        def mifare_classic_write_block(self, block, data): pass

class DebugLevel(Enum):
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4


class NFCDebugger:
    """Centralizovani debug sistem za NFC operacije"""
    
    def __init__(self, level: DebugLevel = DebugLevel.INFO):
        self.level = level
        self.setup_logging()
        self.operation_stats = {
            'reads': 0,
            'writes': 0,
            'errors': 0,
            'authentication_failures': 0,
            'connection_failures': 0
        }
    
    def setup_logging(self):
        """Postavlja logging sistem"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - [NFCReader] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nfc_debug.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('NFCReader')
    
    def log(self, level: DebugLevel, message: str, exception: Exception = None):
        """Centralno logovanje poruka"""
        if level.value <= self.level.value:
            if level == DebugLevel.ERROR:
                self.operation_stats['errors'] += 1
                if exception:
                    self.logger.error(f"{message} - Exception: {str(exception)}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                else:
                    self.logger.error(message)
            elif level == DebugLevel.WARNING:
                self.logger.warning(message)
            elif level == DebugLevel.INFO:
                self.logger.info(message)
            elif level == DebugLevel.DEBUG:
                self.logger.debug(message)
    
    def increment_stat(self, stat_name: str):
        """Incrementira statistiku operacija"""
        if stat_name in self.operation_stats:
            self.operation_stats[stat_name] += 1
    
    def get_stats(self) :
        """Vraća statistike performansi"""
        return self.operation_stats.copy()
    
    def reset_stats(self):
        """Resetuje statistike"""
        for key in self.operation_stats:
            self.operation_stats[key] = 0


class NFCConnectionManager:
    """Upravlja konekcijom sa NFC čitačem"""
    
    def __init__(self, debugger: NFCDebugger):
        self.debugger = debugger
        self.pn532 = None
        self.is_connected = False
        self.connection_retries = 3
        self.retry_delay = 1.0  # sekunde
    
    def connect(self) :
        """Uspostavlja konekciju sa NFC čitačem"""
        for attempt in range(self.connection_retries):
            try:
                self.debugger.log(DebugLevel.INFO, f"Pokušaj konekcije {attempt + 1}/{self.connection_retries}")
                
                i2c = busio.I2C(board.SCL, board.SDA)
                self.pn532 = PN532_I2C(i2c, debug=False)
                self.pn532.SAM_configuration()
                
                # Proveri firmware verziju da potvrdi konekciju
                ic, ver, rev, support = self.pn532.firmware_version
                self.debugger.log(DebugLevel.INFO, f"PN532 Firmware Version: {ver}.{rev}")
                
                self.is_connected = True
                self.debugger.log(DebugLevel.INFO, "NFC konekcija uspešno uspostavljena")
                return True
                
            except Exception as e:
                self.debugger.log(DebugLevel.ERROR, f"Greška pri konekciji (pokušaj {attempt + 1})", e)
                self.debugger.increment_stat('connection_failures')
                
                if attempt < self.connection_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    self.is_connected = False
                    return False
        
        return False
    
    def disconnect(self):
        """Prekida konekciju"""
        self.is_connected = False
        self.pn532 = None
        self.debugger.log(DebugLevel.INFO, "NFC konekcija prekinuta")
    
    def reconnect(self) :
        """Pokušava ponovno povezivanje"""
        self.debugger.log(DebugLevel.WARNING, "Pokušavam ponovno povezivanje...")
        self.disconnect()
        return self.connect()

class NFCReader:
    """
    Poboljšan NFC čitač preko PN532 (I2C) sa naprednim error handling-om i debug sistemom.
    """
    
    def __init__(self, root=None, on_card_read: Callable[[bytes], None] = None, 
                debug_level: DebugLevel = DebugLevel.INFO):

        """
        :param root: Widget koji pokreće/zaustavlja čitanje
        :param on_card_read: Callback funkcija sa potpisom on_card_read(uid, uid_hex)
        :param debug_level: Nivo debug-a
        """
        self.root = root
        self.on_card_read = on_card_read
        
        # Debug sistem
        self.debugger = NFCDebugger(debug_level)
        self.debugger.log(DebugLevel.INFO, "Inicijalizacija NFCReader-a...")
        
        # Connection manager
        self.connection_manager = NFCConnectionManager(self.debugger)
        
        # Operacioni parametri
        self.check_interval_ms = 200
        self.is_running = False
        self.last_uid = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.error_backoff_time = 2.0  # sekunde
        
        # MIFARE parametri
        self.default_key = [0xFF] * 6
        self.block = 6
        
        # Timer za operacije
        self.read_timer = None
        
        # Inicijalna konekcija
        if not self.connection_manager.connect():
            self.debugger.log(DebugLevel.ERROR, "Neuspešna inicijalna konekcija sa NFC čitačem")
    
    def start(self) :
        """Pokretanje čitanja kartica"""
        if not self.connection_manager.is_connected:
            self.debugger.log(DebugLevel.WARNING, "Pokušavam konekciju pre starta...")
            if not self.connection_manager.connect():
                self.debugger.log(DebugLevel.ERROR, "Ne mogu da uspostavim konekciju")
                return False
        
        if not self.is_running:
            self.is_running = True
            self.consecutive_errors = 0
            self._schedule_next_check()
            self.debugger.log(DebugLevel.INFO, "NFC polling startovan")
            return True
        
        return False
    
    def stop(self):
        """Zaustavljanje čitanja kartica"""
        self.is_running = False
        if self.read_timer:
            self.read_timer.stop()
            self.read_timer = None
        self.debugger.log(DebugLevel.INFO, "NFC polling zaustavljen")
    
    def _schedule_next_check(self):
        """Zakazuje sledeću proveru kartice"""
        if self.is_running:
            delay = self.check_interval_ms
            
            # Ako imamo uzastopne greške, povećaj interval
            if self.consecutive_errors > 0:
                delay = int(self.check_interval_ms * (1 + self.consecutive_errors * 0.5))
                self.debugger.log(DebugLevel.DEBUG, f"Povećan interval zbog grešaka: {delay}ms")
            
            self.read_timer = QTimer()
            self.read_timer.singleShot(delay, self._read_card_once)
    
    def _read_card_once(self):
        """Čita karticu jednom"""
        if not self.is_running:
            return
        
        try:
            if not self.connection_manager.is_connected:
                self.debugger.log(DebugLevel.WARNING, "Konekcija izgubljena, pokušavam reconnect...")
                if not self.connection_manager.reconnect():
                    self._handle_error("Neuspešan reconnect")
                    return
            
            uid = self.connection_manager.pn532.read_passive_target(timeout=0.1)
            
            if uid:
                uid_hex = ''.join(f"{b:02X}" for b in uid)
                
                if self.last_uid == uid_hex:
                    # Ista kartica, ne pozivamo callback
                    self.debugger.log(DebugLevel.DEBUG, f"Ista kartica još uvek prisutna: {uid_hex}")
                else:
                    self.last_uid = uid_hex
                    self.consecutive_errors = 0  # Reset error count on successful read
                    self.debugger.log(DebugLevel.INFO, f"Nova kartica detektovana! UID={uid_hex}")
                    self.debugger.increment_stat('reads')
                    
                    # Bezbedni callback poziv
                    try:
                        QTimer.singleShot(0, lambda: self._safe_callback(uid))
                    except Exception as e:
                        self.debugger.log(DebugLevel.ERROR, "Greška u callback pozivu", e)
            else:
                # Resetuj UID ako kartica nije prisutna
                if self.last_uid is not None:
                    self.debugger.log(DebugLevel.DEBUG, "Kartica uklonjena")
                    self.last_uid = None
            
        except Exception as e:
            self._handle_error(f"Greška pri čitanju kartice: {str(e)}", e)
        
        finally:
            self._schedule_next_check()
    
    def _safe_callback(self, uid: bytes):
        """Bezbedni poziv callback funkcije"""
        try:
            self.on_card_read(uid)
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, f"Greška u callback funkciji: {str(e)}", e)
    
    def _handle_error(self, message: str, exception: Exception = None):
        """Centralno rukovanje greškama"""
        self.consecutive_errors += 1
        self.debugger.log(DebugLevel.ERROR, f"{message} (uzastopna greška #{self.consecutive_errors})", exception)
        
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.debugger.log(DebugLevel.ERROR, f"Previše uzastopnih grešaka ({self.consecutive_errors}), privremeno zaustavljam")
            self.is_running = False
            
            # Pokušaj recovery nakon backoff perioda
            QTimer.singleShot(int(self.error_backoff_time * 1000), self._attempt_recovery)
    
    def _attempt_recovery(self):
        """Pokušava oporavak nakon grešaka"""
        self.debugger.log(DebugLevel.INFO, "Pokušavam oporavak sistema...")
        
        if self.connection_manager.reconnect():
            self.consecutive_errors = 0
            self.debugger.log(DebugLevel.INFO, "Oporavak uspešan, nastavljam sa radom")
            self.start()
        else:
            self.debugger.log(DebugLevel.ERROR, "Oporavak neuspešan")
    
    def read_block(self, uid: bytes, block: int):
        """Čita podatke iz datog MIFARE bloka sa error handling-om"""
        try:
            self.debugger.log(DebugLevel.DEBUG, f"Čitam podatke iz bloka {block}")

            
            # Čitanje
            data = self.connection_manager.pn532.mifare_classic_read_block(block)
            if not data or len(data) != 16:
                self.debugger.log(DebugLevel.ERROR, f"Čitanje bloka {block} neuspešno ili pogrešna dužina")
                return None
            
            # Dekodiranje
            result = self._decode_block_data(data)
            self.debugger.log(DebugLevel.INFO, f"Blok {block} uspešno pročitan")
            self.debugger.increment_stat('reads')
            return result
            
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, f"Greška pri čitanju bloka {block}", e)
            return None

    def write_block(self, data: str):
        """Upisuje string u blok 6 (do 16 bajtova)"""
        try:

            block_data = list(data.encode('utf-8'))[:16]
            block_data += [0x00] * (16 - len(block_data))  # padding do 16
            self.connection_manager.pn532.mifare_classic_write_block(self.block, block_data)
            self.debugger.log(DebugLevel.INFO, f"Upisano u blok {self.block}: {data}")
            return True
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, f"Greška pri upisu: {e}")
            return False

    def read_block_simple(self, uid: bytes):
        """Čita string iz bloka 6"""
        try:
            data = self.pn532.mifare_classic_read_block(self.block)
            return ''.join(chr(b) for b in data if 32 <= b <= 126).rstrip('\x00')
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, f"Greška pri čitanju: {e}")
            return ""

    def _authenticate_block(self, uid: bytes, block: int) :
        """Autentifikacija bloka sa error handling-om"""
        try:
            if not self.connection_manager.pn532.mifare_classic_authenticate_block(
                uid, block, MIFARE_CMD_AUTH_B, self.default_key):
                self.debugger.log(DebugLevel.ERROR, f"Autentifikacija bloka {block} neuspešna")
                self.debugger.increment_stat('authentication_failures')
                return False
            return True
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, f"Greška pri autentifikaciji bloka {block}", e)
            return False
    
    def _prepare_block_data(self, data: bytes):
        """Priprema podatke za upis u blok (16 bajtova)"""
        result = list(data)
        if len(result) < 16:
            result += [0x00] * (16 - len(result))
        elif len(result) > 16:
            result = result[:16]
        return result
    
    def _decode_block_data(self, data: bytes) :
        """Dekodira podatke iz bloka"""
        return ''.join(chr(b) for b in data if 32 <= b <= 126).rstrip('\x00')
    
    def _encrypt_with_pin(self, text: str, pin: str) :
        """XOR šifrovanje sa PIN-om"""
        try:
            text_bytes = text.encode('utf-8')
            pin_bytes = pin.encode('utf-8')
            
            if not pin_bytes:
                raise ValueError("PIN ne može biti prazan")
            
            encrypted = bytearray()
            for i, b in enumerate(text_bytes):
                encrypted.append(b ^ pin_bytes[i % len(pin_bytes)])
            
            return bytes(encrypted)
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, "Greška pri šifrovanju", e)
            raise
    
    def _decrypt_with_pin(self, data: bytes, pin: str) :
        """XOR dešifrovanje sa PIN-om"""
        try:
            pin_bytes = pin.encode('utf-8')
            
            if not pin_bytes:
                raise ValueError("PIN ne može biti prazan")
            
            decrypted = bytearray()
            for i, b in enumerate(data):
                decrypted.append(b ^ pin_bytes[i % len(pin_bytes)])
            
            return decrypted.decode('utf-8', errors='ignore').rstrip('\x00')
        except Exception as e:
            self.debugger.log(DebugLevel.ERROR, "Greška pri dešifrovanju", e)
            raise
    
    def get_debug_info(self) :
        """Vraća debug informacije"""
        return {
            'is_running': self.is_running,
            'is_connected': self.connection_manager.is_connected,
            'consecutive_errors': self.consecutive_errors,
            'last_uid': self.last_uid,
            'stats': self.debugger.get_stats()
        }
    
    def set_debug_level(self, level: DebugLevel):
        """Menja nivo debug-a"""
        self.debugger.level = level
        self.debugger.log(DebugLevel.INFO, f"Debug nivo promenjen na: {level.name}")




# Mock klasa za testiranje bez fizičkog čitača
class MockNFCReader(NFCReader):
    """Mock implementacija za testiranje"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.is_running = False
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self._simulate_card_read)
        self.last_uid = "14C12A99"
        
    def _initialize_reader(self):
        #print("Mock NFC Reader inicijalizovan")
        return True
    
    def start(self):
        self.is_running = True
        self.read_timer.start(3000)  # Simuliraj kartu svake 3 sekunde
        #print("Mock NFC čitač pokrenut")
    
    def stop(self):
        self.is_running = False
        self.read_timer.stop()
        #print("Mock NFC čitač zaustavljen")
    
    def _simulate_card_read(self):
        """Simulira čitanje kartice"""
        if not self.is_running:
            return
            
        # Simuliraj random UID
        #import random
        #uid_hex = f"{''.join([f'{random.randint(0,255):02X}' for _ in range(4)])}"
        uid_hex = "63627ECE"
        
        print(f"Mock kartica: {uid_hex}")
        
        if self.callback:
            self.callback()

    

def create_nfc_reader(callback=None, force_mock: bool = False):
    """Factory funkcija za kreiranje NFC čitača.
    Ako smo na Windows‑u, ili je eksplicitno zatražen mock, vraća MockNFCReader.
    Inače vraća pravi NFCReader."""
    is_windows = sys.platform.startswith("win")
    if force_mock or is_windows:
        return MockNFCReader(callback)
    else:
        return NFCReader(root=None, on_card_read=callback)


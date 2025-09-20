#!/usr/bin/env python3
"""
NFC MIFARE čitač/pisač koristeći PN532 preko I2C komunikacije
Potrebne biblioteke: adafruit-circuitpython-pn532
Instalacija: pip install adafruit-circuitpython-pn532
"""

import board
import busio
import time
from adafruit_pn532.i2c import PN532_I2C

class MIFAREHandler:
    def __init__(self):
        """Inicijalizacija PN532 NFC modula preko I2C"""
        try:
            # Kreiranje I2C objekta
            self.i2c = busio.I2C(board.SCL, board.SDA)
            
            # Kreiranje PN532 objekta
            self.pn532 = PN532_I2C(self.i2c, debug=False)
            
            # Konfiguracija PN532
            ic, ver, rev, support = self.pn532.firmware_version
            print(f'PN532 pronađen sa firmware verzijom: {ver}.{rev}')
            
            # Konfiguracija za čitanje kartica
            self.pn532.SAM_configuration()
            
        except Exception as e:
            print(f"Greška pri inicijalizaciji PN532: {e}")
            raise

    def wait_for_card(self, timeout=10):
        """
        Čeka da se kartica približi čitaču
        
        Args:
            timeout (int): Maksimalno vreme čekanja u sekundama
            
        Returns:
            bytes: UID kartice ili None ako nema kartice
        """
        print("Približite karticu čitaču...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Pokušaj čitanja MIFARE kartice
            uid = self.pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                print(f"Kartica pronađena! UID: {[hex(i) for i in uid]}")
                return uid
            time.sleep(0.1)
        
        print("Timeout - kartica nije pronađena")
        return None

    def authenticate_block(self, uid, block_number, key_a=None, key_b=None):
        """
        Autentifikacija za pristup bloku
        
        Args:
            uid (bytes): UID kartice
            block_number (int): Broj bloka (0-63)
            key_a (bytes): Ključ A (default: [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
            key_b (bytes): Ključ B (default: None)
            
        Returns:
            bool: True ako je autentifikacija uspešna
        """
        if key_a is None:
            key_a = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]  # Default MIFARE ključ
        
        try:
            # Pokušaj autentifikacije sa ključem A
            if self.pn532.mifare_classic_authenticate_block(uid, block_number, 0x60, key_a):
                print(f"Autentifikacija bloka {block_number} uspešna (Ključ A)")
                return True
            
            # Ako nije uspelo sa ključem A, pokušaj sa ključem B
            if key_b is not None:
                if self.pn532.mifare_classic_authenticate_block(uid, block_number, 0x61, key_b):
                    print(f"Autentifikacija bloka {block_number} uspešna (Ključ B)")
                    return True
            
            print(f"Autentifikacija bloka {block_number} neuspešna")
            return False
            
        except Exception as e:
            print(f"Greška pri autentifikaciji bloka {block_number}: {e}")
            return False

    def read_block(self, uid, block_number, key_a=None):
        """
        Čitanje podataka iz bloka
        
        Args:
            uid (bytes): UID kartice
            block_number (int): Broj bloka za čitanje
            key_a (bytes): Ključ za autentifikaciju
            
        Returns:
            bytes: Podaci iz bloka ili None ako neuspešno
        """
        if not self.authenticate_block(uid, block_number, key_a):
            return None
        
        try:
            data = self.pn532.mifare_classic_read_block(block_number)
            print(f"Blok {block_number}: {[hex(b) for b in data]}")
            return data
        except Exception as e:
            print(f"Greška pri čitanju bloka {block_number}: {e}")
            return None

    def write_block(self, uid, block_number, data, key_a=None):
        """
        Pisanje podataka u blok
        
        Args:
            uid (bytes): UID kartice
            block_number (int): Broj bloka za pisanje
            data (bytes/list): Podaci za pisanje (16 bajtova)
            key_a (bytes): Ključ za autentifikaciju
            
        Returns:
            bool: True ako je pisanje uspešno
        """
        # Proveri da li su podaci tačno 16 bajtova
        if len(data) != 16:
            print(f"Greška: Podaci moraju biti tačno 16 bajtova, trenutno: {len(data)}")
            return False
        
        # Proveri da li pokušava pisanje u sector trailer (svaki 4. blok počevši od 3)
        if (block_number + 1) % 4 == 0:
            print(f"Upozorenje: Blok {block_number} je sector trailer - pisanje može oštetiti karticu!")
            response = input("Da li želite da nastavite? (y/N): ")
            if response.lower() != 'y':
                return False
        
        if not self.authenticate_block(uid, block_number, key_a):
            return False
        
        try:
            if self.pn532.mifare_classic_write_block(block_number, data):
                print(f"Pisanje u blok {block_number} uspešno")
                return True
            else:
                print(f"Pisanje u blok {block_number} neuspešno")
                return False
        except Exception as e:
            print(f"Greška pri pisanju u blok {block_number}: {e}")
            return False

    def read_sector(self, uid, sector_number, key_a=None):
        """
        Čitanje celog sektora (3 bloka + sector trailer)
        
        Args:
            uid (bytes): UID kartice
            sector_number (int): Broj sektora (0-15)
            key_a (bytes): Ključ za autentifikaciju
            
        Returns:
            list: Lista podataka iz svih blokova sektora
        """
        sector_data = []
        start_block = sector_number * 4
        
        print(f"Čitanje sektora {sector_number} (blokovi {start_block}-{start_block+3}):")
        
        for i in range(4):
            block_number = start_block + i
            data = self.read_block(uid, block_number, key_a)
            if data is not None:
                sector_data.append(data)
            else:
                sector_data.append(None)
        
        return sector_data

    def format_data_as_string(self, data):
        """
        Formatiranje podataka kao string (filtriranje printable karaktera)
        
        Args:
            data (bytes): Podaci za formatiranje
            
        Returns:
            str: Formatiran string
        """
        if data is None:
            return "N/A"
        
        # Konvertuj u printable karaktere
        text = ""
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII karakteri
                text += chr(byte)
            else:
                text += "."
        
        return text

    def write_text_to_blocks(self, uid, start_block, text, key_a=None):
        """
        Pisanje teksta kroz više blokova
        
        Args:
            uid (bytes): UID kartice
            start_block (int): Početni blok
            text (str): Tekst za pisanje
            key_a (bytes): Ključ za autentifikaciju
            
        Returns:
            bool: True ako je pisanje uspešno
        """
        text_bytes = text.encode('utf-8')
        blocks_needed = (len(text_bytes) + 15) // 16  # Okrugli na gornji broj blokova
        
        print(f"Pisanje teksta '{text}' ({len(text_bytes)} bajtova) u {blocks_needed} blokova")
        
        for i in range(blocks_needed):
            block_number = start_block + i
            
            # Uzmi 16 bajtova za trenutni blok
            start_idx = i * 16
            end_idx = min(start_idx + 16, len(text_bytes))
            block_data = text_bytes[start_idx:end_idx]
            
            # Dopuni do 16 bajtova sa nulama
            while len(block_data) < 16:
                block_data += b'\x00'
            
            if not self.write_block(uid, block_number, block_data, key_a):
                print(f"Neuspešno pisanje bloka {block_number}")
                return False
        
        return True


def main():
    """Glavna funkcija - demonstracija rada sa MIFARE karticama"""
    try:
        # Inicijalizacija NFC čitača
        nfc = MIFAREHandler()
        
        while True:
            print("\n" + "="*50)
            print("NFC MIFARE Čitač/Pisač")
            print("="*50)
            print("1. Čitanje kartice")
            print("2. Pisanje u blok")
            print("3. Čitanje sektora")
            print("4. Pisanje teksta")
            print("5. Izlaz")
            
            choice = input("\nIzaberite opciju (1-5): ").strip()
            
            if choice == '1':
                # Čitanje kartice
                uid = nfc.wait_for_card()
                if uid:
                    print("\n--- Čitanje blokova ---")
                    for block in range(1, 4):  # Čitaj blokove 1, 2, 3 iz sektora 0
                        data = nfc.read_block(uid, block)
                        if data:
                            text = nfc.format_data_as_string(data)
                            print(f"Blok {block} kao tekst: '{text}'")
            
            elif choice == '2':
                # Pisanje u specifični blok
                uid = nfc.wait_for_card()
                if uid:
                    try:
                        block_num = int(input("Unesite broj bloka za pisanje (1-62): "))
                        if block_num < 1 or block_num > 62:
                            print("Nevaljan broj bloka!")
                            continue
                        
                        data_input = input("Unesite podatke (max 16 karaktera): ")
                        data_bytes = data_input.encode('utf-8')[:16]
                        
                        # Dopuni do 16 bajtova
                        while len(data_bytes) < 16:
                            data_bytes += b'\x00'
                        
                        nfc.write_block(uid, block_num, data_bytes)
                        
                    except ValueError:
                        print("Nevaljan broj bloka!")
            
            elif choice == '3':
                # Čitanje celog sektora
                uid = nfc.wait_for_card()
                if uid:
                    try:
                        sector_num = int(input("Unesite broj sektora (0-15): "))
                        if sector_num < 0 or sector_num > 15:
                            print("Nevaljan broj sektora!")
                            continue
                        
                        sector_data = nfc.read_sector(uid, sector_num)
                        
                        print(f"\n--- Sektor {sector_num} ---")
                        for i, data in enumerate(sector_data):
                            block_num = sector_num * 4 + i
                            if data:
                                text = nfc.format_data_as_string(data)
                                print(f"Blok {block_num}: '{text}'")
                            
                    except ValueError:
                        print("Nevaljan broj sektora!")
            
            elif choice == '4':
                # Pisanje teksta kroz više blokova
                uid = nfc.wait_for_card()
                if uid:
                    try:
                        start_block = int(input("Unesite početni blok (1-60): "))
                        if start_block < 1 or start_block > 60:
                            print("Nevaljan broj bloka!")
                            continue
                        
                        text = input("Unesite tekst za pisanje: ")
                        nfc.write_text_to_blocks(uid, start_block, text)
                        
                    except ValueError:
                        print("Nevaljan broj bloka!")
            
            elif choice == '5':
                print("Izlazim...")
                break
            
            else:
                print("Nevalidna opcija!")
                
    except KeyboardInterrupt:
        print("\nProgram prekinut od strane korisnika")
    except Exception as e:
        print(f"Greška: {e}")


if __name__ == "__main__":
    main()
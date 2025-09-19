#!/usr/bin/env python3
"""
MIFARE kartica reset na fabricko stanje
Pokušava različite kombinacije ključeva i resetuje kartice
"""

import board
import busio
import time
from adafruit_pn532.i2c import PN532_I2C

class MIFAREResetter:
    def __init__(self):
        """Inicijalizacija PN532 NFC modula"""
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(self.i2c, debug=False)
            
            ic, ver, rev, support = self.pn532.firmware_version
            print(f'PN532 firmware: {ver}.{rev}')
            self.pn532.SAM_configuration()
            
            # Različite kombinacije ključeva koje se često koriste
            self.common_keys = [
                [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],  # Default fabricki
                [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # Sve nule
                [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],  # MAD ključ A
                [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7],  # MAD ključ B
                [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC],  # Test ključ
                [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF],  # Drugi test ključ
                [0x48, 0x4F, 0x4C, 0x4F, 0x4E, 0x45],  # "HOLONE"
                [0x42, 0x52, 0x45, 0x41, 0x4B, 0x45],  # "BREAKE"
            ]
            
            # Fabricki default access bits (FF078069)
            self.default_access_bits = [0xFF, 0x07, 0x80, 0x69]
            
        except Exception as e:
            print(f"Greška pri inicijalizaciji: {e}")
            raise

    def wait_for_card(self, timeout=10):
        """Čekanje kartice"""
        print("Približite karticu čitaču...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            uid = self.pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                print(f"Kartica pronađena! UID: {[hex(i) for i in uid]}")
                return uid
            time.sleep(0.1)
        
        return None

    def try_authenticate(self, uid, block, key, key_type=0x60):
        """Pokušaj autentifikacije sa datim ključem"""
        try:
            return self.pn532.mifare_classic_authenticate_block(uid, block, key_type, key)
        except:
            return False

    def find_working_key(self, uid, block):
        """Pronalaženje radnog ključa za blok"""
        print(f"Tražim radni ključ za blok {block}...")
        
        for i, key in enumerate(self.common_keys):
            # Pokušaj sa ključem A (0x60)
            if self.try_authenticate(uid, block, key, 0x60):
                print(f"  ✓ Ključ A #{i+1} radi: {[hex(k) for k in key]}")
                return key, 0x60
            
            # Pokušaj sa ključem B (0x61)
            if self.try_authenticate(uid, block, key, 0x61):
                print(f"  ✓ Ključ B #{i+1} radi: {[hex(k) for k in key]}")
                return key, 0x61
        
        print(f"  ✗ Nijedan ključ ne radi za blok {block}")
        return None, None

    def reset_sector_trailer(self, uid, sector):
        """Resetovanje sector trailer bloka na fabricke postavke"""
        trailer_block = sector * 4 + 3
        print(f"\nResetujem sector trailer {trailer_block} (sektor {sector})...")
        
        # Pronađi radni ključ
        working_key, key_type = self.find_working_key(uid, trailer_block)
        if not working_key:
            return False
        
        try:
            # Kreiraj fabricki sector trailer
            # Format: Key A (6) + Access bits (4) + Key B (6)
            factory_trailer = (
                [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF] +  # Key A (default)
                self.default_access_bits +                 # Access bits 
                [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]     # Key B (default)
            )
            
            # Pokušaj pisanje
            if self.pn532.mifare_classic_write_block(trailer_block, factory_trailer):
                print(f"  ✓ Sector trailer {trailer_block} resetovan!")
                return True
            else:
                print(f"  ✗ Neuspešno pisanje u trailer {trailer_block}")
                return False
                
        except Exception as e:
            print(f"  ✗ Greška pri resetovanju trailer {trailer_block}: {e}")
            return False

    def clear_data_blocks(self, uid, sector):
        """Brisanje podataka iz data blokova sektora"""
        print(f"\nBrišem podatke iz sektora {sector}...")
        
        success_count = 0
        for block_offset in range(3):  # Blokovi 0, 1, 2 u sektoru
            block = sector * 4 + block_offset
            
            # Preskoči blok 0 (manufacturer data)
            if block == 0:
                print(f"  - Preskačem blok 0 (manufacturer data)")
                continue
            
            # Pokušaj sa default ključem
            if self.try_authenticate(uid, block, self.common_keys[0], 0x60):
                try:
                    # Obriši blok (postavi sve na 0x00)
                    empty_data = [0x00] * 16
                    if self.pn532.mifare_classic_write_block(block, empty_data):
                        print(f"  ✓ Blok {block} obrisan")
                        success_count += 1
                    else:
                        print(f"  ✗ Neuspešno brisanje bloka {block}")
                except Exception as e:
                    print(f"  ✗ Greška pri brisanju bloka {block}: {e}")
            else:
                print(f"  ✗ Ne mogu da pristupim bloku {block}")
        
        return success_count

    def full_card_reset(self, uid):
        """Kompletno resetovanje kartice"""
        print("\n" + "="*60)
        print("KOMPLETNO RESETOVANJE KARTICE")
        print("="*60)
        
        # Prvo pokušaj resetovanje svih sector trailer-a
        trailer_success = 0
        for sector in range(16):  # MIFARE 1K ima 16 sektora
            if self.reset_sector_trailer(uid, sector):
                trailer_success += 1
        
        print(f"\nResetovano {trailer_success}/16 sector trailer blokova")
        
        # Zatim obriši podatke iz blokova
        total_cleared = 0
        for sector in range(16):
            cleared = self.clear_data_blocks(uid, sector)
            total_cleared += cleared
        
        print(f"\nObrisano {total_cleared} data blokova")
        
        if trailer_success > 0 or total_cleared > 0:
            print("\n✓ RESETOVANJE DELIMIČNO ILI POTPUNO USPEŠNO!")
            print("Kartica je vraćena u fabricko stanje koliko god je moguće.")
        else:
            print("\n✗ RESETOVANJE NEUSPEŠNO")
            print("Kartica je možda trajno zaštićena ili oštećena.")
        
        return trailer_success, total_cleared

    def diagnose_card(self, uid):
        """Dijagnostika kartice - provera stanja"""
        print("\n" + "="*60)
        print("DIJAGNOSTIKA KARTICE")
        print("="*60)
        
        accessible_blocks = []
        locked_blocks = []
        
        for sector in range(16):
            print(f"\nSektor {sector} (blokovi {sector*4}-{sector*4+3}):")
            
            for block_offset in range(4):
                block = sector * 4 + block_offset
                block_accessible = False
                
                # Pokušaj sa svim ključevima
                for key in self.common_keys:
                    if self.try_authenticate(uid, block, key, 0x60) or \
                       self.try_authenticate(uid, block, key, 0x61):
                        print(f"  ✓ Blok {block} - pristupačan")
                        accessible_blocks.append(block)
                        block_accessible = True
                        
                        # Pokušaj čitanja
                        try:
                            data = self.pn532.mifare_classic_read_block(block)
                            # Prikaži prvi deo podataka
                            preview = ' '.join([f'{b:02X}' for b in data[:8]]) + "..."
                            print(f"    Data: {preview}")
                        except:
                            print(f"    Data: Neuspešno čitanje")
                        break
                
                if not block_accessible:
                    print(f"  ✗ Blok {block} - ZAKLJUČAN")
                    locked_blocks.append(block)
        
        print(f"\n--- REZIME ---")
        print(f"Pristupačnih blokova: {len(accessible_blocks)}/64")
        print(f"Zaključanih blokova: {len(locked_blocks)}/64")
        
        if len(locked_blocks) > 0:
            print(f"Zaključani blokovi: {locked_blocks}")
        
        return accessible_blocks, locked_blocks

    def sector_by_sector_reset(self, uid):
        """Reset sektor po sektor sa detaljnom dijagnostikom"""
        print("\n" + "="*60)
        print("RESET SEKTOR PO SEKTOR")
        print("="*60)
        
        for sector in range(16):
            print(f"\n--- SEKTOR {sector} ---")
            
            # Pokušaj pristup sector trailer-u
            trailer_block = sector * 4 + 3
            working_key, key_type = self.find_working_key(uid, trailer_block)
            
            if working_key:
                # Resetuj trailer
                self.reset_sector_trailer(uid, sector)
                
                # Obriši podatke
                self.clear_data_blocks(uid, sector)
            else:
                print(f"Sektor {sector} je potpuno zaključan")
            
            time.sleep(0.1)  # Kratka pauza između sektora


def main():
    """Glavna funkcija"""
    try:
        resetter = MIFAREResetter()
        
        while True:
            print("\n" + "="*60)
            print("MIFARE KARTICA RESET TOOL")
            print("="*60)
            print("1. Dijagnostika kartice (proveri stanje)")
            print("2. Pokušaj kompletno resetovanje")
            print("3. Reset sektor po sektor")
            print("4. Reset samo sector trailer blokova")
            print("5. Izlaz")
            
            choice = input("\nIzaberite opciju (1-5): ").strip()
            
            uid = resetter.wait_for_card()
            if not uid:
                print("Kartica nije pronađena!")
                continue
            
            if choice == '1':
                resetter.diagnose_card(uid)
                
            elif choice == '2':
                print("\n⚠️  UPOZORENJE: Ova opcija će pokušati kompletno resetovanje kartice!")
                print("Svi podaci će biti obrisani i kartica vraćena na fabricke postavke.")
                confirm = input("Da li želite da nastavite? (yes/no): ").lower()
                
                if confirm == 'yes':
                    resetter.full_card_reset(uid)
                else:
                    print("Operacija otkazana.")
                    
            elif choice == '3':
                resetter.sector_by_sector_reset(uid)
                
            elif choice == '4':
                print("\nResetujem samo sector trailer blokove...")
                success = 0
                for sector in range(16):
                    if resetter.reset_sector_trailer(uid, sector):
                        success += 1
                print(f"\nResetovano {success}/16 sector trailer blokova")
                
            elif choice == '5':
                print("Izlazim...")
                break
                
            else:
                print("Nevalidna opcija!")
                
    except KeyboardInterrupt:
        print("\nProgram prekinut")
    except Exception as e:
        print(f"Greška: {e}")


if __name__ == "__main__":
    main()
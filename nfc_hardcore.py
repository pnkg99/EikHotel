#!/usr/bin/env python3
"""
Hardcore MIFARE Recovery Tool
Za kartice sa promenjenim ključevima ili corrupted access bits
"""

import board
import busio
import time
import itertools
from adafruit_pn532.i2c import PN532_I2C

class HardcoreRecovery:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pn532 = PN532_I2C(self.i2c, debug=False)
        
        firmware = self.pn532.firmware_version
        if not firmware:
            raise Exception("PN532 ne odgovara!")
            
        print(f"PN532 Firmware: {firmware[1]}.{firmware[2]}")
        self.pn532.SAM_configuration()
        
        # Proširena lista ključeva (uključuje i čudne kombinacije)
        self.recovery_keys = [
            # Standard ključevi
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],  # Default
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # Nule
            [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],  # MAD key
            [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7],  # MAD key B
            
            # Česti programerski ključevi
            [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC],
            [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF],  
            [0x11, 0x11, 0x11, 0x11, 0x11, 0x11],
            [0x22, 0x22, 0x22, 0x22, 0x22, 0x22],
            [0x33, 0x33, 0x33, 0x33, 0x33, 0x33],
            [0x44, 0x44, 0x44, 0x44, 0x44, 0x44],
            [0x55, 0x55, 0x55, 0x55, 0x55, 0x55],
            [0x66, 0x66, 0x66, 0x66, 0x66, 0x66],
            [0x77, 0x77, 0x77, 0x77, 0x77, 0x77],
            [0x88, 0x88, 0x88, 0x88, 0x88, 0x88],
            [0x99, 0x99, 0x99, 0x99, 0x99, 0x99],
            [0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA],
            [0xBB, 0xBB, 0xBB, 0xBB, 0xBB, 0xBB],
            [0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC],
            [0xDD, 0xDD, 0xDD, 0xDD, 0xDD, 0xDD],
            [0xEE, 0xEE, 0xEE, 0xEE, 0xEE, 0xEE],
            
            # ASCII sekvence
            [0x41, 0x42, 0x43, 0x44, 0x45, 0x46],  # ABCDEF
            [0x31, 0x32, 0x33, 0x34, 0x35, 0x36],  # 123456
            [0x30, 0x30, 0x30, 0x30, 0x30, 0x30],  # 000000
            [0x31, 0x31, 0x31, 0x31, 0x31, 0x31],  # 111111
            [0x4D, 0x49, 0x46, 0x41, 0x52, 0x45],  # MIFARE
            
            # Sekvencijalni
            [0x01, 0x02, 0x03, 0x04, 0x05, 0x06],
            [0x06, 0x05, 0x04, 0x03, 0x02, 0x01],  # Obrnut
            [0x10, 0x20, 0x30, 0x40, 0x50, 0x60],
            [0x01, 0x01, 0x01, 0x01, 0x01, 0x01],
            
            # Čudni pattern-i
            [0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56],
            [0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54],
            [0x5A, 0x5A, 0x5A, 0x5A, 0x5A, 0x5A],  # 01011010
            [0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5],  # 10100101
        ]

    def force_detect_card(self):
        """Forsirana detekcija kartice čak i ako je problematična"""
        print("FORSIRANA DETEKCIJA KARTICE...")
        print("Držite karticu ČVRSTO na čitaču...")
        
        # Pokušaj sa različitim parametrima
        detection_methods = [
            ("Kratki timeout, više pokušaja", 0.1, 50),
            ("Srednji timeout", 0.5, 20), 
            ("Dugi timeout", 2.0, 10),
            ("Vrlo dugi timeout", 5.0, 5),
        ]
        
        for method_name, timeout, attempts in detection_methods:
            print(f"\nPokušavam: {method_name}")
            
            for attempt in range(attempts):
                try:
                    uid = self.pn532.read_passive_target(timeout=timeout)
                    if uid is not None:
                        print(f"✓ KARTICA PRONAĐENA sa metodom '{method_name}'!")
                        print(f"  UID: {uid.hex().upper()}")
                        print(f"  Dužina UID: {len(uid)} bajtova")
                        return uid
                except Exception as e:
                    pass
                
                if attempt % 10 == 0 and attempt > 0:
                    print(f"  {attempt}/{attempts}...")
        
        print("✗ Forsirana detekcija neuspešna")
        return None

    def sector_recovery_scan(self, uid):
        """Skeniraj sve sektore za bilo koji pristupačan blok"""
        print(f"\nSEKTOR RECOVERY SCAN za UID: {uid.hex().upper()}")
        print("="*50)
        
        accessible_blocks = {}
        
        for sector in range(16):  # MIFARE 1K ima 16 sektora
            print(f"\nSektor {sector}:")
            
            sector_accessible = False
            
            for block_offset in range(4):  # 4 bloka po sektoru
                block = sector * 4 + block_offset
                block_type = "trailer" if block_offset == 3 else "data"
                
                print(f"  Blok {block} ({block_type}):", end=" ")
                
                # Pokušaj sve ključeve
                for key_idx, key in enumerate(self.recovery_keys):
                    # Pokušaj Key A
                    if self.try_authenticate(uid, block, key, 0x60):
                        print(f"✓ Key A #{key_idx+1}")
                        accessible_blocks[block] = {
                            'key': key,
                            'key_type': 'A', 
                            'key_index': key_idx + 1
                        }
                        sector_accessible = True
                        break
                    
                    # Pokušaj Key B
                    if self.try_authenticate(uid, block, key, 0x61):
                        print(f"✓ Key B #{key_idx+1}")
                        accessible_blocks[block] = {
                            'key': key,
                            'key_type': 'B',
                            'key_index': key_idx + 1
                        }
                        sector_accessible = True
                        break
                
                if block not in accessible_blocks:
                    print("✗ ZAKLJUČAN")
            
            if sector_accessible:
                print(f"  → Sektor {sector}: DELIMIČNO PRISTUPAČAN")
            else:
                print(f"  → Sektor {sector}: POTPUNO ZAKLJUČAN")
        
        print(f"\n=== REZIME SCAN-a ===")
        print(f"Pristupačnih blokova: {len(accessible_blocks)}/64")
        
        if len(accessible_blocks) > 0:
            print("Pristupačni blokovi:")
            for block, info in accessible_blocks.items():
                sector = block // 4
                print(f"  Blok {block} (S{sector}): Key {info['key_type']} #{info['key_index']}")
        
        return accessible_blocks

    def try_authenticate(self, uid, block, key, key_type):
        """Pokušaj autentifikacije sa error handling"""
        try:
            return self.pn532.mifare_classic_authenticate_block(uid, block, key_type, key)
        except:
            return False

    def emergency_sector_reset(self, uid, accessible_blocks):
        """Pokušaj emergency reset pristupačnih sektora"""
        print(f"\nEMERGENCY SECTOR RESET")
        print("="*30)
        
        if len(accessible_blocks) == 0:
            print("✗ Nema pristupačnih blokova za reset!")
            return False
        
        reset_count = 0
        
        # Grupiši blokove po sektorima
        sectors = {}
        for block, info in accessible_blocks.items():
            sector = block // 4
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append((block, info))
        
        for sector, blocks in sectors.items():
            trailer_block = sector * 4 + 3
            
            print(f"\nSektor {sector}:")
            
            # Da li imamo pristup trailer bloku?
            trailer_info = None
            for block, info in blocks:
                if block == trailer_block:
                    trailer_info = info
                    break
            
            if trailer_info:
                print(f"  Imam pristup trailer bloku {trailer_block}")
                print(f"  Pokušavam factory reset...")
                
                try:
                    # Authenticuji se
                    key_type = 0x60 if trailer_info['key_type'] == 'A' else 0x61
                    
                    if self.try_authenticate(uid, trailer_block, trailer_info['key'], key_type):
                        # Kreiraj factory trailer
                        factory_trailer = (
                            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF] +  # Key A
                            [0xFF, 0x07, 0x80, 0x69] +             # Access bits  
                            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]   # Key B
                        )
                        
                        # Pokušaj pisanje
                        success = self.pn532.mifare_classic_write_block(trailer_block, factory_trailer)
                        if success:
                            print(f"  ✓ Sektor {sector} RESETOVAN!")
                            reset_count += 1
                            
                            # Obriši data blokove u sektoru
                            for data_block in range(sector * 4, sector * 4 + 3):
                                if data_block == 0:  # Preskoči manufacturer blok
                                    continue
                                    
                                try:
                                    if self.try_authenticate(uid, data_block, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF], 0x60):
                                        empty_data = [0x00] * 16
                                        self.pn532.mifare_classic_write_block(data_block, empty_data)
                                        print(f"    Blok {data_block} obrisan")
                                except:
                                    pass
                        else:
                            print(f"  ✗ Pisanje u trailer {trailer_block} neuspešno")
                    else:
                        print(f"  ✗ Re-autentifikacija neuspešna")
                        
                except Exception as e:
                    print(f"  ✗ Greška: {e}")
            else:
                print(f"  ✗ Nema pristupa trailer bloku {trailer_block}")
                
                # Pokušaj bar obrisati dostupne data blokove
                data_blocks_cleared = 0
                for block, info in blocks:
                    if block != trailer_block and block != 0:  # Nije trailer ni manufacturer
                        try:
                            key_type = 0x60 if info['key_type'] == 'A' else 0x61
                            if self.try_authenticate(uid, block, info['key'], key_type):
                                empty_data = [0x00] * 16
                                success = self.pn532.mifare_classic_write_block(block, empty_data)
                                if success:
                                    data_blocks_cleared += 1
                                    print(f"    Blok {block} obrisan")
                        except:
                            pass
                
                if data_blocks_cleared > 0:
                    print(f"  ⚠ Obrisano {data_blocks_cleared} data blokova (bez trailer reset-a)")
        
        print(f"\nRESET REZULTAT: {reset_count} sektora resetovano")
        return reset_count > 0

    def nuclear_option_brute_force(self, uid):
        """Nuclear option - brute force sa kratkim ključevima"""
        print(f"\n💥 NUCLEAR OPTION - BRUTE FORCE")
        print("="*40)
        print("⚠️  Ovo može potrajati VRLO DUGO!")
        print("Testiram sve kombinacije kratkih ključeva...")
        
        confirm = input("Nastaviti sa brute force? (yes/no): ")
        if confirm.lower() != 'yes':
            return {}
        
        found_keys = {}
        
        # Generiši kratke kombinacije (samo prvi 2-3 bajta različiti)
        patterns = []
        
        # Pattern 1: AABBCC...
        for a in range(0, 256, 16):  # Svaki 16. broj
            for b in range(0, 256, 16):
                patterns.append([a, b, a, b, a, b])
        
        # Pattern 2: ABCDEF
        for start in range(0, 240):
            patterns.append([start, start+1, start+2, start+3, start+4, start+5])
        
        # Pattern 3: Isti bajt
        for b in range(256):
            patterns.append([b] * 6)
        
        print(f"Testiram {len(patterns)} pattern-a na bloku 4...")
        
        for i, pattern in enumerate(patterns[:500]):  # Ograniči na 500 da ne traje večno
            if i % 50 == 0:
                print(f"Progress: {i}/{len(patterns[:500])}")
            
            # Test Key A
            if self.try_authenticate(uid, 4, pattern, 0x60):
                print(f"🎉 PRONAŠAO KEY A: {[hex(k) for k in pattern]}")
                found_keys[4] = {'key': pattern, 'type': 'A'}
                break
            
            # Test Key B  
            if self.try_authenticate(uid, 4, pattern, 0x61):
                print(f"🎉 PRONAŠAO KEY B: {[hex(k) for k in pattern]}")
                found_keys[4] = {'key': pattern, 'type': 'B'}
                break
        
        return found_keys

    def full_hardcore_recovery(self):
        """Kompletni hardcore recovery proces"""
        print("\n" + "🚨" * 20)
        print("HARDCORE MIFARE RECOVERY")
        print("🚨" * 20)
        
        # Korak 1: Forsirana detekcija
        uid = self.force_detect_card()
        if not uid:
            print("❌ Ne mogu da detektujem karticu - možda je potpuno oštećena")
            return False
        
        # Korak 2: Sector scan
        accessible_blocks = self.sector_recovery_scan(uid)
        
        # Korak 3: Emergency reset ako ima pristupačnih blokova
        if len(accessible_blocks) > 0:
            reset_success = self.emergency_sector_reset(uid, accessible_blocks)
            if reset_success:
                print("✅ EMERGENCY RESET DELIMIČNO USPEŠAN!")
                print("Testirajte karticu ponovo - možda je sada pristupačna")
                return True
        
        # Korak 4: Nuclear option ako ništa ne radi
        print("\n🔍 Pokušavam nuclear option...")
        brute_force_keys = self.nuclear_option_brute_force(uid)
        
        if len(brute_force_keys) > 0:
            print("🎉 BRUTE FORCE USPEŠAN! Pronađeni ključevi:")
            for block, info in brute_force_keys.items():
                print(f"  Blok {block}: Key {info['type']} = {[hex(k) for k in info['key']]}")
            return True
        
        # Korak 5: Finalna dijagnostika
        print("\n💀 KARTICA JE MOŽDA NEPOVRATNO OŠTEĆENA")
        print("Moguci uzroci:")
        print("- Corrupted access bits")
        print("- Hardware oštećenje")
        print("- Specijalna zaštićena kartica")
        print("- Kartica nije MIFARE Classic")
        
        return False

def main():
    try:
        recovery = HardcoreRecovery()
        
        print("🔥 HARDCORE MIFARE RECOVERY TOOL 🔥")
        print("Za kartice koje su 'pokvarene' ili imaju čudne ključeve")
        
        while True:
            print("\n" + "="*50)
            print("OPCIJE:")
            print("1. 🚨 Full Hardcore Recovery (sve tehnike)")
            print("2. 🔍 Forsirana detekcija kartice")  
            print("3. 🔓 Sector recovery scan")
            print("4. 💥 Nuclear brute force")
            print("5. ❌ Izlaz")
            
            choice = input("\nIzaberite opciju (1-5): ").strip()
            
            if choice == '1':
                print("\n⚠️  FULL HARDCORE RECOVERY")
                print("Ovo će pokušati sve dostupne tehnike!")
                confirm = input("Nastaviti? (yes/no): ")
                if confirm.lower() == 'yes':
                    recovery.full_hardcore_recovery()
                
            elif choice == '2':
                recovery.force_detect_card()
                
            elif choice == '3':
                uid = recovery.force_detect_card()
                if uid:
                    recovery.sector_recovery_scan(uid)
                
            elif choice == '4':
                uid = recovery.force_detect_card()  
                if uid:
                    recovery.nuclear_option_brute_force(uid)
                    
            elif choice == '5':
                break
                
            else:
                print("Nevalidna opcija!")
                
    except Exception as e:
        print(f"Fatalna greška: {e}")
        print("\nProvera:")
        print("- PN532 hardware povezan?")
        print("- I2C komunikacija radi?") 
        print("- Biblioteke instalirane?")

if __name__ == "__main__":
    main()
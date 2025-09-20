#!/usr/bin/env python3
"""
Low-level MIFARE Rescue
Za kartice sa corrupted access bits ili drugim problemima
"""

import board
import busio  
import time
from adafruit_pn532.i2c import PN532_I2C

class LowLevelRescue:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pn532 = PN532_I2C(self.i2c, debug=False)
        
        firmware = self.pn532.firmware_version
        if not firmware:
            raise Exception("PN532 ne odgovara!")
            
        self.pn532.SAM_configuration()

    def raw_card_detection(self):
        """Raw detekcija kartice sa maksimalnom tolerancijom"""
        print("RAW CARD DETECTION")
        print("Držite karticu i NE POMERAJTE...")
        
        detection_configs = [
            # (timeout, retries, pause_between)
            (0.05, 100, 0.01),  # Vrlo brzo, puno pokušaja
            (0.1, 50, 0.02),
            (0.2, 25, 0.05), 
            (0.5, 20, 0.1),
            (1.0, 10, 0.2),
            (2.0, 5, 0.5),
            (5.0, 3, 1.0)
        ]
        
        for timeout, retries, pause in detection_configs:
            print(f"\nKonfiguracija: timeout={timeout}s, pokušaji={retries}")
            
            consecutive_detections = 0
            last_uid = None
            
            for attempt in range(retries):
                try:
                    uid = self.pn532.read_passive_target(timeout=timeout)
                    
                    if uid:
                        if uid == last_uid:
                            consecutive_detections += 1
                        else:
                            consecutive_detections = 1
                            last_uid = uid
                        
                        print(f"  {attempt+1}/{retries}: UID={uid.hex().upper()} (x{consecutive_detections})")
                        
                        # Ako imamo stabilnu detekciju
                        if consecutive_detections >= 3:
                            print(f"✓ STABILNA DETEKCIJA: {uid.hex().upper()}")
                            return uid
                    else:
                        consecutive_detections = 0
                        print(f"  {attempt+1}/{retries}: Nema kartice")
                    
                except Exception as e:
                    print(f"  {attempt+1}/{retries}: Greška - {e}")
                
                time.sleep(pause)
        
        print("✗ Raw detekcija neuspešna")
        return None

    def access_bits_analyzer(self, trailer_data):
        """Analiza access bits iz sector trailer-a"""
        if len(trailer_data) < 16:
            return "Nevaljan trailer data"
        
        # Access bits su na pozicijama 6, 7, 8, 9
        access_bytes = trailer_data[6:10]
        
        print(f"Access bytes: {[hex(b) for b in access_bytes]}")
        
        # Dekodiranje access bits
        try:
            # MIFARE access bits format: C1 C2 C3 ~C1 ~C2 ~C3 (invertovani)
            c1 = access_bytes[1] & 0x0F
            c2 = (access_bytes[2] & 0xF0) >> 4  
            c3 = access_bytes[2] & 0x0F
            
            # Inverted bits za verifikaciju
            c1_inv = (access_bytes[0] & 0xF0) >> 4
            c2_inv = access_bytes[0] & 0x0F
            c3_inv = (access_bytes[1] & 0xF0) >> 4
            
            print(f"C1={c1:04b}, C2={c2:04b}, C3={c3:04b}")
            print(f"~C1={c1_inv:04b}, ~C2={c2_inv:04b}, ~C3={c3_inv:04b}")
            
            # Provera konzistentnosti
            if (c1 ^ c1_inv) != 0x0F or (c2 ^ c2_inv) != 0x0F or (c3 ^ c3_inv) != 0x0F:
                return "CORRUPTED ACCESS BITS!"
            else:
                return "Access bits su validni"
                
        except Exception as e:
            return f"Greška analize: {e}"

    def try_all_access_combinations(self, uid, block):
        """Pokušaj sve moguće access bit kombinacije"""
        print(f"Testiram sve access kombinacije za blok {block}...")
        
        # Generiši sve moguće MIFARE ključeve
        test_keys = []
        
        # Osnovni set
        basic_keys = [
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],
            [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]
        ]
        
        # Dodaj pattern-e
        for i in range(0, 256, 8):
            test_keys.append([i] * 6)
        
        for i in range(0, 250):
            test_keys.append([i, i+1, i+2, i+3, i+4, i+5])
        
        print(f"Testiram {len(test_keys)} ključeva...")
        
        found_keys = []
        
        for key_idx, key in enumerate(test_keys):
            if key_idx % 100 == 0:
                print(f"  Progress: {key_idx}/{len(test_keys)}")
            
            # Test Key A
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, block, 0x60, key):
                    print(f"  ✓ Key A pronađen: {[hex(k) for k in key]}")
                    found_keys.append(('A', key))
            except:
                pass
            
            # Test Key B
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, block, 0x61, key):
                    print(f"  ✓ Key B pronađen: {[hex(k) for k in key]}")
                    found_keys.append(('B', key))
            except:
                pass
            
            # Ako pronađemo ključ, ne moramo da testiramo sve
            if len(found_keys) >= 2:  # A i B ključ
                break
        
        return found_keys

    def fix_corrupted_access_bits(self, uid, sector):
        """Pokušaj popravke corrupted access bits"""
        trailer_block = sector * 4 + 3
        
        print(f"Pokušavam popravku access bits za sektor {sector}...")
        
        # Pokušaj čitanje trenutnog trailer-a
        current_trailer = None
        working_key = None
        key_type = None
        
        # Prvo pronađi bilo koji radni ključ za trailer
        test_keys = [
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],
        ]
        
        for key in test_keys:
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, trailer_block, 0x60, key):
                    working_key = key
                    key_type = 0x60
                    current_trailer = self.pn532.mifare_classic_read_block(trailer_block)
                    break
            except:
                pass
            
            try:
                if self.pn532.mifare_classic_authenticate_block(uid, trailer_block, 0x61, key):
                    working_key = key
                    key_type = 0x61
                    current_trailer = self.pn532.mifare_classic_read_block(trailer_block)
                    break
            except:
                pass
        
        if working_key is None:
            print(f"✗ Ne mogu da pristupim trailer bloku {trailer_block}")
            return False
        
        print(f"✓ Pristup trailer bloku sa ključem: {[hex(k) for k in working_key]}")
        
        if current_trailer:
            print(f"Trenutni trailer: {[hex(b) for b in current_trailer]}")
            access_status = self.access_bits_analyzer(current_trailer)
            print(f"Access bits status: {access_status}")
        
        # Kreiraj novi trailer sa factory access bits
        print("Kreiram factory trailer...")
        factory_trailer = (
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF] +  # Key A (factory default)
            [0xFF, 0x07, 0x80, 0x69] +             # Factory access bits
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]   # Key B (factory default)
        )
        
        try:
            success = self.pn532.mifare_classic_write_block(trailer_block, factory_trailer)
            if success:
                print(f"✓ Access bits popravljen za sektor {sector}!")
                return True
            else:
                print(f"✗ Pisanje factory trailer-a neuspešno")
                return False
        except Exception as e:
            print(f"✗ Greška pisanja: {e}")
            return False

    def emergency_format(self, uid):
        """Emergency formatiranje cele kartice"""
        print("\n💥 EMERGENCY FORMAT")
        print("="*30)
        print("⚠️  OVO ĆE OBRISATI SVE PODATKE NA KARTICI!")
        
        confirm = input("Unesite 'FORMAT' za potvrdu: ")
        if confirm != 'FORMAT':
            print("Format otkazan")
            return False
        
        formatted_sectors = 0
        
        for sector in range(16):
            print(f"\nFormatiranje sektor {sector}...")
            
            # Pokušaj popravku access bits
            if self.fix_corrupted_access_bits(uid, sector):
                print(f"  ✓ Access bits popravljen")
                
                # Obriši data blokove
                for block_offset in range(3):  # Blokovi 0,1,2 u sektoru
                    block = sector * 4 + block_offset
                    
                    if block == 0:  # Preskoči manufacturer blok
                        continue
                    
                    try:
                        # Koristi factory ključ posle popravke
                        factory_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                        if self.pn532.mifare_classic_authenticate_block(uid, block, 0x60, factory_key):
                            empty_data = [0x00] * 16
                            success = self.pn532.mifare_classic_write_block(block, empty_data)
                            if success:
                                print(f"    Blok {block} obrisan")
                    except:
                        print(f"    Blok {block} - brisanje neuspešno")
                
                formatted_sectors += 1
            else:
                print(f"  ✗ Sektor {sector} se ne može formatirati")
        
        print(f"\nEMERGENCY FORMAT ZAVRŠEN")
        print(f"Formatirano sektora: {formatted_sectors}/16")
        
        if formatted_sectors > 0:
            print("✅ Kartica je delimično ili potpuno formatirana!")
            print("Testirajte je ponovo - trebala bi raditi sa factory ključevima")
            return True
        else:
            print("❌ Format neuspešan - kartica je možda nepovratno oštećena")
            return False

    def diagnostic_read_attempt(self, uid):
        """Dijagnostika - pokušaj čitanja što god je moguće"""
        print(f"\nDIJAGNOSTICKO ČITANJE")
        print("="*30)
        
        readable_data = {}
        
        for sector in range(16):
            print(f"\nSektor {sector}:")
            
            sector_data = {}
            
            for block_offset in range(4):
                block = sector * 4 + block_offset
                block_type = "manufacturer" if block == 0 else ("trailer" if block_offset == 3 else "data")
                
                print(f"  Blok {block} ({block_type}):", end=" ")
                
                # Pokušaj sa više ključeva
                found_data = False
                
                test_keys = [
                    [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
                    [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                    [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],
                    [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7],
                ]
                
                for key in test_keys:
                    # Key A
                    try:
                        if self.pn532.mifare_classic_authenticate_block(uid, block, 0x60, key):
                            data = self.pn532.mifare_classic_read_block(block)
                            print(f"✓ Key A")
                            sector_data[block] = {
                                'data': data,
                                'key': key,
                                'key_type': 'A'
                            }
                            found_data = True
                            
                            # Analiza podataka
                            if block_offset == 3:  # Trailer
                                access_status = self.access_bits_analyzer(data)
                                print(f"\n      Access: {access_status}")
                            else:
                                # Prikaži podatke
                                text_data = self.format_as_text(data)
                                if text_data.strip():
                                    print(f"\n      Text: '{text_data}'")
                                hex_preview = ' '.join([f'{b:02X}' for b in data[:8]]) + "..."
                                print(f"\n      Hex: {hex_preview}")
                            break
                    except:
                        pass
                    
                    # Key B
                    try:
                        if self.pn532.mifare_classic_authenticate_block(uid, block, 0x61, key):
                            data = self.pn532.mifare_classic_read_block(block)
                            print(f"✓ Key B")
                            sector_data[block] = {
                                'data': data,
                                'key': key,
                                'key_type': 'B'
                            }
                            found_data = True
                            break
                    except:
                        pass
                
                if not found_data:
                    print("✗")
            
            if sector_data:
                readable_data[sector] = sector_data
        
        # Sačuvaj podatke u fajl
        self.save_diagnostic_data(uid, readable_data)
        
        return readable_data

    def format_as_text(self, data):
        """Formatiranje binarnih podataka kao tekst"""
        text = ""
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                text += chr(byte)
            else:
                text += "."
        return text

    def save_diagnostic_data(self, uid, readable_data):
        """Sačuvaj dijagnostičke podatke u fajl"""
        filename = f"mifare_diagnostic_{uid.hex()}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(f"MIFARE Diagnostic Report\n")
                f.write(f"UID: {uid.hex().upper()}\n")
                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n\n")
                
                for sector, sector_data in readable_data.items():
                    f.write(f"SECTOR {sector}:\n")
                    
                    for block, block_info in sector_data.items():
                        data = block_info['data']
                        key = block_info['key']
                        key_type = block_info['key_type']
                        
                        f.write(f"  Block {block}: Key {key_type} = {[hex(k) for k in key]}\n")
                        f.write(f"    Hex: {' '.join([f'{b:02X}' for b in data])}\n")
                        
                        text = self.format_as_text(data)
                        if text.strip():
                            f.write(f"    Text: '{text}'\n")
                        
                        f.write("\n")
                    
                    f.write("\n")
            
            print(f"✓ Dijagnostika sačuvana u: {filename}")
            
        except Exception as e:
            print(f"✗ Greška snimanja: {e}")

    def full_rescue_procedure(self):
        """Kompletna rescue procedura"""
        print("\n" + "🆘" * 15)
        print("FULL MIFARE RESCUE PROCEDURE")
        print("🆘" * 15)
        
        # Korak 1: Raw detekcija
        print("\n1. RAW CARD DETECTION")
        uid = self.raw_card_detection()
        if not uid:
            print("❌ Ne mogu da detektujem karticu")
            return False
        
        # Korak 2: Dijagnostičko čitanje
        print("\n2. DIAGNOSTIC READ")
        readable_data = self.diagnostic_read_attempt(uid)
        
        readable_blocks = sum(len(sector_data) for sector_data in readable_data.values())
        print(f"\nPročitano {readable_blocks}/64 blokova")
        
        if readable_blocks == 0:
            print("❌ Nijedan blok nije čitljiv - kartica možda nije MIFARE Classic")
            return False
        
        # Korak 3: Emergency format ako je potrebno
        if readable_blocks < 32:  # Manje od pola kartice
            print("\n3. EMERGENCY FORMAT POTREBAN")
            print(f"Samo {readable_blocks}/64 blokova je čitljivo")
            
            format_choice = input("Pokušati emergency format? (yes/no): ")
            if format_choice.lower() == 'yes':
                format_success = self.emergency_format(uid)
                if format_success:
                    print("✅ RESCUE USPEŠAN!")
                    print("Kartica je formatirana i trebala bi raditi")
                    return True
        else:
            print(f"\n3. FORMAT NIJE POTREBAN")
            print(f"{readable_blocks}/64 blokova je pristupačno")
            print("✅ KARTICA JE U RELATIVNO DOBROM STANJU")
            
            # Možda samo popravka access bits
            fix_choice = input("Pokušati popravku access bits? (yes/no): ")
            if fix_choice.lower() == 'yes':
                fixed_sectors = 0
                for sector in range(16):
                    if self.fix_corrupted_access_bits(uid, sector):
                        fixed_sectors += 1
                
                print(f"Popravljen {fixed_sectors} sektora")
                return fixed_sectors > 0
        
        return False

def main():
    try:
        rescue = LowLevelRescue()
        
        while True:
            print("\n" + "🆘" + "="*48 + "🆘")
            print("LOW-LEVEL MIFARE RESCUE")
            print("🆘" + "="*48 + "🆘")
            print("1. 🆘 Full Rescue Procedure")
            print("2. 🔍 Raw Card Detection")
            print("3. 📊 Diagnostic Read")
            print("4. 🔧 Fix Corrupted Access Bits")
            print("5. 💥 Emergency Format")
            print("6. ❌ Izlaz")
            
            choice = input("\nIzaberite opciju (1-6): ").strip()
            
            if choice == '1':
                rescue.full_rescue_procedure()
                
            elif choice == '2':
                rescue.raw_card_detection()
                
            elif choice == '3':
                uid = rescue.raw_card_detection()
                if uid:
                    rescue.diagnostic_read_attempt(uid)
                    
            elif choice == '4':
                uid = rescue.raw_card_detection()
                if uid:
                    sector = int(input("Unesite broj sektora (0-15): "))
                    rescue.fix_corrupted_access_bits(uid, sector)
                    
            elif choice == '5':
                uid = rescue.raw_card_detection()
                if uid:
                    rescue.emergency_format(uid)
                    
            elif choice == '6':
                break
                
            else:
                print("Nevalidna opcija!")
                
    except Exception as e:
        print(f"Fatalna greška: {e}")

if __name__ == "__main__":
    main()
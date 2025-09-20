#!/usr/bin/env python3
"""
PN532 Dijagnostika i Debug kod
Testira osnovnu komunikaciju i konfiguraciju
"""

import board
import busio
import time
import sys

def test_i2c_connection():
    """Test osnovne I2C komunikacije"""
    print("=== TEST I2C KOMUNIKACIJE ===")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Skeniranje I2C uređaja
        print("Skeniram I2C bus...")
        while not i2c.try_lock():
            pass
        
        try:
            addresses = i2c.scan()
            print(f"Pronađeni I2C uređaji: {[hex(addr) for addr in addresses]}")
            
            # PN532 treba da bude na 0x24 (36 decimalno)
            if 0x24 in addresses:
                print("✓ PN532 pronađen na adresi 0x24")
                return True
            else:
                print("✗ PN532 NIJE pronađen na adresi 0x24")
                return False
        finally:
            i2c.unlock()
            
    except Exception as e:
        print(f"✗ Greška I2C komunikacije: {e}")
        return False

def test_pn532_basic():
    """Test osnovne PN532 funkcionalnosti"""
    print("\n=== TEST PN532 OSNOVNE FUNKCIONALNOSTI ===")
    
    try:
        from adafruit_pn532.i2c import PN532_I2C
        
        i2c = busio.I2C(board.SCL, board.SDA)
        print("✓ I2C objekat kreiran")
        
        # Kreiranje PN532 objekta sa debug=True
        pn532 = PN532_I2C(i2c, debug=True)
        print("✓ PN532 objekat kreiran")
        
        # Test firmware verzije
        print("Testiram firmware verziju...")
        try:
            firmware = pn532.firmware_version
            if firmware:
                ic, ver, rev, support = firmware
                print(f"✓ Firmware: IC=0x{ic:02X}, Ver={ver}, Rev={rev}, Support=0x{support:02X}")
                return pn532
            else:
                print("✗ Firmware verzija nedostupna")
                return None
        except Exception as e:
            print(f"✗ Greška čitanja firmware: {e}")
            return None
            
    except ImportError:
        print("✗ adafruit_pn532 biblioteka nije instalirana!")
        print("Instaliraj sa: pip install adafruit-circuitpython-pn532")
        return None
    except Exception as e:
        print(f"✗ Greška inicijalizacije PN532: {e}")
        return None

def test_sam_configuration(pn532):
    """Test SAM konfiguracije"""
    print("\n=== TEST SAM KONFIGURACIJE ===")
    
    try:
        result = pn532.SAM_configuration()
        print(f"✓ SAM konfiguracija uspešna: {result}")
        return True
    except Exception as e:
        print(f"✗ SAM konfiguracija neuspešna: {e}")
        return False

def test_card_detection_detailed(pn532):
    """Detaljno testiranje detekcije kartica"""
    print("\n=== DETALJNO TESTIRANJE DETEKCIJE KARTICA ===")
    
    print("Približite karticu čitaču...")
    
    for attempt in range(10):
        print(f"Pokušaj {attempt + 1}/10...")
        
        try:
            # Pokušaj sa različitim timeout vrednostima
            for timeout in [0.1, 0.5, 1.0, 2.0]:
                print(f"  Testiram sa timeout={timeout}s...")
                
                uid = pn532.read_passive_target(timeout=timeout)
                if uid is not None:
                    print(f"✓ KARTICA PRONAĐENA!")
                    print(f"  UID: {[hex(i) for i in uid]}")
                    print(f"  UID dužina: {len(uid)} bajtova")
                    print(f"  UID kao string: {uid.hex()}")
                    return uid
                else:
                    print(f"  Nema kartice (timeout {timeout}s)")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ Greška u pokušaju {attempt + 1}: {e}")
            time.sleep(0.5)
    
    print("✗ Kartica nije pronađena posle 10 pokušaja")
    return None

def test_different_card_types(pn532):
    """Test različitih tipova kartica"""
    print("\n=== TEST RAZLIČITIH TIPOVA KARTICA ===")
    
    print("Približite karticu...")
    
    # Test MIFARE
    print("Testiram MIFARE kartice...")
    try:
        uid = pn532.read_passive_target(timeout=2.0)
        if uid:
            print(f"✓ Kartica detektovana: {[hex(i) for i in uid]}")
            
            # Pokušaj MIFARE autentifikacije
            print("Testiram MIFARE autentifikaciju...")
            try:
                # Test sa default ključem
                default_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                auth_result = pn532.mifare_classic_authenticate_block(uid, 4, 0x60, default_key)
                if auth_result:
                    print("✓ MIFARE Classic autentifikacija uspešna!")
                    
                    # Pokušaj čitanje bloka
                    try:
                        data = pn532.mifare_classic_read_block(4)
                        print(f"✓ Blok 4 pročitan: {[hex(b) for b in data]}")
                    except Exception as e:
                        print(f"✗ Čitanje bloka neuspešno: {e}")
                else:
                    print("✗ MIFARE autentifikacija neuspešna")
            except Exception as e:
                print(f"✗ MIFARE test greška: {e}")
        else:
            print("✗ Kartica nije detektovana")
    except Exception as e:
        print(f"✗ Greška testiranja kartica: {e}")

def test_low_level_communication(pn532):
    """Test komunikacije na niskom nivou"""
    print("\n=== TEST KOMUNIKACIJE NA NISKOM NIVOU ===")
    
    try:
        # Test osnovnih PN532 komandi
        print("Testiram osnovne komande...")
        
        # GetFirmwareVersion komanda direktno
        print("Šaljem GetFirmwareVersion komandu...")
        # Ovo je interno, ali možemo testirati kroz firmware_version
        firmware = pn532.firmware_version
        if firmware:
            print("✓ Niska komunikacija radi")
        else:
            print("✗ Niska komunikacija ne radi")
            
    except Exception as e:
        print(f"✗ Greška niske komunikacije: {e}")

def comprehensive_diagnostic():
    """Sveobuhvatna dijagnostika"""
    print("PN532 SVEOBUHVATNA DIJAGNOSTIKA")
    print("=" * 50)
    
    # Test 1: I2C komunikacija
    if not test_i2c_connection():
        print("\n❌ I2C komunikacija ne radi - proverite konekcije!")
        return False
    
    # Test 2: PN532 inicijalizacija  
    pn532 = test_pn532_basic()
    if not pn532:
        print("\n❌ PN532 inicijalizacija neuspešna!")
        return False
    
    # Test 3: SAM konfiguracija
    if not test_sam_configuration(pn532):
        print("\n❌ SAM konfiguracija neuspešna!")
        return False
    
    # Test 4: Komunikacija na niskom nivou
    test_low_level_communication(pn532)
    
    # Test 5: Detekcija kartica
    print("\n🔍 Testiram detekciju kartica...")
    uid = test_card_detection_detailed(pn532)
    
    if uid:
        # Test 6: Tipovi kartica
        test_different_card_types(pn532)
        print("\n✅ DIJAGNOSTIKA USPEŠNA!")
        return True
    else:
        print("\n⚠️  PN532 radi, ali ne detektuje kartice")
        print("\nMoguci uzroci:")
        print("- Kartica nije dovoljno blizu")
        print("- Kartica nije MIFARE Classic")
        print("- RF antena nije dobro povezana")
        print("- Kartica je oštećena")
        return False

def interactive_card_test():
    """Interaktivni test kartica"""
    print("\n=== INTERAKTIVNI TEST KARTICA ===")
    
    try:
        from adafruit_pn532.i2c import PN532_I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, debug=True)
        pn532.SAM_configuration()
        
        print("Držite karticu na čitaču i pritisnite Enter...")
        input()
        
        print("Pokušavam kontinuiranu detekciju...")
        for i in range(20):
            print(f"Pokušaj {i+1}: ", end="")
            uid = pn532.read_passive_target(timeout=1.0)
            if uid:
                print(f"KARTICA! UID: {[hex(x) for x in uid]}")
                break
            else:
                print("nema kartice")
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Greška: {e}")

def main():
    while True:
        print("\n" + "=" * 50)
        print("PN532 DIJAGNOSTIČKI ALAT")
        print("=" * 50)
        print("1. Potpuna dijagnostika")
        print("2. Test I2C komunikacije")
        print("3. Test PN532 inicijalizacije")
        print("4. Interaktivni test kartica")
        print("5. Kontinuirana detekcija")
        print("6. Izlaz")
        
        choice = input("\nIzaberite opciju (1-6): ").strip()
        
        if choice == '1':
            comprehensive_diagnostic()
            
        elif choice == '2':
            test_i2c_connection()
            
        elif choice == '3':
            test_pn532_basic()
            
        elif choice == '4':
            interactive_card_test()
            
        elif choice == '5':
            try:
                from adafruit_pn532.i2c import PN532_I2C
                i2c = busio.I2C(board.SCL, board.SDA)
                pn532 = PN532_I2C(i2c, debug=True)
                pn532.SAM_configuration()
                
                print("Kontinuirana detekcija... (Ctrl+C za prekid)")
                counter = 0
                while True:
                    counter += 1
                    print(f"[{counter}] ", end="", flush=True)
                    
                    uid = pn532.read_passive_target(timeout=0.5)
                    if uid:
                        print(f"KARTICA: {[hex(x) for x in uid]}")
                    else:
                        print(".", end="", flush=True)
                    
                    if counter % 20 == 0:
                        print()  # Nova linija svakih 20 pokušaja
                        
            except KeyboardInterrupt:
                print("\nPrekinuto")
            except Exception as e:
                print(f"Greška: {e}")
                
        elif choice == '6':
            break
            
        else:
            print("Nevalidna opcija!")

if __name__ == "__main__":
    main()
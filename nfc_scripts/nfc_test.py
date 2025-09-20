#!/usr/bin/env python3
"""
Najjednostavniji mogući test PN532
"""

import board
import busio
import time

def simple_test():
    print("=== JEDNOSTAVAN PN532 TEST ===")
    
    # 1. Test I2C
    print("1. Testiram I2C...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        print("   ✓ I2C kreiran")
        
        # Scan I2C
        while not i2c.try_lock():
            time.sleep(0.1)
        
        try:
            addresses = i2c.scan()
            print(f"   I2C uređaji: {[hex(addr) for addr in addresses]}")
        finally:
            i2c.unlock()
            
    except Exception as e:
        print(f"   ✗ I2C greška: {e}")
        return
    
    # 2. Test PN532 import
    print("2. Testiram PN532 import...")
    try:
        from adafruit_pn532.i2c import PN532_I2C
        print("   ✓ Import uspešan")
    except Exception as e:
        print(f"   ✗ Import greška: {e}")
        return
    
    # 3. Test PN532 kreiranje
    print("3. Kreiram PN532 objekat...")
    try:
        pn532 = PN532_I2C(i2c, debug=False)
        print("   ✓ PN532 objekat kreiran")
    except Exception as e:
        print(f"   ✗ PN532 kreiranje greška: {e}")
        return
    
    # 4. Test firmware
    print("4. Testiram firmware...")
    try:
        firmware_info = pn532.firmware_version
        if firmware_info:
            ic, ver, rev, support = firmware_info
            print(f"   ✓ Firmware: v{ver}.{rev}")
        else:
            print("   ✗ Firmware info nedostupna")
            return
    except Exception as e:
        print(f"   ✗ Firmware greška: {e}")
        return
    
    # 5. Test SAM config
    print("5. Konfigurishem SAM...")
    try:
        pn532.SAM_configuration()
        print("   ✓ SAM konfigurisan")
    except Exception as e:
        print(f"   ✗ SAM greška: {e}")
        return
    
    # 6. Test detekcije
    print("6. Testiram detekciju kartica...")
    print("   Približite karticu u narednih 10 sekundi...")
    
    for i in range(10):
        print(f"   Pokušaj {i+1}/10...", end="")
        try:
            uid = pn532.read_passive_target(timeout=1.0)
            if uid:
                print(f" PRONAŠAO KARTICU!")
                print(f"   UID: {' '.join([f'{b:02X}' for b in uid])}")
                print(f"   UID hex: {uid.hex().upper()}")
                print(f"   UID dužina: {len(uid)} bajtova")
                return uid
            else:
                print(" nema kartice")
        except Exception as e:
            print(f" greška: {e}")
        
        time.sleep(1)
    
    print("   ✗ Kartica nije pronađena")
    return None

def continuous_scan():
    """Kontinuirani sken kartica"""
    print("=== KONTINUIRANI SKEN ===")
    
    try:
        from adafruit_pn532.i2c import PN532_I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, debug=False)
        
        firmware = pn532.firmware_version
        if not firmware:
            print("PN532 ne odgovara!")
            return
            
        pn532.SAM_configuration()
        print("PN532 spreman. Približite karticu... (Ctrl+C za izlaz)")
        
        last_uid = None
        scan_count = 0
        
        while True:
            scan_count += 1
            uid = pn532.read_passive_target(timeout=0.2)
            
            if uid and uid != last_uid:
                print(f"\n[{scan_count}] NOVA KARTICA: {uid.hex().upper()}")
                last_uid = uid
                
                # Kratka pauza da ne spammuje
                time.sleep(1)
                
            elif not uid and last_uid:
                print(f"[{scan_count}] Kartica uklonjena")
                last_uid = None
            
            # Prikaži progress svake sekunde
            if scan_count % 5 == 0:
                print(".", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\nSken prekinut")
    except Exception as e:
        print(f"Greška: {e}")

def debug_scan():
    """Detaljni debug sken"""
    print("=== DEBUG SKEN ===")
    
    try:
        from adafruit_pn532.i2c import PN532_I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Debug mode ON
        pn532 = PN532_I2C(i2c, debug=True)
        
        print("Debug mode omogućen - videćete sve I2C komunikacije")
        print("Približite karticu...")
        
        pn532.SAM_configuration()
        
        for i in range(5):
            print(f"\n--- Pokušaj {i+1} ---")
            uid = pn532.read_passive_target(timeout=2.0)
            if uid:
                print(f"KARTICA DETEKTOVANA: {uid.hex()}")
                break
            else:
                print("Nema kartice")
                
    except Exception as e:
        print(f"Greška: {e}")

if __name__ == "__main__":
    while True:
        print("\n" + "="*40)
        print("JEDNOSTAVAN PN532 TEST")
        print("="*40)
        print("1. Osnovni test")
        print("2. Kontinuirani sken")
        print("3. Debug sken")
        print("4. Izlaz")
        
        choice = input("\nOpcija: ").strip()
        
        if choice == '1':
            simple_test()
        elif choice == '2':
            continuous_scan()
        elif choice == '3':
            debug_scan()
        elif choice == '4':
            break
        else:
            print("Nevalidna opcija!")
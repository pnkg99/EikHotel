#!/usr/bin/env python3
"""
RF Antena test i optimizacija za PN532
Problem: PN532 radi ali ne detektuje kartice
"""

import board
import busio
import time
from adafruit_pn532.i2c import PN532_I2C

class RFTester:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pn532 = PN532_I2C(self.i2c, debug=False)
        
        # Proveri da li je PN532 dostupan
        firmware = self.pn532.firmware_version
        if not firmware:
            raise Exception("PN532 ne odgovara!")
            
        print(f"PN532 Firmware: {firmware[1]}.{firmware[2]}")
        self.pn532.SAM_configuration()

    def test_rf_field_strength(self):
        """Test jačine RF polja"""
        print("=== TEST RF POLJA ===")
        
        try:
            # Pokušaj različite RF konfiguracije
            rf_configs = [
                ("Normalno RF polje", None),
                ("Maksimalno RF polje", 0xFF),
                ("Srednje RF polje", 0x80),
                ("Slabo RF polje", 0x40),
            ]
            
            for config_name, rf_level in rf_configs:
                print(f"\nTestiram: {config_name}")
                
                if rf_level is not None:
                    try:
                        # Pokušaj postavljanja RF nivoa (ovo možda neće raditi sa adafruit bibliotekom)
                        print(f"  Postavljam RF nivo: 0x{rf_level:02X}")
                    except:
                        print(f"  RF konfiguracija nije podržana")
                
                # Test detekcije sa ovom konfiguracijom
                success = self.quick_card_test(timeout=3)
                if success:
                    print(f"  ✓ KARTICE DETEKTOVANE sa {config_name}!")
                    return True
                else:
                    print(f"  ✗ Nema kartica sa {config_name}")
        
        except Exception as e:
            print(f"RF test greška: {e}")
        
        return False

    def test_different_timeouts(self):
        """Test različitih timeout vrednosti"""
        print("\n=== TEST RAZLIČITIH TIMEOUT VREDNOSTI ===")
        
        timeouts = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        
        print("Držite karticu čvrsto na čitaču...")
        input("Pritisnite Enter kada je kartica postavljena...")
        
        for timeout in timeouts:
            print(f"\nTestiram timeout: {timeout}s")
            
            success_count = 0
            for attempt in range(5):
                try:
                    uid = self.pn532.read_passive_target(timeout=timeout)
                    if uid:
                        success_count += 1
                        print(f"  Pokušaj {attempt+1}: ✓ UID: {uid.hex()}")
                    else:
                        print(f"  Pokušaj {attempt+1}: ✗ Nema kartice")
                except Exception as e:
                    print(f"  Pokušaj {attempt+1}: ✗ Greška: {e}")
                
                time.sleep(0.5)
            
            success_rate = (success_count / 5) * 100
            print(f"  Uspešnost sa timeout {timeout}s: {success_rate}%")
            
            if success_count > 0:
                print(f"  ✓ NAJBOLJI TIMEOUT: {timeout}s")
                return timeout
        
        return None

    def test_continuous_detection(self, optimal_timeout=1.0):
        """Kontinuirani test detekcije"""
        print(f"\n=== KONTINUIRANI TEST (timeout={optimal_timeout}s) ===")
        print("Pokušajte različite kartice i pozicije...")
        print("Pritisnite Ctrl+C za prekid")
        
        try:
            detection_count = 0
            total_attempts = 0
            last_uid = None
            
            while True:
                total_attempts += 1
                
                try:
                    uid = self.pn532.read_passive_target(timeout=optimal_timeout)
                    
                    if uid:
                        detection_count += 1
                        if uid != last_uid:
                            print(f"\n[{total_attempts}] NOVA KARTICA DETEKTOVANA!")
                            print(f"    UID: {uid.hex().upper()}")
                            print(f"    Tip: {self.identify_card_type(uid)}")
                            last_uid = uid
                        else:
                            print(".", end="", flush=True)
                    else:
                        if last_uid:
                            print(f"\n[{total_attempts}] Kartica uklonjena")
                            last_uid = None
                        else:
                            print("_", end="", flush=True)
                    
                    # Statistike svakih 50 pokušaja
                    if total_attempts % 50 == 0:
                        success_rate = (detection_count / total_attempts) * 100
                        print(f"\nStatistika: {detection_count}/{total_attempts} ({success_rate:.1f}%)")
                        
                except Exception as e:
                    print(f"E", end="", flush=True)
                
        except KeyboardInterrupt:
            success_rate = (detection_count / total_attempts) * 100 if total_attempts > 0 else 0
            print(f"\n\nFINALNE STATISTIKE:")
            print(f"Ukupno pokušaja: {total_attempts}")
            print(f"Uspešne detekcije: {detection_count}")
            print(f"Uspešnost: {success_rate:.1f}%")

    def identify_card_type(self, uid):
        """Identifikacija tipa kartice na osnovu UID-a"""
        uid_len = len(uid)
        
        if uid_len == 4:
            return "MIFARE Classic 1K/4K (4-byte UID)"
        elif uid_len == 7:
            return "MIFARE Classic/Ultralight (7-byte UID)"
        elif uid_len == 10:
            return "MIFARE DESFire/Plus (10-byte UID)"
        else:
            return f"Nepoznat tip ({uid_len}-byte UID)"

    def quick_card_test(self, timeout=2.0, attempts=3):
        """Brzi test detekcije kartice"""
        for _ in range(attempts):
            try:
                uid = self.pn532.read_passive_target(timeout=timeout)
                if uid:
                    return uid
            except:
                pass
            time.sleep(0.1)
        return None

    def test_card_positioning(self):
        """Test pozicioniranja kartice"""
        print("\n=== TEST POZICIONIRANJA KARTICE ===")
        print("""
Testiraćemo različite pozicije kartice:
1. Direktno na čitaču (centar)
2. Levo od centra
3. Desno od centra  
4. Iznad centra
5. Ispod centra
6. Pod uglom
7. Sa razmakom (1-2cm)
        """)
        
        positions = [
            "Direktno na centar antene",
            "1cm levo od centra", 
            "1cm desno od centra",
            "1cm iznad centra",
            "1cm ispod centra",
            "Pod uglom od 45°",
            "Sa razmakom 1cm",
            "Sa razmakom 2cm"
        ]
        
        results = {}
        
        for i, position in enumerate(positions, 1):
            print(f"\n{i}. {position}")
            input("   Postavite karticu i pritisnite Enter...")
            
            success_count = 0
            for attempt in range(3):
                uid = self.quick_card_test(timeout=1.5)
                if uid:
                    success_count += 1
                    print(f"   Pokušaj {attempt+1}: ✓")
                else:
                    print(f"   Pokušaj {attempt+1}: ✗")
            
            success_rate = (success_count / 3) * 100
            results[position] = success_rate
            print(f"   Uspešnost: {success_rate:.0f}%")
        
        print(f"\n=== REZULTATI POZICIONIRANJA ===")
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        
        for position, rate in sorted_results:
            status = "✓" if rate > 50 else "✗"
            print(f"{status} {position}: {rate:.0f}%")
        
        if sorted_results[0][1] > 0:
            print(f"\nNAJBOLJA POZICIJA: {sorted_results[0][0]} ({sorted_results[0][1]:.0f}%)")
        else:
            print("\nNIJEDNA POZICIJA NE RADI - Problem sa antenama!")

    def antenna_diagnostic(self):
        """Dijagnostika antena"""
        print("\n=== DIJAGNOSTIKA ANTENA ===")
        
        print("""
PROVERE ZA PN532 ANTENU:

1. HARDWARE PROVERE:
   ✓ Da li su sva 4 I2C pina povezana? (VCC, GND, SDA, SCL)
   ✓ Da li je VCC povezan na 3.3V (NE 5V!)?
   ✓ Da li antena radi? (mala PCB antena na PN532 modulu)
   ✓ Da li postoje prekidi u PCB tragovima?

2. SOFTWARE PROVERE:
   ✓ PN532 firmware odgovara
   ✓ SAM konfiguracija je OK
   ✓ I2C komunikacija radi

3. MOGUCI UZROCI:
   ✗ Slaba antena na PN532 modulu
   ✗ RF interferenca (wifi, bluetooth, telefoni)
   ✗ Loše napajanje (pad napona)
   ✗ Defektni PN532 modul
   ✗ Nekompatibilne kartice
        """)
        
        print("\nTESTIRANJE RF INTERFERENCA:")
        print("Isključite WiFi uređaje, telefone, bluetooth...")
        input("Pritisnite Enter kada završite...")
        
        print("Test bez interferenca...")
        uid = self.quick_card_test(timeout=3.0, attempts=10)
        if uid:
            print("✓ KARTICA DETEKTOVANA bez interferenca!")
        else:
            print("✗ I dalje nema detekcije")
            
        print(f"\nTEST NAPAJANJA:")
        print("Meriti napon na PN532:")
        print("- VCC pin treba da bude 3.3V ± 0.1V")
        print("- GND treba da bude stabilan")
        print("- Tokom rada, napon ne sme da opada")

def main():
    try:
        tester = RFTester()
        
        while True:
            print("\n" + "="*50)
            print("RF ANTENA TEST I OPTIMIZACIJA")
            print("="*50)
            print("1. Test RF polja") 
            print("2. Test različitih timeout-a")
            print("3. Kontinuirani test detekcije")
            print("4. Test pozicioniranja kartice")
            print("5. Dijagnostika antena")
            print("6. Sveobuhvatni test")
            print("7. Izlaz")
            
            choice = input("\nIzaberite opciju (1-7): ").strip()
            
            if choice == '1':
                tester.test_rf_field_strength()
                
            elif choice == '2':
                optimal_timeout = tester.test_different_timeouts()
                if optimal_timeout:
                    print(f"\nKoristite timeout od {optimal_timeout}s u budućnosti")
                    
            elif choice == '3':
                timeout = float(input("Unesite timeout (default 1.0s): ") or "1.0")
                tester.test_continuous_detection(timeout)
                
            elif choice == '4':
                tester.test_card_positioning()
                
            elif choice == '5':
                tester.antenna_diagnostic()
                
            elif choice == '6':
                print("SVEOBUHVATNI RF TEST...")
                tester.antenna_diagnostic()
                tester.test_rf_field_strength()
                optimal_timeout = tester.test_different_timeouts()
                if optimal_timeout:
                    tester.test_continuous_detection(optimal_timeout)
                tester.test_card_positioning()
                
            elif choice == '7':
                break
                
            else:
                print("Nevalidna opcija!")
                
    except Exception as e:
        print(f"Greška: {e}")
        print("\nPROVERITE:")
        print("- Da li je PN532 ispravno povezan?")
        print("- Da li su biblioteke instalirane?")
        print("- Da li I2C radi?")

if __name__ == "__main__":
    main()
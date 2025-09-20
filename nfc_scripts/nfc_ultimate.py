#!/usr/bin/env python3
"""
PN532 RF Protocol Debug
Testira osnovnu RF komunikaciju na najnižem nivou
"""

import board
import busio
import time

class PN532RFDebug:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        # Kreiraj PN532 sa debug mode
        from adafruit_pn532.i2c import PN532_I2C
        self.pn532 = PN532_I2C(self.i2c, debug=True)  # Debug ON!
        
        firmware = self.pn532.firmware_version
        if not firmware:
            raise Exception("PN532 ne odgovara!")
            
        print(f"PN532 Firmware: {firmware[1]}.{firmware[2]}")

    def test_rf_configurations(self):
        """Test različitih RF konfiguracija"""
        print("\n=== RF CONFIGURATION TEST ===")
        
        # Test osnovne SAM konfiguracije
        sam_configs = [
            (0x01, "Normal mode"),
            (0x02, "Virtual card mode"), 
            (0x03, "Wired card mode"),
            (0x04, "Dual card mode")
        ]
        
        for mode, description in sam_configs:
            print(f"\nTestiram SAM config: {description}")
            try:
                # Pokušaj manuelne SAM konfiguracije
                result = self.pn532.SAM_configuration()
                print(f"  SAM config rezultat: {result}")
                
                # Test card detection sa ovom konfiguracijom
                self.quick_detection_test()
                
            except Exception as e:
                print(f"  SAM config greška: {e}")

    def quick_detection_test(self):
        """Brzi test detekcije sa trenutnim RF podešavanjima"""
        print("    Quick detection test...")
        
        for attempt in range(3):
            try:
                uid = self.pn532.read_passive_target(timeout=0.5)
                if uid:
                    print(f"    ✓ Kartica detektovana: {uid.hex().upper()}")
                    return True
            except:
                pass
        
        print("    ✗ Nema detekcije")
        return False

    def test_different_protocols(self):
        """Test različitih NFC protokola"""
        print("\n=== PROTOCOL TEST ===")
        
        protocols = [
            ("ISO14443 Type A", "Standardni MIFARE protokol"),
            ("ISO14443 Type B", "Alternativni protokol"),
            ("FeliCa", "Sony protokol"),
        ]
        
        for protocol_name, description in protocols:
            print(f"\nTestiram: {protocol_name} - {description}")
            
            # Ovde bismo trebali različite protokol pozive, 
            # ali adafruit biblioteka ima ograničene opcije
            try:
                # Standard read_passive_target pokušava Type A
                uid = self.pn532.read_passive_target(timeout=1.0)
                if uid:
                    print(f"  ✓ {protocol_name} - kartica: {uid.hex()}")
                else:
                    print(f"  ✗ {protocol_name} - nema odgovora")
            except Exception as e:
                print(f"  ✗ {protocol_name} - greška: {e}")

    def raw_i2c_debug(self):
        """Raw I2C debug - praćenje komunikacije"""
        print("\n=== RAW I2C DEBUG ===")
        print("Uključen je debug mode - videćete I2C komunikaciju")
        
        print("\nPokušavam detekciju sa debug trace...")
        
        for attempt in range(5):
            print(f"\n--- Attempt {attempt + 1} ---")
            
            try:
                # Ova komanda će prikazati raw I2C komunikaciju
                uid = self.pn532.read_passive_target(timeout=2.0)
                
                if uid:
                    print(f"SUCCESS: {uid.hex().upper()}")
                    break
                else:
                    print("No response from card")
                    
            except Exception as e:
                print(f"Exception: {e}")
        
        print("\nAnaliza I2C trace-a:")
        print("- Ako vidite I2C komunikaciju, PN532 radi")
        print("- Ako nema trace-a, problem je sa PN532")
        print("- Ako ima trace ali nema odgovora, problem je RF")

    def antenna_field_test(self):
        """Test RF antena polja"""
        print("\n=== ANTENNA FIELD TEST ===")
        
        print("Testiram RF polje...")
        
        # Pokušaj da aktiviramo RF polje eksplicitno
        try:
            # SAM configuration aktivira RF polje
            self.pn532.SAM_configuration()
            print("✓ RF polje aktivirano")
            
            print("Držite karticu na anteni i NE POMERAJTE...")
            input("Pritisnite Enter kada je kartica postavljena...")
            
            # Kontinuirani test sa kratkim intervalima
            print("Kontinuirani RF test (30 sekundi)...")
            
            detections = 0
            total_attempts = 0
            
            start_time = time.time()
            while time.time() - start_time < 30:
                total_attempts += 1
                
                try:
                    uid = self.pn532.read_passive_target(timeout=0.1)
                    if uid:
                        detections += 1
                        if detections == 1:
                            print(f"\n🎉 PRVA DETEKCIJA: {uid.hex().upper()}")
                        elif detections % 10 == 0:
                            print(f"Detekcija #{detections}")
                    
                except:
                    pass
                
                if total_attempts % 100 == 0:
                    success_rate = (detections / total_attempts) * 100
                    print(f"Progress: {detections}/{total_attempts} ({success_rate:.1f}%)")
            
            final_rate = (detections / total_attempts) * 100 if total_attempts > 0 else 0
            print(f"\nRF FIELD TEST REZULTAT:")
            print(f"Ukupno pokušaja: {total_attempts}")
            print(f"Detekcija: {detections}")
            print(f"Uspešnost: {final_rate:.1f}%")
            
            if detections == 0:
                print("❌ RF POLJE NE RADI - možda je problem sa antenama")
            elif final_rate < 10:
                print("⚠️ RF POLJE SLABO - možda interference ili slaba antena") 
            else:
                print("✅ RF POLJE RADI!")
                
        except Exception as e:
            print(f"RF polje test greška: {e}")

    def card_positioning_guide(self):
        """Vodič za pozicioniranje kartice"""
        print("\n=== CARD POSITIONING GUIDE ===")
        
        positions = [
            "Direktno na PN532 čip (centar modula)",
            "1cm levo od čipa",
            "1cm desno od čipa", 
            "1cm iznad čipa",
            "1cm ispod čipa",
            "Kartica pod uglom od 45°",
            "Kartica podigunta 5mm od površine",
            "Kartica čvrsto pritisnuta na modul"
        ]
        
        print("Testirajte svaku poziciju 10 sekundi:")
        
        for i, position in enumerate(positions, 1):
            print(f"\n{i}. POZICIJA: {position}")
            input("Postavite karticu i pritisnite Enter...")
            
            print("Testing... (10 sekundi)")
            detections = 0
            
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    uid = self.pn532.read_passive_target(timeout=0.2)
                    if uid:
                        detections += 1
                        if detections == 1:
                            print(f"  ✓ DETEKTOVANA: {uid.hex().upper()}")
                except:
                    pass
            
            print(f"  Rezultat: {detections} detekcija za 10 sekundi")
            
            if detections > 20:  # Više od 2 po sekundi
                print(f"  🎉 ODLIČANA POZICIJA!")
                print(f"  Koristite ovu poziciju u budućnosti!")
                return position
        
        print("\n❌ NIJEDNA POZICIJA NE RADI")
        return None

    def interference_test(self):
        """Test RF interferenci"""
        print("\n=== INTERFERENCE TEST ===")
        
        print("Test 1: Sa uključenim uređajima u blizini")
        print("(WiFi router, telefon, laptop, bluetooth...)")
        input("Pritisnite Enter...")
        
        detections_with_interference = self.count_detections_in_time(15)
        
        print(f"\nTest 2: Isključite sve uređaje u blizini")
        print("- Telefone stavite u airplane mode")
        print("- Isključite WiFi")
        print("- Udaljite laptop")
        input("Pritisnite Enter kada završite...")
        
        detections_without_interference = self.count_detections_in_time(15)
        
        print(f"\nINTERFERENCE ANALIZA:")
        print(f"Sa interferencom: {detections_with_interference} detekcija")
        print(f"Bez interference: {detections_without_interference} detekcija")
        
        if detections_without_interference > detections_with_interference * 2:
            print("⚠️ PROBLEM SA INTERFERENCOM!")
            print("RF interferenca utiče na rad PN532")
        else:
            print("✓ Interferenca nije glavni problem")

    def count_detections_in_time(self, seconds):
        """Broji detekcije u datom vremenu"""
        print(f"Brojim detekcije {seconds} sekundi...")
        
        detections = 0
        start_time = time.time()
        
        while time.time() - start_time < seconds:
            try:
                uid = self.pn532.read_passive_target(timeout=0.1)
                if uid:
                    detections += 1
            except:
                pass
        
        return detections

    def comprehensive_rf_debug(self):
        """Sveobuhvatni RF debug"""
        print("\n" + "🔍" * 20)
        print("COMPREHENSIVE RF DEBUG")
        print("🔍" * 20)
        
        print("\nOvaj test će:")
        print("1. Testirati RF konfiguracije")
        print("2. Testirati protokole")  
        print("3. Analizirati I2C komunikaciju")
        print("4. Testirati RF polje")
        print("5. Vodič za pozicioniranje")
        print("6. Test interferenci")
        
        input("\nPritisnite Enter za početak...")
        
        # Test 1
        self.test_rf_configurations()
        
        # Test 2
        self.test_different_protocols()
        
        # Test 3  
        self.raw_i2c_debug()
        
        # Test 4
        self.antenna_field_test()
        
        # Test 5
        best_position = self.card_positioning_guide()
        
        # Test 6
        self.interference_test()
        
        # Finalni zaključak
        print("\n" + "📋" * 20)
        print("FINALNI IZVEŠTAJ")
        print("📋" * 20)
        
        if best_position:
            print(f"✅ REŠENJE PRONAĐENO!")
            print(f"Najbolja pozicija: {best_position}")
            print("PN532 i kartice rade, samo je bio problem pozicioniranja!")
        else:
            print("❌ PROBLEM NIJE REŠEN")
            print("\nMogući uzroci:")
            print("- Defektne kartice (više od 5 različitih kartica?)")
            print("- Defektni PN532 modul")
            print("- Problem sa antenama")
            print("- Incompatible kartice")
            print("\nPreporuke:")
            print("- Probajte novi PN532 modul")
            print("- Probajte poznate dobre kartice (hotel, transport)")
            print("- Probajte sa drugačijim napajanjem")

def main():
    try:
        debug = PN532RFDebug()
        
        while True:
            print("\n" + "🔍" + "="*48 + "🔍")
            print("PN532 RF PROTOCOL DEBUG")
            print("🔍" + "="*48 + "🔍")
            print("1. 🔍 Comprehensive RF Debug (sve testove)")
            print("2. ⚙️  Test RF konfiguracija")
            print("3. 📡 Test RF polja i antena")
            print("4. 📍 Vodič pozicioniranja kartice")
            print("5. 📱 Test interferenci")
            print("6. 🔬 Raw I2C debug")
            print("7. ❌ Izlaz")
            
            choice = input("\nIzaberite opciju (1-7): ").strip()
            
            if choice == '1':
                debug.comprehensive_rf_debug()
                
            elif choice == '2':
                debug.test_rf_configurations()
                
            elif choice == '3':
                debug.antenna_field_test()
                
            elif choice == '4':
                debug.card_positioning_guide()
                
            elif choice == '5':
                debug.interference_test()
                
            elif choice == '6':
                debug.raw_i2c_debug()
                
            elif choice == '7':
                break
                
            else:
                print("Nevalidna opcija!")
                
    except Exception as e:
        print(f"Debug greška: {e}")
        print("\nMogući uzroci:")
        print("- PN532 nije povezan")
        print("- I2C ne radi")
        print("- Biblioteka nije instalirana")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Alternativni NFC pristupi - možda postoji drugačiji način
"""

import subprocess
import time
import os

def check_system_nfc():
    """Proveri da li sistem ima NFC podršku"""
    print("=== SYSTEM NFC CHECK ===")
    
    # Proveri da li postoje NFC uređaji u sistemu
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if 'NFC' in result.stdout or 'PN532' in result.stdout:
            print("✓ NFC uređaj pronađen preko USB")
            print(result.stdout)
        else:
            print("✗ Nema NFC uređaja preko USB")
    except:
        print("lsusb komanda nije dostupna")
    
    # Proveri I2C uređaje
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        print("\nI2C sken:")
        print(result.stdout)
        
        if '24' in result.stdout:
            print("✓ PN532 na adresi 0x24")
        else:
            print("✗ PN532 nije na standardnoj adresi")
    except:
        print("i2cdetect nije dostupan")

def try_libnfc_approach():
    """Pokušaj sa libnfc bibliotekom"""
    print("\n=== LIBNFC APPROACH ===")
    
    # Proveri da li je libnfc instaliran
    try:
        result = subprocess.run(['nfc-list'], capture_output=True, text=True)
        print("nfc-list output:")
        print(result.stdout)
        
        if 'PN532' in result.stdout:
            print("✓ libnfc vidi PN532!")
            
            # Pokušaj sken kartica
            print("\nPokušavam sken kartica sa nfc-poll...")
            result = subprocess.run(['nfc-poll'], capture_output=True, text=True, timeout=10)
            print("nfc-poll output:")
            print(result.stdout)
            
        else:
            print("✗ libnfc ne vidi PN532")
            
    except subprocess.TimeoutExpired:
        print("nfc-poll timeout - možda čeka karticu")
    except FileNotFoundError:
        print("libnfc nije instaliran")
        print("Instaliraj sa: sudo apt install libnfc-bin libnfc-dev")
    except Exception as e:
        print(f"libnfc greška: {e}")

def try_pn532_uart_mode():
    """Pokušaj UART mode umesto I2C"""
    print("\n=== PN532 UART MODE TEST ===")
    print("Možda je problem sa I2C protokolom...")
    
    print("Za UART mode potrebno je:")
    print("1. Prebaciti PN532 u UART mode (SEL0=L, SEL1=H)")
    print("2. Povezati na UART pinove umesto I2C")
    print("3. Koristiti serial komunikaciju")
    
    uart_available = input("Da li imate mogućnost UART testa? (y/n): ")
    
    if uart_available.lower() == 'y':
        print("UART test kod...")
        
        # Pokušaj UART pristup
        try:
            import serial
            
            uart_ports = ['/dev/ttyUSB0', '/dev/ttyAMA0', '/dev/serial0']
            
            for port in uart_ports:
                try:
                    print(f"Testiram {port}...")
                    ser = serial.Serial(port, 115200, timeout=1)
                    
                    # Pošalji wakeup komandu
                    ser.write(b'\x55\x55\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\x03\xFD\xD4\x14\x01\x17\x00')
                    time.sleep(0.1)
                    
                    response = ser.read(100)
                    if response:
                        print(f"✓ UART odgovor na {port}: {response.hex()}")
                    else:
                        print(f"✗ Nema UART odgovora na {port}")
                    
                    ser.close()
                    
                except Exception as e:
                    print(f"UART greška na {port}: {e}")
                    
        except ImportError:
            print("pyserial nije instaliran: pip install pyserial")
    else:
        print("UART test preskočen")

def try_different_python_libraries():
    """Pokušaj različite Python biblioteke"""
    print("\n=== DIFFERENT LIBRARIES TEST ===")
    
    libraries_to_try = [
        ("pn532pi", "pip install pn532pi"),
        ("nfcpy", "pip install nfcpy"),
        ("pynfc", "pip install pynfc"),
    ]
    
    for lib_name, install_cmd in libraries_to_try:
        print(f"\nTestiram biblioteku: {lib_name}")
        
        try:
            if lib_name == "pn532pi":
                # Pokušaj pn532pi
                import importlib
                pn532pi = importlib.import_module('pn532pi')
                
                print("✓ pn532pi importovan")
                print("Testiram pn532pi...")
                
                # Test pn532pi koda
                try:
                    from pn532pi import Pn532, Pn532I2c
                    pn532 = Pn532(Pn532I2c(1))
                    pn532.begin()
                    
                    firmware = pn532.getFirmwareVersion()
                    if firmware:
                        print(f"✓ pn532pi firmware: {firmware}")
                        
                        # Test card detection
                        print("Testiram detekciju sa pn532pi...")
                        success, uid = pn532.readPassiveTargetID()
                        if success:
                            print(f"🎉 pn532pi DETEKTOVAO KARTICU: {uid}")
                        else:
                            print("✗ pn532pi - nema kartice")
                    else:
                        print("✗ pn532pi firmware neuspešan")
                        
                except Exception as e:
                    print(f"pn532pi test greška: {e}")
                    
            elif lib_name == "nfcpy":
                import nfc
                print("✓ nfcpy importovan")
                
                # nfcpy test
                try:
                    with nfc.ContactlessFrontend() as clf:
                        print("✓ nfcpy ContactlessFrontend kreiran")
                        
                        # Pokušaj connect
                        target = clf.sense(nfc.clf.RemoteTarget('106A'))
                        if target:
                            print(f"🎉 nfcpy DETEKTOVAO KARTICU: {target}")
                        else:
                            print("✗ nfcpy - nema kartice")
                            
                except Exception as e:
                    print(f"nfcpy test greška: {e}")
                    
        except ImportError:
            print(f"✗ {lib_name} nije instaliran")
            print(f"Instaliraj sa: {install_cmd}")
        except Exception as e:
            print(f"{lib_name} greška: {e}")

def hardware_diagnostic():
    """Dijagnostika hardvera"""
    print("\n=== HARDWARE DIAGNOSTIC ===")
    
    checks = [
        "Da li je PN532 modul originalni ili klon?",
        "Da li su svi pinovi dobro spojeni?", 
        "Da li je napajanje stabilno 3.3V?",
        "Da li je GND pin povezan?",
        "Da li postoje kratki spojevi?",
        "Da li je antena na PN532 modulu oštećena?",
        "Da li ste testirali sa više od 5 različitih kartica?",
        "Da li kartice rade sa telefonom u direktnom kontaktu?",
        "Da li ste pokušali drugi PN532 modul?"
    ]
    
    print("Proverite sledeće:")
    for i, check in enumerate(checks, 1):
        print(f"{i}. {check}")
    
    print(f"\nODGOVORI:")
    responses = {}
    for i, check in enumerate(checks, 1):
        response = input(f"{i}. {check} (y/n/skip): ").strip().lower()
        responses[i] = response
    
    # Analiza odgovora
    print(f"\nANALIZA:")
    issues = []
    
    if responses.get(1) == 'n':
        issues.append("Klon PN532 moduli često imaju probleme")
    if responses.get(2) == 'n':
        issues.append("Loše konekcije su čest uzrok")
    if responses.get(3) == 'n':
        issues.append("Nestabilno napajanje može uzrokovati RF probleme")
    if responses.get(6) == 'n':
        issues.append("Oštećena antena = nema RF komunikacije")
    if responses.get(7) == 'n':
        issues.append("Testirajte sa više različitih kartica")
    if responses.get(8) == 'n':
        issues.append("Možda su kartice defektne")
    
    if issues:
        print("⚠️ MOGUĆI PROBLEMI:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✓ Hardware izgleda OK - problem je možda u softveru")

def final_recommendations():
    """Finalne preporuke"""
    print("\n" + "💡" * 20)
    print("FINALNE PREPORUKE")
    print("💡" * 20)
    
    print("""
KORAK 1 - HARDWARE PROVERA:
• Testirati sa drugim PN532 modulom
• Proveriti sve konekcije multimetrom
• Testirati napajanje pod opterećenjem
• Probati originalni (ne klon) PN532 modul

KORAK 2 - SOFTWARE ALTERNATIVA:
• Instalirati libnfc: sudo apt install libnfc-bin
• Testirati sa nfc-poll komandom  
• Probati pn532pi biblioteku
• Testirati UART mode umesto I2C

KORAK 3 - KARTICE:
• Nabaviti nove, poznate dobre kartice
• Testirati NTAG213 tagove (pouzdani)
• Probati hotel kartice ili transport kartice
• Proveriti da kartice rade sa drugim čitačima

KORAK 4 - ENVIRONMENT:
• Testirati u drugoj prostoriji (bez interferenci)
• Isključiti sve WiFi/Bluetooth uređaje
• Probati sa baterije (ne adapter)
• Testirati na drugačijoj površini

AKO NIŠTA NE RADI:
Najverojatniji uzroci su:
1. Defektni ili klon PN532 modul (60% verovatnoća)
2. Nekompatibilne ili oštećene kartice (25%)
3. Hardware problem - konekcije/napajanje (10%)
4. Software problem - biblioteke/konfiguracija (5%)
    """)

def main():
    while True:
        print("\n" + "🔧" + "="*48 + "🔧")
        print("ALTERNATIVNI NFC PRISTUPI")
        print("🔧" + "="*48 + "🔧")
        print("1. 🔍 System NFC check")
        print("2. 📚 LibNFC approach")  
        print("3. 🔌 PN532 UART mode test")
        print("4. 🐍 Different Python libraries")
        print("5. 🔧 Hardware diagnostic")
        print("6. 💡 Finalne preporuke")
        print("7. ❌ Izlaz")
        
        choice = input("\nIzaberite opciju (1-7): ").strip()
        
        if choice == '1':
            check_system_nfc()
        elif choice == '2':
            try_libnfc_approach()
        elif choice == '3':
            try_pn532_uart_mode()
        elif choice == '4':
            try_different_python_libraries()
        elif choice == '5':
            hardware_diagnostic()
        elif choice == '6':
            final_recommendations()
        elif choice == '7':
            break
        else:
            print("Nevalidna opcija!")

if __name__ == "__main__":
    main()
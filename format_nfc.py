import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A

# Inicijalizuj I2C i PN532
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()

# Default ključ za autentifikaciju
key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

# Broj sektora (16 za MIFARE Classic 1K, 40 za 4K)
NUM_SECTORS = 16

print("Čekam karticu...")

# Čekaj karticu
while True:
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is not None:
        print("Kartica detektovana! UID:", ''.join(f"{b:02X}" for b in uid))
        break

# Funkcija za autentifikaciju bloka
def authenticate(block):
    if pn532.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_A, key):
        print(f"Autentifikacija uspešna za blok {block}")
        return True
    else:
        print(f"Autentifikacija neuspešna za blok {block}! Proveri ključ.")
        return False

# Default access bits (dozvoljavaju čitanje/pisanje sa Key A)
access_bits = [0xFF, 0x07, 0x80, 0x69]  # Standardni access bits

# Obriši sve sektore
for sector in range(NUM_SECTORS):
    # Preskoči sektor 0, blok 0 (Manufacturer Block)
    if sector == 0:
        start_block = 1
    else:
        start_block = 0
    
    trailer_block = sector * 4 + 3  # Sector trailer blok
    
    # Autentifikuj sector trailer
    if not authenticate(trailer_block):
        print(f"Ne mogu formatirati sektor {sector}! Prekidam.")
        exit()
    
    # Obriši data blokove (popuni nulama)
    for i in range(start_block, 3):
        block = sector * 4 + i
        block_data = [0x00] * 16  # 16 bajtova nula
        pn532.mifare_classic_write_block(block, block_data)
        print(f"Blok {block} obrisan (popunjen nulama)")
        time.sleep(0.1)  # Pauza za stabilnost
    
    # Formatiraj sector trailer (Key A + Access Bits + Key B)
    trailer_data = key + access_bits + key
    pn532.mifare_classic_write_block(trailer_block, trailer_data)
    print(f"Sektor {sector} trailer formatiran: KeyA={key}, AccessBits={access_bits}, KeyB={key}")
    time.sleep(0.1)  # Pauza za stabilnost

print("Kartica uspešno formatirana na fabričko stanje!")
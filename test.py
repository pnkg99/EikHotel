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

print("Čekam karticu...")

while True:
    # Čekaj karticu
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

# Blokovi za upis/čitanje
blocks = [12, 13]
data_to_write = "12345"  # Promeni ovo u broj koji želiš (do 16 bajtova)

for block in blocks:
    # Autentifikuj
    if not authenticate(block):
        # Ako ne uspe, probaj preko sector trailer-a (za sektor 3 to je blok 15)
        trailer_block = (block // 4) * 4 + 3
        if not authenticate(trailer_block):
            print("Nemoguća autentifikacija! Kraj.")
            exit()
    
    # Pripremi podatke za upis (popuni do 16 bajtova sa 0x00)
    block_data = list(data_to_write.encode('utf-8')) + [0x00] * (16 - len(data_to_write.encode('utf-8')))
    
    # Upis
    pn532.mifare_classic_write_block(block, block_data)
    print(f"Upisano u blok {block}: {data_to_write}")
    
    time.sleep(0.2)  # Pauza za stabilnost

# Čitanje nazad
for block in blocks:
    # Ponovo autentifikuj ako treba
    if not authenticate(block):
        trailer_block = (block // 4) * 4 + 3
        authenticate(trailer_block)
    
    data = pn532.mifare_classic_read_block(block)
    if data:
        text = bytes(data).rstrip(b"\x00").decode("utf-8", errors="ignore")
        print(f"Pročitano iz bloka {block}: {text}")
    else:
        print(f"Čitanje bloka {block} neuspešno!")

print("Završeno!")
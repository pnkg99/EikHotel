#!/usr/bin/env python3
import time
from datetime import datetime
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# Konfiguracija I2C
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)

# Konfiguracija PN532
pn532.SAM_configuration()  # inicijalizuje čitač

print("PN532 inicijalizovan. Osluskujemo NFC tagove... (pritisni Ctrl+C za kraj)")

def uid_to_hex(uid):
    return ''.join('{:02X}'.format(b) for b in uid)

try:
    while True:
        # read_passive_target vraća UID ili None
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is None:
            # nema taga u dometu
            time.sleep(0.1)
            continue

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uid_hex = uid_to_hex(uid)
        print(f"[{now}] Detektovan tag! UID: {uid_hex} (len={len(uid)})")

        # Pokušaj ispisati ATQA/SAK ako su dostupni (metapodaci)
        try:
            atqa = pn532.SENS_RES  # može biti None zavisno o biblioteci/firmveru
            sak = pn532.SEL_RES
            if atqa is not None or sak is not None:
                print(f"  ATQA: {atqa}, SAK: {sak}")
        except Exception:
            pass

        # kratka debounce pauza da ne ispise stalno isti tag
        # (produlji ako ti štucne sa više čitanja)
        time.sleep(0.8)

except KeyboardInterrupt:
    print("\nKraj - izlaz.")
except Exception as e:
    print("Greska:", e)

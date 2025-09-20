import time
import logging
import busio
import board
from adafruit_pn532.i2c import PN532_I2C

# Osnovni logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('SimpleTest')

def test_basic_functions():
    """Test osnovnih funkcija bez komplikovanja"""
    try:
        # Inicijalizacija
        logger.info("=== POKRETAM JEDNOSTAVAN TEST ===")
        i2c = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, debug=False)
        pn532.SAM_configuration()
        
        ic, ver, rev, support = pn532.firmware_version
        logger.info(f"✓ PN532 Firmware: {ver}.{rev}")
        
        # Čekaj karticu
        logger.info("Stavi karticu na čitač...")
        uid = None
        for attempt in range(10):
            uid = pn532.read_passive_target(timeout=1.0)
            if uid:
                break
            print(f"Pokušaj {attempt + 1}/10...")
            time.sleep(0.5)
        
        if not uid:
            logger.error("✗ Kartica nije detektovana!")
            return False
            
        uid_hex = ''.join(f"{b:02X}" for b in uid)
        logger.info(f"✓ Kartica detektovana: {uid_hex} (dužina: {len(uid)} bajta)")
        
        # Odredi tip kartice
        if len(uid) == 4:
            card_type = "MIFARE Classic 1K"
        elif len(uid) == 7:
            card_type = "MIFARE Ultralight/NTAG"
        else:
            card_type = f"Nepoznato (UID {len(uid)} bajta)"
            
        logger.info(f"✓ Tip kartice: {card_type}")
        
        # Test dostupnih funkcija
        logger.info("\n=== TEST DOSTUPNIH FUNKCIJA ===")
        read_functions = []
        
        for func_name in dir(pn532):
            if 'read' in func_name.lower() and not func_name.startswith('_'):
                read_functions.append(func_name)
                
        logger.info(f"Dostupne read funkcije: {read_functions}")
        
        # Test ntag funkcija ako postoje
        if hasattr(pn532, 'ntag2xx_read_block'):
            logger.info("\n=== TEST NTAG2XX FUNKCIJA ===")
            
            for page in range(0, 8):  # Test prve stranice
                try:
                    # VAŽNO: Ponovo detektuj karticu pre svakog čitanja!
                    logger.info(f"Detektujem karticu za stranicu {page}...")
                    uid_check = pn532.read_passive_target(timeout=1.0)
                    
                    if not uid_check:
                        logger.warning(f"✗ Kartica se izgubila pre čitanja stranice {page}")
                        continue
                    
                    # Sada pokušaj čitanje
                    data = pn532.ntag2xx_read_block(page)
                    
                    if data:
                        hex_data = ' '.join(f"{b:02X}" for b in data[:8])  # Prikaži prvih 8 bajta
                        text = bytes(data[:4]).decode('utf-8', errors='ignore').strip('\x00')
                        logger.info(f"✓ Stranica {page}: HEX=[{hex_data}] TEXT='{text}'")
                    else:
                        logger.warning(f"✗ Stranica {page}: ntag2xx_read_block vratio None")
                        
                except Exception as e:
                    logger.error(f"✗ Stranica {page}: Greška - {e}")
                    
                time.sleep(0.2)  # Pauza između čitanja
        
        # Test mifare classic funkcija  
        if hasattr(pn532, 'mifare_classic_read_block'):
            logger.info("\n=== TEST MIFARE CLASSIC FUNKCIJA ===")
            
            for page in range(4, 8):  # Skip system pages
                try:
                    # Ponovo detektuj karticu
                    uid_check = pn532.read_passive_target(timeout=1.0)
                    if not uid_check:
                        logger.warning(f"✗ Kartica se izgubila")
                        continue
                        
                    data = pn532.mifare_classic_read_block(page)
                    
                    if data:
                        hex_data = ' '.join(f"{b:02X}" for b in data[:8])
                        text = bytes(data[:4]).decode('utf-8', errors='ignore').strip('\x00')
                        logger.info(f"✓ Classic stranica {page}: HEX=[{hex_data}] TEXT='{text}'")
                    else:
                        logger.info(f"✗ Classic stranica {page}: None")
                        
                except Exception as e:
                    logger.info(f"✗ Classic stranica {page}: {e}")
                    
                time.sleep(0.2)
        
        # Finalni test - šta radi
        logger.info("\n=== ZAKLJUČAK ===")
        logger.info("Ako vidiš bilo koji uspešan HEX/TEXT izlaz iznad,")
        logger.info("onda možemo koristiti tu funkciju u glavnom kodu.")
        logger.info("Ako ne - problem je sa samom karticom ili hardware-om.")
        
        return True
        
    except Exception as e:
        logger.error(f"Kritična greška: {e}")
        return False

if __name__ == "__main__":
    test_basic_functions()
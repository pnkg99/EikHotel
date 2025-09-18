from services.pn532 import SimpleNFCReader
def test_nfc():
    def on_card_read(uid):
        print(f"Kartica detektovana: {''.join(f'{b:02X}' for b in uid)}")
    
    nfc = SimpleNFCReader(on_card_read=on_card_read)
    
    # Čitaj UID
    uid = nfc.read_card_once(timeout=5.0)
    if not uid:
        print("Nema kartice!")
        return
    
    # Pročitaj sector trailer
    sector = 1
    nfc.read_sector_trailer(uid, sector)
    
    # Upis i čitanje bloka
    block = 4
    test_data = "Test123"
    if nfc.write_block(uid, block, test_data):
        print(f"Upis uspešan: {test_data}")
        read_data = nfc.read_block(uid, block)
        print(f"Pročitano: {read_data}")
    
    nfc.stop_polling()

if __name__ == "__main__":
    test_nfc()
import random
import json
import os
from typing import Dict, List, Optional
2
class ParkingSpot:
    def __init__(self, parking_type: str, level: int, section: str, spot_number: str, status: str = 'free'):
        self.parking_type = parking_type  # 'unutrasnji' ili 'spoljasnji'
        self.level = level
        self.section = section
        self.spot_number = spot_number
        self.status = status  # 'free', 'occupied', 'out_of_order'
        self.guest_info = None  # Informacije o gostu koji koristi mesto
        self.license_plate = None  # Registarske tablice
        self.room_number = None  # Broj sobe (ako je zauzeto)
        self.timestamp = None  # Vreme alokacije
    
    def allocate(self, guest_info: dict = None, license_plate: str = None, room_number: str = None):
        """Alociraj parking mesto"""
        if self.status != 'free':
            return False
        
        self.status = 'occupied'
        self.guest_info = guest_info
        self.license_plate = "999 KG"
        self.room_number = room_number
        self.timestamp = self._get_current_timestamp()
        return True
    
    def free(self):
        """Oslobodi parking mesto"""
        self.status = 'free'
        self.guest_info = None
        self.license_plate = None
        self.room_number = None
        self.timestamp = None
    
    def set_current(self, current: bool = True):
        """Postavi mesto kao neispravno ili vrati u funkciju"""
        if current:
            if self.status == 'occupied':
                return False  # Ne može se postaviti kao neispravno ako je zauzeto
            self.status = 'current'
            self.guest_info = None
            self.license_plate = None
            self.room_number = None
            self.timestamp = None
        else:
            if self.status == 'current':
                self.status = 'free'
        return True
    
    def _get_current_timestamp(self):
        import datetime
        return datetime.datetime.now().isoformat()
    
    def to_dict(self):
        """Konvertuj u dictionary za serijalizaciju"""
        return {
            'parking_type': self.parking_type,
            'level': self.level,
            'section': self.section,
            'spot_number': self.spot_number,
            'status': self.status,
            'guest_info': self.guest_info,
            'license_plate': self.license_plate,
            'room_number': self.room_number,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Kreiraj iz dictionary-ja"""
        spot = cls(
            data['parking_type'],
            data['level'],
            data['section'],
            data['spot_number'],
            data['status']
        )
        spot.guest_info = data.get('guest_info')
        spot.license_plate = data.get('license_plate')
        spot.room_number = data.get('room_number')
        spot.timestamp = data.get('timestamp')
        return spot


class ParkingManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ParkingManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        
        self.initialized = True
        self.data_file = 'parking_data.json'
        
        # Struktura parkinga
        self.parking_structure = {
            'unutrasnji': {
                'levels': [1, 2, 3],
                'sections': {
                    1: ['A', 'B', 'C'],
                    2: ['A', 'B', 'C', 'D'],
                    3: ['A', 'B']
                }
            },
            'spoljasnji': {
                'levels': [1, 2],
                'sections': {
                    1: ['A', 'B', 'C', 'D', 'E'],
                    2: ['A', 'B', 'C']
                }
            }
        }
        
        # Dictionary sa svim parking mestima
        # Key: (parking_type, level, section, spot_number)
        # Value: ParkingSpot object
        self.parking_spots: Dict[tuple, ParkingSpot] = {}
        
        # Učitaj postojeće podatke ili inicijalizuj nova mesta
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Učitaj postojeće podatke ili kreiraj nova mesta"""
        if os.path.exists(self.data_file):
            self._load_from_file()
        else:
            self._initialize_parking_spots()
            self._save_to_file()
    
    def _initialize_parking_spots(self):
        """Inicijalizuj parking mesta sa random statusima"""
        switch=1
        for parking_type, data in self.parking_structure.items():
            for level in data['levels']:
                for section in data['sections'][level]:
                    # Generiši random broj mesta po sekciji (10-24)
                    spots_count = random.randint(10, 24)
                    current_index = random.randint(1, spots_count)

                    for i in range(1, spots_count + 1):
                        spot_number = f"{section}{i}"

                        if i == current_index and section == "B" and switch:
                            status = 'current'
                            switch = 0
                        else:
                            status = 'free' if random.random() < 0.6 else 'occupied'

                        print(spot_number, status)

                        spot = ParkingSpot(parking_type, level, section, spot_number, status)

                        if status == 'occupied':
                            spot.license_plate = f"KG {random.randint(100, 999)} {''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}"
                            spot.room_number = f"{random.randint(100, 999)}"
                            spot.guest_info = {"name": f"Guest {random.randint(1, 100)}"}
                            spot.timestamp = spot._get_current_timestamp()

                        key = (parking_type, level, section, spot_number)
                        self.parking_spots[key] = spot

    def _save_to_file(self):
        """Sačuvaj podatke u fajl"""
        data = {}
        for key, spot in self.parking_spots.items():
            data[str(key)] = spot.to_dict()
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_from_file(self):
        """Učitaj podatke iz fajla"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.parking_spots = {}
            for key_str, spot_data in data.items():
                key = eval(key_str)  # Konvertuj string nazad u tuple
                spot = ParkingSpot.from_dict(spot_data)
                self.parking_spots[key] = spot
                
        except Exception as e:
            print(f"Error loading parking data: {e}")
            self._initialize_parking_spots()
    
    def get_spots_for_section(self, parking_type: str, level: int, section: str) -> List[ParkingSpot]:
        """Dobij sva mesta za određenu sekciju"""
        spots = []
        for key, spot in self.parking_spots.items():
            if (key[0] == parking_type and 
                key[1] == level and 
                key[2] == section):
                spots.append(spot)
        
        # Sortiraj po broju mesta
        spots.sort(key=lambda x: int(x.spot_number[1:]))  # Ukloni slovo i sortiraj po broju
        return spots
    
    def get_spot(self, parking_type: str, level: int, section: str, spot_number: str):
        """Dobij specifično mesto"""
        key = (parking_type, level, section, spot_number)
        return self.parking_spots.get(key)
    
    def allocate_spot(self, parking_type: str, level: int, section: str, spot_number: str, 
                     guest_info: dict = None, license_plate: str = None, room_number: str = None):
        """Alociraj parking mesto"""
        spot = self.get_spot(parking_type, level, section, spot_number)
        if spot and spot.allocate(guest_info, license_plate, room_number):
            self._save_to_file()
            return True
        return False
    
    def free_spot(self, parking_type: str, level: int, section: str, spot_number: str):
        """Oslobodi parking mesto"""
        spot = self.get_spot(parking_type, level, section, spot_number)
        if spot:
            spot.free()
            self._save_to_file()
            return True
        return False
    
    def set_spot_current(self, parking_type: str, level: int, section: str, spot_number: str, 
                             current: bool = True) -> bool:
        """Postavi mesto kao neispravno ili vrati u funkciju"""
        spot = self.get_spot(parking_type, level, section, spot_number)
        if spot and spot.set_current(current):
            self._save_to_file()
            return True
        return False
    
    def get_parking_structure(self):
        """Dobij strukturu parkinga"""
        return self.parking_structure
    
    def find_spots_by_license_plate(self, license_plate: str) -> List[ParkingSpot]:
        """Pronađi mesta po registarskim tablicama"""
        spots = []
        for spot in self.parking_spots.values():
            if spot.license_plate and license_plate.lower() in spot.license_plate.lower():
                spots.append(spot)
        return spots
    
    def find_spots_by_room(self, room_number: str) -> List[ParkingSpot]:
        """Pronađi mesta po broju sobe"""
        spots = []
        for spot in self.parking_spots.values():
            if spot.room_number == room_number:
                spots.append(spot)
        return spots
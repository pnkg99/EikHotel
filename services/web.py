import requests

BASE_URL = "https://smartcard.eik.rs/api/"
API_TOKEN = "FZ59cp7oRrABpJYcnqacJMwL8BDlliT1ufrMDdFrjyQqqDKJPy7BYpMQZDg7GXLxYsKMwqrEx4dAkP56Pkqv9gNV1jk93urv79N9"

headers = {
    "X-API-KEY": API_TOKEN,
    "Content-Type": "application/json"
}
    
def get_info():
    url = f"{BASE_URL}info" 
    headers = {
        "X-API-KEY": API_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()["data"]
        else:
            print(f"Greška prilikom poziva GET {url}: {response.status_code} - {response.text}")
            return {} 
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return {}

def register_guest( room_number, name, uuid, card_number, cvc_code):
    url=f"{BASE_URL}nfc-card/activate"
    payload = {
    "fullname" : name,
    "location" : room_number,
    "uuid" : uuid,
    "card_number" : card_number,
    "cvc_code" : cvc_code
    }
    try :
        response =  requests.post(url=url, json=payload, headers=headers, timeout=5).json()
        status = response.get("status", -1)
        if status == 0 :
            print("Podatci nisu dobri")
        elif status == 1 :
            return True
        elif status == 2 :
            print("Korisnik vec postoji u bazi")
            
    except Exception as e:
        print(f"Greška: {e}")
        return None

def get_card_history(card_number, cvc_code):
    url=f"{BASE_URL}nfc-card/history"
    payload={
    "card_number" : card_number,
    "cvc_code" : cvc_code
    }
    try:
        response = requests.post(url,json=payload, headers=headers, timeout=5)    
        return response.json()["data"]
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None
    
def read_nfc_card(card_number, cvc_code):
    url=f"{BASE_URL}nfc-card/read"
    payload={
    "card_number" : card_number,
    "cvc_code" : cvc_code
    }
    try:
        return requests.post(url,json=payload, headers=headers, timeout=5).json()
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None

def enter_restaurant(card_number, cvc_code):
    url=f"{BASE_URL}restaurant/enter"
    payload={
    "card_number" : card_number,
    "cvc_code" : cvc_code
    }
    try:
        return requests.post(url,json=payload, headers=headers, timeout=5).json()
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None

def enter_gym(card_number, cvc_code):
    url=f"{BASE_URL}gym/enter"
    payload={
    "card_number" : card_number,
    "cvc_code" : cvc_code
    }
    try:
        return requests.post(url,json=payload, headers=headers, timeout=5).json()
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None

def parking_allocate(num, cvc, space, registration):
    url=f"{BASE_URL}parking/allocate"
    payload= {
    "card_number" : num,
    "cvc_code" : cvc,
    "parking_space" : space,
    "reg_car_number" : registration
    }
    try:
        return requests.post(url,json=payload, headers=headers, timeout=5).json()
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None
    
def deactivate_nfc(num, cvc):
    url=f"{BASE_URL}nfc-card/deactivate"
    payload={
    "card_number" : num,
    "cvc_code" : cvc
    }
    try:
        return requests.post(url,json=payload, headers=headers, timeout=5).json()
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None
def checkout_service(slug, cart_dict):
    url=f"{BASE_URL}nfc-card/checkout"
    payload = {
        "slug": slug ,
        "cart": cart_dict
    }
    print("checkout_payload: ", payload)
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 422:
            print("Lose uneti podatci")
        elif response.status_code == 401:
            print("Nevalidan slug")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Došlo je do mrežne greške ili time-outa: {e}")
        return None


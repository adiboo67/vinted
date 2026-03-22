import time
from curl_cffi import requests

def test_scraper():
    print("Test avec curl_cffi...")
    for impersonate in ["chrome120", "chrome110", "safari15_5"]:
        print(f"--- Modèle : {impersonate} ---")
        session = requests.Session(impersonate=impersonate)
        try:
            res1 = session.get("https://www.vinted.fr", timeout=10)
            print(f"GET Homepage: {res1.status_code} | Cookies trouvés: {len(session.cookies)}")
            
            # API test
            res2 = session.get("https://www.vinted.fr/api/v2/catalog/items?search_text=nike&order=newest_first", timeout=10)
            print(f"GET API: {res2.status_code}")
            if res2.status_code == 200:
                print("Succès, items renvoyés:", len(res2.json().get('items', [])))
                break
        except Exception as e:
            print(f"Erreur: {e}")
        time.sleep(2)

if __name__ == "__main__":
    test_scraper()

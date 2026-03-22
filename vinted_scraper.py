import urllib.parse
import time
import random
from curl_cffi import requests

class VintedScraper:
    def __init__(self):
        self.domain = "https://www.vinted.fr"
        self.scraper = None
        self._set_session_cookies()

    def _set_session_cookies(self):
        """Récupère le cookie de session Vinted avec une toute nouvelle empreinte Chrome."""
        try:
            print("[Scraper] (Re)Création d'une session vierge pour éviter le cache banni...")
            self.scraper = requests.Session(impersonate="chrome120")
            self.scraper.get(self.domain, timeout=15)
        except Exception as e:
            print(f"[Erreur Scraper] Impossible de générer la session : {e}")

    def search(self, catalog_url):
        """
        Prend une URL de recherche Vinted classique et extrait les articles via leur API cachée.
        """
        parsed_url = urllib.parse.urlparse(catalog_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Construction des paramètres pour l'API
        api_params = {}
        for key, value in query_params.items():
            if len(value) == 1:
                api_params[key] = value[0]
            else:
                api_params[key] = value

        # Toujours trier par les plus récents pour repérer les nouveautés
        api_params['order'] = 'newest_first'
        api_endpoint = f"{self.domain}/api/v2/catalog/items"

        # Délai aléatoire (2 à 5 secondes) pour simuler un comportement humain et éviter le blocage
        time.sleep(random.uniform(2.0, 5.0))

        try:
            response = self.scraper.get(api_endpoint, params=api_params, timeout=15)

            # Si la session expire ou qu'un accès est refusé
            if response.status_code in [401, 403]:
                print("[Scraper] Session expirée ou temporairement bloquée. Renouvellement des cookies...")
                self._set_session_cookies()
                time.sleep(2)
                response = self.scraper.get(api_endpoint, params=api_params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            elif response.status_code == 429:
                print("[Avertissement] Trop de requêtes (Rate Limits). Le bot va temporairement ralentir.")
                return []
            else:
                print(f"[Erreur] Code HTTP {response.status_code} Vinted.")
                return []
                
        except Exception as e:
            print(f"[Erreur Scraper] Échec de la requête : {e}")
            return []

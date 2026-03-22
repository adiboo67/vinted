import json
import time
import sqlite3
import os
from datetime import datetime
from vinted_scraper import VintedScraper
from notifier import Notifier

# Fichiers
CONFIG_FILE = "config.json"
DB_FILE = "articles_vus.db"

def init_db():
    """Initialise la base de données SQL pour mémoriser les articles déjà alertés et éviter les doublons."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_items (
            item_id TEXT PRIMARY KEY,
            date_seen TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def load_config():
    """Charge les paramètres de recherche depuis config.json."""
    if not os.path.exists(CONFIG_FILE):
        print(f"[Erreur] Fichier {CONFIG_FILE} introuvable.")
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_item_seen(conn, item_id):
    """Vérifie si un article avec cet ID est déjà connu."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_items WHERE item_id = ?", (str(item_id),))
    return cursor.fetchone() is not None

def mark_item_seen(conn, item_id):
    """Marque l'article comme connu dans la base de données."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO seen_items (item_id, date_seen) VALUES (?, ?)", (str(item_id), datetime.now().isoformat()))
    conn.commit()

def main():
    print("🤖 Démarrage du bot Vinted...")
    config = load_config()
    if not config:
        return

    conn = init_db()
    scraper = VintedScraper()
    notifier = Notifier(config)

    # Récupérer l'intervalle en secondes
    check_interval = config.get("check_interval_minutes", 5) * 60

    print(f"📡 Bot actif ! Vérification programmée toutes les {config.get('check_interval_minutes', 5)} minutes.")

    while True:
        print(f"\n==============================================")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Lancement d'un cycle de détection...")
        
        for search in config.get("searches", []):
            name = search.get("name", "Recherche")
            url = search.get("url")
            max_price = search.get("max_price")

            print(f"🔍 Scan en cours : {name}...")
            items = scraper.search(url)

            new_deals = 0
            for item in items:
                item_id = item.get("id")

                # Filtrer les doublons : si l'article est déjà en BDD, on ignore
                if is_item_seen(conn, item_id):
                    continue

                # On le sauvegarde pour la prochaine fois
                mark_item_seen(conn, item_id)

                # Filtrage : On vérifie si c'est vraiment une "bonne affaire" (ex: max_price)
                price_info = item.get("price", {})
                price_amount = price_info.get("amount", "999999") if isinstance(price_info, dict) else price_info
                
                try:
                    item_price = float(price_amount)
                except (ValueError, TypeError):
                    item_price = 999999.0
                if max_price and item_price > float(max_price):
                    continue # Article trop cher par rapport à nos limites

                # Bonne affaire confirmée !
                new_deals += 1
                
                # Reconstruire le lien pour l'afficher en console
                item_url = item.get("url") or f"https://www.vinted.fr/items/{item.get('id')}"
                if item_url.startswith("/"):
                    item_url = f"https://www.vinted.fr{item_url}"
                    
                print(f"🎉 ALERTE : {item.get('title')} à {item_price}€")
                print(f"   👉 Lien : {item_url}")
                
                notifier.send_alert(name, item)

            if new_deals == 0:
                print(f"  🤷 Rien de nouveau dans le budget pour : {name}")

        print(f"⏳ Fin du cycle. Attente de {check_interval // 60} minutes...\n(Appuyez sur Ctrl+C pour quitter)")
        time.sleep(check_interval)

if __name__ == "__main__":
    # SERVEUR WEB FANTOME POUR L'HEBERGEMENT GRATUIT RENDER (Web Service)
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot Vinted est 100% En Ligne !")
            
    def run_dummy_server():
        port = int(os.environ.get("PORT", 10000))
        print(f"🌐 Faux serveur web démarré sur le port {port} pour tromper Render...")
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        server.serve_forever()
        
    # Lancement du faux serveur en arrière-plan
    threading.Thread(target=run_dummy_server, daemon=True).start()

    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt manuel du bot effectué.")

import time
import os
import threading
from datetime import datetime
from vinted_scraper import VintedScraper
from notifier import Notifier
from discord_commander import run_discord_bot
import database as db

def main():
    print("🤖 Démarrage du bot Vinted (Architecture Multi-User)...")
    
    # Initialize SQLite database
    conn = db.init_db()
    scraper = VintedScraper()
    print("📡 Bot actif en attente de configurations utilisateur...")

    while True:
        users = db.get_all_users(conn)
        now = time.time()
        
        for user in users:
            discord_id = user["discord_id"]
            webhook_url = user.get("webhook_url")
            search_url = user.get("search_url")
            max_price = user.get("max_price") or float('inf')
            scan_interval_sec = user.get("scan_interval", 60)
            
            # Vérifier si c'est le moment de scanner pour cet utilisateur
            last_scan = user.get("last_scan", 0)
            if now - last_scan < scan_interval_sec:
                continue # Pas encore le moment
                
            if not search_url or not webhook_url:
                continue # Configuration incomplète
            
            # Mise à jour du timer (même si la recherche échoue, on ne veut pas spammer la boucle)
            db.update_last_scan(conn, discord_id, now)

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan pour l'utilisateur {discord_id}...")
            
            try:
                items = scraper.search(search_url)
            except Exception as e:
                print(f"[Erreur Scraper] {e}")
                continue

            new_deals = 0
            
            # Récupérer et nettoyer les mots-clés du filtre (optionnel)
            filter_str = user.get("filters", "")
            filters = [f.strip().lower() for f in filter_str.split(",") if f.strip()] if filter_str else []

            for item in items:
                item_id = str(item.get("id"))

                # Vérifier les doublons
                if db.is_item_seen(conn, discord_id, item_id):
                    continue

                # Marquer vu
                db.mark_item_seen(conn, discord_id, item_id)

                # 1. Filtre par prix
                price_info = item.get("price", {})
                price_amount = price_info.get("amount", "inf") if isinstance(price_info, dict) else price_info
                try:
                    item_price = float(price_amount)
                except (ValueError, TypeError):
                    item_price = float('inf')
                    
                if max_price > 0 and item_price > float(max_price):
                    continue

                # 2. Filtre par mots-clés (titre / description)
                if filters:
                    title = item.get("title", "").lower()
                    description = item.get("description", "").lower()
                    # L'article doit contenir au moins l'un des mots-clés (ou tous ? Par défaut: "OR")
                    match = False
                    for mot in filters:
                        if mot in title or mot in description:
                            match = True
                            break
                    if not match:
                        continue # Ne matche aucun filtre
                
                # Bonne affaire confirmée !
                new_deals += 1
                
                item_url = item.get("url") or f"https://www.vinted.fr/items/{item_id}"
                if item_url.startswith("/"):
                    item_url = f"https://www.vinted.fr{item_url}"
                    
                print(f"🎉 ALERTE pour {discord_id} : {item.get('title')} à {item_price}€")
                
                Notifier.send_alert(item, webhook_url, user.get("auto_message", ""))

            if new_deals == 0:
                print(f"  🤷 Rien de nouveau dans les limites pour {discord_id}.")
        
        # Courte pause globale pour ne pas saturer le CPU (le chronomètre des users pilote les requêtes)
        time.sleep(5)

if __name__ == "__main__":
    from http.server import HTTPServer, BaseHTTPRequestHandler

    # ── Faux serveur HTTP (compatibilité AlwaysData / Render) ──
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot Vinted Multi-User est 100% En Ligne !")

        def log_message(self, format, *args):
            pass  # Silence les logs HTTP

    def run_dummy_server():
        port = int(os.environ.get("PORT", 10000))
        print(f"🌐 Faux serveur web démarré sur le port {port}...")
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        server.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()

    # ── Lancement du bot Discord de commandes ──
    threading.Thread(target=run_discord_bot, daemon=True).start()
    print("🎮 Bot Discord de commandes démarré (thread séparé).")

    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt manuel du bot effectué.")

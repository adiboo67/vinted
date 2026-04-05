import json
import os

CONFIG_FILE = "config.json"

def main():
    print("🌟 Bienvenue dans l'outil d'ajout de filtre Vinted 🌟")
    print("---------------------------------------------------")
    
    # 1. Demander le nom
    name = input("📝 1. Quel est le nom de cette recherche ? (ex: veste nike) : ").strip()
    if not name:
        print("❌ Erreur : Le nom ne peut pas être vide.")
        return

    # 2. Demander l'URL
    url = input("🔗 2. Colle le lien Vinted complet ici : ").strip()
    if not url.startswith("http"):
        print("❌ Erreur : Le lien doit commencer par http ou https.")
        return

    # 3. Demander le prix maximum
    prix_str = input("💰 3. Quel est le prix maximum en euros ? (ex: 25 ou 25.50) : ").strip()
    try:
        max_price = float(prix_str.replace(",", "."))
    except ValueError:
        print("❌ Erreur : Veuillez entrer un nombre valide pour le prix.")
        return

    # Charger le fichier config.json actuel
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print("❌ Erreur : Le fichier config.json est mal formaté.")
                return
    else:
        # Si le fichier n'existe pas, on crée une structure de base
        config = {
            "check_interval_minutes": 5,
            "notifications": {
                "discord_webhook_url": "",
                "telegram_bot_token": "",
                "telegram_chat_id": ""
            },
            "searches": []
        }

    # S'assurer que le bloc 'searches' existe
    if 'searches' not in config:
        config['searches'] = []

    # Ajouter la nouvelle recherche
    nouvelle_recherche = {
        "name": name,
        "url": url,
        "max_price": max_price
    }
    config['searches'].append(nouvelle_recherche)

    # Sauvegarder dans le fichier
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n✅ Super ! Ta recherche a été ajoutée avec succès au fichier.")
    print("💡 Astuce : Comme le bot se met à jour tout seul, la recherche est déjà active !")

if __name__ == "__main__":
    main()

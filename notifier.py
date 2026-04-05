import requests
import time

class Notifier:
    @staticmethod
    def send_alert(item, webhook_url, auto_message=""):
        """Envoie l'alerte sur un webhook Discord sous la forme d'un bel Embed."""
        if not webhook_url or "discord.com/api/webhooks/" not in webhook_url:
            return  # Pas de webhook valide pour cet utilisateur
            
        title = item.get("title", "Sans titre")
        item_id = item.get("id", "")
        price_info = item.get("price", {})
        price = price_info.get("amount", "N/A") if isinstance(price_info, dict) else price_info
        currency = price_info.get("currency_code", "€") if isinstance(price_info, dict) else item.get("currency", "€")
        
        url = item.get("url") or ""
        if not url and item_id:
            url = f"https://www.vinted.fr/items/{item_id}"
        elif url.startswith("/"):
            url = f"https://www.vinted.fr{url}"
            
        brand = item.get("brand_title", "Sans marque")
        size = item.get("size_title", "N/A")
        
        photo_info = item.get("photo")
        photo_url = photo_info.get("url", "") if photo_info else ""

        embed = {
            "title": f"🛒 Nouvel Article: {title}",
            "url": url,
            "color": 3447003, # Bleu
            "fields": [
                {"name": "Prix", "value": f"**{price} {currency}**", "inline": True},
                {"name": "Taille", "value": f"{size}", "inline": True},
                {"name": "Marque", "value": f"{brand}", "inline": True},
                {"name": "Lien", "value": f"**[🛒 Acheter l'article sur Vinted]({url})**", "inline": False}
            ]
        }
        
        if photo_url:
            embed["image"] = {"url": photo_url}
            
        # Si l'utilisateur a configuré un message auto, on l'affiche
        content = "✨ Une nouveauté matche tes critères !"
        if auto_message:
            content += f"\n\n**Texte à copier (favoris) :**\n```{auto_message}```"

        payload = {
            "content": content,
            "embeds": [embed]
        }

        try:
            res = requests.post(webhook_url, json=payload, timeout=10)
            if res.status_code == 429:
                print("[Alerte Discord] Trop de messages d'un coup. Pause de 2s...")
                time.sleep(2)
                requests.post(webhook_url, json=payload, timeout=10)
            elif res.status_code >= 400:
                print(f"[Erreur Discord] Code {res.status_code}: Le lien Webhook refuse le message.")
            
            # Pause préventive
            time.sleep(0.5)
        except Exception as e:
            print(f"[Erreur Discord] {e}")

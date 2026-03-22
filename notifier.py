import requests
import time

class Notifier:
    def __init__(self, config):
        self.config = config.get("notifications", {})
        self.discord_url = self.config.get("discord_webhook_url")
        self.telegram_token = self.config.get("telegram_bot_token")
        self.telegram_chat_id = self.config.get("telegram_chat_id")

    def send_alert(self, search_name, item):
        """Envoie une alerte sur Discord ou Telegram selon la configuration."""
        
        # Extraction sécurisée des informations de l'article
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
        
        # Gestion prudente de la photo (peut être None)
        photo_info = item.get("photo")
        photo_url = photo_info.get("url", "") if photo_info else ""

        message_text = (
            f"🚨 **NOUVELLE BONNE AFFAIRE : {search_name}** 🚨\n\n"
            f"**Article:** {title}\n"
            f"**Prix:** {price} {currency}\n"
            f"**Marque:** {brand}\n"
            f"**Taille:** {size}\n"
            f"**Lien:** {url}"
        )

        if self.discord_url and "TON_LIEN_WEBHOOK_ICI" not in self.discord_url:
            self._send_discord(photo_url, title, price, currency, url, brand, size)

        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message_text, photo_url)

    def _send_discord(self, photo_url, title, price, currency, url, brand, size):
        """Envoie l'alerte sur un webhook Discord sous la forme d'un bel Embed."""
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

        payload = {
            "content": "✨ Une nouveauté matche tes critères !",
            "embeds": [embed]
        }

        try:
            res = requests.post(self.discord_url, json=payload, timeout=10)
            if res.status_code == 429:
                print("[Alerte Discord] Trop de messages d'un coup. Le bot fait une pause de 2s...")
                time.sleep(2)
                requests.post(self.discord_url, json=payload, timeout=10)
            elif res.status_code >= 400:
                print(f"[Erreur Discord] Code {res.status_code}: Le lien Webhook refuse le message.")
            
            # Pause préventive obligatoire pour ne pas fâcher la limite de Discord (5/secondes)
            time.sleep(0.5)
        except Exception as e:
            print(f"[Erreur Discord] {e}")

    def _send_telegram(self, message, photo_url):
        """Envoie l'alerte via un Bot Telegram."""
        try:
            if photo_url:
                api_url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                payload = {"chat_id": self.telegram_chat_id, "photo": photo_url, "caption": message, "parse_mode": "Markdown"}
            else:
                api_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}

            requests.post(api_url, data=payload, timeout=10)
        except Exception as e:
            print(f"[Erreur Telegram] {e}")

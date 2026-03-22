# Bot Vinted - Alertes de Bonnes Affaires 🛍️

Ce bot Python scanne Vinted très régulièrement selon tes critères et t'envoie une notification instantanée (Discord / Telegram) dès qu'une nouveauté correspond à ton budget.

## 🛠️ 1. Installation des pré-requis

1. Il faut que **Python 3** soit installé sur ton PC.
2. Ouvre un Invite de Commandes (`cmd`) ou PowerShell dans le dossier de ce projet (`c:\Users\HP2\Downloads\vintedbot`).
3. Installe les dépendances requises en tapant :
   ```bash
   pip install -r requirements.txt
   ```
*(Ces bibliothèques permettent au bot de contourner les blocages basiques de Vinted et d'envoyer les requêtes Web).*

## ⚙️ 2. Comment le configurer ?

Ouvre le fichier **`config.json`** dans n'importe quel éditeur de texte (Bloc-notes ou VSCode).

1. **`check_interval_minutes`** : L'intervalle de recherche. Laisse-le entre 3 et 5 minutes minimum pour ne pas te faire bloquer ton adresse IP par Vinted.
2. **Notifications** :
   - Pour utiliser **Discord** : Crée un salon > Clic droit/Paramètres du salon > Intégrations > Créer un Webhook. Copie le lien et colle le à la place de `TON_LIEN_WEBHOOK_ICI`.
   - Pour utiliser **Telegram** : Renseigne `telegram_bot_token` (créé via BotFather) et `telegram_chat_id` (ton ID perso).
3. **Recherches personnalisables (`searches`)** :
   Tu peux surveiller autant d'articles que tu le souhaites. Pour chaque article :
   - Va sur le site `Vinted.fr` depuis ton navigateur.
   - Fais une recherche en sélectionnant tous tes filtres (Exprès : Sneakers, Nike, Taille 42, État neuf).
   - **Copie le lien complet qui s'affiche dans ta barre d'URL** et colle-le dans la valeur `"url"` du *config.json*.
   - Renseigne `"max_price"` : C'est la valeur du filtre intelligent "bonne affaire". Si Vinted trouve l'article à 60€ mais que ton max_price est 40€, le bot ne te dérangera pas.

## 🚀 3. Lancer le Bot

Pour faire démarrer la surveillance, double-clique sur le script `vinted_bot.py` ou exécute-le via ton terminal :
```bash
python vinted_bot.py
```

Laisse la fenêtre noire du terminal ouverte pour que le bot tourne en arrière-plan.

### 💡 Le savais-tu ?
- Le bot intègre une base de données locale (`articles_vus.db`) totalement autonome qui mémorise les ID des annonces pour que tu ne sois **jamais spammé deux fois** pour le même article !
- Pour limiter les blocages (Rate Limits) par Vinted (Captcha 403), le scraper utilise `cloudscraper` et un système de rafraichissement automatique de cookies invisibles pour se faire passer pour un humain.

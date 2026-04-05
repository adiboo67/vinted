"""
discord_commander.py
---------------------
Bot Discord de commande pour administrer le VintedBot depuis Discord.
Toutes les modifications sont sauvegardées en temps réel dans config.json
et persistées sur AlwaysData.

Commandes disponibles (préfixe !):
  !help            — Affiche cette aide
  !showconfig      — Affiche la configuration complète
  !listurl         — Liste toutes les recherches actives
  !addurl          — Ajoute une nouvelle recherche
  !seturl          — Met à jour l'URL d'une recherche
  !setprice        — Met à jour le prix maximum d'une recherche
  !delurl          — Supprime une recherche
  !setinterval     — Change la fréquence de scan (minutes)
  !setmessage      — Définit le message automatique favoris
  !showmessage     — Affiche le message auto + historique
  !setwebhook      — Met à jour le webhook Discord d'alerte
  !marksent        — Marque un acheteur comme contacté
  !resetmessages   — Remet à zéro l'historique des messages
"""

import discord
from discord.ext import commands
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"
SENT_MESSAGES_FILE = "sent_messages.json"


# ─────────────────────────────────────────────
#  Utilitaires JSON
# ─────────────────────────────────────────────

def load_config():
    """Charge config.json depuis le disque à chaque appel (toujours à jour)."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    """Sauvegarde config.json sur le serveur AlwaysData."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_sent_messages() -> dict:
    """Charge l'historique des messages envoyés aux acheteurs."""
    if not os.path.exists(SENT_MESSAGES_FILE):
        return {}
    with open(SENT_MESSAGES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_sent_messages(data: dict):
    """Sauvegarde l'historique des messages dans sent_messages.json."""
    with open(SENT_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  Vérification des permissions
# ─────────────────────────────────────────────

def _check_permissions(ctx) -> bool:
    """
    Retourne True si l'utilisateur est autorisé à utiliser les commandes admin.
    - Si discord_admin_user_ids est vide → tout le monde est autorisé.
    - Si discord_admin_channel_id est défini → salon restreint.
    """
    config = load_config()

    # Vérification du salon
    channel_id = config.get("discord_admin_channel_id")
    if channel_id and str(ctx.channel.id) != str(channel_id):
        return False

    # Vérification de l'utilisateur
    admin_ids = config.get("discord_admin_user_ids", [])
    if not admin_ids:  # Liste vide = accès libre (mode démo)
        return True
    return str(ctx.author.id) in [str(uid) for uid in admin_ids]


def _find_search(config: dict, nom: str):
    """Cherche une recherche par nom (insensible à la casse). Retourne l'objet ou None."""
    for s in config.get("searches", []):
        if s.get("name", "").lower() == nom.lower():
            return s
    return None


# ─────────────────────────────────────────────
#  Lancement du bot
# ─────────────────────────────────────────────

def run_discord_bot():
    """
    Point d'entrée principal.
    Appelé dans un thread daemon depuis vinted_bot.py.

    Le token est cherché dans cet ordre :
    1. Variable d'environnement DISCORD_BOT_TOKEN (AlwaysData / Render)
    2. Fichier bot_token.txt sur le serveur (méthode simple AlwaysData)
    3. Champ discord_bot_token dans config.json (développement local)
    """
    # 1. Variable d'environnement
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()

    # 2. Fichier bot_token.txt (ignoré par Git)
    if not token:
        token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_token.txt")
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                token = f.read().strip()
            if token:
                print("[Discord Bot] 🔑 Token chargé depuis bot_token.txt")

    # 3. config.json (fallback local)
    if not token:
        config = load_config()
        token = config.get("discord_bot_token", "").strip()

    if not token or len(token) < 20:
        print("[Discord Bot] ⚠️  Aucun token trouvé. Crée un fichier bot_token.txt avec ton token. Bot de commande désactivé.")
        return

    intents = discord.Intents.default()
    intents.message_content = True  # Obligatoire pour lire les messages

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    # ── Événements ──────────────────────────────

    @bot.event
    async def on_ready():
        print(f"[Discord Bot] ✅ Connecté en tant que {bot.user.name} (ID: {bot.user.id})")
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Vinted 🛒"
        ))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Argument manquant : `{error.param.name}`\n"
                f"Utilise `!help` pour voir l'usage correct."
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argument invalide (nombre attendu ?). Utilise `!help`.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignorer les commandes inconnues silencieusement
        else:
            print(f"[Discord Bot] Erreur commande : {type(error).__name__}: {error}")

    # ── Commandes — Aide ────────────────────────

    @bot.command(name="help")
    async def help_cmd(ctx):
        if not _check_permissions(ctx):
            return
        embed = discord.Embed(
            title="🤖 VintedBot — Commandes Admin",
            description="Toutes les modifications sont sauvegardées immédiatement dans `config.json`.",
            color=0x5865F2
        )
        embed.add_field(
            name="📋 Affichage",
            value=(
                "`!showconfig` — Configuration complète\n"
                "*(ex: `!showconfig`)*\n\n"
                "`!listurl` — Liste toutes les recherches\n"
                "*(ex: `!listurl`)*\n\n"
                "`!showmessage` — Message auto + historique\n"
                "*(ex: `!showmessage`)*"
            ),
            inline=False
        )
        embed.add_field(
            name="🔍 Recherches",
            value=(
                "`!addurl <nom> <prix_max> <url>` — Ajouter\n"
                "*(ex: `!addurl \"sac a main\" 80 https://...`)*\n\n"
                "`!seturl <nom> <url>` — Modifier l'URL\n"
                "*(ex: `!seturl \"pull femme\" https://...`)*\n\n"
                "`!setprice <nom> <prix>` — Modifier le prix max\n"
                "*(ex: `!setprice \"running homme\" 45`)*\n\n"
                "`!delurl <nom>` — Supprimer\n"
                "*(ex: `!delurl \"running homme\"`)*"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Paramètres globaux",
            value=(
                "`!setinterval <minutes>` — Fréquence de scan\n"
                "*(ex: `!setinterval 2`)*\n\n"
                "`!setwebhook <url>` — Webhook Discord d'alerte\n"
                "*(ex: `!setwebhook https://discord.com...`)*\n\n"
                "`!setmessage <texte>` — Message automatique\n"
                "*(ex: `!setmessage Bonjour 👋...`)*"
            ),
            inline=False
        )
        embed.add_field(
            name="📨 Suivi des messages",
            value=(
                "`!marksent <buyer_id>` — Marquer comme contacté\n"
                "*(ex: `!marksent buyer123`)*\n\n"
                "`!resetmessages` — Réinitialiser l'historique\n"
                "*(ex: `!resetmessages`)*"
            ),
            inline=False
        )
        embed.set_footer(text="💡 Noms de recherches : insensibles à la casse")
        await ctx.send(embed=embed)

    # ── Commandes — Affichage ───────────────────

    @bot.command(name="showconfig")
    async def show_config(ctx):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        config = load_config()
        searches = config.get("searches", [])
        interval = config.get("check_interval_minutes", 5)
        webhook = config.get("notifications", {}).get("discord_webhook_url", "")
        auto_msg = config.get("auto_message", "Non défini")

        embed = discord.Embed(
            title="⚙️ Configuration VintedBot",
            color=0x57F287,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="⏱️ Intervalle de scan",
            value=f"**{interval} minutes**",
            inline=True
        )
        embed.add_field(
            name="🔍 Recherches actives",
            value=f"**{len(searches)}**",
            inline=True
        )
        embed.add_field(
            name="🔔 Webhook Discord",
            value="✅ Configuré" if webhook and "webhooks" in webhook else "❌ Non configuré",
            inline=True
        )
        embed.add_field(
            name="💬 Message auto",
            value=f"```{auto_msg[:256]}```",
            inline=False
        )

        if searches:
            lines = []
            for i, s in enumerate(searches, 1):
                lines.append(f"**{i}.** {s.get('name')} — max **{s.get('max_price')}€**")
            embed.add_field(name="📋 Recherches", value="\n".join(lines), inline=False)

        embed.set_footer(text="VintedBot | config.json sur AlwaysData")
        await ctx.send(embed=embed)

    @bot.command(name="listurl")
    async def list_urls(ctx):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        config = load_config()
        searches = config.get("searches", [])

        if not searches:
            await ctx.send("📭 Aucune recherche configurée. Utilise `!addurl` pour en ajouter une.")
            return

        embed = discord.Embed(
            title=f"📋 Recherches Vinted actives ({len(searches)})",
            color=0x5865F2
        )
        for i, s in enumerate(searches, 1):
            url = s.get("url", "#")
            short_url = url[:80] + "..." if len(url) > 80 else url
            embed.add_field(
                name=f"{i}. {s.get('name', 'Sans nom')}",
                value=f"💰 Max : **{s.get('max_price')}€**\n🔗 `{short_url}`",
                inline=False
            )
        await ctx.send(embed=embed)

    @bot.command(name="showmessage")
    async def show_message(ctx):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        config = load_config()
        msg = config.get("auto_message", "Aucun message défini. Utilise `!setmessage`.")
        sent = load_sent_messages()

        embed = discord.Embed(title="💬 Message automatique favoris", color=0x5865F2)
        embed.add_field(name="Message actuel", value=f"```{msg}```", inline=False)
        embed.add_field(
            name="📊 Historique",
            value=f"**{len(sent)}** acheteur(s) déjà contacté(s)",
            inline=True
        )
        if sent:
            last_entries = list(sent.items())[-5:]
            history_text = "\n".join(
                [f"`{bid}` — {data.get('date', '?')[:10]}" for bid, data in last_entries]
            )
            embed.add_field(name="5 derniers", value=history_text, inline=False)
        await ctx.send(embed=embed)

    # ── Commandes — Recherches ──────────────────

    @bot.command(name="addurl")
    async def add_url(ctx, nom: str, prix: float, *, url: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        config = load_config()
        if _find_search(config, nom):
            await ctx.send(
                f"⚠️ Une recherche nommée **{nom}** existe déjà.\n"
                f"Utilise `!seturl {nom} <url>` pour modifier l'URL."
            )
            return
        config.setdefault("searches", []).append({
            "name": nom,
            "url": url.strip(),
            "max_price": prix
        })
        save_config(config)
        embed = discord.Embed(title="✅ Recherche ajoutée", color=0x57F287)
        embed.add_field(name="Nom", value=nom, inline=True)
        embed.add_field(name="Prix max", value=f"**{prix}€**", inline=True)
        embed.set_footer(text="Active dès le prochain cycle de scan.")
        await ctx.send(embed=embed)

    @bot.command(name="seturl")
    async def set_url(ctx, nom: str, *, url: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        if not url.startswith("http"):
            await ctx.send("❌ L'URL doit commencer par `http` ou `https`.")
            return
        config = load_config()
        search = _find_search(config, nom)
        if not search:
            await ctx.send(
                f"❌ Recherche **{nom}** introuvable.\n"
                f"Utilise `!listurl` pour voir les noms disponibles."
            )
            return
        search["url"] = url.strip()
        save_config(config)
        embed = discord.Embed(title=f"✅ URL mise à jour — {search['name']}", color=0x57F287)
        embed.add_field(name="Prix max actuel", value=f"{search.get('max_price')}€", inline=True)
        embed.set_footer(text="Active dès le prochain cycle de scan.")
        await ctx.send(embed=embed)

    @bot.command(name="setprice")
    async def set_price(ctx, nom: str, prix: float):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        if prix <= 0:
            await ctx.send("❌ Le prix doit être supérieur à 0.")
            return
        config = load_config()
        search = _find_search(config, nom)
        if not search:
            await ctx.send(
                f"❌ Recherche **{nom}** introuvable.\n"
                f"Utilise `!listurl` pour voir les noms disponibles."
            )
            return
        old_price = search.get("max_price")
        search["max_price"] = prix
        save_config(config)
        embed = discord.Embed(title=f"✅ Prix mis à jour — {search['name']}", color=0x57F287)
        embed.add_field(name="Ancien prix", value=f"~~{old_price}€~~", inline=True)
        embed.add_field(name="Nouveau prix", value=f"**{prix}€**", inline=True)
        embed.set_footer(text="Actif dès le prochain cycle de scan.")
        await ctx.send(embed=embed)

    @bot.command(name="delurl")
    async def del_url(ctx, *, nom: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        config = load_config()
        searches = config.get("searches", [])
        new_searches = [s for s in searches if s.get("name", "").lower() != nom.lower()]
        if len(new_searches) == len(searches):
            await ctx.send(
                f"❌ Recherche **{nom}** introuvable.\n"
                f"Utilise `!listurl` pour voir les noms disponibles."
            )
            return
        config["searches"] = new_searches
        save_config(config)
        await ctx.send(f"🗑️ Recherche **{nom}** supprimée avec succès. ({len(new_searches)} restante(s))")

    # ── Commandes — Paramètres globaux ──────────

    @bot.command(name="setinterval")
    async def set_interval(ctx, minutes: float):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        if minutes < 1:
            await ctx.send("❌ L'intervalle minimum est **1 minute**.")
            return
        if minutes > 1440:
            await ctx.send("❌ L'intervalle maximum est **1440 minutes** (24h).")
            return
        config = load_config()
        old = config.get("check_interval_minutes", 5)
        config["check_interval_minutes"] = minutes
        save_config(config)
        embed = discord.Embed(title="✅ Intervalle de scan mis à jour", color=0x57F287)
        embed.add_field(name="Avant", value=f"~~{old} min~~", inline=True)
        embed.add_field(name="Maintenant", value=f"**{minutes} min**", inline=True)
        embed.set_footer(text="⚠️ Prend effet au début du prochain cycle.")
        await ctx.send(embed=embed)

    @bot.command(name="setmessage")
    async def set_message(ctx, *, message: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        if len(message) > 500:
            await ctx.send("❌ Le message est trop long (maximum 500 caractères).")
            return
        config = load_config()
        config["auto_message"] = message
        save_config(config)
        embed = discord.Embed(title="✅ Message automatique mis à jour", color=0x57F287)
        embed.add_field(name="Nouveau message", value=f"```{message}```", inline=False)
        embed.set_footer(text="Sauvegardé dans config.json")
        await ctx.send(embed=embed)

    @bot.command(name="setwebhook")
    async def set_webhook(ctx, *, url: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        url = url.strip()
        if "discord.com/api/webhooks/" not in url:
            await ctx.send("❌ L'URL ne semble pas être un webhook Discord valide.")
            return
        config = load_config()
        config.setdefault("notifications", {})["discord_webhook_url"] = url
        save_config(config)
        await ctx.send("✅ Webhook Discord mis à jour ! Les prochaines alertes utiliseront ce nouveau webhook.")

    # ── Commandes — Suivi des messages ──────────

    @bot.command(name="marksent")
    async def mark_sent(ctx, buyer_id: str):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        sent = load_sent_messages()
        already = buyer_id in sent
        sent[buyer_id] = {"sent": True, "date": datetime.now().isoformat()}
        save_sent_messages(sent)
        if already:
            await ctx.send(f"🔄 Acheteur `{buyer_id}` déjà marqué — date mise à jour dans `sent_messages.json`.")
        else:
            await ctx.send(f"✅ Acheteur `{buyer_id}` marqué comme contacté dans `sent_messages.json`.")

    @bot.command(name="resetmessages")
    async def reset_messages(ctx):
        if not _check_permissions(ctx):
            await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
            return
        sent = load_sent_messages()
        count = len(sent)
        save_sent_messages({})
        await ctx.send(
            f"🔄 Historique réinitialisé. **{count}** entrée(s) supprimée(s).\n"
            f"Tous les acheteurs peuvent à nouveau être contactés."
        )

    # ── Démarrage ────────────────────────────────
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("[Discord Bot] ❌ Token invalide. Vérifie 'discord_bot_token' dans config.json.")
    except Exception as e:
        print(f"[Discord Bot] ❌ Erreur de connexion : {e}")


if __name__ == "__main__":
    run_discord_bot()

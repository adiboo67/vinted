import discord
from discord.ext import commands
import os
from datetime import datetime
import database as db

# ─────────────────────────────────────────────
#  Lancement du bot
# ─────────────────────────────────────────────

def run_discord_bot():
    # 1. Variable d'environnement
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()

    # 2. Fichier bot_token.txt
    if not token:
        token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_token.txt")
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                token = f.read().strip()
            if token:
                print("[Discord Bot] 🔑 Token chargé depuis bot_token.txt")

    if not token or len(token) < 20:
        print("[Discord Bot] ⚠️ Aucun token trouvé. Crée un fichier bot_token.txt. Bot désactivé.")
        return

    intents = discord.Intents.default()
    intents.message_content = True  # Obligatoire pour lire les messages

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
    conn = db.init_db()

    # ── Événements ──────────────────────────────

    @bot.event
    async def on_ready():
        print(f"[Discord Bot] ✅ Connecté en tant que {bot.user.name} (ID: {bot.user.id})")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Vinted Multi-User 🛒"))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argument manquant : `{error.param.name}`\nTape `!help` pour voir l'usage correct.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argument invalide (nombre attendu ?). Tape `!help`.")
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            print(f"[Discord] Erreur: {error}")

    # ── Commandes — Profils ──────────────────────

    @bot.command(name="help")
    async def help_cmd(ctx):
        embed = discord.Embed(
            title="🤖 VintedBot — Commandes Multi-Utilisateurs",
            description="Gère ton propre profil et tes alertes Vinted independamment des autres utilisateurs !",
            color=0x5865F2
        )
        embed.add_field(name="🆕 Démarrer", value="`!createprofile` — Crée ton profil utilisateur", inline=False)
        embed.add_field(
            name="⚙️ Configuration",
            value=(
                "`!setwebhook <url>` — Ton webhook Discord pour recevoir tes alertes\n"
                "`!seturl <url>` — L'URL Vinted à surveiller\n"
                "`!setprice <prix>` — Prix maximum accepté\n"
                "`!setfilters <mot1,mot2>` — Mots-clés (titre/desc), séparés par des virgules\n"
                "`!setinterval <secondes>` — Fréquence de scan (ex: 60)\n"
                "`!setmessage <texte>` — Message automatique à intégrer dans tes alertes favoris"
            ),
            inline=False
        )
        embed.add_field(name="📋 Affichage", value="`!myconfig` — Voir ta configuration actuelle", inline=False)
        await ctx.send(embed=embed)

    @bot.command(name="createprofile")
    async def create_profile(ctx):
        user_id = str(ctx.author.id)
        user = db.get_user(conn, user_id)
        if user:
            await ctx.send("✅ Tu as déjà un profil ! Utilise `!myconfig` pour le voir.")
        else:
            db.create_profile(conn, user_id)
            await ctx.send("🎉 **Profil créé avec succès !**\nUtilise `!seturl` et `!setwebhook` pour configurer ton bot.")

    @bot.command(name="myconfig")
    async def my_config(ctx):
        user_id = str(ctx.author.id)
        user = db.get_user(conn, user_id)
        if not user:
            await ctx.send("❌ Tu n'as pas de profil. Utilise `!createprofile` d'abord.")
            return

        embed = discord.Embed(title="⚙️ Ta Configuration VintedBot", color=0x57F287, timestamp=datetime.now())
        embed.add_field(name="Webhook Discord", value="✅ Configuré" if user["webhook_url"] else "❌ Aucun", inline=True)
        embed.add_field(name="Intervalle de scan", value=f"⏱️ {user['scan_interval']} secondes", inline=True)
        embed.add_field(name="Prix maximum", value=f"💰 {user['max_price']}€" if user["max_price"] else "♾️ Illimité", inline=True)
        embed.add_field(name="Filtres (Mots-clés)", value=f"🔤 {user['filters']}" if user["filters"] else "❌ Aucun", inline=False)
        
        url_text = user["search_url"]
        if url_text:
            url_text = url_text[:80] + "..." if len(url_text) > 80 else url_text
        else:
            url_text = "❌ Aucune URL"
        embed.add_field(name="URL Vinted", value=f"🔗 `{url_text}`", inline=False)
        
        msg = user["auto_message"] or "❌ Rien"
        embed.add_field(name="Message Automatique", value=f"💬 ```{msg}```", inline=False)

        await ctx.send(embed=embed)

    # ── Commandes — Modificateurs ──────────────

    @bot.command(name="setwebhook")
    async def set_webhook(ctx, *, url: str):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        
        url = url.strip()
        if "discord.com/api/webhooks/" not in url:
            return await ctx.send("❌ URL Invalide. Cela doit être un Webhook Discord.")
        
        db.update_user_field(conn, user_id, "webhook_url", url)
        await ctx.send("✅ Webhook mis à jour ! C'est ici que tu recevras tes alertes individuelles.")

    @bot.command(name="seturl")
    async def set_url(ctx, *, url: str):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        if not url.startswith("http"):
            return await ctx.send("❌ L'URL doit commencer par `http`.")
        
        db.update_user_field(conn, user_id, "search_url", url.strip())
        await ctx.send("✅ Nouvelle URL Vinted enregistrée !")

    @bot.command(name="setprice")
    async def set_price(ctx, prix: float):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        if prix < 0:
            return await ctx.send("❌ Le prix doit être positif.")
            
        db.update_user_field(conn, user_id, "max_price", prix)
        await ctx.send(f"✅ Prix maximum modifié à **{prix}€**.")

    @bot.command(name="setfilters")
    async def set_filters(ctx, *, filtres: str):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        
        db.update_user_field(conn, user_id, "filters", filtres.strip())
        await ctx.send(f"✅ Filtres mis à jour : `{filtres}`\nLe bot vérifiera que ces mots sont dans le titre ou la description.")

    @bot.command(name="setinterval")
    async def set_interval(ctx, secondes: int):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        if secondes < 60:
            return await ctx.send("❌ L'intervalle **minimum est 60 secondes** (pour éviter un ban Vinted).")
            
        db.update_user_field(conn, user_id, "scan_interval", secondes)
        await ctx.send(f"✅ Fréquence de scan définie à **{secondes} secondes**.")

    @bot.command(name="setmessage")
    async def set_message(ctx, *, message: str):
        user_id = str(ctx.author.id)
        if not db.get_user(conn, user_id): return await ctx.send("❌ Fais `!createprofile` d'abord.")
        if len(message) > 500:
            return await ctx.send("❌ Le message est trop long (maximum 500 caractères).")
            
        db.update_user_field(conn, user_id, "auto_message", message.strip())
        await ctx.send("✅ Message automatique favoris mis à jour !")

    # ── Démarrage ────────────────────────────────
    try:
        bot.run(token)
    except Exception as e:
        print(f"[Discord Bot] ❌ Erreur critique : {e}")

if __name__ == "__main__":
    run_discord_bot()

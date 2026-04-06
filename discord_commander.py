import discord
from discord.ext import commands
import os
import asyncio
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
        embed.add_field(name="🆕 Démarrer", value="`!createprofile` — Crée ton profil utilisateur (assistant interactif)", inline=False)
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
    async def create_profile_wizard(ctx):
        user_id = str(ctx.author.id)
        
        # Vérifier si l'utilisateur a déjà un profil
        user = db.get_user(conn, user_id)
        if user:
            await ctx.send("✅ Tu as déjà un profil ! Utilise `!myconfig` pour le voir ou les commandes `!set...` pour le modifier. Le bot ne va pas te redemander tes informations une autre fois.")
            return

        # S'assurer qu'on peut lui envoyer un message privé
        try:
            if ctx.guild: # Si on est dans un serveur
                await ctx.author.send("👋 Bienvenue ! Je vais t'aider à créer ton profil VintedBot étape par étape.")
                await ctx.send(f"✅ {ctx.author.mention}, je t'ai envoyé un message privé pour configurer ton profil !")
        except discord.Forbidden:
            await ctx.send("❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres de confidentialité sur ce serveur d'abord !")
            return

        dm_channel = ctx.author.dm_channel
        if not dm_channel:
            dm_channel = await ctx.author.create_dm()

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == dm_channel.id

        async def ask(question, error_msg=None, validator=None):
            while True:
                await dm_channel.send(question)
                try:
                    msg = await bot.wait_for('message', check=check, timeout=300.0) # 5 minutes de timeout
                except asyncio.TimeoutError:
                    await dm_channel.send("⏱️ Temps écoulé. La création du profil a été annulée. Tape `!createprofile` pour recommencer.")
                    return None
                
                if msg.content.strip().lower() == "!cancel":
                    await dm_channel.send("❌ Création de profil annulée.")
                    return None
                
                response = msg.content.strip()
                if validator:
                    is_valid, validation_msg = validator(response)
                    if not is_valid:
                        await dm_channel.send(f"⚠️ {validation_msg}")
                        continue
                return response

        # --- Début de l'assistant ---
        await dm_channel.send("*(Tu peux taper `!cancel` à tout moment pour annuler la configuration)*")

        # 1. ID Unique
        def validate_id(val):
            if db.is_profile_id_used(conn, val):
                return False, "Cet ID unique est déjà pris par quelqu'un d'autre. Choisis-en un autre :"
            if len(val) < 3:
                return False, "L'ID doit faire au moins 3 caractères."
            if " " in val:
                return False, "L'ID ne doit pas contenir d'espaces."
            return True, ""
            
        profile_id = await ask("1️⃣ L'ID unique permet de t'identifier (pas d'espaces).\n**Veuillez entrer un ID unique pour ton profil :**", validator=validate_id)
        if profile_id is None: return

        # 2. Nom de profil
        profile_name = await ask("2️⃣ **Entrez le nom de votre profil (ex: 'Mes alertes Sneakers') :**")
        if profile_name is None: return

        # 3. URL Vinted
        def validate_url(val):
            if not val.startswith("http"):
                return False, "L'URL doit commencer par `http` ou `https`."
            if "vinted" not in val.lower():
                return False, "L'URL doit provenir du site Vinted."
            return True, ""
            
        search_url = await ask("3️⃣ **Entrez l'URL de recherche Vinted à surveiller (avec tes filtres) :**", validator=validate_url)
        if search_url is None: return

        # 4. Prix maximum
        def validate_price(val):
            try:
                p = float(val)
                if p < 0:
                    return False, "Le prix ne peut pas être négatif."
                return True, ""
            except ValueError:
                return False, "Veuillez entrer un nombre valide (ex: `50` ou `25.5`)."
                
        max_price_str = await ask("4️⃣ **Entrez le prix maximum pour les alertes (utilise '.' pour les décimales, 0 si pas de limite) :**", validator=validate_price)
        if max_price_str is None: return
        max_price = float(max_price_str)

        # 5. Message automatique
        auto_message = await ask("5️⃣ **Entrez le message automatique à envoyer aux vendeurs (quand tu cliques sur contacter) :**")
        if auto_message is None: return

        # 6. Webhook Discord
        def validate_webhook(val):
            if not val.startswith("https://discord.com/api/webhooks/"):
                return False, "L'URL doit commencer par `https://discord.com/api/webhooks/`"
            return True, ""
            
        webhook_url = await ask("6️⃣ **Entrez l'URL du webhook Discord pour recevoir les alertes :**", validator=validate_webhook)
        if webhook_url is None: return

        # 7. Intervalle de scan
        def validate_interval(val):
            try:
                i = int(val)
                if i < 60:
                    return False, "L'intervalle doit être d'au moins `60` secondes pour éviter le ban Vinted."
                return True, ""
            except ValueError:
                return False, "Veuillez entrer un nombre entier valide."
                
        scan_interval_str = await ask("7️⃣ **Entrez l'intervalle de scan en secondes (Minimum 60) :**", validator=validate_interval)
        if scan_interval_str is None: return
        scan_interval = int(scan_interval_str)

        # Sauvegarde
        db.create_profile(conn, user_id, profile_id, profile_name, search_url, max_price, auto_message, webhook_url, scan_interval)
        
        # Confirmation finale
        embed = discord.Embed(
            title="🎉 Votre profil a été créé avec succès !",
            description="Le bot est maintenant configuré et commencera à scanner cette URL.\nTu peux toujours modifier ces infos plus tard avec les commandes du bot.",
            color=0x57F287
        )
        embed.add_field(name="ID Unique", value=f"`{profile_id}`", inline=True)
        embed.add_field(name="Nom", value=f"**{profile_name}**", inline=True)
        embed.add_field(name="Prix Max", value=f"**{max_price}€**" if max_price > 0 else "Illimité", inline=True)
        embed.add_field(name="Intervalle", value=f"{scan_interval} sec", inline=True)
        
        url_text = search_url[:80] + "..." if len(search_url) > 80 else search_url
        embed.add_field(name="Recherche Vinted", value=f"[Lien de recherche]({search_url})\n`{url_text}`", inline=False)
        embed.add_field(name="Message Vendeur", value=f"```\n{auto_message}\n```", inline=False)
        
        await dm_channel.send(embed=embed)


    @bot.command(name="myconfig")
    async def my_config(ctx):
        user_id = str(ctx.author.id)
        user = db.get_user(conn, user_id)
        if not user:
            await ctx.send("❌ Tu n'as pas de profil. Utilise `!createprofile` d'abord.")
            return

        embed = discord.Embed(title="⚙️ Ta Configuration VintedBot", color=0x57F287, timestamp=datetime.now())
        embed.add_field(name="ID Profil / Nom", value=f"`{user.get('profile_id', 'N/A')}` / **{user.get('profile_name', 'N/A')}**", inline=False)
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

import discord
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import Modal, TextInput, View, Select, button
from datetime import datetime
import os
from flask import Flask
import threading

# ==============================================================================
# FLASK SERVER (Dla Render.com - zapobiega uśpieniu bota)
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Pieniążek Auto Bot jest online 24/7!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1503007115956977706               # ID Twojego serwera

# ROLOWE UPRAWNIENIA
ZARZAD_ROLE_ID = 1503151943688654958        # ID Roli Zarządu
PRACOWNIK_ROLE_ID = 1503009723543191782     # ID Roli Pracownika

# ID RÓL DLA SYSTEMU HR (AWANS / DEGRAD / ZWOLNIENIE)
GRADE1_ROLE_ID = 1547341972484661318        # Świeżak
GRADE2_ROLE_ID = 1547342288231862303        # Handlarz
GRADE3_ROLE_ID = 1548089007416545302        # Doświadczony
GRADE4_ROLE_ID = 1547342464963059885        # Specjalista
GRADE6_ROLE_ID = 1547340918389088296        # Kierownik
GRADE7_ROLE_ID = 1503009931589062727        # Manager
GRADE8_ROLE_ID = 1547339984992731146        # Co Owner

GRADES = [
    GRADE1_ROLE_ID, 
    GRADE2_ROLE_ID, 
    GRADE3_ROLE_ID, 
    GRADE4_ROLE_ID, 
    GRADE6_ROLE_ID, 
    GRADE7_ROLE_ID, 
    GRADE8_ROLE_ID
]
# ==============================================================================


# ==============================================================================
# HELPER FUNCTIONS (SPRAWDZANIE UPRAWNIEŃ)
# ==============================================================================
def is_zarzad(user: discord.Member) -> bool:
    return any(role.id == ZARZAD_ROLE_ID for role in user.roles) or user.guild_permissions.administrator

def is_pracownik(user: discord.Member) -> bool:
    return any(role.id == PRACOWNIK_ROLE_ID for role in user.roles) or is_zarzad(user)


# ==============================================================================
# SYSTEM MANDATÓW BCD (MENU WYBORU I EMBED)
# ==============================================================================
class MandatReasonSelect(Select):
    def __init__(self, ukarany: discord.Member, wystawiajacy: discord.Member):
        self.ukarany = ukarany
        self.wystawiajacy = wystawiajacy

        options = [
            discord.SelectOption(label="Wystawienie samochodów ponad limit", value="Wystawienie samochodów ponad limit*", description="Kwota: 10 000 000 USD", emoji="🚗"),
            discord.SelectOption(label="Strzelanie się na Terenie komisu", value="Strzelanie się na Terenie komisu", description="Kwota: 2 500 000 USD", emoji="🎯"),
            discord.SelectOption(label="Posiadanie nielegalnych przedmiotów", value="Posiadanie nielegalnych przedmiotów", description="Kwota: 2 500 000 USD", emoji="🔨"),
            discord.SelectOption(label="Brak kultury osobistej wobec klientów", value="Brak kultury osobistej wobec klientów", description="Kwota: 2 000 000 USD", emoji="👤"),
            discord.SelectOption(label="Brak kultury wobec inspektorów", value="Brak kultury wobec inspektorów", description="Kwota: 2 000 000 USD", emoji="🪪"),
            discord.SelectOption(label="Brak plakietki", value="Brak plakietki (nazwa komisu, imie i nazwisko)", description="Kwota: 1 000 000 USD", emoji="🏷️")
        ]
        super().__init__(placeholder="Wybierz powód nałożenia mandatu...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.wystawiajacy.id:
            await interaction.response.send_message("❌ Nie możesz używać tego menu!", ephemeral=True)
            return

        powod_wybrany = self.values[0]

        kwoty_mapa = {
            "Wystawienie samochodów ponad limit*": "10 000 000 USD",
            "Strzelanie się na Terenie komisu": "2 500 000 USD",
            "Posiadanie nielegalnych przedmiotów": "2 500 000 USD",
            "Brak kultury osobistej wobec klientów": "2 000 000 USD",
            "Brak kultury wobec inspektorów": "2 000 000 USD",
            "Brak plakietki (nazwa komisu, imie i nazwisko)": "1 000 000 USD"
        }

        kwota = kwoty_mapa.get(powod_wybrany, "Do ustalenia")

        embed = discord.Embed(
            title="⚖️ MANDAT BCD • KOMISY",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.set_author(name=f"💰 | {interaction.guild.name} | Komis | OsloRP", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_thumbnail(url=self.ukarany.display_avatar.url)
        embed.add_field(name="👤 Ukarany Pracownik", value=f"{self.ukarany.mention}\n`ID: {self.ukarany.id}`", inline=True)
        embed.add_field(name="👑 Wystawił", value=f"{self.wystawiajacy.mention}", inline=True)
        embed.add_field(name="📌 Powód Mandatu", value=f"```\n{powod_wybrany}\n```", inline=False)
        embed.add_field(name="💰 Kwota Do Zapłaty", value=f"```css\n[{kwota}]\n```", inline=False)
        embed.add_field(name="⏰ Czas na zapłatę", value="**24 godziny** od momentu wystawienia.", inline=False)
        embed.set_footer(text="System Mandatów BCD • Pieniążek Auto", icon_url=interaction.client.user.display_avatar.url if interaction.client.user else None)

        await interaction.response.edit_message(content="✅ Mandat został pomyślnie wystawiony na kanale!", view=None)
        await interaction.channel.send(content=f"{self.ukarany.mention}", embed=embed)


class MandatView(View):
    def __init__(self, ukarany: discord.Member, wystawiajacy: discord.Member):
        super().__init__(timeout=60)
        self.add_item(MandatReasonSelect(ukarany, wystawiajacy))


# ==============================================================================
# SYSTEM WYPOWIEDZEŃ
# ==============================================================================
class WypowiedzenieModal(Modal, title="📄 Wniosek o Wypowiedzenie"):
    stanowisko = TextInput(
        label="Obecne Stanowisko", 
        placeholder="np. Starszy Sprzedawca / Mechanik", 
        required=True,
        max_length=50
    )
    powod = TextInput(
        label="Powód Wypowiedzenia", 
        style=discord.TextStyle.paragraph, 
        placeholder="Opisz szczegółowo powód rezygnacji...", 
        required=True,
        min_length=10
    )

    async def on_submit(self, interaction: Interaction):
        embed = discord.Embed(
            title="✨ NOWE WYPOWIEDZENIE",
            description="Wpłynął nowy wniosek o rozwiązanie umowy. Oczekuje na weryfikację przez Zarząd.",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.add_field(name="👤 Pracownik", value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`", inline=True)
        embed.add_field(name="💼 Stanowisko", value=f"`{self.stanowisko.value}`", inline=True)
        embed.add_field(name="📝 Powód", value=f"```\n{self.powod.value}\n```", inline=False)
        embed.add_field(name="📊 Status Decyzji", value="⏳ **Oczekuje na rozpatrzenie**", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="System Wypowiedzi • Pieniążek Auto", icon_url=interaction.client.user.display_avatar.url if interaction.client.user else None)

        view = DecyzjaZarzaduView(target_member=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


class DecyzjaZarzaduView(View):
    def __init__(self, target_member: discord.Member):
        super().__init__(timeout=None)
        self.target_member = target_member

    @button(label="Zaakceptuj", style=ButtonStyle.success, custom_id="wyp_accept")
    async def zaakceptuj(self, interaction: Interaction, button: discord.ui.Button):
        if not is_zarzad(interaction.user):
            await interaction.response.send_message("❌ Nie posiadasz uprawnień Zarządu do podjęcia tej decyzji!", ephemeral=True)
            return

        roles_to_remove = [r for r in self.target_member.roles if r != interaction.guild.default_role]
        
        try:
            await self.target_member.remove_roles(*roles_to_remove)
            status_desc = f"✅ **Zatwierdzono przez {interaction.user.mention}**\n*Rangi pracownika zostały pomyślnie usunięte.*"
        except discord.Forbidden:
            status_desc = f"⚠️ **Zatwierdzono przez {interaction.user.mention}**\n*Bot nie ma uprawnień (rola bota musi być wyżej na liście ról)!*"

        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name="📊 Status Decyzji", value=status_desc, inline=False)
        embed.color = discord.Color.green()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="Odrzuć", style=ButtonStyle.danger, custom_id="wyp_reject")
    async def odrzuc(self, interaction: Interaction, button: discord.ui.Button):
        if not is_zarzad(interaction.user):
            await interaction.response.send_message("❌ Nie posiadasz uprawnień Zarządu do podjęcia tej decyzji!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name="📊 Status Decyzji", value=f"❌ **Odrzucono przez {interaction.user.mention}**", inline=False)
        embed.color = discord.Color.red()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


# ==============================================================================
# GŁÓWNA KLASA BOTA
# ==============================================================================
class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = MyClient()


# ==============================================================================
# KOMENDY SLASH Z UPRAWNIENIAMI
# ==============================================================================

@client.tree.command(name="wypowiedzenie", description="Złóż oficjalne wypowiedzenie ze stanowiska")
async def wypowiedzenie(interaction: Interaction):
    if not is_pracownik(interaction.user):
        await interaction.response.send_message("❌ Ta komenda jest dostępna tylko dla osób z rangą Pracownik!", ephemeral=True)
        return

    await interaction.response.send_modal(WypowiedzenieModal())


@client.tree.command(name="zarzadzaj", description="Panel zarządzania pracownikiem (Tylko dla Zarządu)")
@app_commands.choices(akcja=[
    app_commands.Choice(name="⬆️ Awans", value="awans"),
    app_commands.Choice(name="⬇️ Degradacja", value="degrad"),
    app_commands.Choice(name="🚫 Zwolnienie dyscyplinarne", value="zwolnienie")
])
async def zarzadzaj(interaction: Interaction, pracownik: discord.Member, akcja: app_commands.Choice[str], powod: str):
    if not is_zarzad(interaction.user):
        await interaction.response.send_message("❌ Nie posiadasz uprawnień Zarządu do użycia tej komendy!", ephemeral=True)
        return

    current_index = -1
    for i, role_id in enumerate(GRADES):
        if any(r.id == role_id for r in pracownik.roles):
            current_index = i
            break

    embed = discord.Embed(timestamp=datetime.now())
    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_thumbnail(url=pracownik.display_avatar.url)
    embed.add_field(name="👤 Pracownik", value=f"{pracownik.mention}\n`ID: {pracownik.id}`", inline=True)
    embed.add_field(name="👑 Wykonał", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="📝 Powód", value=f"```\n{powod}\n```", inline=False)
    embed.set_footer(text="System HR • Pieniążek Auto", icon_url=client.user.display_avatar.url if client.user else None)

    try:
        if akcja.value == "awans":
            if current_index == -1:
                new_role_id = GRADES[0]
            elif current_index < len(GRADES) - 1:
                new_role_id = GRADES[current_index + 1]
            else:
                await interaction.response.send_message("❌ Pracownik posiada już najwyższy możliwy stopień!", ephemeral=True)
                return

            old_roles = [r for r in pracownik.roles if r.id in GRADES]
            new_role = interaction.guild.get_role(new_role_id)
            
            if old_roles:
                await pracownik.remove_roles(*old_roles)
            if new_role:
                await pracownik.add_roles(new_role)

            embed.title = "📈 AWANS PRACOWNIKA"
            embed.color = discord.Color.gold()
            embed.add_field(name="💼 Nowe Stanowisko", value=f"{new_role.mention if new_role else 'Brak roli'}", inline=False)

        elif akcja.value == "degrad":
            if current_index > 0:
                new_role_id = GRADES[current_index - 1]
                old_roles = [r for r in pracownik.roles if r.id in GRADES]
                new_role = interaction.guild.get_role(new_role_id)

                if old_roles:
                    await pracownik.remove_roles(*old_roles)
                if new_role:
                    await pracownik.add_roles(new_role)

                embed.title = "📉 DEGRADACJA PRACOWNIKA"
                embed.color = discord.Color.orange()
                embed.add_field(name="💼 Nowe Stanowisko", value=f"{new_role.mention if new_role else 'Brak roli'}", inline=False)
            else:
                await interaction.response.send_message("❌ Pracownik nie posiada niższej rangi do degradacji!", ephemeral=True)
                return

        elif akcja.value == "zwolnienie":
            roles_to_remove = [r for r in pracownik.roles if r != interaction.guild.default_role]
            await pracownik.remove_roles(*roles_to_remove)

            embed.title = "🚫 ZWOLNIENIE PRACOWNIKA"
            embed.color = discord.Color.red()
            embed.add_field(name="📊 Status", value="*Wszystkie rangi zostały odebrane.*", inline=False)

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ **Brak uprawnień bota!** Przeciągnij rolę bota wyżej w Ustawieniach Serwera -> Role.",
            ephemeral=True
        )


@client.tree.command(name="raport", description="Zgłoś raport ze sprzedaży pojazdu")
async def raport(interaction: Interaction, kwota: str, dowod: discord.Attachment):
    if not is_pracownik(interaction.user):
        await interaction.response.send_message("❌ Ta komenda jest dostępna tylko dla osób z rangą Pracownik!", ephemeral=True)
        return

    ping_zarzad = f"<@&{ZARZAD_ROLE_ID}>"

    embed = discord.Embed(
        title="📝 RAPORT ZE SPRZEDAŻY",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.add_field(name="👤 Kto:", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="💰 Za ile sprzedano:", value=f"`{kwota}`", inline=False)
    embed.add_field(name="🔔 Powiadomienie:", value=ping_zarzad, inline=False)
    
    if dowod.content_type and "image" in dowod.content_type:
        embed.set_image(url=dowod.url)
        embed.add_field(name="🧾 Dowód sprzedaży:", value="*Załączono w zdjęciu poniżej*", inline=False)
    else:
        embed.add_field(name="🧾 Dowód sprzedaży:", value=f"[Otwórz załącznik]({dowod.url})", inline=False)

    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="System Raportów • Pieniążek Auto", icon_url=client.user.display_avatar.url if client.user else None)

    mentions = discord.AllowedMentions(roles=True)

    await interaction.response.send_message(
        content=ping_zarzad, 
        embed=embed, 
        allowed_mentions=mentions
    )


@client.tree.command(name="mandat", description="Wystaw mandat pracownikowi (Tylko dla Zarządu)")
async def mandat(interaction: Interaction, pracownik: discord.Member):
    if not is_zarzad(interaction.user):
        await interaction.response.send_message("❌ Nie posiadasz uprawnień Zarządu do użycia tej komendy!", ephemeral=True)
        return

    view = MandatView(ukarany=pracownik, wystawiajacy=interaction.user)
    await interaction.response.send_message(
        f"⚙️ Wybierz powód mandatu BCD dla pracownika {pracownik.mention}:", 
        view=view, 
        ephemeral=True
    )


# ==============================================================================
# URUCHOMIENIE BOTA ORAZ SERWERA FLASK
# ==============================================================================
@client.event
async def on_ready():
    print(f"✅ Bot działa! Zalogowano jako: {client.user}")

if __name__ == "__main__":
    if TOKEN is None:
        print("❌ BŁĄD: Brak zmiennej środowiskowej DISCORD_TOKEN! Ustaw ją w panelu Render.")
    else:
        # Uruchomienie mikroserwera Flask w tle na porcie z Render.com
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Uruchomienie bota Discord w głównym wątku
        client.run(TOKEN)

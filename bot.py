from datetime import datetime
import os
import threading
import discord
from discord import ButtonStyle, Interaction, app_commands
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View, button
from flask import Flask

# ==============================================================================
# FLASK SERVER (Dla Render.com - zapobiega uśpieniu bota)
# ==============================================================================
app = Flask(__name__)


@app.route("/")
def home():
  return "Pieniążek Auto Bot jest online 24/7!"


def run_flask():
  port = int(os.getenv("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1503007115956977706  # ID Twojego serwera

# ROLOWE UPRAWNIENIA
ZARZAD_ROLE_ID = 1503151943688654958  # ID Roli Zarządu
PRACOWNIK_ROLE_ID = 1503009723543191782  # ID Roli Pracownika

# ID RÓL DLA SYSTEMU HR (AWANS / DEGRAD / ZWOLNIENIE)
GRADE1_ROLE_ID = 1547341972484661318  # Świeżak
GRADE2_ROLE_ID = 1547342288231862303  # Handlarz
GRADE3_ROLE_ID = 1548089007416545302  # Doświadczony
GRADE4_ROLE_ID = 1547342464963059885  # Specjalista
GRADE6_ROLE_ID = 1547340918389088296  # Kierownik
GRADE7_ROLE_ID = 1503009931589062727  # Manager
GRADE8_ROLE_ID = 1547339984992731146  # Co Owner

GRADES = [
    GRADE1_ROLE_ID,
    GRADE2_ROLE_ID,
    GRADE3_ROLE_ID,
    GRADE4_ROLE_ID,
    GRADE6_ROLE_ID,
    GRADE7_ROLE_ID,
    GRADE8_ROLE_ID,
]

# KONFIGURACJA WERYFIKACJI I KANAŁÓW POWITALNYCH
VERIFY_ROLE_ID = 1503009366985408553
WELCOME_CHANNEL_ID = 1503013291197202432

# URL grafiki powitalnej (baner na dole embeda)
WELCOME_IMAGE_URL = (
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70"  # Podmień na link do swojego banera
)


# ==============================================================================
# HELPER FUNCTIONS (SPRAWDZANIE UPRAWNIEŃ)
# ==============================================================================
def is_zarzad(user: discord.Member) -> bool:
  return (
      any(role.id == ZARZAD_ROLE_ID for role in user.roles)
      or user.guild_permissions.administrator
  )


def is_pracownik(user: discord.Member) -> bool:
  return any(
      role.id == PRACOWNIK_ROLE_ID for role in user.roles
  ) or is_zarzad(user)


# ==============================================================================
# MODAL DO USTAWIANIA DANYCH IC
# ==============================================================================
class UstawDaneModal(Modal, title="Ustaw dane IC"):
  imie_nazwisko = TextInput(
      label="Imię i Nazwisko IC",
      placeholder="np. Xavier Pieniążek",
      required=True,
      max_length=32,
  )

  async def on_submit(self, interaction: Interaction):
    nowy_nick = self.imie_nazwisko.value
    try:
      await interaction.user.edit(nick=nowy_nick)
      await interaction.response.send_message(
          f"✅ Twoje dane zostały zaktualizowane na: **{nowy_nick}**",
          ephemeral=True,
      )
    except discord.Forbidden:
      await interaction.response.send_message(
          "❌ Bot nie ma uprawnień do zmiany Twojego pseudonimu (Twoja rola"
          " jest wyżej niż rola bota w ustawieniach ról).",
          ephemeral=True,
      )


# ==============================================================================
# SYSTEM MANDATÓW BCD
# ==============================================================================
class MandatReasonSelect(Select):

  def __init__(self, ukarany: discord.Member, wystawiajacy: discord.Member):
    self.ukarany = ukarany
    self.wystawiajacy = wystawiajacy

    options = [
        discord.SelectOption(
            label="Wystawienie samochodów ponad limit",
            value="Wystawienie samochodów ponad limit*",
            description="Kwota: 10 000 000 USD",
            emoji="🚗",
        ),
        discord.SelectOption(
            label="Strzelanie się na Terenie komisu",
            value="Strzelanie się na Terenie komisu",
            description="Kwota: 2 500 000 USD",
            emoji="🎯",
        ),
        discord.SelectOption(
            label="Posiadanie nielegalnych przedmiotów",
            value="Posiadanie nielegalnych przedmiotów",
            description="Kwota: 2 500 000 USD",
            emoji="🔨",
        ),
        discord.SelectOption(
            label="Brak kultury osobistej wobec klientów",
            value="Brak kultury osobistej wobec klientów",
            description="Kwota: 2 000 000 USD",
            emoji="👤",
        ),
        discord.SelectOption(
            label="Brak kultury wobec inspektorów",
            value="Brak kultury wobec inspektorów",
            description="Kwota: 2 000 000 USD",
            emoji="🪪",
        ),
        discord.SelectOption(
            label="Brak plakietki",
            value="Brak plakietki (nazwa komisu, imie i nazwisko)",
            description="Kwota: 1 000 000 USD",
            emoji="🏷️",
        ),
    ]
    super().__init__(
        placeholder="Wybierz powód nałożenia mandatu...",
        min_values=1,
        max_values=1,
        options=options,
    )

  async def callback(self, interaction: Interaction):
    if interaction.user.id != self.wystawiajacy.id:
      await interaction.response.send_message(
          "❌ Nie możesz używać tego menu!", ephemeral=True
      )
      return

    powod_wybrany = self.values[0]
    kwoty_mapa = {
        "Wystawienie samochodów ponad limit*": "10 000 000 USD",
        "Strzelanie się na Terenie komisu": "2 500 000 USD",
        "Posiadanie nielegalnych przedmiotów": "2 500 000 USD",
        "Brak kultury osobistej wobec klientów": "2 000 000 USD",
        "Brak kultury wobec inspektorów": "2 000 000 USD",
        "Brak plakietki (nazwa komisu, imie i nazwisko)": "1 000 000 USD",
    }
    kwota = kwoty_mapa.get(powod_wybrany, "Do ustalenia")

    embed = discord.Embed(
        title="⚖️ MANDAT BCD • KOMISY",
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_author(
        name=f"💰 | {interaction.guild.name} | Komis | OsloRP",
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )
    embed.set_thumbnail(url=self.ukarany.display_avatar.url)
    embed.add_field(
        name="👤 Ukarany Pracownik",
        value=f"{self.ukarany.mention}\n`ID: {self.ukarany.id}`",
        inline=True,
    )
    embed.add_field(
        name="👑 Wystawił", value=f"{self.wystawiajacy.mention}", inline=True
    )
    embed.add_field(
        name="📌 Powód Mandatu",
        value=f"```\n{powod_wybrany}\n```",
        inline=False,
    )
    embed.add_field(
        name="💰 Kwota Do Zapłaty",
        value=f"```css\n[{kwota}]\n```",
        inline=False,
    )
    embed.add_field(
        name="⏰ Czas na zapłatę",
        value="**24 godziny** od momentu wystawienia.",
        inline=False,
    )
    embed.set_footer(
        text="System Mandatów BCD • Pieniążek Auto",
        icon_url=(
            interaction.client.user.display_avatar.url
            if interaction.client.user
            else None
        ),
    )

    await interaction.response.edit_message(
        content="✅ Mandat został pomyślnie wystawiony na kanale!", view=None
    )
    await interaction.channel.send(
        content=f"{self.ukarany.mention}", embed=embed
    )


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
      max_length=50,
  )
  powod = TextInput(
      label="Powód Wypowiedzenia",
      style=discord.TextStyle.paragraph,
      placeholder="Opisz szczegółowo powód rezygnacji...",
      required=True,
      min_length=10,
  )

  async def on_submit(self, interaction: Interaction):
    embed = discord.Embed(
        title="✨ NOWE WYPOWIEDZENIE",
        description=(
            "Wpłynął nowy wniosek o rozwiązanie umowy. Oczekuje na weryfikację"
            " przez Zarząd."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_author(
        name=interaction.guild.name,
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )
    embed.add_field(
        name="👤 Pracownik",
        value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`",
        inline=True,
    )
    embed.add_field(
        name="💼 Stanowisko", value=f"{self.stanowisko.value}", inline=True
    )
    embed.add_field(
        name="📝 Powód", value=f"```\n{self.powod.value}\n```", inline=False
    )
    embed.add_field(
        name="📊 Status Decyzji",
        value="⏳ **Oczekuje na rozpatrzenie**",
        inline=False,
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(
        text="System Wypowiedzi • Pieniążek Auto",
        icon_url=(
            interaction.client.user.display_avatar.url
            if interaction.client.user
            else None
        ),
    )

    view = DecyzjaZarzaduView(target_member=interaction.user)
    await interaction.response.send_message(embed=embed, view=view)


class DecyzjaZarzaduView(View):

  def __init__(self, target_member: discord.Member):
    super().__init__(timeout=None)
    self.target_member = target_member

  @button(
      label="Zaakceptuj", style=ButtonStyle.success, custom_id="wyp_accept"
  )
  async def zaakceptuj(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    if not is_zarzad(interaction.user):
      await interaction.response.send_message(
          "❌ Nie posiadasz uprawnień Zarządu do podjęcia tej decyzji!",
          ephemeral=True,
      )
      return

    roles_to_remove = [
        r
        for r in self.target_member.roles
        if r != interaction.guild.default_role
    ]
    try:
      await self.target_member.remove_roles(*roles_to_remove)
      status_desc = (
          f"✅ **Zatwierdzono przez {interaction.user.mention}**\n*Rangi"
          " pracownika zostały pomyślnie usunięte.*"
      )
    except discord.Forbidden:
      status_desc = (
          f"⚠️ **Zatwierdzono przez {interaction.user.mention}**\n*Bot nie ma"
          " uprawnień do odebrania ról!*"
      )

    embed = interaction.message.embeds[0]
    embed.set_field_at(
        3, name="📊 Status Decyzji", value=status_desc, inline=False
    )
    embed.color = discord.Color.green()

    for child in self.children:
      child.disabled = True

    await interaction.response.edit_message(embed=embed, view=self)

  @button(label="Odrzuć", style=ButtonStyle.danger, custom_id="wyp_reject")
  async def odrzuc(self, interaction: Interaction, button: discord.ui.Button):
    if not is_zarzad(interaction.user):
      await interaction.response.send_message(
          "❌ Nie posiadasz uprawnień Zarządu do podjęcia tej decyzji!",
          ephemeral=True,
      )
      return

    embed = interaction.message.embeds[0]
    embed.set_field_at(
        3,
        name="📊 Status Decyzji",
        value=f"❌ **Odrzucono przez {interaction.user.mention}**",
        inline=False,
    )
    embed.color = discord.Color.red()

    for child in self.children:
      child.disabled = True

    await interaction.response.edit_message(embed=embed, view=self)


# ==============================================================================
# GŁÓWNY WIDOK POWITALNY (ZE SCREENA: Weryfikacja, Ustaw dane, Kontakt, Podanie)
# ==============================================================================
class WelcomeTicketView(View):

  def __init__(self):
    super().__init__(timeout=None)

  # Rząd 1: Przycisk weryfikacji / statusu Gościa
  @button(
      label="Gość",
      style=ButtonStyle.secondary,
      custom_id="status_gosc_btn",
      emoji="👤",
      disabled=True,
  )
  async def status_gosc(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    pass

  # Rząd 1: Przycisk ustawiania danych IC (otwierający okienko Modal)
  @button(
      label="Ustaw dane",
      style=ButtonStyle.secondary,
      custom_id="ustaw_dane_modal_btn",
      emoji="✏️",
  )
  async def ustaw_dane(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(UstawDaneModal())

  # Rząd 1 / 2: Przycisk Linku do Kontaktu
  @button(
      label="Kontakt",
      style=ButtonStyle.link,
      url="https://discord.com",  # Podmień na link do kanału kontaktowego
      emoji="🗂️",
  )
  async def kontakt_link(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    pass

  # Rząd 2: Przycisk Podania o pracę (Tworzy prywatny ticket)
  @button(
      label="Podanie o pracę",
      style=ButtonStyle.blurple,
      custom_id="ticket_job_btn",
      emoji="📄",
  )
  async def ticket_job(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(
        interaction, "podanie", "📄 ⟡ 𝐏𝐨𝐝𝐚𝐧𝐢𝐚", "Podanie o pracę"
    )

  # Rząd 2: Przycisk Pomocy / Zarządu (Tworzy prywatny ticket)
  @button(
      label="Pomoc / Zarząd",
      style=ButtonStyle.gray,
      custom_id="ticket_help_btn",
      emoji="🛠️",
  )
  async def ticket_help(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(
        interaction, "pomoc", "👑 ⟡ 𝐒𝐭𝐫𝐞𝐟𝐚 𝐙𝐚𝐫𝐳𝐚𝐝𝐮", "Pomoc / Support OOC"
    )

  async def create_ticket(
      self,
      interaction: Interaction,
      ticket_type: str,
      category_name: str,
      topic_desc: str,
  ):
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
    }

    category = discord.utils.get(guild.categories, name=category_name)
    channel_name = f"{ticket_type}-{interaction.user.name}"
    ticket_channel = await guild.create_text_channel(
        name=channel_name, overwrites=overwrites, category=category
    )

    close_view = TicketCloseView()
    embed = discord.Embed(
        title=f"Ticket: {topic_desc}",
        description=(
            f"Witaj {interaction.user.mention}!\nOpisz szczegółowo swoją sprawę"
            " lub zawrzyj informacje dotyczące podania. Zarząd wkrótce się z"
            " Tobą skontaktuje."
        ),
        color=discord.Color.gold(),
    )

    await ticket_channel.send(
        content=f"{interaction.user.mention}", embed=embed, view=close_view
    )
    await interaction.response.send_message(
        f"Utworzono dla Ciebie ticket: {ticket_channel.mention}", ephemeral=True
    )


class TicketCloseView(View):

  def __init__(self):
    super().__init__(timeout=None)

  @button(
      label="Zamknij ticket",
      style=ButtonStyle.red,
      custom_id="close_ticket",
      emoji="🔒",
  )
  async def close_ticket(
      self, interaction: Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message("Zamykanie kanału za 3 sekundy...")
    import asyncio

    await asyncio.sleep(3)
    await interaction.channel.delete()


# ==============================================================================
# GŁÓWNA KLASA BOTA
# ==============================================================================
class MyClient(discord.Client):

  def __init__(self):
    super().__init__(intents=discord.Intents.all())
    self.tree = app_commands.CommandTree(self)

  async def setup_hook(self):
    self.add_view(WelcomeTicketView())
    self.add_view(TicketCloseView())

    guild = discord.Object(id=GUILD_ID)
    self.tree.copy_global_to(guild=guild)
    await self.tree.sync(guild=guild)


client = MyClient()


# ==============================================================================
# ZDARZENIA BOTA (EVENTS)
# ==============================================================================
@client.event
async def on_ready():
  print(f"✅ Bot działa! Zalogowano jako: {client.user}")


@client.event
async def on_member_join(member: discord.Member):
  channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
  if channel:
    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
        description=(
            f"Siema {member.mention}! 🥂\n\n"
            "> Właśnie przekroczyłeś próg\n"
            "> najchętniej wybieranego komisu w\n"
            "> mieście.\n\n"
            "Ustaw swoje dane IC i baw się dobrze!"
        ),
        color=discord.Color.gold(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url=WELCOME_IMAGE_URL)
    embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

    await channel.send(embed=embed, view=WelcomeTicketView())


# ==============================================================================
# KOMENDY SLASH Z UPRAWNIENIAMI
# ==============================================================================
@client.tree.command(
    name="setup_panel",
    description="Wysłanie panelu powitalnego z przyciskami na kanał",
)
async def setup_panel(interaction: Interaction):
  if not is_zarzad(interaction.user):
    await interaction.response.send_message(
        "❌ Brak uprawnień Zarządu!", ephemeral=True
    )
    return

  embed = discord.Embed(
      title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
      description=(
          "Witamy na oficjalnym serwerze komisu!\n\n"
          "> Kliknij przycisk **'Ustaw dane'**, aby zmienić nick na swoje imię"
          " i nazwisko IC.\n"
          "> Skorzystaj z przycisków poniżej, aby złożyć podanie lub uzyskać"
          " pomoc."
      ),
      color=discord.Color.gold(),
  )
  embed.set_image(url=WELCOME_IMAGE_URL)
  embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

  await interaction.channel.send(embed=embed, view=WelcomeTicketView())
  await interaction.response.send_message(
      "✅ Panel został wysłany!", ephemeral=True
  )


@client.tree.command(
    name="testjoin",
    description="Testuje powitanie dla wybranego użytkownika (Tylko dla Zarządu)",
)
async def testjoin(interaction: Interaction, member: discord.Member):
  if not is_zarzad(interaction.user):
    await interaction.response.send_message(
        "❌ Brak uprawnień Zarządu!", ephemeral=True
    )
    return

  channel = interaction.guild.get_channel(WELCOME_CHANNEL_ID)
  if not channel:
    await interaction.response.send_message(
        "❌ Nie znaleziono kanału powitalnego!", ephemeral=True
    )
    return

  embed = discord.Embed(
      title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
      description=(
          f"Siema {member.mention}! 🥂\n\n"
          "> Właśnie przekroczyłeś próg\n"
          "> najchętniej wybieranego komisu w\n"
          "> mieście.\n\n"
          "Ustaw swoje dane IC i baw się dobrze!"
      ),
      color=discord.Color.gold(),
  )
  embed.set_thumbnail(url=member.display_avatar.url)
  embed.set_image(url=WELCOME_IMAGE_URL)
  embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

  await channel.send(embed=embed, view=WelcomeTicketView())
  await interaction.response.send_message(
      f"✅ Wysłano testowe powitanie dla {member.mention}!", ephemeral=True
  )


@client.tree.command(
    name="wypowiedzenie", description="Złóż oficjalne wypowiedzenie ze stanowiska"
)
async def wypowiedzenie(interaction: Interaction):
  if not is_pracownik(interaction.user):
    await interaction.response.send_message(
        "❌ Dostępne tylko dla pracowników!", ephemeral=True
    )
    return
  await interaction.response.send_modal(WypowiedzenieModal())


@client.tree.command(
    name="raport", description="Zgłoś raport ze sprzedaży pojazdu"
)
async def raport(
    interaction: Interaction, kwota: str, dowod: discord.Attachment
):
  if not is_pracownik(interaction.user):
    await interaction.response.send_message(
        "❌ Dostępne tylko dla pracowników!", ephemeral=True
    )
    return

  ping_zarzad = f"<@&{ZARZAD_ROLE_ID}>"
  embed = discord.Embed(
      title="📝 RAPORT ZE SPRZEDAŻY",
      color=discord.Color.gold(),
      timestamp=datetime.now(),
  )
  embed.add_field(
      name="👤 Kto:", value=f"{interaction.user.mention}", inline=False
  )
  embed.add_field(name="💰 Za ile sprzedano:", value=f"`{kwota}`", inline=False)
  if dowod.content_type and "image" in dowod.content_type:
    embed.set_image(url=dowod.url)

  await interaction.response.send_message(
      content=ping_zarzad,
      embed=embed,
      allowed_mentions=discord.AllowedMentions(roles=True),
  )


@client.tree.command(
    name="mandat", description="Wystaw mandat pracownikowi (Tylko dla Zarządu)"
)
async def mandat(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    await interaction.response.send_message(
        "❌ Brak uprawnień Zarządu!", ephemeral=True
    )
    return
  view = MandatView(ukarany=pracownik, wystawiajacy=interaction.user)
  await interaction.response.send_message(
      f"⚙️ Wybierz powód mandatu dla pracownika {pracownik.mention}:",
      view=view,
      ephemeral=True,
  )


# ==============================================================================
# URUCHOMIENIE BOTA
# ==============================================================================
if __name__ == "__main__":
  if TOKEN is None:
    print("❌ BŁĄD: Brak zmiennej DISCORD_TOKEN!")
  else:
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    client.run(TOKEN)

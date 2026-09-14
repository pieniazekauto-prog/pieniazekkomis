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

# ID RÓL DLA SYSTEMU HR (OD NAJNIŻSZEJ DO NAJWYŻSZEJ)
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

GRADE_NAMES = {
    GRADE1_ROLE_ID: "Świeżak",
    GRADE2_ROLE_ID: "Handlarz",
    GRADE3_ROLE_ID: "Doświadczony",
    GRADE4_ROLE_ID: "Specjalista",
    GRADE6_ROLE_ID: "Kierownik",
    GRADE7_ROLE_ID: "Manager",
    GRADE8_ROLE_ID: "Co Owner",
}

WELCOME_CHANNEL_ID = 1503013291197202432
WELCOME_IMAGE_URL = "https://raw.githubusercontent.com/twoje-repo/twoja-sciezka/main/image_7.png"


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


def get_current_grade_index(member: discord.Member) -> int:
  highest_index = -1
  for i, g_id in enumerate(GRADES):
    if any(r.id == g_id for r in member.roles):
      highest_index = i
  return highest_index


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
          "❌ Bot nie ma uprawnień do zmiany Twojego pseudonimu.", ephemeral=True
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
    embed.set_footer(text="System Mandatów BCD • Pieniążek Auto")

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
# AUTOMATYCZNY SYSTEM ZARZĄDZANIA KADRAMI (/ZARZĄDZAJ)
# ==============================================================================
class ZarzadzajSelect(Select):

  def __init__(self, target_member: discord.Member):
    self.target_member = target_member
    options = [
        discord.SelectOption(
            label="📈 Awans",
            value="awans",
            description="Automatycznie awansuj pracownika o 1 rangę wyżej",
            emoji="🟢",
        ),
        discord.SelectOption(
            label="📉 Degrad",
            value="degrad",
            description="Automatycznie degraduj pracownika o 1 rangę niżej",
            emoji="🟠",
        ),
        discord.SelectOption(
            label="❌ Zwolnienie",
            value="zwolnienie",
            description="Natychmiastowo zwolnij pracownika (odeberz rangi)",
            emoji="🔴",
        ),
    ]
    super().__init__(
        placeholder="Wybierz akcję zarządzania pracownikiem...",
        min_values=1,
        max_values=1,
        options=options,
    )

  async def callback(self, interaction: Interaction):
    akcja = self.values[0]
    guild = interaction.guild
    current_index = get_current_grade_index(self.target_member)

    if akcja == "zwolnienie":
      roles_to_remove = [r for r in self.target_member.roles if r.id in GRADES]
      try:
        if roles_to_remove:
          await self.target_member.remove_roles(*roles_to_remove)
        await interaction.response.edit_message(
            content=(
                f"❌ Pracownik {self.target_member.mention} został zwolniony i"
                " odebrano mu rangi pracownicze."
            ),
            view=None,
        )
      except discord.Forbidden:
        await interaction.response.edit_message(
            content="⚠️ Bot nie ma uprawnień do edycji ról tego użytkownika!",
            view=None,
        )
      return

    if current_index == -1:
      await interaction.response.edit_message(
          content=(
              f"❌ Użytkownik {self.target_member.mention} nie posiada żadnej"
              " oficjalnej rangi pracowniczej!"
          ),
          view=None,
      )
      return

    if akcja == "awans":
      if current_index + 1 >= len(GRADES):
        await interaction.response.edit_message(
            content=(
                f"⚠️ Pracownik {self.target_member.mention} posiada już"
                " **najwyższą** możliwą rangę!"
            ),
            view=None,
        )
        return
      new_role_id = GRADES[current_index + 1]
    else:
      if current_index - 1 < 0:
        await interaction.response.edit_message(
            content=(
                f"⚠️ Pracownik {self.target_member.mention} posiada już"
                " **najniższą** możliwą rangę!"
            ),
            view=None,
        )
        return
      new_role_id = GRADES[current_index - 1]

    new_role = guild.get_role(new_role_id)
    if not new_role:
      await interaction.response.edit_message(
          content="❌ Nie znaleziono docelowej rangi na serwerze!", view=None
      )
      return

    old_roles_to_remove = [
        r for r in self.target_member.roles if r.id in GRADES
    ]

    try:
      if old_roles_to_remove:
        await self.target_member.remove_roles(*old_roles_to_remove)
      await self.target_member.add_roles(new_role)

      komunikat_akcji = (
          "Awansowano" if akcja == "awans" else "Zdegradowano"
      )
      await interaction.response.edit_message(
          content=(
              f"✅ {komunikat_akcji} pracownika {self.target_member.mention} na"
              f" nowe stanowisko: **{new_role.name}**."
          ),
          view=None,
      )
    except discord.Forbidden:
      await interaction.response.edit_message(
          content="⚠️ Bot nie ma uprawnień do zmiany ról tego użytkownika!",
          view=None,
      )


class ZarzadzajView(View):

  def __init__(self, target_member: discord.Member):
    super().__init__(timeout=60)
    self.add_item(ZarzadzajSelect(target_member))


# ==============================================================================
# SYSTEM WYPOWIEDZEŃ
# ==============================================================================
class WypowiedzenieModal(Modal, title="📄 Wniosek o Wypowiedzenie"):
  stanowisko = TextInput(
      label="Obecne Stanowisko", placeholder="np. Handlarz", required=True
  )
  powod = TextInput(
      label="Powód Wypowiedzenia",
      style=discord.TextStyle.paragraph,
      required=True,
  )

  async def on_submit(self, interaction: Interaction):
    embed = discord.Embed(
        title="✨ NOWE WYPOWIEDZENIE", color=discord.Color.gold()
    )
    embed.add_field(name="👤 Pracownik", value=f"{interaction.user.mention}")
    embed.add_field(name="💼 Stanowisko", value=f"{self.stanowisko.value}")
    embed.add_field(
        name="📝 Powód", value=f"```\n{self.powod.value}\n```", inline=False
    )
    embed.add_field(
        name="📊 Status Decyzji",
        value="⏳ **Oczekuje na rozpatrzenie**",
        inline=False,
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
  async def zaakceptuj(self, interaction: Interaction, button: Button):
    if not is_zarzad(interaction.user):
      return await interaction.response.send_message(
          "❌ Brak uprawnień!", ephemeral=True
      )
    roles_to_remove = [
        r
        for r in self.target_member.roles
        if r != interaction.guild.default_role
    ]
    try:
      await self.target_member.remove_roles(*roles_to_remove)
    except:
      pass
    embed = interaction.message.embeds[0]
    embed.set_field_at(
        3,
        name="📊 Status Decyzji",
        value=f"✅ **Zatwierdzono przez {interaction.user.mention}**",
        inline=False,
    )
    embed.color = discord.Color.green()
    for child in self.children:
      child.disabled = True
    await interaction.response.edit_message(embed=embed, view=self)

  @button(label="Odrzuć", style=ButtonStyle.danger, custom_id="wyp_reject")
  async def odrzuc(self, interaction: Interaction, button: Button):
    if not is_zarzad(interaction.user):
      return await interaction.response.send_message(
          "❌ Brak uprawnień!", ephemeral=True
      )
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
# GŁÓWNY WIDOK POWITALNY I TICKETÓW (PRZYWRÓCONE DWA PRZYCISKI!)
# ==============================================================================
class WelcomeTicketView(View):

  def __init__(self):
    super().__init__(timeout=None)

  @button(
      label="Ustaw dane",
      style=ButtonStyle.blurple,
      custom_id="set_data_btn",
      emoji="✏️",
  )
  async def set_data(self, interaction: Interaction, button: Button):
    await interaction.response.send_modal(UstawDaneModal())

  @button(
      label="Podanie o pracę",
      style=ButtonStyle.blurple,
      custom_id="ticket_podanie_btn",
      emoji="📄",
  )
  async def ticket_podanie(self, interaction: Interaction, button: Button):
    await self.create_ticket(
        interaction, "podanie", "👑 ⟡ 𝐒𝐭𝐫𝐞𝐟𝐚 𝐙𝐚𝐫𝐳𝐚𝐝𝐮", "Podanie o Pracę"
    )

  @button(
      label="Pomoc / Zarząd",
      style=ButtonStyle.blurple,
      custom_id="ticket_help_btn",
      emoji="🛠️",
  )
  async def ticket_help(self, interaction: Interaction, button: Button):
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
            f"Witaj {interaction.user.mention}!\nOpisz szczegółowo swoją sprawę."
        ),
        color=discord.Color.gold(),
    )

    await ticket_channel.send(
        content=f"{interaction.user.mention}", embed=embed, view=close_view
    )
    await interaction.response.send_message(
        f"Utworzono dla Ciebie ticket: {ticket_channel.mention}", ephemeral=True
    )


class TicketCloseConfirmView(View):

  def __init__(self):
    super().__init__(timeout=60)

  @button(
      label="Potwierdź zamknięcie", style=ButtonStyle.red, custom_id="conf_close"
  )
  async def confirm_close(self, interaction: Interaction, button: Button):
    if not is_zarzad(interaction.user):
      return await interaction.response.send_message(
          "❌ Tylko Zarząd może usunąć ten ticket!", ephemeral=True
      )
    await interaction.response.send_message(
        "🔒 Usuwanie kanału za 3 sekundy..."
    )
    import asyncio

    await asyncio.sleep(3)
    await interaction.channel.delete()

  @button(label="Anuluj", style=ButtonStyle.secondary, custom_id="canc_close")
  async def cancel_close(self, interaction: Interaction, button: Button):
    await interaction.message.delete()
    await interaction.response.send_message(
        "✅ Anulowano.", ephemeral=True
    )


class TicketCloseView(View):

  def __init__(self):
    super().__init__(timeout=None)

  @button(
      label="Zamknij ticket", style=ButtonStyle.red, custom_id="close_tckt"
  )
  async def close_ticket(self, interaction: Interaction, button: Button):
    await interaction.response.send_message(
        "⚠️ Czy na pewno chcesz zamknąć ten ticket?",
        view=TicketCloseConfirmView(),
        ephemeral=True,
    )


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


@client.event
async def on_ready():
  print(f"✅ Bot działa! Zalogowano jako: {client.user}")


# ==============================================================================
# KOMENDY SLASH
# ==============================================================================
@client.tree.command(name="setup_panel", description="Wysyła panel z przyciskami")
async def setup_panel(interaction: Interaction):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )

  embed = discord.Embed(
      title="👑 ⟡ STREFA ZARZĄDU • POMOC I WSPARCIE",
      description=(
          "Wybierz odpowiedni przycisk poniżej, aby ustawić swoje dane IC,"
          " złożyć podanie lub skontaktować się z Zarządem."
      ),
      color=discord.Color.gold(),
  )
  await interaction.channel.send(embed=embed, view=WelcomeTicketView())
  await interaction.response.send_message("✅ Wysłano panel!", ephemeral=True)


@client.tree.command(name="testjoin", description="Testuje powitanie")
async def testjoin(interaction: Interaction, member: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )

  channel = interaction.guild.get_channel(WELCOME_CHANNEL_ID)
  if not channel:
    return await interaction.response.send_message(
        "❌ Brak kanału powitalnego!", ephemeral=True
    )

  embed = discord.Embed(
      title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
      description=(
          f"Siema {member.mention}! 🥂\n\n> Właśnie przekroczyłeś próg\n>"
          " najchętniej wybieranego komisu w\n> mieście.\n\nUstaw swoje dane"
          " IC i baw się dobrze!"
      ),
      color=discord.Color.gold(),
  )
  embed.set_thumbnail(url=member.display_avatar.url)
  embed.set_image(url=WELCOME_IMAGE_URL)
  embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

  await channel.send(embed=embed, view=WelcomeTicketView())
  await interaction.response.send_message(
      f"✅ Wysłano powitanie dla {member.mention}!", ephemeral=True
  )


@client.tree.command(name="zarzadzaj", description="Zarządzaj rangami pracownika")
async def zarzadzaj(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )
  await interaction.response.send_message(
      f"⚙️ Wybierz akcję dla {pracownik.mention}:",
      view=ZarzadzajView(pracownik),
      ephemeral=True,
  )


@client.tree.command(name="wypowiedzenie", description="Złóż wypowiedzenie")
async def wypowiedzenie(interaction: Interaction):
  if not is_pracownik(interaction.user):
    return await interaction.response.send_message(
        "❌ Tylko dla pracowników!", ephemeral=True
    )
  await interaction.response.send_modal(WypowiedzenieModal())


@client.tree.command(name="raport", description="Raport ze sprzedaży")
async def raport(
    interaction: Interaction, kwota: str, dowod: discord.Attachment
):
  if not is_pracownik(interaction.user):
    return await interaction.response.send_message(
        "❌ Tylko dla pracowników!", ephemeral=True
    )
  embed = discord.Embed(
      title="📝 RAPORT ZE SPRZEDAŻY",
      color=discord.Color.gold(),
      timestamp=datetime.now(),
  )
  embed.add_field(name="👤 Kto:", value=f"{interaction.user.mention}")
  embed.add_field(name="💰 Za ile:", value=f"`{kwota}`")
  if dowod.content_type and "image" in dowod.content_type:
    embed.set_image(url=dowod.url)
  await interaction.response.send_message(
      content=f"<@&{ZARZAD_ROLE_ID}>",
      embed=embed,
      allowed_mentions=discord.AllowedMentions(roles=True),
  )


@client.tree.command(name="mandat", description="Wystaw mandat")
async def mandat(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )
  await interaction.response.send_message(
      f"⚙️ Wybierz mandat dla {pracownik.mention}:",
      view=MandatView(pracownik, interaction.user),
      ephemeral=True,
  )


if __name__ == "__main__":
  if TOKEN is None:
    print("❌ BŁĄD: Brak DISCORD_TOKEN!")
  else:
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    client.run(TOKEN)

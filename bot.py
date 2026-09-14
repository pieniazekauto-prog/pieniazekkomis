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
AWANS_LOG_CHANNEL_ID = 1503394099661639680  # Dedykowany kanał na awansy, degrady i zwolnienia
WELCOME_IMAGE_URL = (
    "https://raw.githubusercontent.com/twoje-repo/twoja-sciezka/main/image_9.png"
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
# SYSTEM ZARZĄDZANIA PODANIAMI (Z AKCEPTACJĄ I NADANIEM ROLI)
# ==============================================================================
class PodanieZarzadView(View):

  def __init__(self, applicant: discord.Member):
    super().__init__(timeout=None)
    self.applicant = applicant

  @button(
      label="Zaakceptuj Podanie",
      style=ButtonStyle.success,
      custom_id="podanie_accept",
      emoji="✅",
  )
  async def accept_podanie(self, interaction: Interaction, button: Button):
    if not is_zarzad(interaction.user):
      return await interaction.response.send_message(
          "❌ Brak uprawnień!", ephemeral=True
      )

    guild = interaction.guild
    swiezak_role = guild.get_role(GRADE1_ROLE_ID)
    pracownik_role = guild.get_role(PRACOWNIK_ROLE_ID)

    try:
      roles_to_add = []
      if swiezak_role:
        roles_to_add.append(swiezak_role)
      if pracownik_role:
        roles_to_add.append(pracownik_role)

      if roles_to_add:
        await self.applicant.add_roles(*roles_to_add)
    except discord.Forbidden:
      return await interaction.response.send_message(
          "⚠️ Bot nie posiada uprawnień do nadania ról temu użytkownikowi!",
          ephemeral=True,
      )

    embed = interaction.message.embeds[0]
    embed.color = discord.Color.green()
    embed.add_field(
        name="📊 Status Podania",
        value=(
            f"✅ **Zatwierdzone i przyjęte przez {interaction.user.mention}**\nNadano"
            f" rangę: `{swiezak_role.name if swiezak_role else 'Świeżak'}`"
        ),
        inline=False,
    )

    for child in self.children:
      child.disabled = True

    await interaction.response.edit_message(embed=embed, view=self)
    await interaction.channel.send(
        f"🎉 Gratulacje {self.applicant.mention}! Twoje podanie zostało"
        " **zaakceptowane**. Witamy w zespole Pieniążek Auto!"
    )

  @button(
      label="Odrzuć Podanie",
      style=ButtonStyle.danger,
      custom_id="podanie_reject",
      emoji="❌",
  )
  async def reject_podanie(self, interaction: Interaction, button: Button):
    if not is_zarzad(interaction.user):
      return await interaction.response.send_message(
          "❌ Brak uprawnień!", ephemeral=True
      )

    embed = interaction.message.embeds[0]
    embed.color = discord.Color.red()
    embed.add_field(
        name="📊 Status Podania",
        value=f"❌ **Odrzucone przez {interaction.user.mention}**",
        inline=False,
    )

    for child in self.children:
      child.disabled = True

    await interaction.response.edit_message(embed=embed, view=self)
    await interaction.channel.send(
        f"❌ Przykro nam {self.applicant.mention}, Twoje podanie zostało"
        " niestety odrzucone."
    )


# ==============================================================================
# MODAL DO WPROWADZANIA POWODU AWANSU / DEGRADU
# ==============================================================================
class PowodHRModal(Modal):

  def __init__(self, action_type: str, pracownik: discord.Member):
    title_map = {
        "awans": "Podaj powód awansu",
        "degrad": "Podaj powód degradacji",
    }
    super().__init__(title=title_map.get(action_type, "Powód HR"))
    self.action_type = action_type
    self.pracownik = pracownik

    self.powod_input = TextInput(
        label="Powód",
        placeholder=(
            "Wpisz szczegółowy powód awansu/degradacji..."
            if action_type == "awans"
            else "Wpisz szczegółowy powód degradacji..."
        ),
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )
    self.add_item(self.powod_input)

  async def on_submit(self, interaction: Interaction):
    powod_tekst = self.powod_input.value

    if self.action_type == "awans":
      current_index = get_current_grade_index(self.pracownik)
      if current_index == -1:
        return await interaction.response.send_message(
            f"❌ Użytkownik {self.pracownik.mention} nie posiada żadnej oficjalnej rangi"
            " pracowniczej!",
            ephemeral=True,
        )

      if current_index + 1 >= len(GRADES):
        return await interaction.response.send_message(
            f"⚠️ Pracownik {self.pracownik.mention} posiada już **najwyższą** możliwą"
            " rangę!",
            ephemeral=True,
        )

      old_role_id = GRADES[current_index]
      new_role_id = GRADES[current_index + 1]

      old_role = interaction.guild.get_role(old_role_id)
      new_role = interaction.guild.get_role(new_role_id)

      try:
        if old_role:
          await self.pracownik.remove_roles(old_role)
        await self.pracownik.add_roles(new_role)
      except discord.Forbidden:
        return await interaction.response.send_message(
            "⚠️ Bot nie ma uprawnień do zmiany ról tego użytkownika!",
            ephemeral=True,
        )

      embed = discord.Embed(
          title="🟢 OFICJALNY AWANS PRACOWNIKA",
          description=(
              f"Gratulacje dla pracownika {self.pracownik.mention} za świetną pracę i"
              " zaangażowanie!"
          ),
          color=discord.Color.green(),
          timestamp=datetime.now(),
      )
      embed.set_thumbnail(url=self.pracownik.display_avatar.url)
      embed.add_field(
          name="👤 Awansowany",
          value=f"{self.pracownik.mention}\n`ID: {self.pracownik.id}`",
          inline=True,
      )
      embed.add_field(
          name="👑 Decyzja Zarządu",
          value=f"{interaction.user.mention}",
          inline=True,
      )
      embed.add_field(
          name="📈 Poprzednia Ranga",
          value=f"`{old_role.name if old_role else 'Brak'}`",
          inline=False,
      )
      embed.add_field(
          name="🚀 Nowa Ranga", value=f"**{new_role.name}**", inline=False
      )
      embed.add_field(
          name="📌 Powód Awansu",
          value=f"```\n{powod_tekst}\n```",
          inline=False,
      )
      embed.set_footer(
          text="Pieniążek Auto OSLORP • System Kadr",
          icon_url=(
              interaction.guild.icon.url if interaction.guild.icon else None
          ),
      )

      log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
      if log_channel:
        await log_channel.send(content=f"{self.pracownik.mention}", embed=embed)
      await interaction.response.send_message(
          f"✅ Pomyślnie awansowano pracownika {self.pracownik.mention} na stanowisko"
          f" **{new_role.name}**!",
          ephemeral=True,
      )

    elif self.action_type == "degrad":
      current_index = get_current_grade_index(self.pracownik)
      if current_index == -1:
        return await interaction.response.send_message(
            f"❌ Użytkownik {self.pracownik.mention} nie posiada żadnej oficjalnej rangi"
            " pracowniczej!",
            ephemeral=True,
        )

      if current_index - 1 < 0:
        return await interaction.response.send_message(
            f"⚠️ Pracownik {self.pracownik.mention} posiada już **najniższą** możliwą"
            " rangę!",
            ephemeral=True,
        )

      old_role_id = GRADES[current_index]
      new_role_id = GRADES[current_index - 1]

      old_role = interaction.guild.get_role(old_role_id)
      new_role = interaction.guild.get_role(new_role_id)

      try:
        if old_role:
          await self.pracownik.remove_roles(old_role)
        await self.pracownik.add_roles(new_role)
      except discord.Forbidden:
        return await interaction.response.send_message(
            "⚠️ Bot nie ma uprawnień do zmiany ról tego użytkownika!",
            ephemeral=True,
        )

      embed = discord.Embed(
          title="🟠 OFICJALNA DEGRADACJA PRACOWNIKA",
          description=(
              f"Pracownik {self.pracownik.mention} został zdegradowany z powodu"
              " decyzji zarządu."
          ),
          color=discord.Color.orange(),
          timestamp=datetime.now(),
      )
      embed.set_thumbnail(url=self.pracownik.display_avatar.url)
      embed.add_field(
          name="👤 Zdegradowany",
          value=f"{self.pracownik.mention}\n`ID: {self.pracownik.id}`",
          inline=True,
      )
      embed.add_field(
          name="👑 Decyzja Zarządu",
          value=f"{interaction.user.mention}",
          inline=True,
      )
      embed.add_field(
          name="📉 Poprzednia Ranga",
          value=f"`{old_role.name if old_role else 'Brak'}`",
          inline=False,
      )
      embed.add_field(
          name="📉 Nowa Ranga", value=f"**{new_role.name}**", inline=False
      )
      embed.add_field(
          name="📌 Powód Degradacji",
          value=f"```\n{powod_tekst}\n```",
          inline=False,
      )
      embed.set_footer(
          text="Pieniążek Auto OSLORP • System Kadr",
          icon_url=(
              interaction.guild.icon.url if interaction.guild.icon else None
          ),
      )

      log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
      if log_channel:
        await log_channel.send(content=f"{self.pracownik.mention}", embed=embed)
      await interaction.response.send_message(
          f"✅ Pomyślnie zdegradowano pracownika {self.pracownik.mention} na stanowisko"
          f" **{new_role.name}**!",
          ephemeral=True,
      )


# ==============================================================================
# GŁÓWNY WIDOK POWITALNY I TICKETÓW (SZARE / NEUTRALNE PRZYCISKI)
# ==============================================================================
class WelcomeTicketView(View):

  def __init__(self):
    super().__init__(timeout=None)

  @button(
      label="Ustaw dane",
      style=ButtonStyle.secondary,
      custom_id="set_data_btn",
      emoji="✏️",
  )
  async def set_data(self, interaction: Interaction, button: Button):
    await interaction.response.send_modal(UstawDaneModal())

  @button(
      label="Podanie o pracę",
      style=ButtonStyle.secondary,
      custom_id="ticket_podanie_btn",
      emoji="📄",
  )
  async def ticket_podanie(self, interaction: Interaction, button: Button):
    await self.create_ticket(
        interaction, "podanie", "📄 ⟡ 𝐏𝐨𝐝𝐚𝐧𝐢𝐚", "podanie"
    )

  @button(
      label="Pomoc / Zarząd",
      style=ButtonStyle.secondary,
      custom_id="ticket_help_btn",
      emoji="🛠️",
  )
  async def ticket_help(self, interaction: Interaction, button: Button):
    await self.create_ticket(
        interaction, "pomoc", "👑 ⟡ 𝐒𝐭𝐫𝐞𝐟𝐚 𝐙𝐚𝐫𝐳𝐚𝐝𝐮", "pomoc"
    )

  async def create_ticket(
      self,
      interaction: Interaction,
      ticket_type: str,
      category_name: str,
      mode: str,
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

    if mode == "podanie":
      embed = discord.Embed(
          title="📄 OFICJALNE PODANIE O PRACĘ",
          description=(
              f"Witaj {interaction.user.mention} w strefie składania"
              " podania!\n\nProsimy o dokładne uzupełnienie poniższego wzoru:"
              " wyślij swoje zgłoszenie w wiadomościach na tym kanale.\n\n"
              "**WZÓR PODANIA:**\n"
              "```text\n1. Imię:\n2. Nazwisko:\n3. Wiek:\n4. Mutacja:\n5. Stan"
              " konta (zdjęcie):\n6. Ilość aut (zdjęcie):\n7. Czy pracowałeś"
              " już kiedyś na komisie (jak tak to jakim):\n```\n\n"
              "⏳ **Status:** Twoje podanie jest w trakcie rozpatrywania."
              " Prosimy o cierpliwość i oczekiwanie na decyzję Zarządu."
          ),
          color=discord.Color.gold(),
          timestamp=datetime.now(),
      )
      embed.set_footer(text="Pieniążek Auto OSLORP • System Podaniowy")
      zarzad_view = PodanieZarzadView(applicant=interaction.user)
      await ticket_channel.send(
          content=f"<@&{ZARZAD_ROLE_ID}> {interaction.user.mention}",
          embed=embed,
          view=zarzad_view,
          allowed_mentions=discord.AllowedMentions(roles=True, users=True),
      )
    else:
      embed = discord.Embed(
          title="🛠️ POMOC / SUPPORT OOC",
          description=(
              f"Witaj {interaction.user.mention} w oficjalnym centrum"
              " pomocy!\n\nOpisz dokładnie swoją sprawę, problem lub pytanie,"
              " z którym przychodzisz. Zarząd odpowie najszybciej jak to"
              " możliwe.\n\n*Prosimy o cierpliwość i wyrozumiałość.*"
          ),
          color=discord.Color.gold(),
          timestamp=datetime.now(),
      )
      embed.set_footer(text="Pieniążek Auto OSLORP • System Supportu")
      await ticket_channel.send(
          content=f"<@&{ZARZAD_ROLE_ID}> {interaction.user.mention}",
          embed=embed,
          view=close_view,
          allowed_mentions=discord.AllowedMentions(roles=True, users=True),
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
      title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
      description=(
          "Witaj w oficjalnym centrum dowodzenia komisu **Pieniążek Auto**!\n\n"
          "> *Skup • Sprzedaż • Zamiana pojazdów w najlepszych cenach w"
          " mieście.*\n\n"
          "**Jak zacząć?**\n"
          "• Kliknij **✏️ Ustaw dane**, aby zaktualizować swoje imię i nazwisko"
          " IC.\n• Kliknij **📄 Podanie o pracę**, jeśli chcesz dołączyć do"
          " naszej ekipy.\n• Kliknij **🛠️ Pomoc / Zarząd**, aby skontaktować"
          " się z kadrą zarządzającą.\n\n"
          "*Ustaw swoje dane IC i baw się dobrze!*"
      ),
      color=discord.Color.gold(),
  )
  embed.set_image(url=WELCOME_IMAGE_URL)
  embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

  await interaction.channel.send(embed=embed, view=WelcomeTicketView())
  await interaction.response.send_message("✅ Wysłano panel!", ephemeral=True)


@client.tree.command(
    name="skip",
    description="Oznacza ticket jako pominięty lub przenosi do archiwum uwagi",
)
@app_commands.describe(powod="Powód pominięcia ticketa")
async def skip_ticket(interaction: Interaction, powod: str = "Brak"):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień do użycia tej komendy!", ephemeral=True
    )

  embed = discord.Embed(
      title="⏭️ TICKET POMINIĘTY / ARCHIWIZOWANY",
      description=(
          f"Zarząd {interaction.user.mention} oznaczył ten ticket jako"
          f" pominięty.\n\n**Powód:** `{powod}`"
      ),
      color=discord.Color.orange(),
      timestamp=datetime.now(),
  )
  embed.set_footer(text="Pieniążek Auto • System Zarządzania")

  await interaction.response.send_message(embed=embed)


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
          f"Siema {member.mention}! 🥂\n\n"
          "> Właśnie przekroczyłeś próg\n"
          "> najchętniej wybieranego komisu w\n"
          "> mieście.\n\n"
          "**Jak zacząć?**\n"
          "• Użyj przycisku **✏️ Ustaw dane**, aby dopasować swój nick IC.\n"
          "• Skorzystaj z zakładek poniżej w razie pytań lub chęci podjęcia"
          " pracy.\n\n"
          "Ustaw swoje dane IC i baw się dobrze!"
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


@client.tree.command(
    name="awans", description="Awansuj pracownika i wpisz powód"
)
@app_commands.describe(pracownik="Pracownik, którego chcesz awansować")
async def awans(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )
  await interaction.response.send_modal(PowodHRModal("awans", pracownik))


@client.tree.command(
    name="degrad", description="Zdegraduj pracownika i wpisz powód"
)
@app_commands.describe(pracownik="Pracownik, którego chcesz zdegradować")
async def degrad(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )
  await interaction.response.send_modal(PowodHRModal("degrad", pracownik))


@client.tree.command(
    name="zwolnienie", description="Zwolnij pracownika i wyślij profesjonalny embed"
)
@app_commands.describe(pracownik="Pracownik, którego chcesz zwolnić")
async def zwolnienie(interaction: Interaction, pracownik: discord.Member):
  if not is_zarzad(interaction.user):
    return await interaction.response.send_message(
        "❌ Brak uprawnień!", ephemeral=True
    )

  roles_to_remove = [
      r for r in pracownik.roles if r.id in GRADES or r.id == PRACOWNIK_ROLE_ID
  ]

  try:
    if roles_to_remove:
      await pracownik.remove_roles(*roles_to_remove)
  except discord.Forbidden:
    return await interaction.response.send_message(
        "⚠️ Bot nie ma uprawnień do odebrania ról temu użytkownikowi!",
        ephemeral=True,
    )

  embed = discord.Embed(
      title="🔴 ZWOLNIENIE Z PRACOWNICZYCH SZEREGÓW",
      description=(
          f"Pracownik {pracownik.mention} został zwolniony z komisu"
          " **Pieniążek Auto**."
      ),
      color=discord.Color.red(),
      timestamp=datetime.now(),
  )
  embed.set_thumbnail(url=pracownik.display_avatar.url)
  embed.add_field(
      name="👤 Zwolniony",
      value=f"{pracownik.mention}\n`ID: {pracownik.id}`",
      inline=True,
  )
  embed.add_field(
      name="👑 Decyzja Zarządu", value=f"{interaction.user.mention}", inline=True
  )
  embed.add_field(
      name="📊 Status", value="**Zwolniony / Odrzucony z kadry**", inline=False
  )
  embed.set_footer(
      text="Pieniążek Auto OSLORP • System Kadr",
      icon_url=(
          interaction.guild.icon.url if interaction.guild.icon else None
      ),
  )

  log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
  if log_channel:
    await log_channel.send(content=f"{pracownik.mention}", embed=embed)
  await interaction.response.send_message(
      f"✅ Pracownik {pracownik.mention} został pomyślnie zwolniony, a jego"
      " rangi pracownicze zostały odebrane.",
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
  embed.add_field(name="💰 Za ile:", value=f"{kwota}")
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


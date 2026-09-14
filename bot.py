from datetime import datetime, timedelta
import os
import threading
import discord
from discord import ButtonStyle, Interaction, app_commands
from discord.ext import commands, tasks
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
PRACOWNIK_ROLE_ID = 1503009723543191782  # ID Roli Pracownika (Weryfikacji)

# ID RÓL DLA SYSTEMU HR (OD NAJWYŻSZEJ DO NAJNIŻSZEJ DO WYŚWIETLANIA NA LIŚCIE)
GRADE8_ROLE_ID = 1547339984992731146  # Co Owner
GRADE7_ROLE_ID = 1503009931589062727  # Manager
GRADE6_ROLE_ID = 1547340918389088296  # Kierownik
GRADE4_ROLE_ID = 1547342464963059885  # Specjalista
GRADE3_ROLE_ID = 1548089007416545302  # Doświadczony
GRADE2_ROLE_ID = 1547342288231862303  # Handlarz
GRADE1_ROLE_ID = 1547341972484661318  # Świeżak
OCHRONA_ROLE_ID = 1547694612070666260  # Ochrona

GRADES = [
    GRADE1_ROLE_ID,
    GRADE2_ROLE_ID,
    GRADE3_ROLE_ID,
    GRADE4_ROLE_ID,
    GRADE6_ROLE_ID,
    GRADE7_ROLE_ID,
    GRADE8_ROLE_ID,
]

WELCOME_CHANNEL_ID = 1503013291197202432
AWANS_LOG_CHANNEL_ID = 1503394099661639680
EMPLOYEE_LIST_CHANNEL_ID = 1547346427976482927
FEES_CHANNEL_ID = 1503394328670634026

WELCOME_IMAGE_URL = (
    "https://raw.githubusercontent.com/twoje-repo/twoja-sciezka/main/image_9.png"
)


# ==============================================================================
# HELPER FUNCTIONS
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
                "❌ Bot nie ma uprawnień do zmiany Twojego pseudonimu.",
                ephemeral=True,
            )


# ==============================================================================
# SYSTEM WERYFIKACJI I WIDOKI GŁÓWNE
# ==============================================================================
class VerificationView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Zweryfikuj się",
        style=ButtonStyle.success,
        custom_id="verify_btn",
        emoji="🛡️",
    )
    async def verify_user(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        pracownik_role = guild.get_role(PRACOWNIK_ROLE_ID)

        if not pracownik_role:
            return await interaction.response.send_message(
                "❌ Nie znaleziono roli weryfikacji na serwerze!",
                ephemeral=True,
            )

        if pracownik_role in interaction.user.roles:
            return await interaction.response.send_message(
                "ℹ️ Jesteś już zweryfikowany!", ephemeral=True
            )

        try:
            await interaction.user.add_roles(pracownik_role)
            await interaction.response.send_message(
                "✅ Pomyślnie przeszedłeś weryfikację! Witaj w gronie"
                f" **Pieniążek Auto** {interaction.user.mention}.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot posiada uprawnień do nadawania tej roli.", ephemeral=True
            )


class WelcomeTicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Zweryfikuj konto",
        style=ButtonStyle.success,
        custom_id="verify_main_btn",
        emoji="🛡️",
    )
    async def verify_main(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        pracownik_role = guild.get_role(PRACOWNIK_ROLE_ID)
        if pracownik_role and pracownik_role not in interaction.user.roles:
            await interaction.user.add_roles(pracownik_role)
            await interaction.response.send_message(
                "✅ Pomyślnie zweryfikowano i nadano dostęp!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ Masz już tę rolę lub wystąpił błąd uprawnień.", ephemeral=True
            )

    @button(
        label="Ustaw dane IC",
        style=ButtonStyle.secondary,
        custom_id="set_data_btn",
        emoji="✏️",
    )
    async def set_data(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(UstawDaneModal())

    @button(
        label="Podanie o pracę",
        style=ButtonStyle.primary,
        custom_id="ticket_podanie_btn",
        emoji="📄",
    )
    async def ticket_podanie(self, interaction: Interaction, button: Button):
        await self.create_ticket(
            interaction, "podanie", "📄 ⟡ 𝐏𝐨𝐝𝐚𝐧𝐢𝐚", "podanie"
        )

    @button(
        label="Strefa Zarządu",
        style=ButtonStyle.secondary,
        custom_id="ticket_help_btn",
        emoji="👑",
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
                title="✦ PIENIĄŻEK AUTO | OFICJALNE PODANIE",
                description=(
                    f"Witaj {interaction.user.mention} w strefie podania!\n\nUzupełnij"
                    " poniższy wzór:\n```text\n1. Imię:\n2. Nazwisko:\n3. Wiek:\n4."
                    " Mutacja:\n5. Stan konta (zdjęcie):\n6. Ilość aut"
                    " (zdjęcie):\n7. SS dowodu osobistego (zdjęcie):\n8. Czy byłeś"
                    " karany:\n9. Doświadczenie w komisach:\n```"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )
            embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")
            zarzad_view = PodanieZarzadView(applicant=interaction.user)
            await ticket_channel.send(
                content=f"<@&{ZARZAD_ROLE_ID}> {interaction.user.mention}",
                embed=embed,
                view=zarzad_view,
                allowed_mentions=discord.AllowedMentions(
                    roles=True, users=True
                ),
            )
        else:
            embed = discord.Embed(
                title="✦ PIENIĄŻEK AUTO | STREFA POMOCY",
                description=(
                    f"Witaj {interaction.user.mention}!\n\nOpisz dokładnie swój"
                    " problem lub sprawę. Zarząd odpowie najszybciej jak to możliwe."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )
            embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")
            await ticket_channel.send(
                content=f"<@&{ZARZAD_ROLE_ID}> {interaction.user.mention}",
                embed=embed,
                view=close_view,
                allowed_mentions=discord.AllowedMentions(
                    roles=True, users=True
                ),
            )

        await interaction.response.send_message(
            f"Utworzono dla Ciebie ticket: {ticket_channel.mention}",
            ephemeral=True,
        )


class SetupPanelView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Ustaw dane IC",
        style=ButtonStyle.secondary,
        custom_id="setup_set_data_btn",
        emoji="✏️",
    )
    async def set_data(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(UstawDaneModal())

    @button(
        label="Podanie o pracę",
        style=ButtonStyle.primary,
        custom_id="setup_ticket_podanie_btn",
        emoji="📄",
    )
    async def ticket_podanie(self, interaction: Interaction, button: Button):
        temp_obj = WelcomeTicketView()
        await temp_obj.create_ticket(
            interaction, "podanie", "📄 ⟡ 𝐏𝐨𝐝𝐚𝐧𝐢𝐚", "podanie"
        )

    @button(
        label="Strefa Zarządu",
        style=ButtonStyle.secondary,
        custom_id="setup_ticket_help_btn",
        emoji="👑",
    )
    async def ticket_help(self, interaction: Interaction, button: Button):
        temp_obj = WelcomeTicketView()
        await temp_obj.create_ticket(
            interaction, "pomoc", "👑 ⟡ 𝐒𝐭𝐫𝐞𝐟𝐚 𝐙𝐚𝐫𝐳𝐚𝐝𝐮", "pomoc"
        )


# ==============================================================================
# POPRAWIONy SYSTEM LISTY PRACOWNIKÓW (BEZ BŁĘDÓW PRZESUNIĘĆ)
# ==============================================================================
async def update_employee_list(guild: discord.Guild):
    channel = guild.get_channel(EMPLOYEE_LIST_CHANNEL_ID)
    if not channel:
        return

    # Dokładna hierarchia od NAJWYŻSZEJ do NAJNIŻSZEJ rangi
    roles_config = [
        ("⟡ @👑 ⟡ Owner⟡", GRADE8_ROLE_ID),
        ("⟡ @💫 ⟡ Co-Owner⟡", GRADE7_ROLE_ID),
        ("⟡ @✨ ⟡ Manager ⟡", GRADE6_ROLE_ID),
        ("⟡ @⚡️ ⟡ Kierownik ⟡", GRADE4_ROLE_ID),
        ("⟡ @🚕 ⟡ Specjalista ⟡", GRADE3_ROLE_ID),
        ("⟡ @🐤 ⟡ Doświadczony ⟡", GRADE2_ROLE_ID),
        ("⟡ @💰 ⟡ Handlarz ⟡", GRADE1_ROLE_ID),
        ("⟡ @🧸 ⟡ Świeżak ⟡", PRACOWNIK_ROLE_ID),
        ("⟡ @🛡️ ⟡ Ochrona  ⟡", OCHRONA_ROLE_ID),
    ]

    sections = {header: [] for header, _ in roles_config}
    assigned_user_ids = set()
    total_employees = set()

    # Sprawdzamy każdego członka serwera pod kątem ról
    for member in guild.members:
        if member.bot:
            continue

        assigned_role_header = None
        # Przechodzimy po konfiguracji OD GÓRY DO DOŁU.
        # Pierwsza rola z góry, którą użytkownik posiada, jest jego najwyższym stanowiskiem!
        for header, role_id in roles_config:
            role = guild.get_role(role_id)
            if role and role in member.roles:
                assigned_role_header = header
                break  # Przerywamy pętlę, bo znalezliśmy najwyższą rangę dla tego usera

        if assigned_role_header and member.id not in assigned_user_ids:
            assigned_user_ids.add(member.id)
            sections[assigned_role_header].append(member)
            total_employees.add(member.id)

    # Sortujemy członków w każdej sekcji alfabetycznie
    for header in sections:
        sections[header] = sorted(
            sections[header], key=lambda m: m.display_name.lower()
        )

    # Składanie czystego embedu
    desc_lines = []
    for header, _ in roles_config:
        desc_lines.append(f"> # {header}")
        members_list = sections[header]
        if members_list:
            for m in members_list:
                desc_lines.append(f"- {m.display_name} | {m.mention}")
        else:
            desc_lines.append("-")
        desc_lines.append("")

    desc_lines.append(f"## Liczba pracowników: `{len(total_employees)}`")

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO | LISTA PRACOWNIKÓW",
        description="\n".join(desc_lines),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_footer(text="© Pieniążek Auto OSLORP | Automatyczna lista kadry")

    async for message in channel.history(limit=10):
        if message.author == guild.me:
            await message.edit(embed=embed, view=EmployeePanelView())
            return

    await channel.send(embed=embed, view=EmployeePanelView())


class EmployeePanelView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Odśwież listę",
        style=ButtonStyle.secondary,
        custom_id="refresh_emp_list",
        emoji="🔄",
    )
    async def refresh_list(self, interaction: Interaction, button: Button):
        await update_employee_list(interaction.guild)
        await interaction.response.send_message(
            "✅ Odświeżono listę pracowników!", ephemeral=True
        )


class FeeSearchModal(Modal, title="Wyszukaj pracownika (Opłaty)"):
    search_query = TextInput(
        label="Imię, nazwisko lub wzmianka",
        placeholder="Wpisz fragment nicku pracownika...",
        required=True,
    )

    async def on_submit(self, interaction: Interaction):
        query = self.search_query.value.lower().strip()
        embed = interaction.message.embeds[0]
        content = embed.description

        lines = content.split("\n")
        matched_lines = []
        for line in lines:
            if query in line.lower() and ("✅" in line or "❌" in line):
                matched_lines.append(line)

        if not matched_lines:
            return await interaction.response.send_message(
                f"❌ Nie znaleziono pracownika pasującego do: **{query}**",
                ephemeral=True,
            )

        target_line = matched_lines[0]
        if "❌" in target_line:
            new_line = target_line.replace("❌", "✅")
        else:
            new_line = target_line.replace("✅", "❌")

        embed.description = content.replace(target_line, new_line)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(
            f"✅ Zmieniono status dla pasującego wpisu:\n`{target_line}` ➡️"
            f" `{new_line}`",
            ephemeral=True,
        )


class FeesView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="🔍 Wyszukaj i zmień status opłaty",
        style=ButtonStyle.primary,
        custom_id="fee_search_btn",
    )
    async def search_fee(self, interaction: Interaction, button: Button):
        if not is_zarzad(interaction.user):
            return await interaction.response.send_message(
                "❌ Brak uprawnień do zmiany opłat!", ephemeral=True
            )
        await interaction.response.send_modal(FeeSearchModal())


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
            title="✦ PIENIĄŻEK AUTO | SYSTEM MANDATÓW",
            description=(
                "Nałożono oficjalny mandat dyscyplinarny na pracownika"
                f" {self.ukarany.mention}."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=self.ukarany.display_avatar.url)
        embed.add_field(
            name="👤 Ukarany",
            value=f"{self.ukarany.mention}\n`ID: {self.ukarany.id}`",
            inline=True,
        )
        embed.add_field(
            name="👑 Wystawiający",
            value=f"{self.wystawiajacy.mention}",
            inline=True,
        )
        embed.add_field(
            name="📌 Powód", value=f"```text\n{powod_wybrany}\n```", inline=False
        )
        embed.add_field(
            name="💰 Kwota do zapłaty",
            value=f"```css\n[{kwota}]\n```",
            inline=False,
        )
        embed.set_footer(
            text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
            icon_url=(
                interaction.guild.icon.url if interaction.guild.icon else None
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
# SYSTEM WYPOWIEDZEŃ I PODAŃ
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
            title="✦ PIENIĄŻEK AUTO | WNIOSEK O WYPOWIEDZENIE",
            description=(
                f"Pracownik {interaction.user.mention} złożył wniosek o"
                " rozwiązanie umowy."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(
            name="👤 Pracownik",
            value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`",
            inline=True,
        )
        embed.add_field(
            name="💼 Stanowisko", value=f"`{self.stanowisko.value}`", inline=True
        )
        embed.add_field(
            name="📝 Powód", value=f"```text\n{self.powod.value}\n```", inline=False
        )
        embed.add_field(
            name="📊 Status",
            value="⏳ **Oczekuje na decyzję Zarządu**",
            inline=False,
        )
        embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

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
        embed.color = discord.Color.green()
        embed.add_field(
            name="📊 Status",
            value=f"✅ **Zatwierdzone przez {interaction.user.mention}**",
            inline=False,
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        await update_employee_list(interaction.guild)

    @button(label="Odrzuć", style=ButtonStyle.danger, custom_id="wyp_reject")
    async def odrzuc(self, interaction: Interaction, button: Button):
        if not is_zarzad(interaction.user):
            return await interaction.response.send_message(
                "❌ Brak uprawnień!", ephemeral=True
            )
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(
            name="📊 Status",
            value=f"❌ **Odrzucono przez {interaction.user.mention}**",
            inline=False,
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


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
                "⚠️ Bot nie posiada uprawnień do nadania ról!", ephemeral=True
            )

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name="📊 Status Podania",
            value=(
                f"✅ **Zatwierdzone przez {interaction.user.mention}**\nNadano"
                f" rangę: `{swiezak_role.name if swiezak_role else 'Świeżak'}`"
            ),
            inline=False,
        )
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)
        await update_employee_list(guild)

        info_channel_mention = "<#1547357733626577027>"
        await interaction.channel.send(
            f"❗⬩𝗜𝗻𝗳𝗼𝗿𝗺𝗮𝗰𝗷𝗲\n\nGratulacje {self.applicant.mention}! Twoje podanie"
            " zostało zaakceptowane. Zapoznaj się z dostępnymi informacjami"
            f" w {info_channel_mention}, a następnie zgłoś się do Zarządu po"
            " przydzielenie odpowiedniego joba."
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
            " odrzucone."
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
            placeholder="Wpisz szczegółowy powód...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.powod_input)

    async def on_submit(self, interaction: Interaction):
        powod_tekst = self.powod_input.value
        current_index = get_current_grade_index(self.pracownik)

        if current_index == -1:
            return await interaction.response.send_message(
                f"❌ Użytkownik {self.pracownik.mention} nie posiada rangi"
                " pracowniczej!",
                ephemeral=True,
            )

        if self.action_type == "awans":
            if current_index + 1 >= len(GRADES):
                return await interaction.response.send_message(
                    f"⚠️ Pracownik ma już najwyższą rangę!", ephemeral=True
                )

            old_role = interaction.guild.get_role(GRADES[current_index])
            new_role = interaction.guild.get_role(GRADES[current_index + 1])

            try:
                if old_role and old_role in self.pracownik.roles:
                    await self.pracownik.remove_roles(old_role)
                if new_role:
                    await self.pracownik.add_roles(new_role)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "⚠️ Brak uprawnień bota do zmiany ról!", ephemeral=True
                )

            embed = discord.Embed(
                title="✦ PIENIĄŻEK AUTO | OFICJALNY AWANS",
                description=(
                    f"Pracownik {self.pracownik.mention} awansował w hierarchii"
                    " komisu."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=self.pracownik.display_avatar.url)
            embed.add_field(
                name="👤 Awansowany",
                value=f"{self.pracownik.mention}\n`ID: {self.pracownik.id}`",
                inline=True,
            )
            embed.add_field(
                name="👑 Decyzja", value=f"{interaction.user.mention}", inline=True
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
                value=f"```text\n{powod_tekst}\n```",
                inline=False,
            )
            embed.set_footer(
                text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
                icon_url=(
                    interaction.guild.icon.url if interaction.guild.icon else None
                ),
            )

            log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    content=f"{self.pracownik.mention}", embed=embed
                )
            await update_employee_list(interaction.guild)
            await interaction.response.send_message(
                f"✅ Pomyślnie awansowano pracownika na **{new_role.name}**!",
                ephemeral=True,
            )

        elif self.action_type == "degrad":
            if current_index - 1 < 0:
                return await interaction.response.send_message(
                    f"⚠️ Pracownik ma już najniższą rangę!", ephemeral=True
                )

            old_role = interaction.guild.get_role(GRADES[current_index])
            new_role = interaction.guild.get_role(GRADES[current_index - 1])

            try:
                if old_role and old_role in self.pracownik.roles:
                    await self.pracownik.remove_roles(old_role)
                if new_role:
                    await self.pracownik.add_roles(new_role)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "⚠️ Brak uprawnień bota do zmiany ról!", ephemeral=True
                )

            embed = discord.Embed(
                title="✦ PIENIĄŻEK AUTO | OFICJALNA DEGRADACJA",
                description=(
                    f"Pracownik {self.pracownik.mention} został zdegradowany."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=self.pracownik.display_avatar.url)
            embed.add_field(
                name="👤 Zdegradowany",
                value=f"{self.pracownik.mention}\n`ID: {self.pracownik.id}`",
                inline=True,
            )
            embed.add_field(
                name="👑 Decyzja", value=f"{interaction.user.mention}", inline=True
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
                value=f"```text\n{powod_tekst}\n```",
                inline=False,
            )
            embed.set_footer(
                text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
                icon_url=(
                    interaction.guild.icon.url if interaction.guild.icon else None
                ),
            )

            log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    content=f"{self.pracownik.mention}", embed=embed
                )
            await update_employee_list(interaction.guild)
            await interaction.response.send_message(
                f"✅ Pomyślnie zdegradowano pracownika na **{new_role.name}**!",
                ephemeral=True,
            )


# ==============================================================================
# TICKETY - ZAMYKANIE
# ==============================================================================
class TicketCloseConfirmView(View):

    def __init__(self):
        super().__init__(timeout=60)

    @button(
        label="Potwierdź zamknięcie",
        style=ButtonStyle.red,
        custom_id="conf_close",
    )
    async def confirm_close(self, interaction: Interaction, button: Button):
        if not is_zarzad(interaction.user):
            return await interaction.response.send_message(
                "❌ Tylko Zarząd może usunąć ticket!", ephemeral=True
            )
        await interaction.response.send_message("🔒 Usuwanie kanału za 3 sekundy...")
        import asyncio

        await asyncio.sleep(3)
        await interaction.channel.delete()

    @button(label="Anuluj", style=ButtonStyle.secondary, custom_id="canc_close")
    async def cancel_close(self, interaction: Interaction, button: Button):
        await interaction.message.delete()
        await interaction.response.send_message("✅ Anulowano.", ephemeral=True)


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
        self.add_view(VerificationView())
        self.add_view(SetupPanelView())
        self.add_view(EmployeePanelView())
        self.add_view(FeesView())

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.auto_refresh_loop.start()

    @tasks.loop(minutes=10)
    async def auto_refresh_loop(self):
        guild = self.get_guild(GUILD_ID)
        if guild:
            try:
                await update_employee_list(guild)
            except Exception as e:
                print(f"Błąd automatycznego odświeżania listy: {e}")

    @auto_refresh_loop.before_loop
    async def before_auto_refresh(self):
        await self.wait_until_ready()


client = MyClient()


@client.event
async def on_ready():
    print(f"✅ Bot działa! Zalogowano jako: {client.user}")


# ==============================================================================
# AUTOMATYCZNE POWITANIA (Z WERYFIKACJĄ)
# ==============================================================================
@client.event
async def on_member_join(member: discord.Member):
    if member.guild.id != GUILD_ID:
        return

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO OSLORP | OFICJALNA BRAMA",
        description=(
            f"Siema {member.mention}! 🥂\n\n> Właśnie przekroczyłeś próg"
            " najbardziej prestiżowego komisu w mieście.\n\n"
            "**Jak rozpocząć karierę?**\n"
            "• Kliknij poniższy przycisk **🛡️ Zweryfikuj się**, aby uzyskać"
            " dostęp do serwera.\n• Użyj **✏️ Ustaw dane IC**, aby dopasować"
            " swoje imię i nazwisko.\n• Sprawdź zakładki poniżej w celu"
            " złożenia podania lub kontaktu z zarządem."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url=WELCOME_IMAGE_URL)
    embed.set_footer(
        text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    await channel.send(
        content=f"{member.mention}", embed=embed, view=WelcomeTicketView()
    )


# ==============================================================================
# KOMENDY SLASH
# ==============================================================================
@client.tree.command(
    name="setup_panel", description="Wysyła odświeżony panel główny komisu"
)
async def setup_panel(interaction: Interaction):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO OSLORP | CENTRUM DOWODZENIA",
        description=(
            "Witaj w oficjalnym systemie zarządzania komisem **Pieniążek"
            " Auto**!\n\n> *Skup • Sprzedaż • Profesjonalna obsługa klientów na"
            " terenie OSLORP.*\n\n"
            "**Dostępne akcje:**\n"
            "• **✏️ Ustaw dane IC** – zaktualizuj swoje in-game ID/pseudonim.\n"
            "• **📄 Podanie o pracę** – dołącz do naszego zespołu.\n"
            "• **👑 Strefa Zarządu** – otwórz poufny ticket do kadry."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_image(url=WELCOME_IMAGE_URL)
    embed.set_footer(
        text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )

    await interaction.channel.send(embed=embed, view=SetupPanelView())
    await interaction.response.send_message(
        "✅ Pomyślnie wysłano panel!", ephemeral=True
    )


@client.tree.command(
    name="zatrudnij", description="Zatrudnia pracownika i nadaje rangę Świeżak"
)
async def zatrudnij(interaction: Interaction, pracownik: discord.Member):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )

    guild = interaction.guild
    swiezak_role = guild.get_role(GRADE1_ROLE_ID)
    pracownik_role = guild.get_role(PRACOWNIK_ROLE_ID)

    if not swiezak_role:
        return await interaction.response.send_message(
            "❌ Nie znaleziono roli Świeżak na serwerze!", ephemeral=True
        )

    roles_to_add = [swiezak_role]
    if pracownik_role and pracownik_role not in pracownik.roles:
        roles_to_add.append(pracownik_role)

    try:
        await pracownik.add_roles(*roles_to_add)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "⚠️ Bot nie posiada uprawnień do nadania ról temu użytkownikowi!",
            ephemeral=True,
        )

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO | ZATRUDNIENIE W KADRZE",
        description=f"Pracownik {pracownik.mention} został oficjalnie zatrudniony!",
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=pracownik.display_avatar.url)
    embed.add_field(
        name="👤 Nowy Pracownik",
        value=f"{pracownik.mention}\n`ID: {pracownik.id}`",
        inline=True,
    )
    embed.add_field(
        name="👑 Zatrudniający", value=f"{interaction.user.mention}", inline=True
    )
    embed.add_field(
        name="🚀 Przyznana Ranga", value=f"**{swiezak_role.name}**", inline=False
    )
    embed.set_footer(
        text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )

    log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(content=f"{pracownik.mention}", embed=embed)

    await update_employee_list(guild)
    await interaction.response.send_message(
        f"✅ Pomyślnie zatrudniono pracownika {pracownik.mention}!",
        ephemeral=True,
    )


@client.tree.command(
    name="panel_pracownikow",
    description="Wysyła lub odświeża automatyczną listę pracowników",
)
async def panel_pracownikow(interaction: Interaction):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await update_employee_list(interaction.guild)
    await interaction.response.send_message(
        "✅ Wygenerowano/odświeżono listę pracowników!", ephemeral=True
    )


@client.tree.command(
    name="panel_oplat", description="Tworzy cotygodniowy panel opłat pracowniczych"
)
async def panel_oplat(interaction: Interaction):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )

    guild = interaction.guild
    fees_channel = guild.get_channel(FEES_CHANNEL_ID)
    if not fees_channel:
        return await interaction.response.send_message(
            "❌ Nie znaleziono kanału opłat!", ephemeral=True
        )

    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    date_str = (
        f"{start_of_week.strftime('%d.%m.%Y')} do"
        f" {end_of_week.strftime('%d.%m.%Y')}"
    )

    role = guild.get_role(PRACOWNIK_ROLE_ID) or guild.get_role(GRADE1_ROLE_ID)
    members_text = []
    if role:
        for m in role.members:
            members_text.append(f"- {m.display_name} | {m.mention} ❌")

    embed = discord.Embed(
        title=f"✦ PIENIĄŻEK AUTO | OPŁATY TYGODNIOWE",
        description=(
            f"**Okres rozliczeniowy:** `{date_str}`\n\n"
            + ("\n".join(members_text) if members_text else "Brak pracowników.")
            + "\n\n> *Kliknij przycisk poniżej, aby wyszukać pracownika i"
            " zmienić status opłaty.*"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_footer(text="© Pieniążek Auto OSLORP | System Opłat Tygodniowych")

    await fees_channel.send(embed=embed, view=FeesView())
    await interaction.response.send_message(
        f"✅ Pomyślnie utworzono nowy panel opłat na kanale"
        f" {fees_channel.mention}!",
        ephemeral=True,
    )


@client.tree.command(name="skip", description="Oznacza ticket jako w trakcie")
async def skip_ticket(interaction: Interaction):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO | STATUS PODANIA",
        description=(
            "Twoje podanie jest aktualnie **w trakcie rozpatrywania**.\n\n📸"
            " **Wymagane dodatkowo:**\n• Prześlij **screenshot dowodu"
            " osobistego**.\n• Informacja, **czy byłeś karany**."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="add", description="Dodaje użytkownika do ticketa")
async def add_member(interaction: Interaction, member: discord.Member):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await interaction.channel.set_permissions(
        member, view_channel=True, send_messages=True, read_message_history=True
    )
    await interaction.response.send_message(
        f"✅ Pomyślnie dodano {member.mention} do ticketa."
    )


@client.tree.command(name="remove", description="Wyrzuca użytkownika z ticketa")
async def remove_member(interaction: Interaction, member: discord.Member):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await interaction.channel.set_permissions(member, overwrite=None)
    await interaction.response.send_message(
        f"🔒 Użytkownik {member.mention} został usunięty z ticketa."
    )


@client.tree.command(name="close", description="Zamyka bieżący ticket")
async def close_ticket_cmd(interaction: Interaction):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await interaction.response.send_message(
        "🔒 Ten ticket zostanie zamknięty za 3 sekundy..."
    )
    import asyncio

    await asyncio.sleep(3)
    await interaction.channel.delete()


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
            f"Siema {member.mention}! 🥂\n\n> Właśnie przekroczyłeś próg"
            " najbardziej prestiżowego komisu w mieście.\n\n"
            "**Jak rozpocząć karierę?**\n"
            "• Kliknij poniższy przycisk **🛡️ Zweryfikuj się**, aby uzyskać"
            " dostęp do serwera."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url=WELCOME_IMAGE_URL)
    embed.set_footer(text="© Pieniążek Auto OSLORP | powered by Keshy Dev")

    await channel.send(
        content=f"{member.mention}", embed=embed, view=WelcomeTicketView()
    )
    await interaction.response.send_message(
        f"✅ Wysłano powitanie testowe dla {member.mention}!", ephemeral=True
    )


@client.tree.command(name="awans", description="Awansuj pracownika")
async def awans(interaction: Interaction, pracownik: discord.Member):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await interaction.response.send_modal(PowodHRModal("awans", pracownik))


@client.tree.command(name="degrad", description="Zdegraduj pracownika")
async def degrad(interaction: Interaction, pracownik: discord.Member):
    if not is_zarzad(interaction.user):
        return await interaction.response.send_message(
            "❌ Brak uprawnień!", ephemeral=True
        )
    await interaction.response.send_modal(PowodHRModal("degrad", pracownik))


@client.tree.command(name="zwolnienie", description="Zwolnij pracownika")
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
            "⚠️ Brak uprawnień bota!", ephemeral=True
        )

    embed = discord.Embed(
        title="✦ PIENIĄŻEK AUTO | ZWOLNIENIE Z KADRY",
        description=f"Pracownik {pracownik.mention} został zwolniony z komisu.",
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=pracownik.display_avatar.url)
    embed.add_field(
        name="👤 Zwolniony",
        value=f"{pracownik.mention}\n`ID: {pracownik.id}`",
        inline=True,
    )
    embed.add_field(
        name="👑 Zarząd", value=f"{interaction.user.mention}", inline=True
    )
    embed.add_field(
        name="📊 Status", value="**Zwolniony z szeregów**", inline=False
    )
    embed.set_footer(
        text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )

    log_channel = interaction.guild.get_channel(AWANS_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(content=f"{pracownik.mention}", embed=embed)

    await update_employee_list(interaction.guild)
    await interaction.response.send_message(
        f"✅ Zwolniono pracownika {pracownik.mention}.", ephemeral=True
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
        title="✦ PIENIĄŻEK AUTO | RAPORT SPRZEDAŻY",
        color=discord.Color.gold(),
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(
        name="👤 Pracownik",
        value=f"{interaction.user.mention}\n`ID: {interaction.user.id}`",
        inline=True,
    )
    embed.add_field(
        name="💰 Kwota / Auto", value=f"```css\n[{kwota}]\n```", inline=True
    )
    if dowod.content_type and "image" in dowod.content_type:
        embed.set_image(url=dowod.url)
    embed.set_footer(
        text="© Pieniążek Auto OSLORP | powered by Keshy Dev",
        icon_url=(
            interaction.guild.icon.url if interaction.guild.icon else None
        ),
    )

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
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("❌ BŁĄD: Brak DISCORD_TOKEN!")
    else:
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        client.run(TOKEN)

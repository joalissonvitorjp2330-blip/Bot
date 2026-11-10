import discord

class MainPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Inscrição", style=discord.ButtonStyle.success, custom_id="farm:signup")
    async def signup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Use `/inscrever` para cadastrar sua dupla e escolher a modalidade.", ephemeral=True)

    @discord.ui.button(label="Partidas", style=discord.ButtonStyle.primary, custom_id="farm:matches")
    async def matches(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Use `/partidas` para consultar a agenda.", ephemeral=True)

    @discord.ui.button(label="Regulamento", style=discord.ButtonStyle.secondary, custom_id="farm:rules")
    async def rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .rules import rules_text
        await interaction.response.send_message(rules_text(), ephemeral=True)

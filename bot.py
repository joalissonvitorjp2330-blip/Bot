import logging
import discord
from discord import app_commands
from discord.ext import commands
from .config import settings, validate_settings
from .db import Database
from .views import MainPanel
from .rules import rules_text

log = logging.getLogger("farmbot")
db = Database()
FEES = {"R$ 0,50": 50, "R$ 1,00": 100, "R$ 2,00": 200, "R$ 5,00": 500,
        "R$ 10,00": 1000, "R$ 20,00": 2000, "R$ 50,00": 5000}

def money(cents):
    return f"R$ {cents // 100},{cents % 100:02d}"

def admin(interaction):
    return interaction.user.guild_permissions.administrator or (
        settings.admin_role_id and any(r.id == settings.admin_role_id for r in getattr(interaction.user, "roles", []))
    )

async def require_admin(interaction):
    if not admin(interaction):
        await interaction.response.send_message("Comando exclusivo da administração.", ephemeral=True)
        return False
    return True

class FarmBot(commands.Bot):
    async def setup_hook(self):
        await db.connect()
        self.add_view(MainPanel())
        if settings.guild_id:
            guild = discord.Object(id=settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        log.info("Banco conectado e comandos sincronizados.")

bot = FarmBot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    log.info("FARM BOT conectado como %s", bot.user)

@bot.tree.command(name="painel", description="Publica o painel principal do FARM BOT.")
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(title="🌾 FARM BOT — Central de Torneios",
        description="Inscrições em dupla, partidas, PIX com conferência manual e regulamento.",
        color=discord.Color.green())
    embed.add_field(name="Inscrição", value="Use `/inscrever` para cadastrar sua dupla.", inline=False)
    embed.add_field(name="Pagamento", value="Use `/comprovante` e aguarde a aprovação da equipe.", inline=False)
    await interaction.response.send_message(embed=embed, view=MainPanel())

@bot.tree.command(name="regras", description="Mostra o regulamento.")
async def regras(interaction: discord.Interaction):
    await interaction.response.send_message(rules_text(), ephemeral=True)

@bot.tree.command(name="inscrever", description="Inscreve uma dupla.")
@app_commands.choices(valor=[app_commands.Choice(name=k, value=v) for k, v in FEES.items()])
async def inscrever(interaction: discord.Interaction, nome_dupla: str, parceiro: discord.Member, valor: app_commands.Choice[int]):
    if parceiro.bot or parceiro.id == interaction.user.id:
        return await interaction.response.send_message("Marque outro jogador humano como parceiro.", ephemeral=True)
    if not 2 <= len(nome_dupla.strip()) <= 40:
        return await interaction.response.send_message("O nome da dupla deve ter de 2 a 40 caracteres.", ephemeral=True)
    fee = valor.value
    async with db.pool.acquire() as c:
        async with c.transaction():
            duplicate = await c.fetchrow("""SELECT id FROM registrations WHERE captain_id=$1 AND partner_id=$2
                AND entry_fee_cents=$3 AND status IN ('awaiting_payment','payment_review','confirmed')""",
                interaction.user.id, parceiro.id, fee)
            if duplicate:
                return await interaction.response.send_message("Essa dupla já tem inscrição ativa nessa modalidade.", ephemeral=True)
            await c.execute("INSERT INTO players(discord_id,username) VALUES($1,$2) ON CONFLICT(discord_id) DO UPDATE SET username=EXCLUDED.username", interaction.user.id, str(interaction.user))
            await c.execute("INSERT INTO players(discord_id,username) VALUES($1,$2) ON CONFLICT(discord_id) DO UPDATE SET username=EXCLUDED.username", parceiro.id, str(parceiro))
            reg = await c.fetchrow("INSERT INTO registrations(captain_id,partner_id,team_name,entry_fee_cents) VALUES($1,$2,$3,$4) RETURNING id",
                interaction.user.id, parceiro.id, nome_dupla.strip(), fee)
            await c.execute("INSERT INTO payments(registration_id,amount_cents) VALUES($1,$2)", reg["id"], fee * 2)
    key = await db.setting("pix_key", "")
    receiver = await db.setting("pix_receiver", "")
    text = (f"**Inscrição #{reg['id']} criada**\\nDupla: **{discord.utils.escape_markdown(nome_dupla)}**"
            f"\\nValor por jogador: **{money(fee)}** | Total da dupla: **{money(fee*2)}**"
            f"\\nChave PIX: `{key or 'Aguardando configuração da organização'}`"
            f"\\nRecebedor: **{receiver or 'Não informado'}**"
            "\\nApós pagar, use `/comprovante` com o ID da inscrição e uma referência. A confirmação é manual.")
    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="comprovante", description="Registra referência do comprovante para análise.")
async def comprovante(interaction: discord.Interaction, inscricao_id: int, referencia: str):
    if not 3 <= len(referencia.strip()) <= 120:
        return await interaction.response.send_message("A referência deve ter de 3 a 120 caracteres.", ephemeral=True)
    async with db.pool.acquire() as c:
        row = await c.fetchrow("""SELECT id FROM registrations WHERE id=$1 AND (captain_id=$2 OR partner_id=$2)
            AND status='awaiting_payment'""", inscricao_id, interaction.user.id)
        if not row:
            return await interaction.response.send_message("Inscrição não encontrada ou fora do estado de pagamento.", ephemeral=True)
        await c.execute("UPDATE payments SET proof_reference=$2,status='review' WHERE registration_id=$1 AND status='pending'", inscricao_id, referencia.strip())
        await c.execute("UPDATE registrations SET status='payment_review' WHERE id=$1", inscricao_id)
    await interaction.response.send_message("Referência enviada para análise. Aguarde a conferência manual.", ephemeral=True)

@bot.tree.command(name="partidas", description="Lista partidas agendadas.")
async def partidas(interaction: discord.Interaction):
    async with db.pool.acquire() as c:
        rows = await c.fetch("SELECT id,title,starts_at,room_info,status FROM matches WHERE status <> 'cancelled' ORDER BY id DESC LIMIT 10")
    if not rows:
        return await interaction.response.send_message("Ainda não há partidas publicadas.", ephemeral=True)
    await interaction.response.send_message("\\n".join(
        f"**#{r['id']} — {r['title']}** | {r['starts_at']} | {r['room_info']} | {r['status']}" for r in rows
    ), ephemeral=True)

@bot.tree.command(name="criar_partida", description="[Admin] Cria uma partida.")
async def criar_partida(interaction: discord.Interaction, titulo: str, horario: str, sala: str = "A definir"):
    if not await require_admin(interaction): return
    async with db.pool.acquire() as c:
        row = await c.fetchrow("INSERT INTO matches(title,starts_at,room_info,created_by) VALUES($1,$2,$3,$4) RETURNING id",
            titulo[:80], horario[:80], sala[:150], interaction.user.id)
    await interaction.response.send_message(f"Partida **#{row['id']}** criada.", ephemeral=True)

@bot.tree.command(name="fila_pagamentos", description="[Admin] Lista pagamentos pendentes.")
async def fila_pagamentos(interaction: discord.Interaction):
    if not await require_admin(interaction): return
    async with db.pool.acquire() as c:
        rows = await c.fetch("""SELECT p.id,p.registration_id,p.amount_cents,p.proof_reference,r.team_name
            FROM payments p JOIN registrations r ON r.id=p.registration_id WHERE p.status='review' ORDER BY p.created_at LIMIT 15""")
    if not rows:
        return await interaction.response.send_message("Fila vazia: não há pagamentos para revisar.", ephemeral=True)
    await interaction.response.send_message("\\n".join(
        f"Pagamento **#{r['id']}** | inscrição #{r['registration_id']} | {r['team_name']} | {money(r['amount_cents'])} | ref `{r['proof_reference'] or '—'}`"
        for r in rows), ephemeral=True)

@bot.tree.command(name="aprovar_pix", description="[Admin] Aprova após conferir o crédito no banco.")
async def aprovar_pix(interaction: discord.Interaction, pagamento_id: int):
    if not await require_admin(interaction): return
    async with db.pool.acquire() as c:
        async with c.transaction():
            row = await c.fetchrow("SELECT registration_id FROM payments WHERE id=$1 AND status='review' FOR UPDATE", pagamento_id)
            if not row:
                return await interaction.response.send_message("Pagamento não encontrado ou já analisado.", ephemeral=True)
            await c.execute("UPDATE payments SET status='approved',reviewed_by=$2,reviewed_at=NOW() WHERE id=$1", pagamento_id, interaction.user.id)
            await c.execute("UPDATE registrations SET status='confirmed' WHERE id=$1", row["registration_id"])
    await interaction.response.send_message(f"Pagamento #{pagamento_id} aprovado; inscrição confirmada.", ephemeral=True)

@bot.tree.command(name="reprovar_pix", description="[Admin] Reprova com justificativa.")
async def reprovar_pix(interaction: discord.Interaction, pagamento_id: int, motivo: str):
    if not await require_admin(interaction): return
    async with db.pool.acquire() as c:
        async with c.transaction():
            row = await c.fetchrow("SELECT registration_id FROM payments WHERE id=$1 AND status='review' FOR UPDATE", pagamento_id)
            if not row:
                return await interaction.response.send_message("Pagamento não encontrado ou já analisado.", ephemeral=True)
            await c.execute("UPDATE payments SET status='rejected',reviewed_by=$2,review_note=$3,reviewed_at=NOW() WHERE id=$1", pagamento_id, interaction.user.id, motivo[:250])
            await c.execute("UPDATE registrations SET status='awaiting_payment' WHERE id=$1", row["registration_id"])
    await interaction.response.send_message("Pagamento reprovado; justificativa registrada.", ephemeral=True)

@bot.tree.command(name="configurar_pix", description="[Admin] Configura chave PIX e recebedor.")
async def configurar_pix(interaction: discord.Interaction, chave: str, recebedor: str):
    if not await require_admin(interaction): return
    await db.set_setting("pix_key", chave[:160])
    await db.set_setting("pix_receiver", recebedor[:100])
    await interaction.response.send_message("Configuração PIX atualizada.", ephemeral=True)

@bot.tree.command(name="configurar_valores", description="[Admin] Ativa ou desativa um valor.")
@app_commands.choices(valor=[app_commands.Choice(name=k, value=v) for k, v in FEES.items()])
async def configurar_valores(interaction: discord.Interaction, valor: app_commands.Choice[int], ativo: bool):
    if not await require_admin(interaction): return
    current = {int(x) for x in (await db.setting("entry_options", "50,100,200,500,1000,2000,5000")).split(",") if x}
    if ativo: current.add(valor.value)
    else: current.discard(valor.value)
    if not current:
        return await interaction.response.send_message("Deixe ao menos uma modalidade ativa.", ephemeral=True)
    await db.set_setting("entry_options", ",".join(map(str, sorted(current))))
    await interaction.response.send_message(f"{money(valor.value)} {'ativado' if ativo else 'desativado'}.", ephemeral=True)

async def run():
    validate_settings()
    try:
        await bot.start(settings.discord_token)
    finally:
        await db.close()

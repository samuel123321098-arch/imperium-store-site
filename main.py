"""
Desenvolvido por Naoeocask
© 2025 Naoeocask

Você pode usar este código livremente, desde que dê os devidos créditos ao autor.
"""

import json
import os
import re
import io
import qrcode
import crcmod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

# ===== CARREGAR VARIÁVEIS DE AMBIENTE (.env) =====
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PIX_KEY = os.getenv("PIX_KEY", "")
CANAL_FEEDBACK_ID = int(os.getenv("CANAL_FEEDBACK", 0))
CANAL_LOGS_ID = int(os.getenv("CANAL_LOGS", 0))
CANAL_AVALIACOES_ID = int(os.getenv("CANAL_AVALIACOES", 0))

# ===== CONFIGURAÇÕES GLOBAIS =====
PAINEL_CHANNEL_ID = None
PAINEL_MESSAGE_ID = None

CONFIG = {
    "nome_loja": "Imperium store",
    "descricao_painel": "Bem-vindo(a)! Trabalhamos com venda de contas de Blox Fruits 👑",
    "pix_key": PIX_KEY,
    "categoria_tickets": "Tickets",
    "banner_url": "https://cdn.discordapp.com/attachments/1476268449184612415/1544433251869917285/standard_1.gif?ex=6a9dc30d&is=6a9c718d&hm=943fd6c8698cf1ab91cdf22bf42868ee079563877455ae39075cc6bd32c3540f&",
    "moeda": "R$",
    "canal_feedback": str(CANAL_FEEDBACK_ID),
    "cor_embed": 0x00FF00
}

DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
VITRINES_FILE = os.path.join(DATA_DIR, "vitrines.json")
STOCK_CONFIG_FILE = os.path.join(DATA_DIR, "stock_config.json")
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ===== GERADOR DE PAYLOAD E QR CODE PIX =====
def gerar_pix_payload(chave: str, valor: float, nome_recebedor: str = "Imperium Store", cidade: str = "SAO PAULO") -> str:
    """Gera a string do PIX Copia e Cola no padrão EMVCo/BR Code"""
    payload = (
        "000201"
        "010212"
        f"26{len(chave) + 22:02d}0014br.gov.bcb.pix01{len(chave):02d}{chave}"
        "52040000"
        "5303986"
        f"54{len(f'{valor:.2f}'):02d}{valor:.2f}"
        "5802BR"
        f"59{len(nome_recebedor):02d}{nome_recebedor}"
        f"60{len(cidade):02d}{cidade}"
        "62070503***"
        "6304"
    )
    crc16_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc = hex(crc16_func(payload.encode('utf-8')))[2:].upper().zfill(4)
    return payload + crc

def gerar_qrcode_bytes(payload: str) -> io.BytesIO:
    """Gera o arquivo PNG do QR Code em memória para o Discord"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ===== FUNÇÕES DE CARGA/SALVAMENTO =====
def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

products: Dict[str, Dict[str, Any]] = load_json(PRODUCTS_FILE, {})
persisted_config: Dict[str, Any] = load_json(CONFIG_FILE, {})
persisted_config.update(CONFIG)
save_json(CONFIG_FILE, persisted_config)

def recarregar_produtos():
    """Recarrega os produtos do arquivo para a memória global"""
    global products
    products = load_json(PRODUCTS_FILE, {})

# ===== CLASSE PRODUTO =====
@dataclass
class Produto:
    sku: str
    nome: str
    preco: float
    descricao: str
    estoque: int

    @staticmethod
    def from_dict(sku: str, d: Dict[str, Any]) -> "Produto":
        return Produto(
            sku=sku,
            nome=d.get("nome", sku),
            preco=float(d.get("preco", 0.0)),
            descricao=d.get("descricao", ""),
            estoque=int(d.get("estoque", 0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "preco": self.preco,
            "descricao": self.descricao,
            "estoque": self.estoque,
        }

def get_produto(sku: str) -> Optional[Produto]:
    recarregar_produtos()
    data = products.get(sku)
    if not data:
        return None
    return Produto.from_dict(sku, data)

def set_produto(p: Produto) -> None:
    products[p.sku] = p.to_dict()
    save_json(PRODUCTS_FILE, products)

# ===== FUNÇÕES AUXILIARES =====
def staff_role_name() -> str:
    return persisted_config.get("cargo_staff", "Vendedor")

def moeda() -> str:
    return persisted_config.get("moeda", "R$")

def cor_embed() -> int:
    return int(persisted_config.get("cor_embed", CONFIG["cor_embed"]))

def pix_key() -> str:
    return persisted_config.get("pix_key", PIX_KEY)

def tickets_category_name() -> str:
    return persisted_config.get("categoria_tickets", "Tickets")

def loja_nome() -> str:
    return persisted_config.get("nome_loja", "Minha Loja")

def banner_url() -> Optional[str]:
    return persisted_config.get("banner_url") or None

def canal_feedback_id() -> int:
    return int(persisted_config.get("canal_feedback", CANAL_FEEDBACK_ID))

# ===== FUNÇÃO ADMIN_ONLY =====
def admin_only():
    async def predicate(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Você precisa ser administrador para usar este comando.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# ===== FUNÇÃO CRIAR_EMBED =====
def criar_embed(title: str, description: str, color: int = cor_embed()) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Desenvolvido por naoeocask | github.com/naoeocask",
                     icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
    return embed

# ===== DEFINIÇÃO DO BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

active_tickets: Dict[int, Dict[str, int | str]] = {}

# ===== VIEW DO PAINEL ÚNICO (MENU DROPDOWN) =====
class PainelUnicoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        products_data = load_json(PRODUCTS_FILE, {})
        options = []

        for sku, dados in products_data.items():
            nome = dados.get("nome", sku)
            preco = dados.get("preco", 0.0)
            estoque = dados.get("estoque", 0)
            
            status_texto = f"R$ {preco:.2f} | Estoque: {estoque}" if estoque > 0 else "ESGOTADO"
            
            options.append(
                discord.SelectOption(
                    label=nome[:100],
                    value=sku,
                    description=status_texto[:100],
                    emoji="🛒" if estoque > 0 else "❌"
                )
            )

        if options:
            select = discord.ui.Select(
                placeholder="Selecione um produto para comprar...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="select_painel_unico"
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        sku = interaction.data["values"][0]
        produto = get_produto(sku)

        if not produto:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return

        if produto.estoque <= 0:
            await interaction.response.send_message("⚠️ Este produto está esgotado no momento!", ephemeral=True)
            return

        for ch_id, info in active_tickets.items():
            if info.get("user_id") == interaction.user.id and info.get("sku") == produto.sku:
                ch = interaction.guild.get_channel(ch_id)
                if ch:
                    await interaction.response.send_message(
                        f"⚠️ Você já tem um ticket aberto para este produto: {ch.mention}", ephemeral=True
                    )
                    return

        await interaction.response.defer(ephemeral=True)

        category = await ensure_tickets_category(interaction.guild)
        if not category:
            await interaction.followup.send("❌ Não consegui criar/achar a categoria de Tickets.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        staff_role = discord.utils.get(interaction.guild.roles, name=staff_role_name())
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"ticket-{interaction.user.name[:16]}-{produto.sku}".lower()
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {interaction.user.id} | SKU={produto.sku}"
        )

        active_tickets[ticket_channel.id] = {"user_id": interaction.user.id, "sku": produto.sku}

        # Gerando PIX e QR Code
        payload_pix = gerar_pix_payload(chave=pix_key(), valor=produto.preco, nome_recebedor=loja_nome())
        buffer_img = gerar_qrcode_bytes(payload_pix)
        file = discord.File(fp=buffer_img, filename="qrcode_pix.png")

        embed = criar_embed(
            title=f"🎫 Ticket de Compra — {produto.nome}",
            description=(
                f"**Preço:** {moeda()} {produto.preco:,.2f}\n"
                f"**Produto:** `{produto.nome}`\n\n"
                f"**Instruções de Pagamento:**\n"
                f"1. Escaneie o **QR Code** abaixo com o app do seu banco.\n"
                f"2. Ou use o **PIX Copia e Cola** abaixo:\n```\n{payload_pix}\n```\n"
                f"3. Envie o comprovante neste canal.\n"
                f"4. Aguarde a aprovação da staff."
            ),
            color=cor_embed()
        )
        embed.set_image(url="attachment://qrcode_pix.png")

        await ticket_channel.send(content=interaction.user.mention, embed=embed, file=file)
        await interaction.followup.send(f"✅ Ticket criado com sucesso: {ticket_channel.mention}", ephemeral=True)

# ===== ATUALIZAR PAINEL =====
async def atualizar_painel():
    """Atualiza a mensagem do painel único recriando o embed e as opções do Select Menu"""
    global PAINEL_CHANNEL_ID, PAINEL_MESSAGE_ID
    if not PAINEL_CHANNEL_ID or not PAINEL_MESSAGE_ID:
        return

    canal = bot.get_channel(PAINEL_CHANNEL_ID)
    if not canal:
        return

    try:
        mensagem = await canal.fetch_message(PAINEL_MESSAGE_ID)
    except:
        return

    products_data = load_json(PRODUCTS_FILE, {})

    embed = discord.Embed(
        title=f"🛒 {loja_nome()} — Vitrine de Produtos",
        description="Selecione o produto desejado no **menu abaixo** para abrir um ticket de compra automático.\n\n",
        color=cor_embed()
    )

    if not products_data:
        embed.description += "⚠️ Nenhum produto cadastrado no momento."
    else:
        for sku, dados in products_data.items():
            nome = dados.get('nome', 'Produto')
            preco = dados.get('preco', 0)
            estoque = dados.get('estoque', 0)
            status = f"✅ `{estoque}` disponível(is)" if estoque > 0 else "❌ **ESGOTADO**"
            embed.add_field(
                name=f"📦 {nome} — R$ {preco:.2f}",
                value=f"**Estoque:** {status}\n**SKU:** `{sku}`",
                inline=False
            )

    if banner_url():
        embed.set_image(url=banner_url())

    view = PainelUnicoView()
    await mensagem.edit(embed=embed, view=view)

    for sku in products_data.keys():
        await atualizar_vitrine(sku)

# ===== ATUALIZAR STOCK FIXO =====
async def atualizar_stock_novos():
    """Atualiza a mensagem fixa no canal de estoque com visual chamativo"""
    config = load_json(STOCK_CONFIG_FILE, {})
    if not config or "channel_id" not in config or "message_id" not in config:
        return

    canal = bot.get_channel(config["channel_id"])
    if not canal:
        return

    try:
        mensagem = await canal.fetch_message(config["message_id"])
    except:
        return

    products_data = load_json(PRODUCTS_FILE, {})

    if not products_data:
        embed = discord.Embed(
            title="📦 ESTOQUE VAZIO",
            description="Nenhum produto cadastrado no momento.",
            color=0xFF0000
        )
        await mensagem.edit(embed=embed)
        return

    em_estoque = []
    esgotados = []
    total_contas = 0
    valor_total = 0.0

    for sku, dados in products_data.items():
        nome = dados.get('nome', 'Produto')
        preco = dados.get('preco', 0)
        estoque = dados.get('estoque', 0)
        total_contas += estoque
        valor_total += preco * estoque

        if estoque > 0:
            em_estoque.append((sku, nome, preco, estoque))
        else:
            esgotados.append((sku, nome, preco))

    desc_parts = ["📊 **IMPERIUM STORE – ESTOQUE ATUAL**\n"]

    if em_estoque:
        desc_parts.append("✅ **EM ESTOQUE**")
        for sku, nome, preco, qtd in em_estoque:
            desc_parts.append(f"• **{nome}** | R$ {preco:.2f} | `{sku}`")
            desc_parts.append(f"   Estoque: {qtd} disponível{'is' if qtd > 1 else ''}")
            desc_parts.append("")
    else:
        desc_parts.append("⚠️ Nenhum produto em estoque no momento.\n")

    if esgotados:
        desc_parts.append("❌ **ESGOTADOS**")
        for sku, nome, preco in esgotados:
            desc_parts.append(f"• **{nome}** – R$ {preco:.2f} (`{sku}`)")

    desc_parts.append("")
    desc_parts.append(f"📌 **Total de contas:** {total_contas} | **Valor total em estoque:** R$ {valor_total:.2f}")

    cor = 0x00FF00 if em_estoque else 0xFF0000

    embed = discord.Embed(
        title="📊 IMPERIUM STORE",
        description="\n".join(desc_parts),
        color=cor
    )
    embed.set_footer(text=f"Última atualização: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}")
    if banner_url():
        embed.set_thumbnail(url=banner_url())

    await mensagem.edit(embed=embed)

# ===== FUNÇÃO LOG_VENDA =====
async def log_venda(interaction: discord.Interaction, produto_nome: str, preco: float, comprador: discord.Member, sku: str, conta: str):
    if CANAL_LOGS_ID == 0:
        return

    canal = bot.get_channel(CANAL_LOGS_ID)
    if not canal:
        return

    embed = discord.Embed(
        title="💰 Nova Venda",
        description=f"**Produto:** {produto_nome}\n**SKU:** `{sku}`\n**Preço:** R$ {preco:.2f}\n**Comprador:** {comprador.mention}\n**Atendente:** {interaction.user.mention}",
        color=0xFFD700
    )
    embed.add_field(name="🔑 Conta Entregue", value=f"```\n{conta}\n```", inline=False)
    embed.set_footer(text=f"Venda registrada em {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}")
    await canal.send(embed=embed)

# ===== OUTRAS FUNÇÕES AUXILIARES =====
async def ensure_tickets_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    cat_name = tickets_category_name()
    category = discord.utils.get(guild.categories, name=cat_name)
    if category is None:
        try:
            category = await guild.create_category(cat_name, reason="Categoria de Tickets (bot)")
        except discord.Forbidden:
            return None
    return category

def user_is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role = discord.utils.get(member.roles, name=staff_role_name())
    return role is not None

async def send_dm_safe(user: discord.User | discord.Member, embed: discord.Embed, content: Optional[str] = None):
    try:
        return await user.send(content=content, embed=embed)
    except discord.Forbidden:
        return None

# ===== ATUALIZAR VITRINE INDIVIDUAL =====
async def atualizar_vitrine(sku: str):
    try:
        produto = get_produto(sku)
        if not produto:
            return

        vitrines_data = load_json(VITRINES_FILE, {})
        if sku not in vitrines_data:
            return

        info = vitrines_data[sku]
        canal = bot.get_channel(info["channel_id"])
        if not canal:
            return

        try:
            mensagem = await canal.fetch_message(info["message_id"])
        except:
            return

        embed = mensagem.embeds[0] if mensagem.embeds else discord.Embed()
        desc = embed.description

        if desc and "Estoque:" in desc:
            nova_desc = re.sub(r'\*\*Estoque:\*\* \*\*\d+\*\*', f'**Estoque:** **{produto.estoque}**', desc)
            nova_desc = re.sub(r'Estoque: .+', f'Estoque: **{produto.estoque}**', nova_desc)
            embed.description = nova_desc
        else:
            embed.description = (
                f"{produto.descricao}\n\n"
                f"**Preço:** {moeda()} {produto.preco:,.2f}\n"
                f"**Estoque:** **{produto.estoque}**\n"
                f"**SKU:** `{produto.sku}`\n\n"
                f"Clique em **Comprar** para abrir um ticket privado."
            )

        await mensagem.edit(embed=embed)
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar vitrine do SKU {sku}: {e}")

# ===== EVENTO ON_READY =====
@bot.event
async def on_ready():
    recarregar_produtos()
    bot.add_view(PainelUnicoView())
    try:
        synced = await bot.tree.sync()
        print(f"[OK] Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print("Erro ao sincronizar comandos:", e)
    print(f"Logado como {bot.user} (ID: {bot.user.id})")
    
    await atualizar_painel()
    await atualizar_stock_novos()

# ===== COMANDOS =====
@bot.command(name="desligar")
async def desligar(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você precisa ser administrador para usar este comando.")
        return
    await ctx.send("🔄 Desligando o bot...")
    await bot.close()

@bot.tree.command(name="postar_painel_unico", description="Envia o painel geral de vendas com menu de seleção")
@admin_only()
async def postar_painel_unico(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    products_data = load_json(PRODUCTS_FILE, {})
    embed = discord.Embed(
        title=f"🛒 {loja_nome()} — Vitrine de Produtos",
        description="Selecione o produto desejado no **menu abaixo** para abrir um ticket de compra automático.\n\n",
        color=cor_embed()
    )

    for sku, dados in products_data.items():
        nome = dados.get('nome', 'Produto')
        preco = dados.get('preco', 0)
        estoque = dados.get('estoque', 0)
        status = f"✅ `{estoque}` disponível(is)" if estoque > 0 else "❌ **ESGOTADO**"
        embed.add_field(
            name=f"📦 {nome} — R$ {preco:.2f}",
            value=f"**Estoque:** {status}\n**SKU:** `{sku}`",
            inline=False
        )

    if banner_url():
        embed.set_image(url=banner_url())

    view = PainelUnicoView()
    mensagem = await interaction.channel.send(embed=embed, view=view)

    global PAINEL_CHANNEL_ID, PAINEL_MESSAGE_ID
    PAINEL_CHANNEL_ID = interaction.channel.id
    PAINEL_MESSAGE_ID = mensagem.id

    save_json(os.path.join(DATA_DIR, "painel_config.json"), {
        "channel_id": PAINEL_CHANNEL_ID,
        "message_id": PAINEL_MESSAGE_ID
    })

    await interaction.followup.send("✅ Painel único postado e configurado como principal!", ephemeral=True)

@bot.tree.command(name="produtos", description="Lista produtos disponíveis")
async def produtos_cmd(interaction: discord.Interaction):
    recarregar_produtos()
    if not products:
        await interaction.response.send_message("Ainda não há produtos cadastrados.", ephemeral=True)
        return

    desc = []
    for sku, data in products.items():
        p = Produto.from_dict(sku, data)
        desc.append(f"**{p.nome}** — `{sku}`\nPreço: {moeda()} {p.preco:,.2f} | Estoque: **{p.estoque}**\n")

    embed = criar_embed(
        title=f"🛒 Produtos — {loja_nome()}",
        description="\n".join(desc),
        color=cor_embed()
    )
    if banner_url():
        embed.set_thumbnail(url=banner_url())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="criar_produto", description="Adiciona/atualiza um produto")
@admin_only()
@app_commands.describe(
    sku="Identificador único (ex: LOJA1X)",
    nome="Nome exibido",
    preco="Preço (ex: 99.90)",
    descricao="Descrição curta do produto"
)
async def admin_add_produto(interaction: discord.Interaction, sku: str, nome: str, preco: float, descricao: str):
    sku = sku.upper()
    p = get_produto(sku) or Produto(sku=sku, nome=nome, preco=preco, descricao=descricao, estoque=0)
    p.nome = nome
    p.preco = preco
    p.descricao = descricao
    set_produto(p)
    await atualizar_painel()
    await interaction.response.send_message(f"✅ Produto **{p.nome}** (`{p.sku}`) salvo. Estoque: {p.estoque}", ephemeral=True)

@bot.tree.command(name="fixar_stock", description="Envia uma nova mensagem de estoque no canal informado")
@admin_only()
@app_commands.describe(canal_id="ID do canal onde a mensagem de estoque será enviada")
async def fixar_stock(interaction: discord.Interaction, canal_id: str):
    await interaction.response.defer(ephemeral=True)

    try:
        canal_id = int(canal_id)
    except ValueError:
        await interaction.followup.send("❌ O ID do canal deve ser um número inteiro.", ephemeral=True)
        return

    canal = bot.get_channel(canal_id)
    if not canal:
        await interaction.followup.send("❌ Canal não encontrado. Verifique o ID.", ephemeral=True)
        return

    products_data = load_json(PRODUCTS_FILE, {})

    if not products_data:
        embed = discord.Embed(
            title="📦 ESTOQUE VAZIO",
            description="Nenhum produto cadastrado.",
            color=0xFF0000
        )
    else:
        linhas = []
        total_estoque = 0
        for sku, dados in products_data.items():
            nome = dados.get('nome', 'Produto')
            estoque = dados.get('estoque', 0)
            total_estoque += estoque
            status = "✅" if estoque > 0 else "❌"
            linhas.append(f"`{sku}` **{nome}** — {status} **{estoque}**")
        embed = discord.Embed(
            title="📊 ESTOQUE DISPONÍVEL",
            description="\n".join(linhas),
            color=0x00FF00
        )
        embed.set_footer(text=f"Total de produtos: {len(products_data)} | Total de contas: {total_estoque}")

    mensagem = await canal.send(embed=embed)

    config = {
        "channel_id": canal_id,
        "message_id": mensagem.id
    }
    save_json(STOCK_CONFIG_FILE, config)

    await atualizar_stock_novos()

    await interaction.followup.send(
        f"✅ Mensagem de estoque enviada e configurada!\n"
        f"**Canal:** {canal.mention}\n"
        f"**Mensagem ID:** `{mensagem.id}`\n"
        f"O estoque será atualizado automaticamente.",
        ephemeral=True
    )

@bot.tree.command(name="atualizar_preco", description="Atualiza preço de um produto")
@admin_only()
@app_commands.describe(sku="SKU", preco="Novo preço")
async def admin_set_preco(interaction: discord.Interaction, sku: str, preco: float):
    p = get_produto(sku.upper())
    if not p:
        await interaction.response.send_message("❌ SKU não encontrado.", ephemeral=True)
        return
    p.preco = preco
    set_produto(p)
    await atualizar_painel()
    await interaction.response.send_message(f"✅ Preço atualizado para {moeda()} {p.preco:,.2f} em `{p.sku}`.", ephemeral=True)

@bot.tree.command(name="listar_produtos_admin", description="Lista todos os produtos (detalhado para staff)")
@admin_only()
async def admin_list_produtos(interaction: discord.Interaction):
    recarregar_produtos()
    if not products:
        await interaction.response.send_message("Não há produtos.", ephemeral=True)
        return
    desc = []
    for sku, data in products.items():
        p = Produto.from_dict(sku, data)
        desc.append(f"• **{p.nome}** (`{p.sku}`) — {moeda()} {p.preco:,.2f} | Estoque: {p.estoque}")
    embed = criar_embed(title="📦 Produtos (Admin)", description="\n".join(desc), color=cor_embed())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="definir_pix", description="Define a chave PIX do painel")
@admin_only()
@app_commands.describe(chave="Chave PIX")
async def admin_set_pix(interaction: discord.Interaction, chave: str):
    persisted_config["pix_key"] = chave
    save_json(CONFIG_FILE, persisted_config)
    await interaction.response.send_message("✅ Chave PIX atualizada.", ephemeral=True)

@bot.tree.command(name="definir_cargo_staff", description="Define o nome do cargo de staff")
@admin_only()
@app_commands.describe(cargo="Nome exato do cargo")
async def admin_set_staff(interaction: discord.Interaction, cargo: str):
    persisted_config["cargo_staff"] = cargo
    save_json(CONFIG_FILE, persisted_config)
    await interaction.response.send_message(f"✅ Cargo de staff atualizado para **{cargo}**.", ephemeral=True)

@bot.tree.command(name="definir_categoria_ticket", description="Define/Cria a categoria de tickets")
@admin_only()
@app_commands.describe(nome="Nome da categoria")
async def admin_set_categoria(interaction: discord.Interaction, nome: str):
    persisted_config["categoria_tickets"] = nome
    save_json(CONFIG_FILE, persisted_config)
    cat = await ensure_tickets_category(interaction.guild)
    if cat:
        await interaction.response.send_message(f"✅ Categoria definida: **{cat.name}**.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Não consegui criar a categoria (permissões?).", ephemeral=True)

@bot.tree.command(name="ajuda_vendas", description="Lista comandos e suas funções")
async def ajuda_cmd(interaction: discord.Interaction):
    txt = (
        "**Comandos disponíveis:**\n"
        "• `/postar_painel_unico` — Posta o painel geral de produtos com menu dropdown\n"
        "• `/criar_produto` — Adiciona ou atualiza um produto\n"
        "• `/addkey` — Adiciona contas/chaves ao estoque de um produto\n"
        "• `/aprovar` — Aprova ticket e envia código por DM\n"
        "• `/recusar` — Recusa ticket\n"
        "• `/atualizar_preco` — Atualiza o preço de um produto\n"
        "• `/listar_produtos_admin` — Lista todos os produtos detalhado (staff)\n"
        "• `/definir_pix` — Define a chave PIX do painel\n"
        "• `/definir_cargo_staff` — Define o cargo de staff\n"
        "• `/definir_categoria_ticket` — Define/Cria categoria de tickets\n"
        "• `/produtos` — Lista produtos disponíveis para clientes\n"
        "• `/remover_produto` — Deleta um produto pelo SKU\n"
        "• `/estoque` — Mostra o estoque atual (comando rápido)\n"
        "• `/fixar_stock` — Define a mensagem fixa para atualização automática do estoque"
    )
    await interaction.response.send_message(txt, ephemeral=True)

@bot.tree.command(name="estoque", description="Mostra o estoque atual de todos os produtos")
async def estoque_cmd(interaction: discord.Interaction):
    products_data = load_json(PRODUCTS_FILE, {})

    if not products_data:
        await interaction.response.send_message("📦 Nenhum produto cadastrado.", ephemeral=True)
        return

    linhas = []
    for sku, dados in products_data.items():
        nome = dados.get('nome', 'Produto')
        estoque = dados.get('estoque', 0)
        status = "✅" if estoque > 0 else "❌"
        linhas.append(f"`{sku}` **{nome}** — {status} **{estoque}** disponível")

    embed = discord.Embed(
        title="📊 ESTOQUE ATUAL",
        description="\n".join(linhas),
        color=0x00FF00
    )
    embed.set_footer(text=f"Total de produtos: {len(products_data)}")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="aprovar", description="Aprova ticket e envia 1 código por DM")
@admin_only()
async def aprovar_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    try:
        ch = interaction.channel
        if not isinstance(ch, discord.TextChannel):
            await interaction.followup.send("Use isso dentro do canal do ticket.", ephemeral=True)
            return

        info = active_tickets.get(ch.id)
        if not info and ch.topic and "SKU=" in ch.topic and "Ticket de " in ch.topic:
            try:
                uid = int(ch.topic.split("Ticket de ")[1].split(" | ")[0])
                sku = ch.topic.split("SKU=")[1].strip()
                info = {"user_id": uid, "sku": sku}
                active_tickets[ch.id] = info
            except:
                pass

        if not info:
            await interaction.followup.send("❌ Não consegui identificar o ticket.", ephemeral=True)
            return

        user = interaction.guild.get_member(info["user_id"])
        sku = str(info["sku"])

        # Verifica se há chaves disponíveis antes de alterar o estoque
        keys_data = load_json(KEYS_FILE, {})
        if sku not in keys_data or not keys_data[sku]:
            await interaction.followup.send("❌ Não há contas disponíveis no estoque para este produto!", ephemeral=True)
            return

        products_data = load_json(PRODUCTS_FILE, {})
        produto_encontrado = products_data.get(sku)

        if not produto_encontrado:
            await interaction.followup.send("❌ Produto não encontrado no estoque.", ephemeral=True)
            return

        if produto_encontrado.get('estoque', 0) <= 0:
            await interaction.followup.send("⚠️ Produto esgotado!", ephemeral=True)
            return

        # Retira a conta do arquivo de keys e atualiza estoque sincronizado
        conta = keys_data[sku].pop(0)
        save_json(KEYS_FILE, keys_data)

        produto_encontrado['estoque'] = len(keys_data[sku])
        save_json(PRODUCTS_FILE, products_data)
        recarregar_produtos()

        produto = get_produto(sku)

        await atualizar_painel()
        await atualizar_stock_novos()

        try:
            await user.send(f"✅ **Sua compra foi aprovada!**\n\n**Produto:** {produto.nome}\n**Preço:** R$ {produto.preco:.2f}\n\n**📝 Dados da conta:**\n```\n{conta}\n```\n\n🔒 Troque a senha após o login.")
        except:
            await interaction.channel.send(f"⚠️ Não foi possível enviar DM para {user.mention}. Envie manualmente:\n```\n{conta}\n```")
        finally:
            await log_venda(interaction, produto.nome, produto.preco, user, sku, conta)

        await interaction.followup.send("✅ Compra aprovada e conta enviada!", ephemeral=True)

        active_tickets.pop(ch.id, None)
        try:
            await ch.delete(reason="Ticket finalizado (aprovado)")
        except:
            await ch.send("⚠️ Não consegui apagar o canal (permissões).")

    except Exception as e:
        print(f"[ERRO] /aprovar: {e}")
        await interaction.followup.send(f"❌ Ocorreu um erro: {e}", ephemeral=True)

@bot.tree.command(name="remover_produto", description="Deleta um produto pelo SKU")
@admin_only()
@app_commands.describe(sku="SKU do produto a ser deletado")
async def admin_del_produto(interaction: discord.Interaction, sku: str):
    sku = sku.upper()
    recarregar_produtos()
    if sku not in products:
        await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
        return
    products.pop(sku)
    save_json(PRODUCTS_FILE, products)
    await atualizar_painel()
    await interaction.response.send_message(f"✅ Produto `{sku}` deletado com sucesso.", ephemeral=True)

@bot.tree.command(name="recusar", description="Recusa ticket")
@admin_only()
@app_commands.describe(motivo="Motivo opcional")
async def recusar_cmd(interaction: discord.Interaction, motivo: Optional[str] = None):
    await interaction.response.defer(ephemeral=True)

    ch = interaction.channel
    if not isinstance(ch, discord.TextChannel):
        await interaction.followup.send("Use isso dentro do canal do ticket.", ephemeral=True)
        return

    info = active_tickets.get(ch.id)
    if not info and ch.topic and "SKU=" in ch.topic and "Ticket de " in ch.topic:
        try:
            uid = int(ch.topic.split("Ticket de ")[1].split(" | ")[0])
            sku = ch.topic.split("SKU=")[1].strip()
            info = {"user_id": uid, "sku": sku}
            active_tickets[ch.id] = info
        except:
            pass

    user = interaction.guild.get_member(info["user_id"]) if info else None
    texto = "❌ Seu pedido foi **recusado**."
    if motivo:
        texto += f"\n**Motivo:** {motivo}"

    if user:
        embed_dm = criar_embed(title="❌ Pedido recusado", description=texto, color=0xED4245)
        await send_dm_safe(user, embed_dm)

    await interaction.followup.send("✅ Ticket recusado.", ephemeral=True)
    active_tickets.pop(ch.id, None)
    try:
        await ch.delete(reason="Ticket finalizado (recusado)")
    except:
        await ch.send("⚠️ Não consegui apagar o canal (permissões?).")

@bot.tree.command(name="addkey", description="Adiciona uma ou mais contas ao estoque de um produto")
@admin_only()
@app_commands.describe(sku="SKU do produto", contas="Contas separadas por pipe (|)")
async def addkey(interaction: discord.Interaction, sku: str, contas: str):
    sku = sku.upper()
    await interaction.response.defer(ephemeral=True)

    try:
        keys_data = load_json(KEYS_FILE, {})
        lista_contas = [c.strip() for c in contas.split('|') if c.strip()]

        if sku not in keys_data:
            keys_data[sku] = []

        keys_data[sku].extend(lista_contas)
        save_json(KEYS_FILE, keys_data)

        products_data = load_json(PRODUCTS_FILE, {})

        if sku in products_data:
            products_data[sku]['estoque'] = len(keys_data[sku])
            save_json(PRODUCTS_FILE, products_data)
            recarregar_produtos()

            await atualizar_painel()
            await atualizar_stock_novos()

        await interaction.followup.send(
            f"✅ Adicionadas {len(lista_contas)} conta(s) ao SKU `{sku}`.\n"
            f"Estoque atual: {len(keys_data[sku])}",
            ephemeral=True
        )
    except Exception as e:
        print(f"[ERRO] /addkey: {e}")
        await interaction.followup.send(f"❌ Erro ao adicionar contas: {e}", ephemeral=True)

@bot.tree.command(name="configurar_painel", description="Define o painel oficial informando IDs do canal e da mensagem")
@admin_only()
@app_commands.describe(
    canal_id="ID do canal onde está a mensagem do painel",
    mensagem_id="ID da mensagem do painel"
)
async def configurar_painel(interaction: discord.Interaction, canal_id: str, mensagem_id: str):
    await interaction.response.defer(ephemeral=True)

    global PAINEL_CHANNEL_ID, PAINEL_MESSAGE_ID

    try:
        canal_id = int(canal_id)
        mensagem_id = int(mensagem_id)
    except ValueError:
        await interaction.followup.send("❌ Os IDs devem ser números inteiros.", ephemeral=True)
        return

    canal = bot.get_channel(canal_id)
    if not canal:
        await interaction.followup.send("❌ Canal não encontrado. Verifique o ID.", ephemeral=True)
        return

    try:
        mensagem = await canal.fetch_message(mensagem_id)
    except:
        await interaction.followup.send("❌ Mensagem não encontrada. Verifique o ID e se ela está no canal informado.", ephemeral=True)
        return

    PAINEL_CHANNEL_ID = canal_id
    PAINEL_MESSAGE_ID = mensagem_id

    save_json(os.path.join(DATA_DIR, "painel_config.json"), {
        "channel_id": PAINEL_CHANNEL_ID,
        "message_id": PAINEL_MESSAGE_ID
    })

    await atualizar_painel()
    await atualizar_stock_novos()

    await interaction.followup.send(
        f"✅ Painel configurado e atualizado com sucesso!\n"
        f"**Canal:** {canal.mention}\n"
        f"**Mensagem ID:** `{mensagem_id}`",
        ephemeral=True
    )

@bot.tree.command(name="avaliar", description="Avalie a loja após sua compra")
@app_commands.describe(nota="Nota de 1 a 5", comentario="Comentário opcional")
async def avaliar(interaction: discord.Interaction, nota: int, comentario: Optional[str] = None):
    if nota < 1 or nota > 5:
        await interaction.response.send_message("⚠️ Nota deve ser entre 1 e 5.", ephemeral=True)
        return

    if CANAL_AVALIACOES_ID == 0:
        await interaction.response.send_message("❌ Canal de avaliações não configurado.", ephemeral=True)
        return

    canal = bot.get_channel(CANAL_AVALIACOES_ID)
    if not canal:
        await interaction.response.send_message("❌ Canal de avaliações não encontrado.", ephemeral=True)
        return

    estrelas = "⭐" * nota + "☆" * (5 - nota)
    embed = discord.Embed(
        title="📝 Nova Avaliação",
        description=f"**Usuário:** {interaction.user.mention}\n**Nota:** {estrelas} ({nota}/5)",
        color=0x00FF00
    )
    if comentario:
        embed.add_field(name="💬 Comentário", value=comentario, inline=False)
    embed.set_footer(text=f"ID: {interaction.user.id}")

    await canal.send(embed=embed)
    await interaction.response.send_message("✅ Avaliação enviada com sucesso! Obrigado!", ephemeral=True)

# ===== COMANDO DE SINCRONIZAÇÃO MANUAL =====
@bot.command(name="sync")
async def sync(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você precisa ser administrador para usar este comando.")
        return
    await bot.tree.sync()
    await ctx.send("✅ Comandos sincronizados!")

# ===== CARREGAR CONFIGURAÇÃO DO PAINEL =====
painel_config_file = os.path.join(DATA_DIR, "painel_config.json")
if os.path.exists(painel_config_file):
    config = load_json(painel_config_file, {})
    PAINEL_CHANNEL_ID = config.get("channel_id")
    PAINEL_MESSAGE_ID = config.get("message_id")
    print("✅ Configuração do painel carregada!")

# ===== RODAR O BOT =====
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERRO: O DISCORD_TOKEN não foi encontrado no arquivo .env!")
    else:
        bot.run(DISCORD_TOKEN)
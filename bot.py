import discord
from discord.ext import commands
import random
import re
import logging
import atexit
from datetime import datetime, timezone
import psutil
import asyncio
import os
from dotenv import load_dotenv
import psutil

# --- Intents設定 ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot_start_time = datetime.now(timezone.utc)

# --- ログ設定 ---
class ExcludeMessageLogsFilter(logging.Filter):
    def filter(self, record):
        return "UserMessage" not in record.getMessage()

log_filename = f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(ExcludeMessageLogsFilter())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, console_handler]
)

# --- 起動時イベント ---
@bot.event
async def on_ready():
    print(f"✅ Bot Logged in as {bot.user}")

# --- エラーハンドリング ---
@bot.event
async def on_command_error(ctx, error):
    if re.fullmatch(r"!([1-9][0-9]*)d([1-9][0-9]*)", ctx.message.content.strip()):
        return
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("⚠️ 未知のコマンドです。`!bot_help`で使用可能なコマンドを確認してください。")
    else:
        raise error

# --- ヘルプコマンド ---
@bot.command(name='bot_help')
async def help_command(ctx):
    embed = discord.Embed(
        title="🛠 コマンド一覧",
        description="Botで使用可能なコマンドの一覧です。",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎵 音楽", value="`!play URL`, `!volume 数値`, `!join`, `!leave`, `!pause`, `!resume`, `!skip`,`!repeat`,`!queue`,`!stop`", inline=False)
    embed.add_field(name="🎮 ミニゲーム", value="`!スロット`, `!じゃんけん グー/チョキ/パー`", inline=False)
    embed.add_field(name="🎲 ダイス", value="`!AdB`形式でダイスロール（例：`!1d6`, `!3d10000`）", inline=False)
    embed.add_field(name="📊 ステータス", value="`!status`：Botの応答速度やリソース情報", inline=False)
    await ctx.send(embed=embed)

# --- メッセージ受信処理 ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    author = f"{message.author.name}#{message.author.discriminator}"

    if isinstance(message.channel, discord.TextChannel):
        channel_name = f"#{message.channel.name}"
    elif isinstance(message.channel, discord.DMChannel):
        channel_name = "📩 DM"
    elif isinstance(message.channel, discord.Thread):
        channel_name = f"🧵 {message.channel.name}"
    else:
        channel_name = str(message.channel)

    print(f"\033[92m[{timestamp}]\033[0m \033[96m{author}\033[0m in \033[93m{channel_name}\033[0m: {message.content}")
    logging.info(f"[UserMessage] {timestamp} {author} in {channel_name}: {message.content}")

    # ダイス判定
    dice_match = re.fullmatch(r"!([1-9][0-9]*)d([1-9][0-9]*)", message.content.strip())
    if dice_match:
        count = int(dice_match.group(1))
        sides = int(dice_match.group(2))

        if not (1 <= count <= 100):
            await message.channel.send("⚠️ サイコロの数は1〜100個にしてください。")
            return
        if not (1 <= sides <= 10000):
            await message.channel.send("⚠️ 面の数は1〜10000にしてください。")
            return

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        rolls_str = ', '.join(str(r) for r in rolls)

        await message.channel.send(
            f"🎲 {sides}面ダイスを{count}個振りました！\n"
            f"出目: [{rolls_str}]\n合計: **{total}**"
        )
        return

    await bot.process_commands(message)

# --- ステータスコマンド ---
@bot.command()
async def status(ctx):
    start_time = discord.utils.utcnow()
    msg = await ctx.send("📊 ステータスを測定中...")
    end_time = discord.utils.utcnow()
    api_latency = (end_time - start_time).total_seconds() * 1000
    websocket_latency = bot.latency * 1000

    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    mem_used_mb = mem.used // (1024 * 1024)
    mem_total_mb = mem.total // (1024 * 1024)
    mem_percent = mem.percent

    uptime_delta = datetime.now(timezone.utc) - bot_start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}時間 {minutes}分 {seconds}秒"

    embed = discord.Embed(
        title="📊 Botステータス",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="📡 API応答速度", value=f"{api_latency:.2f}ms", inline=True)
    embed.add_field(name="🔌 WebSocket遅延", value=f"{websocket_latency:.2f}ms", inline=True)
    embed.add_field(name="🧠 CPU使用率", value=f"{cpu_percent:.1f}%", inline=True)
    embed.add_field(
        name="💾 メモリ使用量",
        value=f"{mem_used_mb}MB / {mem_total_mb}MB ({mem_percent:.1f}%)",
        inline=False
    )
    embed.add_field(name="⏱ Uptime（稼働時間）", value=uptime_str, inline=False)
    embed.set_footer(text=f"{bot.user.name} | ステータス情報")

    await msg.edit(content=None, embed=embed)


# --- 終了ログ ---
def on_exit():
    logging.info("Bot has finished. Log saved.")
atexit.register(on_exit)

# --- 起動処理 ---
import os
import logging
from dotenv import load_dotenv

async def main():
    load_dotenv()

    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    if TOKEN:  # ← 修正
        print("✅ トークンを読み込みました:", TOKEN[:10], "...")
    else:
        print("❌ トークンが読み込めませんでした。")
        return  # トークンがない場合はここで終了した方が安全

    async with bot:
        try:
            await bot.load_extension("minigames")
            await bot.load_extension("music_youtube")
            await bot.load_extension("host_info")
        except Exception as e:
            logging.error(f"拡張の読み込みに失敗: {e}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[PCからの入力によりBotが停止しました。正常に停止できました。]")

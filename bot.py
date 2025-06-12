import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
import atexit
from datetime import datetime, timezone
import psutil
import asyncio
import os
from dotenv import load_dotenv

# --- Intents設定 ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True

# プレフィックス無しのBot（スラッシュコマンド用）
bot = commands.Bot(command_prefix=None, intents=intents)
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
    # スラッシュコマンドをDiscordに登録（全ギルド or グローバル）
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)}個のスラッシュコマンドを同期しました。")
    except Exception as e:
        print(f"❌ スラッシュコマンドの同期に失敗しました: {e}")

# --- エラーハンドリング ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # コマンドが見つからないエラーは通常は起きにくいですが念のため
    if isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("⚠️ 未知のコマンドです。", ephemeral=True)
    else:
        logging.error(f"スラッシュコマンドエラー: {error}")
        # エラー内容をユーザーに簡単に通知
        try:
            await interaction.response.send_message(f"⚠️ エラーが発生しました: {error}", ephemeral=True)
        except Exception:
            pass

# --- ヘルプコマンド（スラッシュ） ---
@bot.tree.command(name="bot_help", description="使用可能なコマンド一覧を表示します")
async def bot_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠 コマンド一覧",
        description="Botで使用可能なコマンドの一覧です。",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎵 音楽", value="`/play URL`, `/volume 数値`, `/join`, `/leave`, `/pause`, `/resume`, `/skip`,`/repeat`,`/queue`,`/stop`", inline=False)
    embed.add_field(name="🎮 ミニゲーム", value="`/slot`, `/janken グー/チョキ/パー`", inline=False)
    embed.add_field(name="🎲 ダイス", value="`/dice 個数 面数`形式でダイスロール（例：`/dice count:3 sides:6`）", inline=False)
    embed.add_field(name="📊 ステータス", value="`/status`：Botの応答速度やリソース情報", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- ダイスコマンド（スラッシュ） ---
@bot.tree.command(name="dice", description="指定した個数・面数のダイスを振ります")
@app_commands.describe(count="振るサイコロの数（1〜100）", sides="サイコロの面数（1〜10000）")
async def dice(interaction: discord.Interaction, count: int, sides: int):
    if not (1 <= count <= 100):
        await interaction.response.send_message("⚠️ サイコロの数は1〜100個にしてください。", ephemeral=True)
        return
    if not (1 <= sides <= 10000):
        await interaction.response.send_message("⚠️ 面の数は1〜10000にしてください。", ephemeral=True)
        return

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    rolls_str = ', '.join(str(r) for r in rolls)

    await interaction.response.send_message(
        f"🎲 {sides}面ダイスを{count}個振りました！\n"
        f"出目: [{rolls_str}]\n合計: **{total}**"
    )

# --- ステータスコマンド（スラッシュ） ---
@bot.tree.command(name="status", description="Botの応答速度やリソース情報を表示します")
async def status(interaction: discord.Interaction):
    start_time = discord.utils.utcnow()
    msg = await interaction.response.send_message("📊 ステータスを測定中...", ephemeral=True)
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

    # interaction.response.send_messageは1回しか呼べないためeditで送る場合はfollowupを使う必要があるが
    # 今回は即時返信にembedを乗せて終了するので問題なし
    await interaction.edit_original_response(embed=embed)

# --- 終了ログ ---
def on_exit():
    logging.info("Bot has finished. Log saved.")
atexit.register(on_exit)

# --- 起動処理 ---
async def main():
    load_dotenv()

    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("❌ トークンが読み込めませんでした。")
        return

    print("✅ トークンを読み込みました:", TOKEN[:10] + "...")

    async with bot:
        try:
            await bot.load_extension("minigames")
            await bot.load_extension("music_youtube")
            await bot.load_extension("host_info")
        except Exception as e:
            logging.error(f"拡張の読み込みに失敗しました: {e}")
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[PCからの入力によりBotが停止しました。正常に停止できました。]")

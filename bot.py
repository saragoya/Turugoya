import discord
from discord.ext import commands
import random
import re
import logging
import atexit
from datetime import datetime, timezone
import psutil
import yt_dlp
from discord import FFmpegPCMAudio

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot_start_time = datetime.now(timezone.utc)


class ExcludeMessageLogsFilter(logging.Filter):
    def filter(self, record):
        # "UserMessage" というタグが含まれるログはコンソールに表示しない
        return "UserMessage" not in record.getMessage()

log_filename = f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# ファイルにはすべて記録
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# コンソールには "UserMessage" を除外して出力
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(ExcludeMessageLogsFilter())

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, console_handler]
)

@bot.command(aliases=["ジャンケン", "じゃんけん"])
async def janken(ctx, user_hand: str):
    print(f"じゃんけん実行: {user_hand}")
    hands = ['グー', 'チョキ', 'パー']
    bot_hand = random.choice(hands)
    print(f"Botの手: {bot_hand}")

    if user_hand not in hands:
        await ctx.send("無効な手です!「グー」「チョキ」「パー」から選んでね。")
        return

    if user_hand == bot_hand:
        result = "あいこ!"
    elif (
        (user_hand == "グー" and bot_hand == "チョキ") or
        (user_hand == "チョキ" and bot_hand == "パー") or
        (user_hand == "パー" and bot_hand == "グー")
    ):
        result = "あなたの勝ち!🎉"
    else:
        result = "Botの勝ち!"

    print(f"結果: {result}")
    await ctx.send(f"あなた: {user_hand} | Bot: {bot_hand}\n{result}")


@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("ボイスチャンネルに参加しました。")
    else:
        await ctx.send("あなたはボイスチャンネルに参加していません。")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("切断しました。")
    else:
        await ctx.send("Botはボイスチャンネルに参加していません。")

@bot.command()
async def play_Y(ctx, *, url):
    vc = ctx.voice_client
    if not vc:
        await ctx.send("先に `!join` でボイスチャンネルに参加させてください。")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        title = info.get("title", "（タイトル不明）")

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    source = FFmpegPCMAudio(audio_url, **ffmpeg_options)
    vc.play(source)

    await ctx.send(f"再生中: {title}")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("再生を停止しました。")
    else:
        await ctx.send("現在再生中の音声はありません。")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("再生を一時停止しました。")
    else:
        await ctx.send("再生中の音声がありません。")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("再生を再開しました。")
    else:
        await ctx.send("一時停止中の音声はありません。")

@bot.command()
async def スロット(ctx):
    symbols = ['🍒', '🍋', '🍊', '🔔', '⭐', '7️⃣']
    weights = [30, 25, 20, 15, 7, 3]
    result = random.choices(symbols, weights=weights, k=3)
    await ctx.send(f"| {' | '.join(result)} |")

    counts = {sym: result.count(sym) for sym in symbols}
    if counts['7️⃣'] == 3:
        await ctx.send(f"🎉 ジャックポット!7️⃣が3つ揃ったよ!大当たり! {result}")
    elif counts['7️⃣'] == 2:
        await ctx.send(f"✨ ナイス!7️⃣が2つ揃った! {result}")
    if result[0] == result[1] == result[2]:
        await ctx.send("🎉 おめでとう!3つ揃いました!当たり!")
    else:
        await ctx.send("残念、揃いませんでした…また挑戦してね!")

# ダイス正規表現
dice_pattern = re.compile(r'^!(\d+)d(\d+)$')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    author = f"{message.author.name}#{message.author.discriminator}"

    # チャンネルの種類に応じて表示名を変える
    if isinstance(message.channel, discord.TextChannel):
        channel_name = f"#{message.channel.name}"
    elif isinstance(message.channel, discord.DMChannel):
        channel_name = "📩 DM"
    elif isinstance(message.channel, discord.Thread):
        channel_name = f"🧵 {message.channel.name}"
    else:
        channel_name = str(message.channel)  # fallback

    # CMD出力（カラー表示）
    print(f"\033[92m[{timestamp}]\033[0m \033[96m{author}\033[0m in \033[93m{channel_name}\033[0m: {message.content}")

    # ログファイルに書き込み
    logging.info(f"[UserMessage] {timestamp} {author} in {channel_name}: {message.content}")

    # ダイス判定
    match = dice_pattern.match(message.content)
    if match:
        count = int(match.group(1))
        sides = int(match.group(2))
        logging.info(f"{message.author} が !{count}d{sides} を使いました")

        if count < 1 or count > 100:
            await message.channel.send("⚠️ ダイスの数は1〜100個にしてください。")
            return
        if sides < 1 or sides > 10000:
            await message.channel.send("⚠️ 面の数は1〜10000にしてください。")
            return

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        rolls_str = ', '.join(str(r) for r in rolls)
        result = f"🎲 {sides}面ダイスを{count}個振りました！\n出目: [{rolls_str}]\n合計: **{total}**"

        await message.channel.send(result)
        logging.info(result)
        return

    # 他のコマンドも通す
    await bot.process_commands(message)

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
        timestamp = datetime.now(timezone.utc)
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

def on_exit():
    logging.info("Bot has finished. Log saved.")

atexit.register(on_exit)

bot.run('MTM3MzM2MTAxNTgxNDc1NDQwNQ.GaZGJg.RPMHv-k9KctipmZFZyd0wBNwwYlGVjeUAchxTw')

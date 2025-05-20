import discord
from discord.ext import commands
import random
import re
import logging
import atexit
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'[Bot startup and login completed]: {bot.user}')

log_filename = f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
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

    # CMDログ出力
    print(f'{message.author} ({message.channel}): {message.content}')

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

def on_exit():
    logging.info("Bot has finished. Log saved.")

atexit.register(on_exit)

bot.run('MTM3MzM2MTAxNTgxNDc1NDQwNQ.GaZGJg.RPMHv-k9KctipmZFZyd0wBNwwYlGVjeUAchxTw')

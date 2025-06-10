import discord
from discord.ext import commands
import random

class MiniGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["ジャンケン", "じゃんけん"])
    async def janken(self, ctx, user_hand: str = None):
        if user_hand is None:
            await ctx.send("✋ 手を指定してください！ 例: `!janken グー`")
            return

        hand_map = {
            "グー": "グー", "ぐー": "グー",
            "チョキ": "チョキ", "ちょき": "チョキ",
            "パー": "パー", "ぱー": "パー"
        }

        normalized = hand_map.get(user_hand.strip().lower())
        if not normalized:
            await ctx.send("✋ グー、チョキ、パーのいずれかを指定してください（ひらがな／カタカナOK）")
            return

        bot_hand = random.choice(["グー", "チョキ", "パー"])

        if normalized == bot_hand:
            result = "あいこ!"
        elif (
            (normalized == "グー" and bot_hand == "チョキ") or
            (normalized == "チョキ" and bot_hand == "パー") or
            (normalized == "パー" and bot_hand == "グー")
        ):
            result = "あなたの勝ち! 🎉"
        else:
            result = "Botの勝ち!"

        await ctx.send(f"あなた: {normalized} | Bot: {bot_hand}\n{result}")

    @commands.command()
    async def スロット(self, ctx):
        symbols = ['🍒', '🍋', '🍊', '🔔', '⭐', '7️⃣']
        weights = [30, 25, 20, 15, 7, 3]  # レア度設定
        result = random.choices(symbols, weights=weights, k=3)

        await ctx.send(f"🎰 結果: [ {' | '.join(result)} ]")

        if result.count('7️⃣') == 3:
            await ctx.send("🎉 ジャックポット! 7️⃣が3つ揃ったよ! 大当たり!")
        elif result.count('7️⃣') == 2:
            await ctx.send("✨ ナイス! 7️⃣が2つ揃った!")
        elif result[0] == result[1] == result[2]:
            await ctx.send("🎉 おめでとう! 絵柄が3つ揃いました! 当たり!")
        else:
            await ctx.send("残念、揃いませんでした…また挑戦してね!")

# Cogを読み込む
async def setup(bot):
    await bot.add_cog(MiniGames(bot))

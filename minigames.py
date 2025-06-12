import discord
from discord.ext import commands
from discord import app_commands
import random

class MiniGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="janken", description="ジャンケンで勝負します")
    @app_commands.describe(user_hand="グー、チョキ、パーのいずれかを指定してください")
    async def janken(self, interaction: discord.Interaction, user_hand: str):
        hand_map = {
            "グー": "グー", "ぐー": "グー",
            "チョキ": "チョキ", "ちょき": "チョキ",
            "パー": "パー", "ぱー": "パー"
        }

        normalized = hand_map.get(user_hand.strip())
        if not normalized:
            await interaction.response.send_message("✋ グー、チョキ、パーのいずれかを指定してください（ひらがな／カタカナOK）", ephemeral=True)
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

        await interaction.response.send_message(f"あなた: {normalized} | Bot: {bot_hand}\n{result}")

    @app_commands.command(name="slot", description="スロットを回します")
    async def slot(self, interaction: discord.Interaction):
        symbols = ['🍒', '🍋', '🍊', '🔔', '⭐', '7️⃣']
        weights = [30, 25, 20, 15, 7, 3]  # レア度設定
        result = random.choices(symbols, weights=weights, k=3)

        msg = f"🎰 結果: [ {' | '.join(result)} ]\n"

        if result.count('7️⃣') == 3:
            msg += "🎉 ジャックポット! 7️⃣が3つ揃ったよ! 大当たり!"
        elif result.count('7️⃣') == 2:
            msg += "✨ ナイス! 7️⃣が2つ揃った!"
        elif result[0] == result[1] == result[2]:
            msg += "🎉 おめでとう! 絵柄が3つ揃いました! 当たり!"
        else:
            msg += "残念、揃いませんでした…また挑戦してね!"

        await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(MiniGames(bot))
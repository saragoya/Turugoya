import discord
from discord.ext import commands
import asyncio
import yt_dlp

class YouTubeMusic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}

    def get_state(self, guild_id):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {
                "queue": [],
                "vc": None,
                "is_playing": False,
                "repeat": False,
                "volume": 0.5
            }
        return self.guild_states[guild_id]

    def get_volume(self, guild_id):
        return max(0.0, min(2.0, self.get_state(guild_id)["volume"]))

    async def play_next(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state["queue"]:
            state["is_playing"] = False
            return

        url = state["queue"][0]
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')

            if not state["vc"] or not state["vc"].is_connected():
                if ctx.author.voice:
                    state["vc"] = await ctx.author.voice.channel.connect()
                else:
                    await ctx.send("❌ ボイスチャンネルに参加していません。")
                    return

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(audio_url),
                volume=self.get_volume(ctx.guild.id)
            )

            def after_play(error):
                if error:
                    print(f"[ERROR] 再生後処理中にエラー: {error}")
                fut = self.play_next(ctx)
                asyncio.run_coroutine_threadsafe(fut, self.bot.loop)

            state["vc"].play(source, after=after_play)
            state["is_playing"] = True

            await ctx.send(f"▶️ 再生中: `{title}`")

            if not state["repeat"]:
                state["queue"].pop(0)

        except Exception as e:
            await ctx.send(f"❌ 再生エラーが発生しました。\n```{e}```")
            state["queue"].pop(0)
            await self.play_next(ctx)

    @commands.command()
    async def join(self, ctx):
        state = self.get_state(ctx.guild.id)
        if ctx.author.voice is None:
            await ctx.send("❌ ボイスチャンネルに接続してから実行してください。")
            return

        channel = ctx.author.voice.channel
        if state["vc"] and state["vc"].is_connected():
            await state["vc"].move_to(channel)
        else:
            state["vc"] = await channel.connect()

        await ctx.send(f"✅ `{channel.name}` に接続しました。")

    @commands.command()
    async def play(self, ctx, *, url: str):
        state = self.get_state(ctx.guild.id)
        ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        state["queue"].append(video_url)
                    await ctx.send(f"📃 プレイリストから {len(info['entries'])} 件を追加しました。")
                else:
                    state["queue"].append(url)
                    await ctx.send(f"🎵 動画をキューに追加しました。")

            if not state["is_playing"]:
                await self.play_next(ctx)

        except Exception as e:
            await ctx.send(f"❌ YouTube読み込みに失敗しました。\n```{e}```")

    @commands.command()
    async def skip(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state["vc"] and state["vc"].is_playing():
            state["vc"].stop()
            await ctx.send("⏭️ スキップしました。")
        else:
            await ctx.send("⚠️ 再生中の音声がありません。")

    @commands.command()
    async def pause(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state["vc"] and state["vc"].is_playing():
            state["vc"].pause()
            await ctx.send("⏸️ 一時停止しました。")
        else:
            await ctx.send("⚠️ 一時停止できる音声がありません。")

    @commands.command()
    async def resume(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state["vc"] and state["vc"].is_paused():
            state["vc"].resume()
            await ctx.send("▶️ 再開しました。")
        else:
            await ctx.send("⚠️ 一時停止中の音声がありません。")

    @commands.command()
    async def stop(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state["vc"]:
            state["queue"].clear()
            state["vc"].stop()
            await ctx.send("🛑 再生を停止しました。")
        else:
            await ctx.send("⚠️ 再生していません。")

    @commands.command()
    async def volume(self, ctx, value: float):
        state = self.get_state(ctx.guild.id)
        if not (0.0 <= value <= 2.0):
            await ctx.send("🔈 音量は 0.0 ～ 2.0 の範囲で指定してください（例：`!volume 1.0`）")
            return
        state["volume"] = value
        await ctx.send(f"🔊 音量を `{value:.1f}` に設定しました。")

    @commands.command()
    async def repeat(self, ctx, mode: str = None):
        state = self.get_state(ctx.guild.id)
        if mode == "on":
            state["repeat"] = True
            await ctx.send("🔁 リピート再生を有効にしました。")
        elif mode == "off":
            state["repeat"] = False
            await ctx.send("🔁 リピート再生を無効にしました。")
        else:
            await ctx.send("使い方: `!repeat on` または `!repeat off`")

    @commands.command()
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state["queue"]:
            await ctx.send("📭 キューは空です。")
        else:
            preview = state["queue"][:10]
            msg = "\n".join(f"{i+1}. {url}" for i, url in enumerate(preview))
            await ctx.send(f"📋 再生キュー:\n{msg}")

    @commands.command()
    async def leave(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state["vc"]:
            await state["vc"].disconnect()
            state["vc"] = None
            await ctx.send("👋 切断しました。")
        else:
            await ctx.send("⚠️ 接続していません。")

async def setup(bot):
    await bot.add_cog(YouTubeMusic(bot))

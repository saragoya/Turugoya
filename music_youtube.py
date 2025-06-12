import discord
from discord.ext import commands
import asyncio
import yt_dlp
from discord import app_commands
import os
import functools

MUSIC_FOLDER = "music_files"  # ローカル音楽ファイルのフォルダ

class YouTubeMusic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}

    def get_state(self, guild_id):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {
                "queue": [],  # List of (title, url)
                "vc": None,
                "is_playing": False,
                "repeat": False,
                "volume": 0.5
            }
        return self.guild_states[guild_id]

    def get_volume(self, guild_id):
        return max(0.0, min(2.0, self.get_state(guild_id)["volume"]))
    
    async def extract_info_async(ydl, url):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(ydl.extract_info, url, False))

    async def auto_disconnect(self, guild_id, delay=300):
        await asyncio.sleep(delay)
        state = self.get_state(guild_id)
        if state["vc"] and not state["vc"].is_playing():
            await state["vc"].disconnect()
            state["vc"] = None

    async def play_next(self, guild_id: int, interaction: discord.Interaction = None):
        state = self.get_state(guild_id)
        if state["vc"] and state["vc"].is_playing():
            return

        if not state["queue"]:
            state["is_playing"] = False
            return

        title, url = state["queue"][0]
        try:
            if os.path.isfile(url):
                audio_source = discord.FFmpegPCMAudio(url)
            else:
                with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
                    info = await extract_info_async(ydl, url)
                    audio_url = info["url"]
                    audio_source = discord.FFmpegPCMAudio(audio_url)

            source = discord.PCMVolumeTransformer(audio_source, volume=self.get_volume(guild_id))

            if not state["vc"] or not state["vc"].is_connected():
                if interaction and interaction.user.voice:
                    state["vc"] = await interaction.user.voice.channel.connect()
                else:
                    if interaction:
                        await interaction.followup.send("❌ ボイスチャンネルに接続できません。")
                    return

            def after_play(error):
                if error:
                    print(f"[after_play ERROR] {error}")
                future = asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)
                try:
                    future.result()
                except Exception as e:
                    print(f"[after_play EXCEPTION] {e}")

            state["vc"].play(source, after=after_play)
            state["is_playing"] = True

            if interaction:
                await interaction.followup.send(f"▶️ 再生中: `{title}`")

            if not state["repeat"]:
                state["queue"].pop(0)

        except Exception as e:
            if interaction:
                await interaction.followup.send(f"❌ 再生中にエラーが発生しました\n```{e}```")
            else:
                print(f"[play_next ERROR] {e}")
            if state["queue"]:
                state["queue"].pop(0)
            await self.play_next(guild_id)



    @app_commands.command(name="play", description="YouTubeのURLを再生キューに追加して再生します")
    @app_commands.describe(url="再生したいYouTubeのURL")
    async def play(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)
        ydl_opts = {'quiet': True, 'skip_download': True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        state["queue"].append((entry.get('title', 'Unknown'), video_url))
                    await interaction.followup.send(f"📃 プレイリストから {len(info['entries'])} 件を追加しました。")
                else:
                    title = info.get('title', 'Unknown')
                    state["queue"].append((title, url))
                    await interaction.followup.send(f"🎵 `{title}` をキューに追加しました。")

            if not state["is_playing"]:
                await self.play_next(interaction.guild.id, interaction)


        except Exception as e:
            await interaction.followup.send(f"❌ YouTube読み込みに失敗しました。\n```{e}```")
        
    @app_commands.command(name="playfile", description="ホストPC内の音楽ファイルを再生キューに追加して再生します")
    @app_commands.describe(name="再生したいファイル名（拡張子不要）")
    async def playfile(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        state = self.get_state(interaction.guild.id)

        supported_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        found_path = None
        for ext in supported_extensions:
            candidate = os.path.join(MUSIC_FOLDER, name + ext)
            if os.path.isfile(candidate):
                found_path = candidate
                break

        if not found_path:
            await interaction.followup.send("❌ 指定された音楽ファイルが見つかりません。")
            return

        title = os.path.basename(found_path)
        state["queue"].append((title, found_path))
        await interaction.followup.send(f"📥 `{title}` をキューに追加しました。")

        if not state["is_playing"]:
            await self.play_next(interaction.guild.id, interaction)

    @app_commands.command(name="filelist", description="ホストPC上の音楽ファイル一覧を表示します")
    @app_commands.describe(keyword="ファイル名に含まれるキーワード（省略可）")
    async def filelist(self, interaction: discord.Interaction, keyword: str = ""):
        try:
            files = os.listdir(MUSIC_FOLDER)
            supported = [f for f in files if os.path.splitext(f)[1] in ['.mp3', '.wav', '.flac', '.m4a','.ogg']]
            if keyword:
                supported = [f for f in supported if keyword.lower() in f.lower()]

            if not supported:
                await interaction.response.send_message("📭 該当する音楽ファイルが見つかりません。")
                return

            file_names = [os.path.splitext(f)[0] for f in supported]
            file_list = "\n".join(file_names[:30])
            await interaction.response.send_message(f"📂 利用可能な音楽ファイル一覧:\n```{file_list}```")
        except Exception as e:
            await interaction.response.send_message(f"❌ ファイル一覧取得に失敗しました。\n```{e}```")

    @app_commands.command(name="queue", description="再生キューの一覧を表示します")
    async def queue(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if not state["queue"]:
            await interaction.response.send_message("📭 キューは空です。")
        else:
            embed = discord.Embed(title="🎶 再生キュー", color=discord.Color.green())
            preview = state["queue"][:10]
            for i, (title, url) in enumerate(preview):
                embed.add_field(name=f"{i+1}. {title}", value=url, inline=False)
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="現在再生中の曲をスキップします")
    async def skip(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if state["vc"] and state["vc"].is_playing():
            state["vc"].stop()
            await interaction.response.send_message("⏭️ スキップしました。")
        else:
            await interaction.response.send_message("⚠️ 再生中の音声がありません。", ephemeral=True)

    @app_commands.command(name="pause", description="再生中の曲を一時停止します")
    async def pause(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if state["vc"] and state["vc"].is_playing():
            state["vc"].pause()
            await interaction.response.send_message("⏸️ 一時停止しました。")
        else:
            await interaction.response.send_message("⚠️ 一時停止できる音声がありません。", ephemeral=True)

    @app_commands.command(name="resume", description="一時停止中の曲を再開します")
    async def resume(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if state["vc"] and state["vc"].is_paused():
            state["vc"].resume()
            await interaction.response.send_message("▶️ 再開しました。")
        else:
            await interaction.response.send_message("⚠️ 一時停止中の音声がありません。", ephemeral=True)

    @app_commands.command(name="stop", description="再生を停止し、キューをクリアします")
    async def stop(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if state["vc"]:
            state["queue"].clear()
            state["vc"].stop()
            await interaction.response.send_message("🛑 再生を停止しました。")
        else:
            await interaction.response.send_message("⚠️ 再生していません。", ephemeral=True)

    @app_commands.command(name="volume", description="音量を設定します（0.0～2.0）")
    @app_commands.describe(value="音量（0.0～2.0）")
    async def volume(self, interaction: discord.Interaction, value: float):
        if not (0.0 <= value <= 2.0):
            await interaction.response.send_message("🔈 音量は 0.0 ～ 2.0 の範囲で指定してください（例：/volume 1.0）", ephemeral=True)
            return
        state = self.get_state(interaction.guild.id)
        state["volume"] = value
        await interaction.response.send_message(f"🔊 音量を `{value:.1f}` に設定しました。")

    @app_commands.command(name="repeat", description="リピート再生をオン/オフします")
    @app_commands.describe(mode="on または off を指定してください")
    async def repeat(self, interaction: discord.Interaction, mode: str):
        state = self.get_state(interaction.guild.id)
        if mode.lower() == "on":
            state["repeat"] = True
            await interaction.response.send_message("🔁 リピート再生を有効にしました。")
        elif mode.lower() == "off":
            state["repeat"] = False
            await interaction.response.send_message("🔁 リピート再生を無効にしました。")
        else:
            await interaction.response.send_message("使い方: /repeat on または /repeat off", ephemeral=True)

    @app_commands.command(name="join", description="Botをあなたのボイスチャンネルに参加させます")
    async def join(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            if state["vc"] and state["vc"].is_connected():
                await state["vc"].move_to(channel)
            else:
                state["vc"] = await channel.connect()
            await interaction.response.send_message(f"👋 `{channel.name}` に接続しました。")
        else:
            await interaction.response.send_message("⚠️ まずボイスチャンネルに参加してください。", ephemeral=True)
    
    @app_commands.command(name="leave", description="ボイスチャンネルから切断します")
    async def leave(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        if state["vc"]:
            await state["vc"].disconnect()
            state["vc"] = None
            await interaction.response.send_message("👋 切断しました。")
        else:
            await interaction.response.send_message("⚠️ 接続していません。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(YouTubeMusic(bot))

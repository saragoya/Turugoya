import discord
from discord.ext import commands
from discord import app_commands
import platform
import psutil
import shutil
import wmi
import socket
import winreg
import time
import datetime

class SystemInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wmi = wmi.WMI(namespace="root\\wmi")

    # ここに追加
    def get_windows_edition(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
            )
            edition, _ = winreg.QueryValueEx(key, "EditionID")
            return edition
        except Exception as e:
            return f"取得失敗: {e}"
    
    def get_network_info(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return f"ホスト名: {hostname}\nIPアドレス: {ip_address}"
        except Exception as e:
            return f"ネットワーク情報取得エラー: {e}"

    def get_network_speed(self):
        # 簡易的に1秒間での送受信バイト数を計測し、Mbpsに変換
        try:
            net1 = psutil.net_io_counters()
            time.sleep(1)
            net2 = psutil.net_io_counters()
            bytes_sent = net2.bytes_sent - net1.bytes_sent
            bytes_recv = net2.bytes_recv - net1.bytes_recv
            speed_mbps = (bytes_sent + bytes_recv) * 8 / 1_000_000  # Mbps
            return f"{speed_mbps:.2f} Mbps"
        except Exception as e:
            return f"通信速度取得エラー: {e}"

    def get_cpu_usage(self):
        try:
            usage = psutil.cpu_percent(interval=1)
            return f"{usage}%"
        except Exception as e:
            return f"CPU使用率取得エラー: {e}"

    # (省略: 既存のメソッド群はそのまま)

    @app_commands.command(name="host_info", description="ホストPCの詳細情報を表示します（管理者のみ）")
    @app_commands.checks.has_permissions(administrator=True)
    async def host_info(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        w = wmi.WMI()
        cpu = w.Win32_Processor()[0].Name
        ram = round(psutil.virtual_memory().total / (1024 ** 3), 2)

        memory = psutil.virtual_memory()
        memory_total = round(memory.total / (1024 ** 3), 2)
        memory_used = round(memory.used / (1024 ** 3), 2)
        memory_percent = memory.percent

        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}日{hours}時間{minutes}分{seconds}秒"

        storage_info = ""
        for p in psutil.disk_partitions():
            try:
                usage = shutil.disk_usage(p.mountpoint)
                total = round(usage.total / (1024**3), 2)
                used = round(usage.used / (1024**3), 2)
                free = round(usage.free / (1024**3), 2)
                storage_info += (
                    f"{p.device} ({p.mountpoint})\n"
                    f"  総容量: {total} GB\n"
                    f"  使用済: {used} GB\n"
                    f"  空き:   {free} GB\n"
                )
            except PermissionError:
                continue

        gpus = w.Win32_VideoController()
        gpu_info = "\n".join(gpu.Name for gpu in gpus) if gpus else "GPU情報なし"

        os_system = platform.system()
        os_release = platform.release()
        os_version = platform.version()
        os_arch = platform.machine()
        os_edition = self.get_windows_edition()

        network_info = self.get_network_info()
        net_speed = self.get_network_speed()
        cpu_usage = self.get_cpu_usage()

        embed = discord.Embed(
            title="🖥️ ホストPC 情報",
            color=discord.Color.teal()
        )
        embed.add_field(name="🧠 CPU", value=cpu or "不明", inline=False)
        embed.add_field(name="💻 CPU使用率", value=cpu_usage, inline=False)
        embed.add_field(name="💾 RAM", value=f"{ram} GB", inline=False)
        embed.add_field(name="📊 メモリ使用率",value=f"{memory_used} GB / {memory_total} GB ({memory_percent}%)",inline=False)
        embed.add_field(name="🗄️ ストレージ情報", value=storage_info or "取得不可", inline=False)
        embed.add_field(name="🎮 GPU", value=gpu_info or "取得不可", inline=False)
        embed.add_field(name="🪟 OS",value=f"{os_system} {os_release} {os_edition}\nBuild: {os_version}\nアーキテクチャ: {os_arch}",inline=False)
        embed.add_field(name="🌐 ネットワーク", value=network_info, inline=False)
        embed.add_field(name="📶 通信速度", value=net_speed, inline=False)
        embed.add_field(name="⏱️ 稼働時間",value=uptime_str,inline=False)
        embed.set_footer(text=f"要求者: {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await interaction.followup.send(embed=embed)

    @host_info.error
    async def host_info_error(self, interaction: discord.Interaction, error):
        if interaction.response.is_done():
            # すでに応答済みなら followup で送信
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.followup.send("⚠️ 管理者権限が必要です。", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ エラーが発生しました: {error}", ephemeral=True)
        else:
            # 応答していないなら response で送信
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message("⚠️ 管理者権限が必要です。", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ エラーが発生しました: {error}", ephemeral=True)



async def setup(bot):
    await bot.add_cog(SystemInfo(bot))

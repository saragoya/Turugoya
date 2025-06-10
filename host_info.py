import discord
from discord.ext import commands
import platform
import psutil
import shutil
import wmi
import socket
import winreg
import time
import subprocess
import datetime

class SystemInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wmi = wmi.WMI(namespace="root\\wmi")

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

    def get_battery_info(self):
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = battery.power_plugged
            return f"{percent}%（{'充電中' if plugged else 'バッテリー駆動'}）"
        else:
            return "バッテリー情報なし"

    def get_network_info(self):
        hostname = socket.gethostname()
        try:
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            ip_address = "取得失敗"
        return f"ホスト名: {hostname}\nIPアドレス: {ip_address}"

    def get_cpu_temperature(self):
        try:
            temps = self.wmi.MSAcpi_ThermalZoneTemperature()
            if not temps:
                return "対応センサーなし"
            temp_c = temps[0].CurrentTemperature / 10 - 273.15
            return f"{temp_c:.1f} °C"
        except Exception:
            return "取得失敗"

    def get_network_speed(self):
        net1 = psutil.net_io_counters()
        time.sleep(1)
        net2 = psutil.net_io_counters()
        upload = (net2.bytes_sent - net1.bytes_sent) / 1024  # KB/s
        download = (net2.bytes_recv - net1.bytes_recv) / 1024
        return f"⬆️ {upload:.2f} KB/s\n⬇️ {download:.2f} KB/s"

    def get_cpu_usage(self):
        usage = psutil.cpu_percent(interval=1)
        return f"{usage}%"

    def get_process_count(self):
        return len(psutil.pids())

    @commands.command(name="host_info")
    @commands.has_permissions(administrator=True)
    async def host_info(self, ctx):
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
        embed.set_footer(text=f"要求者: {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SystemInfo(bot))

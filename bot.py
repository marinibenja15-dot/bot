import discord
from discord import app_commands
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = 558111011924869120
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio.mp3")

intents = discord.Intents.default()
intents.voice_states = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="play", description="Reproduce el audio en el canal de voz")
async def play_command(interaction: discord.Interaction):
    await interaction.response.defer()

    channel = client.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, discord.VoiceChannel):
        await interaction.followup.send("Canal de voz no encontrado.")
        return

    voice_client = await channel.connect()

    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def after(error):
            if error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, None)

        voice_client.play(discord.FFmpegPCMAudio(AUDIO_FILE, options="-vn"), after=after)
        await interaction.followup.send(f"Reproduciendo en **{channel.name}**...")
        await future

    finally:
        await voice_client.disconnect()


@client.event
async def on_ready():
    logger.info(f"Bot online: {client.user}")
    for guild in client.guilds:
        await tree.sync(guild=discord.Object(id=guild.id))
        logger.info(f"Sync: {guild.name}")


client.run(TOKEN)

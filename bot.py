import disnake
from disnake.ext import commands
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = 558111011924869120

bot = commands.InteractionBot()


@bot.slash_command(name="play", description="Reproduce un audio en el canal de voz")
async def play_command(inter: disnake.ApplicationCommandInteraction, archivo: str):
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, disnake.VoiceChannel):
        await inter.response.send_message("Canal de voz no encontrado.")
        return

    if not os.path.isfile(archivo):
        await inter.response.send_message(f"Archivo `{archivo}` no encontrado.")
        return

    await inter.response.send_message(f"Reproduciendo `{archivo}` en **{channel.name}**...")
    voice_client = await channel.connect()

    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def after(error):
            if error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, None)

        voice_client.play(disnake.FFmpegPCMAudio(archivo, options="-vn"), after=after)
        await future

    except Exception as e:
        logger.error(f"Error: {e}")

    finally:
        if voice_client.is_connected():
            await voice_client.disconnect()


@bot.event
async def on_ready():
    logger.info(f"Bot online: {bot.user}")
    for guild in bot.guilds:
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)


bot.run(TOKEN)

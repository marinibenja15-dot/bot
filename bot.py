import discord
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = 558111011924869120
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio.mp3")

bot = discord.Bot()


@bot.slash_command(name="play", description="Reproduce un audio en el canal de voz")
async def play_command(ctx: discord.ApplicationContext, archivo: str):
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, discord.VoiceChannel):
        await ctx.respond("Canal de voz no encontrado.")
        return

    if not os.path.isfile(archivo):
        await ctx.respond(f"Archivo `{archivo}` no encontrado.")
        return

    await ctx.respond(f"Reproduciendo `{archivo}` en **{channel.name}**...")
    voice_client = await channel.connect()

    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def after(error):
            if error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, None)

        voice_client.play(discord.FFmpegPCMAudio(archivo, options="-vn"), after=after)
        await future

    except Exception as e:
        logger.error(f"Error: {e}")

    finally:
        if voice_client.is_connected():
            await voice_client.disconnect()


@bot.event
async def on_ready():
    logger.info(f"Bot online: {bot.user}")
    # Limpiar conexiones de voz colgadas de sesiones anteriores
    for guild in bot.guilds:
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
            logger.info(f"Desconectado voice client colgado en: {guild.name}")


bot.run(TOKEN)

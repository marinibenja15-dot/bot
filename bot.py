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


@bot.slash_command(name="play", description="Reproduce el audio en el canal de voz")
async def play_command(ctx: discord.ApplicationContext):
    await ctx.defer()

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, discord.VoiceChannel):
        await ctx.respond("Canal de voz no encontrado.")
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
        await ctx.respond(f"Reproduciendo en **{channel.name}**...")
        await future

    except Exception as e:
        logger.error(f"Error: {e}")
        await ctx.respond(f"Error: {e}")

    finally:
        if voice_client.is_connected():
            await voice_client.disconnect()


@bot.event
async def on_ready():
    logger.info(f"Bot online: {bot.user}")


bot.run(TOKEN)

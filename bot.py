import discord
from discord.ext import tasks, commands
import asyncio
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = 558111011924869120
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio.mp3")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "30"))

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set")

# --- Bot setup ---
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True  # Required for prefix commands

bot = commands.Bot(command_prefix="!", intents=intents)


async def play_audio_in_channel(response_ctx=None):
    """Join the voice channel, play the audio file, then disconnect.

    If response_ctx is provided (a discord.abc.Messageable), sends status messages there.
    """
    async def reply(msg):
        if response_ctx:
            await response_ctx.send(msg)
        else:
            logger.info(msg)

    channel = bot.get_channel(VOICE_CHANNEL_ID)

    if channel is None:
        await reply(f"No encontré el canal de voz `{VOICE_CHANNEL_ID}`. "
                    "Asegurate de que el bot esté en el servidor.")
        return

    if not isinstance(channel, discord.VoiceChannel):
        await reply("El canal configurado no es un canal de voz.")
        return

    if not os.path.isfile(AUDIO_FILE):
        await reply(f"Archivo de audio `{AUDIO_FILE}` no encontrado.")
        return

    guild = channel.guild
    voice_client = guild.voice_client

    try:
        if voice_client is None:
            voice_client = await channel.connect()
            logger.info(f"Conectado al canal: {channel.name}")
        elif voice_client.channel.id != VOICE_CHANNEL_ID:
            await voice_client.move_to(channel)
            logger.info(f"Movido al canal: {channel.name}")

        if voice_client.is_playing():
            voice_client.stop()

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def after_play(error):
            if error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, None)

        audio_source = discord.FFmpegPCMAudio(AUDIO_FILE)
        voice_client.play(audio_source, after=after_play)
        await reply(f"Reproduciendo `{AUDIO_FILE}` en **{channel.name}**...")
        logger.info(f"Reproduciendo '{AUDIO_FILE}'...")

        await future
        logger.info("Reproducción terminada.")

    except Exception as e:
        logger.error(f"Error durante la reproducción: {e}")
        await reply(f"Error: {e}")

    finally:
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            logger.info("Desconectado del canal de voz.")


# --- Scheduled task ---
@tasks.loop(minutes=INTERVAL_MINUTES)
async def scheduled_play():
    logger.info(f"Tarea programada ejecutándose (cada {INTERVAL_MINUTES} min).")
    await play_audio_in_channel()


@scheduled_play.before_loop
async def before_scheduled_play():
    await bot.wait_until_ready()


# --- Prefix command: !play ---
@bot.command(name="play")
async def play_command(ctx: commands.Context):
    """Reproduce el audio manualmente en el canal de voz configurado."""
    await play_audio_in_channel(response_ctx=ctx)


# --- Slash command: /play ---
@bot.tree.command(name="play", description="Reproduce el audio en el canal de voz ahora")
async def play_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    await play_audio_in_channel(response_ctx=interaction.channel)


# --- on_ready ---
@bot.event
async def on_ready():
    logger.info(f"Conectado como {bot.user} (ID: {bot.user.id})")
    logger.info(f"Canal de voz: {VOICE_CHANNEL_ID}")
    logger.info(f"Audio: {AUDIO_FILE} | Intervalo: cada {INTERVAL_MINUTES} min")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        logger.error(f"Error al sincronizar slash commands: {e}")
    if not scheduled_play.is_running():
        scheduled_play.start()


bot.run(TOKEN)

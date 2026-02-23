import discord
from discord import app_commands
from discord.ext import tasks
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = 558111011924869120
AUDIO_FILE = os.getenv("AUDIO_FILE", "audio.mp3")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "30"))

if not TOKEN:
    raise ValueError("DISCORD_TOKEN no está configurado")

# --- Client ---
intents = discord.Intents.default()
intents.voice_states = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
voice_lock = asyncio.Lock()


async def play_audio(interaction: discord.Interaction = None):
    async def reply(msg):
        if interaction:
            try:
                await interaction.followup.send(msg)
            except Exception:
                pass
        else:
            logger.info(msg)

    if voice_lock.locked():
        await reply("Ya hay una reproducción en curso.")
        return

    async with voice_lock:
        channel = client.get_channel(VOICE_CHANNEL_ID)

        if not isinstance(channel, discord.VoiceChannel):
            await reply(f"Canal {VOICE_CHANNEL_ID} no encontrado.")
            return

        if not os.path.isfile(AUDIO_FILE):
            await reply(f"Archivo `{AUDIO_FILE}` no encontrado.")
            return

        guild = channel.guild
        voice_client = guild.voice_client

        try:
            if voice_client is None:
                voice_client = await channel.connect()
            elif not voice_client.is_connected():
                # Stale client: esperar a que Discord lo limpie antes de reconectar
                await voice_client.disconnect(force=True)
                await asyncio.sleep(3)
                voice_client = await channel.connect()
            elif voice_client.channel.id != VOICE_CHANNEL_ID:
                await voice_client.move_to(channel)

            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.5)

            loop = asyncio.get_running_loop()
            future = loop.create_future()

            def after_play(error):
                if error:
                    loop.call_soon_threadsafe(future.set_exception, error)
                else:
                    loop.call_soon_threadsafe(future.set_result, None)

            source = discord.FFmpegPCMAudio(AUDIO_FILE, options="-vn")
            voice_client.play(source, after=after_play)

            await asyncio.sleep(0.5)
            if not voice_client.is_playing():
                raise RuntimeError("FFmpeg no pudo iniciar la reproducción.")

            await reply(f"Reproduciendo en **{channel.name}**...")
            logger.info(f"Reproduciendo '{AUDIO_FILE}'...")
            await future
            logger.info("Reproducción terminada.")

        except Exception as e:
            logger.error(f"Error: {e}")
            await reply(f"Error: {e}")

        finally:
            vc = guild.voice_client
            if vc and vc.is_connected():
                await vc.disconnect()
                logger.info("Desconectado.")


@tasks.loop(minutes=INTERVAL_MINUTES)
async def scheduled_play():
    logger.info("Ejecutando tarea programada...")
    await play_audio()


@scheduled_play.before_loop
async def before_scheduled_play():
    await client.wait_until_ready()
    await asyncio.sleep(15)


@tree.command(name="play", description="Reproduce el audio en el canal de voz ahora")
async def play_command(interaction: discord.Interaction):
    await interaction.response.defer()
    await play_audio(interaction)


@client.event
async def on_ready():
    logger.info(f"Bot online: {client.user} (ID: {client.user.id})")
    for guild in client.guilds:
        try:
            await tree.sync(guild=discord.Object(id=guild.id))
            logger.info(f"Slash commands sincronizados en: {guild.name}")
        except Exception as e:
            logger.error(f"Error sync {guild.name}: {e}")
    if not scheduled_play.is_running():
        scheduled_play.start()


client.run(TOKEN)

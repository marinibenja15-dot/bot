import discord
from discord.ext import tasks
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

client = discord.Client(intents=intents)


async def play_audio_in_channel():
    """Join the voice channel, play the audio file, then disconnect."""
    channel = client.get_channel(VOICE_CHANNEL_ID)

    if channel is None:
        logger.error(f"Voice channel {VOICE_CHANNEL_ID} not found. "
                     "Make sure the bot is in the server and the ID is correct.")
        return

    if not isinstance(channel, discord.VoiceChannel):
        logger.error(f"Channel {VOICE_CHANNEL_ID} is not a voice channel.")
        return

    if not os.path.isfile(AUDIO_FILE):
        logger.error(f"Audio file '{AUDIO_FILE}' not found.")
        return

    guild = channel.guild
    voice_client = guild.voice_client

    try:
        # Connect or move to the target channel
        if voice_client is None:
            voice_client = await channel.connect()
            logger.info(f"Connected to channel: {channel.name}")
        elif voice_client.channel.id != VOICE_CHANNEL_ID:
            await voice_client.move_to(channel)
            logger.info(f"Moved to channel: {channel.name}")

        # If already playing, stop first
        if voice_client.is_playing():
            voice_client.stop()

        # Use a Future to wait for playback to finish (thread-safe)
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def after_play(error):
            if error:
                loop.call_soon_threadsafe(future.set_exception, error)
            else:
                loop.call_soon_threadsafe(future.set_result, None)

        audio_source = discord.FFmpegPCMAudio(AUDIO_FILE)
        voice_client.play(audio_source, after=after_play)
        logger.info(f"Playing '{AUDIO_FILE}'...")

        await future
        logger.info("Playback finished.")

    except Exception as e:
        logger.error(f"Error during audio playback: {e}")

    finally:
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            logger.info("Disconnected from voice channel.")


@tasks.loop(minutes=INTERVAL_MINUTES)
async def scheduled_play():
    logger.info(f"Scheduled task triggered (every {INTERVAL_MINUTES} min).")
    await play_audio_in_channel()


@scheduled_play.before_loop
async def before_scheduled_play():
    await client.wait_until_ready()


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
    logger.info(f"Targeting voice channel ID: {VOICE_CHANNEL_ID}")
    logger.info(f"Audio file: {AUDIO_FILE}")
    logger.info(f"Interval: every {INTERVAL_MINUTES} minutes")
    if not scheduled_play.is_running():
        scheduled_play.start()


client.run(TOKEN)

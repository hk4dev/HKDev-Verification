import os
import asyncio
import discord
from discord.ext import interaction

from config.config import get_config
from config.log_config import log


if __name__ == "__main__":
    directory = os.path.dirname(os.path.abspath(__file__))
    parser = get_config()

    log.info("HKDev Korea 인증시스템을 불러오는 중입니다.")
    bot = interaction.Client(
        command_prefix="!",
        intents=discord.Intents.all(),
        enable_debug_events=True
    )

    # cogs = ["cogs." + file[:-3] for file in os.listdir(os.path.join(directory, 'cogs')) if file.endswith(".py")]
    # for cog in cogs:
    #    bot.load_extension(cog)
    asyncio.run(
        bot.load_extensions("cogs", directory)
    )
    token = parser.get('DEFAULT', 'token')
    bot.run(token)

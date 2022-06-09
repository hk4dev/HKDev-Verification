import datetime
import logging
from typing import Optional, NamedTuple, List

import discord
from discord.ext import commands, interaction
from discord.state import ConnectionState

from config.config import get_config

logger = logging.getLogger(__name__)
parser = get_config()
comment_parser = get_config("comment")


class WelcomeMessageReceived:
    def __init__(self, bot: interaction.Client):
        self.bot = bot
        self._connection: ConnectionState = getattr(bot, "_connection")
        self.color = int(parser.get("Color", "default"), 16)
        self.error_color = int(parser.get("Color", "error"), 16)
        self.warning_color = int(parser.get("Color", "warning"), 16)

        self.channel_discord: Optional[discord.TextChannel] = None
        self.channel: Optional[interaction.MessageSendable] = None
        self._guild: Optional[discord.Guild] = None
        self._invites = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel_discord = self._connection.get_channel(
            id=parser.getint("WelcomeMessage", "channel_id", fallback=0)
        )
        if self.channel_discord is not None and self.channel is None:
            self.channel = interaction.MessageSendable(
                state=self._connection,
                channel=self.channel_discord
            )

        guild_id = parser.getint("WelcomeMessage", "guild_id", fallback=0)
        self._guild = self.bot.get_guild(guild_id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        comment = comment_parser.get("WelcomeMessage", "comment").format(
            author="{0}#{1}".format(member.name, member.discriminator),
            author_menthon=member.mention
        )
        await self.channel.send(comment)
        return


async def setup(client):
    client.add_icog(WelcomeMessageReceived(client))

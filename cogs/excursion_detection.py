import datetime
import logging
from typing import Optional

import discord
from discord.ext import interaction
from discord.state import ConnectionState

from config.config import get_config

logger = logging.getLogger(__name__)
logger_member = logger.getChild("member")
logger_generation = logger.getChild("generation")
parser = get_config()
comment_parser = get_config("comment")


class ExcursionDetection:
    def __init__(self, bot: interaction.Client):
        self.bot = bot
        self._connection: ConnectionState = getattr(bot, "_connection")
        self.color = int(parser.get("Color", "default"), 16)
        self.error_color = int(parser.get("Color", "error"), 16)
        self.warning_color = int(parser.get("Color", "warning"), 16)

        self.channel_discord: Optional[discord.TextChannel] = None
        self.channel: Optional[interaction.MessageSendable] = None
        self._guild: Optional[discord.Guild] = None

    @interaction.listener()
    async def on_ready(self):
        self.channel_discord = self._connection.get_channel(
            id=parser.getint("ExcursionDetection", "channel_id", fallback=0)
        )
        if self.channel_discord is not None and self.channel is None:
            self.channel = interaction.MessageSendable(
                state=self._connection,
                channel=self.channel_discord
            )

        guild_id = parser.getint("ExcursionDetection", "guild_id", fallback=0)
        self._guild = self.bot.get_guild(guild_id)

    @interaction.listener()
    async def on_member_remove(self, member: discord.Member):
        registered_time = datetime.datetime.now(tz=datetime.timezone.utc) - member.joined_at
        if registered_time.days < 7:
            embed = discord.Embed(
                description="{0}#{1}({2})가 7일 이전에 커뮤니티를 탈퇴 하였습니다.".format(
                    member.name, member.discriminator, member.id
                ),
                color=self.color
            )
            embed.add_field(name="활동 기간", value="{0}일".format(registered_time.days), inline=True)
            embed.add_field(name="역할 목록", value=", ".join([x.name for x in member.roles]), inline=True)
            embed.add_field(name="인증 유무", value="O" if member.pending else "X", inline=True)
            await self.channel.send(embed=embed)
        return


async def setup(client):
    client.add_icog(ExcursionDetection(client))

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


class InviteListData(NamedTuple):
    users: List[str] = []
    id: List[str] = []
    created_at: List[str] = []
    channel: List[str] = []
    uses: List[str] = []


class InviteLoggerReceived:
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
            id=parser.getint("InviteLogger", "channel_id", fallback=0)
        )
        if self.channel_discord is not None and self.channel is None:
            self.channel = interaction.MessageSendable(
                state=self._connection,
                channel=self.channel_discord
            )

        guild_id = parser.getint("InviteLogger", "guild_id", fallback=0)
        self._guild = self.bot.get_guild(guild_id)
        self._invites = await self._guild.invites()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self._invites.append(invite)
        return

    @commands.Cog.listener()
    async def on_invite_delete(self, _: discord.Invite):
        self._invites = await self._guild.invites()
        return

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        invite_data = InviteListData()
        invites = {}
        pre_invites = self._invites[:]
        for invite in pre_invites:
            invites[invite.code] = {
                "preData": invite,
                "postData": None
            }
        self._invites = await self._guild.invites()
        post_invites = self._invites[:]
        for invite in post_invites:
            if invite.code not in invites:
                invites[invite.code] = {
                    "preData": None,
                    "postData": None
                }
            invites[invite.code]['postData'] = invite

        for changed_invite in invites.values():
            if changed_invite['preData'] is None or changed_invite['postData'] is None:
                continue

            if int(changed_invite['preData'].uses) != int(changed_invite['postData'].uses):
                _invite: discord.Invite = changed_invite['postData']
                # if labeling_parser.has_option('InviteLabeling', _invite.code):
                #     footer_invite.append(
                #         labeling_parser.get('InviteLabeling', _invite.code)
                #     )
                #     continue
                inviter = _invite.inviter
                invite_data.users.append('{}#{}'.format(inviter.name, inviter.discriminator))
                invite_data.id.append(_invite.code)
                invite_data.created_at.append(
                    "<t:{}:R>".format(
                        int(_invite.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())
                    )
                )
                invite_data.uses.append(
                    "{}회/{}".format(_invite.uses, "{}회".format(_invite.max_uses) if _invite.max_uses > 0 else "무제한")
                )
                invite_data.channel.append(_invite.channel.mention)

        embed = discord.Embed(color=self.color)
        embed.set_author(
            name='{}#{}'.format(member.name, member.discriminator),
            icon_url=member.display_avatar.url
        )
        if len(invite_data.users) > 0:
            embed.description = "유입 경로: {0}".format(" ".join(invite_data.users))
            embed.add_field(name="초대 ID", value=" ".join(invite_data.id))
            embed.add_field(name="초대 코드 생성시간", value=" ".join(invite_data.created_at))
            embed.add_field(name="초대 사용 횟수", value=" ".join(invite_data.uses))
            embed.add_field(name="채널", value=" ".join(invite_data.channel))
        else:
            embed.description = "유입 경로: 알 수 없음.\n사용자 지정 초대 코드 또는 `guild.join` scope에 의한 초대)"
        await self.channel.send(embed=embed)
        return


async def setup(client):
    client.add_icog(InviteLoggerReceived(client))

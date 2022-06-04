import io
import logging
from typing import NamedTuple

import discord
from discord.ext import commands, interaction

from config.config import get_config
from module import nCaptcha

logger = logging.getLogger(__name__)
parser = get_config()
comment_parser = get_config("comment")


class AuthorizedSession(NamedTuple):
    context: interaction.ComponentsContext
    client: nCaptcha.Client
    verificationType: nCaptcha.VerificationType


class AuthorizedReceived:
    def __init__(self, bot: interaction.Client):
        self.bot = bot
        self.color = int(parser.get("Color", "default"), 16)
        self.error_color = int(parser.get("Color", "error"), 16)
        self.warning_color = int(parser.get("Color", "warning"), 16)

        self.client_id = parser.get("DEFAULT", "naver_id")
        self.client_secret = parser.get("DEFAULT", "naver_secret")

        self.authorized_session = dict()

        self._title = comment_parser.get("Authorization", "title")
        self._warning_title = comment_parser.get("Authorization", "warningTitle", fallback=None) or self._title
        self._error_title = comment_parser.get("Authorization", "errorTitle", fallback=None) or self._warning_title
        self._icon_url = comment_parser.get("Authorization", "title_icon")
        self.authorized_process = discord.Embed(
            description=comment_parser.get("Authorization", "authorized_process"),
            color=self.color
        )
        self.authorized_result_success = discord.Embed(
            description=comment_parser.get("Authorization", "authorized_result_success"),
            color=self.color
        )
        self.authorized_result_failed = discord.Embed(
            description=comment_parser.get("Authorization", "authorized_result_failed"),
            color=self.warning_color
        )

        self.authorized_timeout_input = discord.Embed(
            description=comment_parser.get("Authorization", "authorized_input_timeout"),
            color=self.warning_color
        )

        self.authorized_no_session = discord.Embed(
            description=comment_parser.get("Authorization", "authorized_session_not_found"),
            color=self.error_color
        )

        self.authorized_process.set_author(
            name=self._title,
            icon_url=self._icon_url
        )
        self.authorized_result_success.set_author(
            name=self._title,
            icon_url=self._icon_url
        )
        self.authorized_result_failed.set_author(
            name=self._warning_title,
            icon_url=self._icon_url
        )
        self.authorized_timeout_input.set_author(
            name=self._warning_title,
            icon_url=self._icon_url
        )
        self.authorized_no_session.set_author(
            name=self._error_title,
            icon_url=self._icon_url
        )

    def authorization_check_session(self, member: discord.User) -> bool:
        return member.id in self.authorized_session

    async def authorization_setup(
            self,
            ctx: interaction.ComponentsContext,
            verification_type: nCaptcha.VerificationType,
            client: nCaptcha.Client = None,
            refresh: bool = False
    ) -> None:
        if not ctx.responded:
            await ctx.defer(hidden=True)

        # Comment
        verification_type_comment = {
            nCaptcha.VerificationType.image: "이미지",
            nCaptcha.VerificationType.sound: "음성"
        }
        self.authorized_process.description = self.authorized_process.description.format(
            guild=ctx.guild.name,
            guild_id=ctx.guild_id,
            verification_type=verification_type_comment[verification_type]
        )

        if client is None:
            client = nCaptcha.Client(client_id=self.client_id, client_secret=self.client_secret, loop=self.bot.loop)

        if verification_type == nCaptcha.VerificationType.image:
            if not refresh:
                file = await client.get_image()
            else:
                file = await client.refresh_image()
            file_type = "jpeg"
            self.authorized_process.set_image(url="attachment://authorized-file-{}.jpeg".format(
                ctx.author.id
            ))
        elif verification_type == nCaptcha.VerificationType.sound:
            if not refresh:
                file = await client.get_sound()
            else:
                file = await client.refresh_sound()
            file_type = "wav"
        else:
            await client.http.requests.close()
            return

        discord_file = discord.File(io.BytesIO(file), filename="authorized-file-{}.{}".format(
            ctx.author.id, file_type
        ))
        components = [
            interaction.ActionRow(components=[
                interaction.Button(
                    style=1,
                    custom_id="authorized_session",
                    # emoji="\U00002328",
                    label="인증하기"
                ),
                interaction.Button(
                    style=1,
                    custom_id="authorized_refresh",
                    label="갱신하기"
                ),
            ])
        ]
        if not ctx.responded:
            await ctx.send(
                embed=self.authorized_process,
                file=discord_file,
                components=components,
                hidden=True
            )
        else:
            await ctx.edit(
                embed=self.authorized_process,
                file=discord_file,
                components=components
            )
        self.authorized_session[ctx.author.id] = AuthorizedSession(
            client=client,
            context=ctx,
            verificationType=verification_type
        )
        return

    @interaction.detect_component(custom_id="authorized_session")
    async def authorized_session_call(self, ctx: interaction.ComponentsContext):
        if not self.authorization_check_session(ctx.author):
            await ctx.send(embed=self.authorized_no_session, hidden=True)
            return
        await ctx.send(comment_parser.get("Authorization", "session_call"), hidden=True)
        return

    @interaction.detect_component()
    async def authorized_refresh(self, ctx: interaction.ComponentsContext):
        if not self.authorization_check_session(ctx.author):
            await ctx.send(embed=self.authorized_no_session, hidden=True)
            return
        session: AuthorizedSession = self.authorized_session[ctx.author.id]
        await ctx.defer_update(hidden=True)
        await self.authorization_setup(
            ctx=session.context,
            client=session.client,
            verification_type=session.verificationType,
            refresh=True
        )
        return

    def cog_check(self, _):
        return True

    async def cog_before_invoke(self, ctx):
        pass

    async def cog_after_invoke(self, ctx):
        pass

    async def cog_command_error(self, ctx, error):
        pass

    @staticmethod
    def has_error_handler():
        return False

    @interaction.detect_component()
    async def authorization_request_button(self, ctx: interaction.ComponentsContext):
        if self.authorization_check_session(ctx.author):
            # If a session already exists, it makes it go through the deletion process.
            self.authorized_session.pop(ctx.author.id)
        await self.authorization_setup(ctx, nCaptcha.VerificationType.image)
        return

    @interaction.command(name="인증", description="인증할 때 사용하는 명령어입니다.", sync_command=True)
    @interaction.option(name="인증키", description="인증 키 값이 입력됩니다.")
    async def authorized(self, ctx: interaction.ApplicationContext, key: str):
        if not self.authorization_check_session(ctx.author):
            await ctx.send(embed=self.authorized_no_session, hidden=True)
            return
        session: AuthorizedSession = self.authorized_session[ctx.author.id]
        response = await session.client.verification(key, verification_type=session.verificationType)
        self.authorized_session.pop(ctx.author.id)
        if parser.has_option("Authorization", "timeout"):
            timeout = parser.getint("Authorization", "timeout")
            self.authorized_timeout_input.description = self.authorized_timeout_input.description.format(
                guild=ctx.guild.name,
                guild_id=ctx.guild_id,
                time=response.time,
                max_time=timeout
            )
            if timeout == -1 and response.time > 200:
                await ctx.send(embed=self.authorized_timeout_input, hidden=True)
                return
            elif response.time > timeout != -1:
                await ctx.send(embed=self.authorized_timeout_input, hidden=True)
                return

        if response.result:
            self.authorized_result_success.description = self.authorized_result_success.description.format(
                guild=ctx.guild.name,
                guild_id=ctx.guild_id,
                time=response.time
            )
            await ctx.send(embed=self.authorized_result_success, hidden=True)
            self.bot.dispatch('authorized_result_success', ctx, response.time)
        else:
            self.authorized_result_failed.description = self.authorized_result_failed.description.format(
                guild=ctx.guild.name,
                guild_id=ctx.guild_id,
                time=response.time
            )
            await ctx.send(embed=self.authorized_result_failed, hidden=True)
        return

    @commands.command(name="register_authorization")
    async def register_authorization(self, ctx):
        channel = interaction.MessageSendable(
            state=getattr(self.bot, "_connection"),
            channel=ctx.channel
        )
        await channel.send(
            comment_parser.get("RegisterComment", "comment"),
            components=[
                interaction.ActionRow(components=[
                    interaction.Button(
                        style=1,
                        custom_id="authorization_request_button",
                        emoji="\U0001F513"
                    )
                ])
            ]
        )
        return

    @interaction.listener()
    async def on_message(self, ctx: discord.Message):
        if ctx is None:
            return

        if (
            ctx.channel.id == 981966649953509446 and
            718064689140989983 not in [role.id for role in ctx.author.roles] and
            ctx.author.id != self.bot.user.id
        ):
            await ctx.delete()
        return


async def setup(client):
    client.add_icog(AuthorizedReceived(client))

import asyncio
import json
import logging
import os
import io

import discord
from enum import Enum
from datetime import datetime, timedelta
from pytz import timezone
from discord.ext import commands, interaction

from config.config import get_config
from module import nCaptcha
from utils.directory import directory


logger = logging.getLogger(__name__)
parser = get_config()
comment_parser = get_config("comment")
DBS = None


class AuthorizedReceived:
    def __init__(self, bot: interaction.Client):
        self.bot = bot
        self.color = int(parser.get("Color", "default"), 16)
        self.error_color = int(parser.get("Color", "error"), 16)
        self.warning_color = int(parser.get("Color", "warning"), 16)

        self.client_id = parser.get("DEFAULT", "naver_id")
        self.client_secret = parser.get("DEFAULT", "naver_secret")

        self.authorized_process = discord.Embed(
            title="인증(Authorized)",
            description="해당 서버({guild})에 접근하기 위해서는 캡차 과정을 통과하셔야 합니다. 아래의 {tp}의 값을 알맞게 입력해주세요.",
            color=self.color
        )
        self.authorized_process_verification = discord.Embed(
            title="인증(Authorized)",
            description="30초 내에 {tp}안에 있는 값을 정확히 입력해주세요.",
            color=self.color
        )

        self.authorized_result_success = discord.Embed(
            title="인증(Authorized)",
            description="인증에 성공하였습니다..",
            color=self.color
        )
        self.authorized_result_failed = discord.Embed(
            title="안내(Warning)",
            description="결과 다릅니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )

        self.authorized_timeout = discord.Embed(
            title="안내(Warning)",
            description="인증 시간(5분)이 초과되어 인증에 실패하였습니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )
        self.authorized_timeout_input = discord.Embed(
            title="안내(Warning)",
            description="인증 입력 시간(30초)가 초과되어 인증에 실패하였습니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )

    @staticmethod
    def authorization_response_button_check(ctx: interaction.ComponentsContext):
        user_id = int(ctx.custom_id.lstrip("authorization_response_"))
        return ctx.custom_id.startswith("authorization_response_") and user_id == ctx.author.id

    async def authorization_check(
            self,
            ctx: interaction.ComponentsContext,
            verification_type: nCaptcha.VerificationType,
            client: nCaptcha.Client = None,
            refresh: bool = False
    ) -> bool:
        await ctx.defer(hidden=True)

        # Comment
        verification_type_comment = {
            nCaptcha.VerificationType.image: "이미지",
            nCaptcha.VerificationType.sound: "음성"
        }
        self.authorized_process.description = self.authorized_process.description.format(
            guild=ctx.guild.name, tp=verification_type_comment[verification_type]
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
            return False

        discord_file = discord.File(io.BytesIO(file), filename="authorized-file-{}.{}".format(
            ctx.author.id, file_type
        ))
        components = [
            interaction.ActionRow(components=[
                interaction.Button(
                    style=1,
                    custom_id="authorization_response_{}".format(ctx.author.id),
                    # emoji="\U00002328",
                    label="인증하기"
                ),
                interaction.Button(style=1, custom_id="authorized_refresh", label="갱신 하기"),
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
        response: interaction.ComponentsContext = await self.bot.wait_for_global_component(
            check=self.authorization_response_button_check,
            timeout=300
        )
        await response.modal(
            custom_id="authorization_response_modal",
            title="{} 속 문자를 입력하세요.".format(verification_type_comment[verification_type]),
            components=[
                interaction.ActionRow(components=[
                    interaction.TextInput(
                        custom_id="authorization_response_modal_key",
                        style=1,
                        label="{} 속 문자를 입력하세요.".format(verification_type_comment[verification_type]),
                        required=True
                    )
                ])
            ]
        )
        return False

    # @commands.Cog.listener()
    # async def on_member_join(self, member: discord.Member):
    #     self.bot.dispatch(event_name="authorized", member=member)
    #     return

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
        await self.authorization_check(ctx, nCaptcha.VerificationType.image)
        return

    @commands.command(name="add_authorization")
    async def test_robot(self, ctx):
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

    @commands.Cog.listener()
    async def on_authorized(self, member: discord.Member):
        return


async def setup(client):
    client.add_icog(AuthorizedReceived(client))

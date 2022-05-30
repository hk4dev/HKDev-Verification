import asyncio
import json
import logging
import os
import io

import discord
from enum import Enum
from datetime import datetime, timedelta
from pytz import timezone
from discord.ext import commands

from config.config import get_config
from module.components import ActionRow, Button
from module.interaction import ComponentsContext
from module import nCaptcha
from module.message import MessageSendable, Message
from utils.database import Database
from utils.directory import directory


logger = logging.getLogger(__name__)
parser = get_config()
DBS = None


class RobotCheckType(Enum):
    image = 0
    sound = 1


class AuthorizedReceived:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open(os.path.join(directory, "data", "ticket.json"), "r", encoding='utf-8') as file:
            self.ticket = json.load(fp=file)
        self.color = int(parser.get("Color", "default"), 16)
        self.error_color = int(parser.get("Color", "error"), 16)
        self.warning_color = int(parser.get("Color", "warning"), 16)

        self.client_id = parser.get("DEFAULT", "naver_id")
        self.client_secret = parser.get("DEFAULT", "naver_secret")

        self.robot_process = discord.Embed(
            title="인증(Authorized)",
            description="해당 서버({guild})에 접근하기 위해서는 캡차 과정을 통과하셔야 합니다. 아래의 {tp}의 값을 알맞게 입력해주세요.",
            color=self.color
        )
        self.robot_process_verification = discord.Embed(
            title="인증(Authorized)",
            description="30초 내에 {tp}안에 있는 값을 정확히 입력해주세요.",
            color=self.color
        )
        self.robot_success = discord.Embed(
            title="인증(Authorized)",
            description="인증에 성공하였습니다..",
            color=self.color
        )
        self.robot_wrong = discord.Embed(
            title="안내(Warning)",
            description="결과 다릅니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )
        self.robot_timeout1 = discord.Embed(
            title="안내(Warning)",
            description="인증 시간(5분)이 초과되어 인증에 실패하였습니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )
        self.robot_timeout2 = discord.Embed(
            title="안내(Warning)",
            description="인증 입력 시간(30초)가 초과되어 인증에 실패하였습니다. 인증을 다시 시도해주시기 바랍니다.",
            color=self.warning_color
        )
        self.robot_process.set_footer(text="Powered by Naver Captcha")

    async def robot_check(
            self,
            member: discord.Member,
            mode: RobotCheckType,
            client: nCaptcha.Client = None,
            message: Message = None,
            refresh: bool = False
    ) -> bool:
        verification_type_comment = {
            nCaptcha.VerificationType.image: "이미지",
            nCaptcha.VerificationType.sound: "음성"
        }
        self.robot_process.description = self.robot_process.description.format(
            guild=member.guild, tp=verification_type_comment[mode.value]
        )

        channel = member.dm_channel
        if channel is None:
            channel = await member.create_dm()
        _channel = MessageSendable(state=getattr(self.bot, "_connection"), channel=channel)
        if client is None:
            client = nCaptcha.Client(client_id=self.client_id, client_secret=self.client_secret, loop=self.bot.loop)

        if mode.value == 0:
            if not refresh:
                file = await client.get_image()
            else:
                file = await client.refresh_sound()
            tp = "jpeg"
            self.robot_process.set_image(url="attachment://Authorized-File.jpeg")
        elif mode.value == 1:
            if not refresh:
                file = await client.get_sound()
            else:
                file = await client.refresh_sound()
            tp = "wav"
        else:
            await client.http.requests.close()
            return False
        discord_file = discord.File(io.BytesIO(file), filename="Authorized-File.{0}".format(tp))

        try:
            if message is None:
                msg = await _channel.send(
                    embed=self.robot_process,
                    file=discord_file,
                    components=[
                        ActionRow(components=[
                            Button(style=1, custom_id="authorized", label="인증 하기"),
                            Button(
                                style=1,
                                custom_id="authorized_change_mode",
                                label="유형 변경({0}->{1})".format(
                                    verification_type_comment[mode.value], verification_type_comment[1 - mode.value]
                                )
                            ),
                            Button(style=1, custom_id="authorized_refresh", label="갱신 하기"),
                        ])
                    ]
                )
            else:
                await message.edit(
                    embed=self.robot_process,
                    file=discord_file,
                    components=[
                        ActionRow(components=[
                            Button(style=1, custom_id="authorized", label="인증 하기"),
                            Button(
                                style=1,
                                custom_id="authorized_change_mode",
                                label="유형 변경({0}->{1})".format(
                                    verification_type_comment[mode.value], verification_type_comment[1 - mode.value]
                                )
                            ),
                            Button(style=1, custom_id="authorized_refresh", label="갱신 하기"),
                        ])
                    ]
                )
                msg = message
        except discord.Forbidden as E:
            await client.http.requests.close()
            raise E
        else:
            try:
                def check1(component: ComponentsContext):
                    return component.author.id == member.id and \
                           (component.message.id or component.message.webhook_id) == msg.id
                result: ComponentsContext = await self.bot.wait_for("components", check=check1, timeout=300)
            except asyncio.TimeoutError:
                await _channel.send(embed=self.robot_timeout1)
                await client.http.requests.close()
                return False
            else:
                if result.custom_id == "authorized":
                    self.robot_process_verification.description = self.robot_process_verification.description.format(
                        guild=member.guild, tp=verification_type_comment[mode.value]
                    )
                    await result.send(embed=self.robot_process_verification, hidden=True)

                    def check2(_message: Message):
                        return _message.author.id == member.id and _message.channel.id == member.dm_channel.id
                    try:
                        result: Message = await self.bot.wait_for("interaction_message", check=check2, timeout=30)
                    except asyncio.TimeoutError:
                        await _channel.send(embed=self.robot_timeout2)
                        await client.http.requests.close()
                        return False

                    final_data = await client.verification(value=result.content)
                    verification_result = final_data.get("result")
                    if verification_result:
                        await _channel.send(embed=self.robot_success)
                        await client.http.requests.close()
                        return True
                    else:
                        await _channel.send(embed=self.robot_wrong)
                        await client.http.requests.close()
                        return False
                elif result.custom_id == "authorized_change_mode":
                    await result.defer_update()
                    another_mode = mode
                    if mode.value == 1:
                        another_mode = RobotCheckType.image
                    elif mode.value == 0:
                        another_mode = RobotCheckType.sound
                    return await self.robot_check(
                        member=member,
                        mode=another_mode,
                        client=client,
                        message=msg,
                        refresh=False
                    )
                elif result.custom_id == "authorized_refresh":
                    await result.defer_update()
                    return await self.robot_check(
                        member=member,
                        mode=mode,
                        client=client,
                        message=msg,
                        refresh=True
                    )
        await client.http.requests.close()
        return False

    # @commands.Cog.listener()
    # async def on_member_join(self, member: discord.Member):
    #     self.bot.dispatch(event_name="authorized", member=member)
    #     return

    @commands.command(name="test_robot")
    async def test_robot(self, ctx):
        await self.robot_check(member=ctx.author, mode=RobotCheckType.image)
        return

    @commands.Cog.listener()
    async def on_authorized(self, member: discord.Member):
        database = Database(bot=self.bot, guild=member.guild)
        if not database.get_activation("authorized"):
            return
        data = database.get_data("authorized")
        if member.bot:
            if data.bot_role_id is None:
                return
            await member.add_roles(data.bot_role)
            return

        if data.robot:
            try:
                robot = await self.robot_check(member=member, mode=RobotCheckType.image)
            except discord.Forbidden:
                if data.robot_kick >= 2:
                    # 일부 사용자는 DM을 차단하고 접속 한 경우가 있으며, 이럴 경우 해당 사용자는 인증이 필요하단 사실을 인지하지 못할 가능성이 높음.
                    await asyncio.sleep(10)
                    await member.kick(reason="AUTO KICK: Robot")
                return

            if not robot:
                if data.robot_kick >= 1:
                    await member.kick(reason="AUTO KICK: Robot")
                return
        if data.user_role_id is not None:
            await member.add_roles(data.user_role)
        return


def setup(client):
    client.add_icog(AuthorizedReceived(client))

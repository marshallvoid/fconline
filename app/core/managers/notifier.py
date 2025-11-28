import traceback
from typing import TYPE_CHECKING

import apprise

from app.core.managers.file import file_mgr
from app.core.settings import settings
from app.utils.decorators.singleton import singleton

if TYPE_CHECKING:
    from loguru import Message


@singleton
class NotifierManager:
    def __init__(self) -> None:
        self.discord_developer_role_id = settings.discord.roles["developer"]
        self.discord_developer_webhook_id = settings.discord.webhooks["develop"]["id"]
        self.discord_developer_webhook_token = settings.discord.webhooks["develop"]["token"]
        self.discord_fco_role_id = settings.discord.roles["fco"]
        self.discord_fco_webhook_id = settings.discord.webhooks["fco_reward"]["id"]
        self.discord_fco_webhook_token = settings.discord.webhooks["fco_reward"]["token"]

        self.appriser = self._initialize()

    def _initialize(self) -> apprise.Apprise:
        appriser = apprise.Apprise()

        appriser.add(
            servers=(
                f"discord://{self.discord_fco_webhook_id}/{self.discord_fco_webhook_token}?"
                f"avatar={file_mgr.get_resource_path('assets/images/fco.png')}&"
                f"botname={settings.program_name}&"
                "url=https://fconline.garena.vn/&"
                "format=Markdown&"
            ),
            tag="discord.fco_reward",
        )

        appriser.add(
            servers=(
                f"discord://{self.discord_developer_webhook_id}/{self.discord_developer_webhook_token}?"
                f"avatar={file_mgr.get_resource_path('assets/images/fco.png')}&"
                f"botname={settings.program_name}&"
                "url=https://fconline.garena.vn/&"
                "format=Markdown&"
            ),
            tag="discord.developer",
        )

        return appriser

    def discord_winner_notifier(
        self,
        is_jackpot: bool,
        username: str,
        nickname: str,
        value: str,
    ) -> None:
        message_title = "__**🎉 Congratulations! 🎉**__"

        fco_mention = f"<@&{self.discord_fco_role_id}>"
        prize_type = "🏆 Ultimate Prize" if is_jackpot else "🎁 Mini Prize"
        message_body = (
            f"{fco_mention}\n\n"
            f"**{nickname}** has just won the **{prize_type}**!\n\n"
            f"> 👤 **Username:** `{username}`\n"
            f"> 💰 **Prize Amount:** **{value}**\n\n"
        )

        self.appriser.notify(
            body=message_body,
            title=message_title,
            notify_type=apprise.NotifyType.INFO,
            tag="discord.fco_reward",
        )

    def discord_error_notifier(self, message: "Message") -> None:
        record = message.record

        level_icon = record["level"].icon or "❗"
        message_title = f"__**{level_icon} {record['message']}**__"

        developer_mention = f"<@&{self.discord_developer_role_id}>"
        message_body = f"{developer_mention}\nNo traceback available."
        if record["exception"]:
            # pretty traceback string
            exc = record["exception"]
            traceback_str = "".join(traceback.format_exception(exc.type, exc.value, exc.traceback))
            message_body = f"{developer_mention}\n\n**Traceback:**\n```py\n{traceback_str.strip()}\n```"

        self.appriser.notify(
            body=message_body,
            title=message_title,
            notify_type=apprise.NotifyType.FAILURE,
            tag="discord.developer",
        )


notifier_mgr = NotifierManager()

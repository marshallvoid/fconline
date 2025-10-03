# import traceback
# from typing import TYPE_CHECKING

# import apprise

# from src.core.configs import settings
# from src.core.decorators import singleton
# from src.core.managers.file import file_mgr

# if TYPE_CHECKING:
#     from loguru import Message


# @singleton
# class NotifierManager:
#     def __init__(self) -> None:
#         self.appriser = self.make()

#     def make(self) -> apprise.Apprise:
#         appriser = apprise.Apprise()

#         appriser.add(
#             servers=(
#                 f"discord://{settings.discord_developer_webhook_id}/{settings.discord_developer_webhook_token}?"
#                 f"avatar={file_mgr.get_resource_path('assets/images/fco.png')}&"
#                 f"botname={settings.program_name}&"
#                 "url=https://fconline.garena.vn/&"
#                 "format=Markdown&"
#             ),
#             tag="discord.developer",
#         )

#         appriser.add(
#             servers=(
#                 f"discord://{settings.discord_fco_webhook_id}/{settings.discord_fco_webhook_token}?"
#                 f"avatar={file_mgr.get_resource_path('assets/images/fco.png')}&"
#                 f"botname={settings.program_name}&"
#                 "url=https://fconline.garena.vn/&"
#                 "format=Markdown&"
#             ),
#             tag="discord.fco",
#         )

#         return appriser

#     def discord_error_notifier(self, message: "Message") -> None:
#         record = message.record

#         level_icon = record["level"].icon or "❗"
#         message_title = f"__**{level_icon} {record['message']}**__"

#         developer_mention = f"<@&{settings.discord_developer_role_id}>"
#         message_body = f"{developer_mention}\nNo traceback available."
#         if record["exception"]:
#             # pretty traceback string
#             exc = record["exception"]
#             traceback_str = "".join(traceback.format_exception(exc.type, exc.value, exc.traceback))
#             message_body = f"{developer_mention}\n\n**Traceback:**\n```py\n{traceback_str.strip()}\n```"

#         self.appriser.notify(
#             body=message_body,
#             title=message_title,
#             notify_type=apprise.NotifyType.FAILURE,
#             tag="discord.developer",
#         )

#     def discord_winner_notifier(
#         self,
#         is_jackpot: bool,
#         username: str,
#         nickname: str,
#         value: str,
#     ) -> None:
#         message_title = "__**🎉 Congratulations! 🎉**__"

#         fco_mention = f"<@&{settings.discord_fco_webhook_role_id}>"
#         prize_type = "🏆 Ultimate Prize" if is_jackpot else "🎁 Mini Prize"
#         message_body = (
#             f"{fco_mention}\n\n"
#             f"**{nickname}** has just won the **{prize_type}**!\n\n"
#             f"> 👤 **Username:** `{username}`\n"
#             f"> 💰 **Prize Amount:** **{value}**\n\n"
#         )

#         self.appriser.notify(
#             body=message_body,
#             title=message_title,
#             notify_type=apprise.NotifyType.INFO,
#             tag="discord.fco",
#         )


# notifier_mgr = NotifierManager()

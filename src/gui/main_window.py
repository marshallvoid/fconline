import asyncio
import concurrent.futures
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import darkdetect
import sv_ttk
from loguru import logger

from src.gui.accounts_tab import AccountsTab
from src.gui.activity_log_tab import ActivityLogTab
from src.gui.notification_icon import NotificationIcon
from src.schemas.enums.message_tag import MessageTag
from src.schemas.user_response import UserDetail
from src.services.configs import ConfigsManager
from src.services.fco.main_tool import MainTool
from src.services.files import FileManager
from src.services.platforms import PlatformManager
from src.utils import helpers as hp
from src.utils.contants import EVENT_CONFIGS_MAP, PROGRAM_NAME


class MainWindow:
    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title(string=PROGRAM_NAME)
        self._root.resizable(width=False, height=False)

        try:
            png_path = FileManager.get_resource_path("assets/icon.png")
            icon = tk.PhotoImage(file=png_path)
            self._root.iconphoto(True, icon)

        except Exception:
            pass

        if PlatformManager.is_windows():
            try:
                ico_path = FileManager.get_resource_path("assets/icon.ico")
                self._root.iconbitmap(ico_path)

            except Exception:
                pass

        # Track per-account running tool instances
        self._configs = ConfigsManager.load_configs()
        self._selected_event = self._configs.event or list(EVENT_CONFIGS_MAP.keys())[0]
        self._running_tools: Dict[str, MainTool] = {}

        self._setup_ui()

    def run(self) -> None:
        logger.info(f"Running {PROGRAM_NAME}")

        def on_close() -> None:
            if not self._running_tools:
                self._root.destroy()
                return

            # Mark all tools as not running first
            for running_tool in self._running_tools.values():
                running_tool.update_configs(is_running=False)

            def close_tool_safely(tool: MainTool) -> None:
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Run close with timeout
                    loop.run_until_complete(asyncio.wait_for(tool.close(), timeout=3.0))

                except asyncio.TimeoutError:
                    logger.warning("Tool close timeout, forcing shutdown")

                except Exception as error:
                    logger.exception(f"Error closing tool: {error}")

                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass

            # Close tools in separate threads to avoid blocking the UI
            def close_tools_concurrently() -> None:
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(self._running_tools)) as executor:
                    # Submit all close tasks
                    future_to_tool = {
                        executor.submit(close_tool_safely, tool): tool for tool in self._running_tools.values()
                    }

                    # Wait for all to complete with timeout
                    try:
                        concurrent.futures.wait(future_to_tool.keys(), timeout=5.0)  # 5 second timeout
                    except Exception:
                        pass  # Ignore timeout errors

                    # Cancel any remaining tasks
                    for future in future_to_tool:
                        if not future.done():
                            future.cancel()

            # Start closing process in background thread
            threading.Thread(target=close_tools_concurrently, daemon=True).start()

            # Destroy the root window immediately
            self._root.destroy()

        self._root.protocol("WM_DELETE_WINDOW", on_close)

        sv_ttk.set_theme(darkdetect.theme() or "dark")

        try:
            style = ttk.Style(self._root)
            layout = style.layout("TNotebook.Tab")

            def _strip_focus(elements: Any) -> Any:
                if not isinstance(elements, (list, tuple)):
                    return elements

                cleaned = []
                for elem in elements:
                    if isinstance(elem, tuple) and elem:
                        name = elem[0]
                        opts = elem[1] if len(elem) > 1 else {}

                        if isinstance(name, str) and name.endswith(".focus"):
                            continue

                        if isinstance(opts, dict) and "children" in opts:
                            opts = dict(opts)
                            opts["children"] = _strip_focus(opts.get("children", []))
                            cleaned.append((name, opts))
                            continue

                        cleaned.append(elem)
                        continue

                    cleaned.append(elem)

                return cleaned

            cleaned_layout = _strip_focus(layout)
            style.layout("TNotebook.Tab", cleaned_layout)

        except Exception:
            pass

        self._root.mainloop()

    def _setup_ui(self) -> None:
        self._setup_notification_icon()
        self._setup_event_selection()
        self._setup_main_content()

        self._root.update_idletasks()
        _, _, width, height, x, y = hp.get_window_position(child_frame=self._root)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_notification_icon(self) -> None:
        notification_frame = ttk.Frame(self._root)
        notification_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # Spacer to push icon to right
        spacer = ttk.Frame(notification_frame)
        spacer.pack(side="left", fill="x", expand=True)

        # Notification icon
        self._notification_icon = NotificationIcon(notification_frame)
        self._notification_icon.frame.pack(side="right")

    def _setup_event_selection(self) -> None:
        event_selection_frame = ttk.LabelFrame(self._root, padding=10, text="Select Event:")
        event_selection_frame.pack(fill="x", padx=10, pady=(10, 5))

        event_var = tk.StringVar(value=self._selected_event)

        # Create dropdown menu for event selection
        event_combobox = ttk.Combobox(
            event_selection_frame,
            textvariable=event_var,
            values=list(EVENT_CONFIGS_MAP.keys()),
            state="readonly",
            width=30,
        )
        event_combobox.pack(anchor="w", fill="x")

        def on_event_changed(_event: Optional[tk.Event] = None) -> None:
            # Get the selected event from combobox
            self._selected_event = event_var.get()

            # Update the accounts tab with new event configuration
            self._accounts_tab.selected_event = self._selected_event

            self._configs.event = self._selected_event
            ConfigsManager.save_configs(self._configs)

        event_combobox.bind("<<ComboboxSelected>>", on_event_changed)

    def _setup_main_content(self) -> None:
        main_container = ttk.Frame(self._root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Notebook for tabs
        self._notebook = ttk.Notebook(main_container, takefocus=False)
        self._notebook.pack(fill="both", expand=True)

        # Accounts tab
        self._accounts_tab = AccountsTab(
            parent=self._notebook,
            selected_event=self._selected_event,
            on_account_run=self._run_account,
            on_account_stop=self._stop_account,
            on_refresh_page=self._refresh_page,
            on_reload_balance=self._reload_balance,
            on_update_target=self._update_account_target,
        )
        self._notebook.add(self._accounts_tab.frame, text="Accounts")

        # Activity log tab
        self._activity_log_tab = ActivityLogTab(parent=self._notebook)
        self._notebook.add(self._activity_log_tab.frame, text="Activity Log")

        self._setup_focus_handling()

    def _setup_focus_handling(self) -> None:
        self._focus_after_id: Optional[str] = None

        def _schedule_focus_current_tab() -> None:
            def _focus_current_tab() -> None:
                try:
                    current = self._notebook.nametowidget(self._notebook.select())
                    if current and isinstance(current, (tk.Frame, ttk.Frame)):
                        current.focus_set()
                except Exception:
                    pass

            if self._focus_after_id:
                try:
                    self._root.after_cancel(self._focus_after_id)
                except Exception:
                    pass
                finally:
                    self._focus_after_id = None

            self._focus_after_id = self._root.after(10, _focus_current_tab)

        def _on_tab_changed(_: object) -> None:
            try:
                current = self._notebook.nametowidget(self._notebook.select())
                if current and isinstance(current, (tk.Frame, ttk.Frame)):
                    current.focus_set()
            except Exception:
                pass

            _schedule_focus_current_tab()

        self._notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)
        self._notebook.bind("<ButtonRelease-1>", lambda e: _schedule_focus_current_tab())
        self._root.after_idle(_schedule_focus_current_tab)

    def _check_account_not_running(self, username: str) -> bool:
        is_not_running = username not in self._running_tools
        if is_not_running:
            message = f"Account '{username}' is not running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)

        return is_not_running

    def _run_account(
        self,
        username: str,
        password: str,
        spin_action: int,
        target_special_jackpot: int,
        close_when_jackpot_won: bool,
    ) -> None:
        # Avoid starting duplicate runner for same username
        if username in self._running_tools:
            message = f"Account '{username}' is already running"
            self._activity_log_tab.add_message(tag=MessageTag.WARNING, message=message)
            return

        # Build a dedicated tool instance for this account
        browser_index = len(self._running_tools)
        new_tool = MainTool(
            browser_index=browser_index,
            screen_width=self._root.winfo_screenwidth(),
            screen_height=self._root.winfo_screenheight(),
            req_width=self._root.winfo_reqwidth(),
            req_height=self._root.winfo_reqheight(),
            event_config=EVENT_CONFIGS_MAP[self._selected_event],
            username=username,
            password=password,
            spin_action=spin_action,
            target_special_jackpot=target_special_jackpot,
        )

        self._accounts_tab.update_browser_position(username=username, browser_index=browser_index)

        # Announce start in activity log
        spin_action_name = EVENT_CONFIGS_MAP[self._selected_event].spin_actions[spin_action - 1]
        message = f"Running account '{username}' with action '{spin_action_name}'"
        self._activity_log_tab.add_message(tag=MessageTag.INFO, message=message)

        def on_account_won(won_username: str) -> None:
            def _cb() -> None:
                self._accounts_tab.mark_account_as_won(username=won_username)
                if close_when_jackpot_won:
                    self._stop_account(username=won_username)

            self._root.after(0, _cb)

        def on_add_message(tag: MessageTag, message: str, compact: bool = False) -> None:
            def _cb() -> None:
                self._activity_log_tab.add_message(tag=tag, message=f"[{username}] {message}", compact=compact)

            self._root.after(0, _cb)

        def on_add_notification(nickname: str, jackpot_value: str) -> None:
            def _cb() -> None:
                self._notification_icon.add_notification(nickname=nickname, jackpot_value=jackpot_value)

            self._root.after(0, _cb)

        def on_update_current_jackpot(value: int) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_current_jackpot(value=value)

            self._root.after(0, _cb)

        def on_update_ultimate_prize_winner(nickname: str, value: str) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_ultimate_prize_winner(nickname=nickname, value=value)

            self._root.after(0, _cb)

        def on_update_mini_prize_winner(nickname: str, value: str) -> None:
            def _cb() -> None:
                self._activity_log_tab.update_mini_prize_winner(nickname=nickname, value=value)

            self._root.after(0, _cb)

        def on_update_user_info(username: str, user: UserDetail) -> None:
            def _cb() -> None:
                self._accounts_tab.update_user_info(username=username, user=user)

            self._root.after(0, _cb)

        new_tool.update_configs(
            is_running=True,
            on_account_won=on_account_won,
            on_add_message=on_add_message,
            on_add_notification=on_add_notification,
            on_update_current_jackpot=on_update_current_jackpot,
            on_update_ultimate_prize_winner=on_update_ultimate_prize_winner,
            on_update_mini_prize_winner=on_update_mini_prize_winner,
            on_update_user_info=on_update_user_info,
        )

        # Runner thread
        def handle_run_account() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(new_tool.run())

            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", f"Failed to run account: {error}")

        self._running_tools[username] = new_tool
        threading.Thread(target=handle_run_account, daemon=True).start()

    def _stop_account(self, username: str) -> None:
        if self._check_account_not_running(username=username):
            return

        running_tool = self._running_tools.pop(username)
        running_tool.update_configs(is_running=False)

        def handle_stop_account() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(running_tool.close())

            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", f"Failed to stop account: {error}")

        threading.Thread(target=handle_stop_account, daemon=True).start()

    def _reload_balance(self, username: str) -> None:
        if self._check_account_not_running(username=username):
            return

        running_tool = self._running_tools[username]

        def handle_reload_balance() -> None:
            if not running_tool:
                return

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(running_tool.reload_balance())

                messagebox.showinfo("Success", f"Account '{username}' balance reloaded successfully!")

            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", f"Failed to reload balance: {error}")

        threading.Thread(target=handle_reload_balance, daemon=True).start()

    def _refresh_page(self, username: str) -> None:
        if self._check_account_not_running(username=username):
            return

        running_tool = self._running_tools[username]

        def handle_page_reload() -> None:
            if not running_tool.page:
                return

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(running_tool.page.reload())

            except Exception as error:
                self._root.after(0, messagebox.showerror, "❌ Error", f"Failed to refresh page: {error}")

        threading.Thread(target=handle_page_reload, daemon=True).start()

    def _update_account_target(self, username: str, new_target: int) -> None:
        if self._check_account_not_running(username=username):
            return

        running_tool = self._running_tools[username]
        running_tool.update_target_special_jackpot(new_target)

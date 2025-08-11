import asyncio
import os
import shutil
from typing import Callable, Optional

from loguru import logger

from src.models import UserInfo
from src.utils.platforms import PlatformManager

from .auto_spin import AutoSpinHandler
from .browser_manager import BrowserManager
from .login_handler import LoginHandler
from .user_info_manager import UserInfoManager
from .websocket_monitor import WebSocketMonitor


class FCOnlineTool:
    """Main FC Online automation tool that coordinates all components."""

    # URL constants
    BASE_URL = "https://bilac.fconline.garena.vn/"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        target_special_jackpot: int = 10000,
        spin_action: int = 1,
    ) -> None:
        """
        Initialize FC Online automation tool.

        Args:
            username: User login username
            password: User login password
            headless: Run browser in headless mode
            target_special_jackpot: Jackpot value to trigger auto-spin
            spin_action: Spin action type (1-4)
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.spin_action = spin_action
        self.target_special_jackpot = target_special_jackpot

        # User data directory path - use platform-specific directory
        self._user_data_dir = PlatformManager.get_user_data_directory(username)

        # Initialize components
        self.browser_manager = BrowserManager(headless=headless, user_data_dir=self._user_data_dir)
        self.login_handler = LoginHandler(username=username, password=password)
        self.websocket_monitor = WebSocketMonitor()
        self.auto_spin_handler = AutoSpinHandler(spin_action=spin_action)
        self.user_info_manager = UserInfoManager()

        # Running state
        self._stop_flag = False
        self._needs_cookie_clear = False

        # Setup component callbacks
        self._setup_component_callbacks()

    def _setup_component_callbacks(self) -> None:
        """Setup callbacks between components."""
        # WebSocket monitor callbacks
        self.websocket_monitor.set_target_jackpot(self.target_special_jackpot)
        self.websocket_monitor.set_auto_spin_callback(self._trigger_auto_spin)

        # Auto-spin handler callbacks
        self.auto_spin_handler.set_message_callback(self._send_message)

        # User info manager callbacks
        self.user_info_manager.set_user_info_callback(self._on_user_info_updated)

    def _trigger_auto_spin(self) -> None:
        """Trigger auto-spin when target jackpot is reached."""
        if self.browser_manager.page:
            asyncio.create_task(
                self.auto_spin_handler.start_auto_spin(
                    page=self.browser_manager.page,
                    current_value=self.websocket_monitor.special_jackpot,
                    target_value=self.target_special_jackpot,
                )
            )

    def _send_message(self, message: str, code: str = "general") -> None:
        """Send message through WebSocket monitor callback."""
        if self.websocket_monitor.message_callback:
            self.websocket_monitor.message_callback(message, code)

    def _on_user_info_updated(self) -> None:
        """Handle user info updates."""
        if self.websocket_monitor.special_jackpot_callback:
            self.websocket_monitor.special_jackpot_callback()

    async def run(self) -> None:
        """
        Main automation loop - setup browser, login, and monitor WebSocket.

        Raises:
            Exception: For various automation errors
        """
        # Setup browser
        await self.browser_manager.setup_browser()

        try:
            # Clear cookies if needed (when credentials were updated before browser started)
            if self._needs_cookie_clear:
                try:
                    await self.browser_manager.page.context.clear_cookies()
                    logger.info("🍪 Cleared cookies after browser startup")
                    self._needs_cookie_clear = False
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clear cookies at startup: {e}")

            # Setup WebSocket interception before loading the page
            self.websocket_monitor.setup_websocket_listeners(page=self.browser_manager.page)

            # Navigate to base URL
            await self.browser_manager.page.goto(url=self.BASE_URL)
            await self.browser_manager.page.wait_for_load_state(state="networkidle")

            # Ensure user is logged in
            login_success = await self.login_handler.ensure_logged_in(page=self.browser_manager.page)
            if not login_success:
                logger.error("❌ Login failed!")
                return

            # Always fetch user info when starting automation
            await self.user_info_manager.fetch_user_info(page=self.browser_manager.page)

            logger.info("🚀 Starting WebSocket monitoring...")
            # Keep the browser open and monitor WebSocket
            while not self._stop_flag:
                await asyncio.sleep(delay=1)

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")

        finally:
            await self.browser_manager.close_browser()

    def stop(self) -> None:
        """Stop the automation tool."""
        self._stop_flag = True
        self.auto_spin_handler.stop()

    def start(self) -> None:
        """Start the automation tool."""
        self._stop_flag = False
        self.auto_spin_handler.start()

    def update_credentials(self, username: str, password: str) -> None:
        """
        Update login credentials and clean old user data if username changed.

        Args:
            username: New username
            password: New password

        Raises:
            Exception: For file system cleanup errors
        """
        old_username = self.username
        old_password = self.password

        # Only clean up if credentials actually changed
        credentials_changed = (old_username != username) or (old_password != password)

        if not credentials_changed:
            # No changes, nothing to do
            return

        if old_username != username:
            # Username changed, clean old user data directory
            old_user_data_dir = PlatformManager.get_user_data_directory(old_username)
            try:
                if os.path.exists(old_user_data_dir):
                    shutil.rmtree(old_user_data_dir)
                logger.info(f"🧹 Cleaned old user data directory: {old_user_data_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean old user data directory: {e}")

        # Update credentials and user data directory
        self.username = username
        self.password = password
        self._user_data_dir = PlatformManager.get_user_data_directory(username)

        # Update components
        self.login_handler.update_credentials(username=username, password=password)
        self.browser_manager.user_data_dir = self._user_data_dir

        # Clear cached data only when credentials changed
        self.user_info_manager.clear_cookies()

        # Clear browser cookies if browser is running and credentials changed
        if self.browser_manager.page:
            try:
                # Check if we're already in an event loop
                loop = asyncio.get_running_loop()
                # Schedule the cookie clearing in the existing loop
                loop.create_task(self.browser_manager.page.context.clear_cookies())
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                try:
                    asyncio.run(self.browser_manager.page.context.clear_cookies())
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clear cookies: {e}")
        else:
            # Mark that cookies need to be cleared when browser starts
            self._needs_cookie_clear = True
            logger.info("🍪 Cookies will be cleared when browser starts")

        # Notify GUI to update user info display
        if self.websocket_monitor.special_jackpot_callback:
            self.websocket_monitor.special_jackpot_callback()

    def update_config(self, target_special_jackpot: int, spin_action: int) -> None:
        """
        Update automation configuration.

        Args:
            target_special_jackpot: New target jackpot value
            spin_action: New spin action type
        """
        self.target_special_jackpot = target_special_jackpot
        self.spin_action = spin_action

        # Update components
        self.websocket_monitor.set_target_jackpot(target_special_jackpot)
        self.auto_spin_handler.set_spin_action(spin_action)

    def set_callbacks(
        self,
        message_callback: Optional[Callable[[str], None]] = None,
        user_info_callback: Optional[Callable[[], None]] = None,
        special_jackpot_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Set callbacks for GUI updates.

        Args:
            message_callback: Function to call with status messages
            user_info_callback: Function to call when user info updates
            special_jackpot_callback: Function to call when special jackpot changes
        """
        if message_callback:
            self.websocket_monitor.message_callback = message_callback

        if user_info_callback:
            self.user_info_manager.user_info_callback = user_info_callback

        if special_jackpot_callback:
            self.websocket_monitor.special_jackpot_callback = special_jackpot_callback

    async def close_browser(self) -> None:
        """Close browser context and cleanup resources."""
        await self.browser_manager.close_browser()

    @property
    def user_info(self) -> Optional["UserInfo"]:
        """Get current user info."""
        return self.user_info_manager.user_info

    @property
    def special_jackpot(self) -> int:
        """Get current special jackpot value."""
        return self.websocket_monitor.special_jackpot

import asyncio
from typing import Callable, Optional

from loguru import logger
from playwright.async_api import Page


class AutoSpinHandler:
    """Handles automatic spinning when target jackpot is reached."""

    # Spin action selectors
    SPIN_ACTION_1_SELECTOR = "div.spin__actions a.btn-spin.btn-spin--1"
    SPIN_ACTION_2_SELECTOR = "div.spin__actions a.btn-spin.btn-spin--2"
    SPIN_ACTION_3_SELECTOR = "div.spin__actions a.btn-spin.btn-spin--3"
    SPIN_ACTION_4_SELECTOR = "div.spin__actions a.btn-spin.btn-spin--4"

    SPIN_ACTION_SELECTORS = {
        1: (SPIN_ACTION_1_SELECTOR, "Free Spin"),
        2: (SPIN_ACTION_2_SELECTOR, "FC10 Spin"),
        3: (SPIN_ACTION_3_SELECTOR, "FC190 Spin"),
        4: (SPIN_ACTION_4_SELECTOR, "FC900 Spin"),
    }

    def __init__(self, spin_action: int = 1) -> None:
        """
        Initialize the auto-spin handler.

        Args:
            spin_action: Spin action type (1-4)
        """
        self.spin_action = spin_action
        self._stop_flag = False
        self._message_callback: Optional[Callable[[str, str], None]] = None

    async def start_auto_spin(self, page: Page, current_value: int, target_value: int) -> None:
        """
        Start automatic spinning when target is reached.

        Args:
            page: Playwright page instance
            current_value: Current jackpot value
            target_value: Target jackpot threshold

        Raises:
            Exception: For page interaction errors
        """
        selector = self.SPIN_ACTION_SELECTORS.get(self.spin_action, self.SPIN_ACTION_1_SELECTOR)[0]

        try:
            while current_value >= target_value and not self._stop_flag:
                # Check for and handle SweetAlert2 modal first
                #  await self._handle_swal_modal(page)

                spin_element = await page.query_selector(selector)
                if spin_element:
                    try:
                        # Use JavaScript click to bypass intercepting elements
                        await page.evaluate(f"document.querySelector('{selector}').click()")
                        if self._message_callback:
                            msg = f"🎰 Auto-spinning with action: {self.SPIN_ACTION_SELECTORS.get(self.spin_action, 'Unknown')[1]}"  # noqa: E501
                            self._message_callback(msg, "event")
                    except Exception as click_error:
                        logger.warning(f"⚠️ Click failed, trying alternative method: {click_error}")
                        # Try JavaScript click as fallback
                        await page.evaluate(f"document.querySelector('{selector}').click()")
                else:
                    logger.warning(f"⚠️ Spin element not found: {selector}")
                    break

                # Small delay to prevent overwhelming the browser
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"❌ Auto-spin error: {e}")

    async def _handle_swal_modal(self, page: Page) -> None:
        """
        Handle SweetAlert2 modal if present.

        Args:
            page: Playwright page instance

        Raises:
            Exception: For modal handling errors (non-critical)
        """
        try:
            # Check if SweetAlert2 modal is present
            swal_container = await page.query_selector(".swal2-container")
            if swal_container:
                # Try to find and click OK/Confirm button
                confirm_btn = await page.query_selector(".swal2-confirm")
                if confirm_btn:
                    await confirm_btn.click(force=True)
                    await asyncio.sleep(0.2)  # Wait for modal to close
                else:
                    # Try other common button selectors
                    for btn_selector in [".swal2-styled", ".swal2-close", ".swal2-cancel"]:
                        btn = await page.query_selector(btn_selector)
                        if btn:
                            await btn.click(force=True)
                            await asyncio.sleep(0.2)
                            break
        except Exception as e:
            logger.debug(f"Modal handling error (non-critical): {e}")

    def set_spin_action(self, spin_action: int) -> None:
        """
        Set the spin action type.

        Args:
            spin_action: Spin action type (1-4)
        """
        self.spin_action = spin_action

    def set_message_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Set callback for sending messages during auto-spin.

        Args:
            callback: Function to call with messages
        """
        self._message_callback = callback

    def stop(self) -> None:
        """Stop the auto-spin process."""
        self._stop_flag = True

    def start(self) -> None:
        """Start the auto-spin process."""
        self._stop_flag = False

from loguru import logger
from playwright.async_api import Page


class LoginHandler:
    """Handles user login and authentication for FC Online."""

    # Selector constants
    LOGIN_BTN_SELECTOR = "a.btn-header.btn-header--login"
    LOGOUT_BTN_SELECTOR = "a.btn-header.btn-header--logout"
    USERNAME_INPUT_SELECTOR = "form input[type='text']"
    PASSWORD_INPUT_SELECTOR = "form input[type='password']"
    SUBMIT_BTN_SELECTOR = "form button[type='submit']"

    # URL constants
    BASE_URL = "https://bilac.fconline.garena.vn/"

    def __init__(self, username: str, password: str) -> None:
        """
        Initialize the login handler.

        Args:
            username: User login username
            password: User login password
        """
        self.username = username
        self.password = password

    async def check_login_status(self, page: Page) -> bool:
        """
        Check if user is logged in by looking for login/logout buttons.

        Args:
            page: Playwright page instance

        Returns:
            True if logged in, False otherwise

        Raises:
            Exception: For page interaction errors
        """
        try:
            # Check for login button (not logged in)
            login_btn = await page.query_selector(selector=self.LOGIN_BTN_SELECTOR)
            if login_btn:
                return False

            # Check for logout button (logged in)
            logout_btn = await page.query_selector(selector=self.LOGOUT_BTN_SELECTOR)
            if logout_btn:
                return True

            logger.warning("⚠️ Unable to determine login status")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking login status: {e}")
            return False

    async def perform_login(self, page: Page) -> bool:
        """
        Perform login by filling credentials and submitting form.

        Args:
            page: Playwright page instance

        Returns:
            True if login successful, False otherwise

        Raises:
            Exception: For page interaction or login errors
        """
        try:
            # Click login button
            login_btn = await page.query_selector(selector=self.LOGIN_BTN_SELECTOR)
            if not login_btn:
                logger.error("❌ Login button not found")
                return False

            await login_btn.click()

            # Wait for login page to load
            await page.wait_for_load_state(state="networkidle")

            # Fill username
            username_input = await page.query_selector(selector=self.USERNAME_INPUT_SELECTOR)
            if username_input:
                await username_input.fill(value=self.username)

            # Fill password
            password_input = await page.query_selector(selector=self.PASSWORD_INPUT_SELECTOR)
            if password_input:
                await password_input.fill(value=self.password)

            # Click submit button
            submit_btn = await page.query_selector(selector=self.SUBMIT_BTN_SELECTOR)
            if not submit_btn:
                logger.error("❌ Submit button not found")
                return False

            await submit_btn.click()

            # Wait for login completion - either redirect to BASE_URL or stay on login page for captcha
            logger.info("🔐 Login form submitted, waiting for response...")

            # Wait for either successful redirect to BASE_URL or captcha/error handling
            try:
                # Wait for navigation or URL change (up to 30 seconds for captcha solving)
                wait_condition = (
                    f"window.location.href.includes('{self.BASE_URL}') || "
                    "document.querySelector('.captcha') || document.querySelector('.error')"
                )
                await page.wait_for_function(wait_condition)

                # Check current URL to determine login result
                current_url = page.url
                if self.BASE_URL in current_url:
                    logger.success("🔐 Login completed successfully - redirected to main page")
                    return True
                else:
                    # Still on login page, might need captcha or have error
                    logger.info("🔐 Login requires additional steps (captcha/verification)")

                    # Wait for user to solve captcha and redirect (up to 5 minutes)
                    logger.info("⏳ Waiting for captcha resolution and redirect...")
                    await page.wait_for_function(f"window.location.href.includes('{self.BASE_URL}')")

                    logger.success("🔐 Login completed successfully after captcha resolution")
                    return True

            except Exception as timeout_error:
                logger.error(f"❌ Login timeout or failed: {timeout_error}")
                return False

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    async def ensure_logged_in(self, page: Page) -> bool:
        """
        Ensure user is logged in, performing login if necessary.

        Args:
            page: Playwright page instance

        Returns:
            True if logged in successfully, False otherwise
        """
        # Check login status and perform login if needed
        login_needed = not await self.check_login_status(page=page)
        if login_needed:
            login_success = await self.perform_login(page=page)
            if not login_success:
                logger.error("❌ Login failed!")
                return False

            # After successful login, ensure we're back to BASE_URL
            current_url = page.url
            if self.BASE_URL not in current_url:
                logger.info("🔄 Navigating back to main page after login...")
                await page.goto(url=self.BASE_URL)
                await page.wait_for_load_state(state="networkidle")

        return True

    def update_credentials(self, username: str, password: str) -> None:
        """
        Update login credentials.

        Args:
            username: New username
            password: New password
        """
        self.username = username
        self.password = password

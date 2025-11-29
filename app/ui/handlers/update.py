from tkinter import messagebox

from loguru import logger

from app.core.managers.local_config import local_config_mgr
from app.core.managers.update import update_mgr
from app.ui.components.dialogs.input import ask_string_custom
from app.ui.components.dialogs.update import UpdateDialog
from app.ui.handlers.base import BaseHandler
from app.ui.utils.ui_helpers import UIHelpers
from app.utils.concurrency import run_in_thread


class UpdateHandler(BaseHandler):
    def check(self, license_key: str, is_auto_check: bool = True) -> None:
        async def _check() -> None:
            try:
                # Check license first
                license_valid = await self._check_license_key(license_key=license_key, is_auto_check=is_auto_check)
                if not license_valid:
                    return

                # If license is valid, check for updates
                await self._check_latest_update()

            except Exception as error:
                logger.warning(f"Startup check failed: {error}")

        run_in_thread(coro_func=_check)

    async def _check_license_key(self, license_key: str, is_auto_check: bool) -> bool:
        logger.info("Starting license key validation...")
        logger.debug(f"License key from config: {'<set>' if license_key else '<empty>'}")

        # If no license key, prompt user to enter one
        if not license_key:
            self._root.after(
                0,
                lambda: self._prompt_license_key(
                    initial_value=license_key,
                    is_auto_check=is_auto_check,
                ),
            )
            return False

        # Check global active flag
        if not self._app_configs.is_active:
            self._root.after(
                0,
                lambda: UIHelpers.show_blocking_error(
                    root=self._root,
                    message=self._app_configs.message,
                ),
            )
            return False

        # Check if license is blocked
        if license_key in self._app_configs.blocked_licenses:
            # Show error and prompt for new license
            messagebox.showerror("License Blocked", self._app_configs.blocked_license_message)
            self._root.after(
                0,
                lambda: self._prompt_license_key(
                    initial_value=license_key,
                    is_auto_check=is_auto_check,
                ),
            )
            return False

        # Check if license is valid
        if license_key not in self._app_configs.valid_licenses:
            messagebox.showerror("Invalid License", self._app_configs.invalid_license_message)
            self._root.after(
                0,
                lambda: self._prompt_license_key(
                    initial_value=license_key,
                    is_auto_check=is_auto_check,
                ),
            )
            return False

        logger.success(f"License key validated successfully: {license_key[:8]}...")

        # Save to config
        if self._local_configs.license_key != license_key:
            self._local_configs.license_key = license_key.strip()
            local_config_mgr.save_local_configs(configs=self._local_configs)

        return True

    async def _check_latest_update(self) -> None:
        logger.info("Checking for application updates...")
        has_update, latest_version, release_notes = await update_mgr.check_for_updates()

        if not has_update or not latest_version:
            logger.info("Application is up to date")
            return

        logger.info(f"Update available: {latest_version}")
        # Schedule UI update on main thread
        self._root.after(
            0,
            lambda: UpdateDialog(
                parent=self._root,
                latest_version=latest_version,
                release_notes=release_notes,
            ),
        )

    def manual_change_license_key(self) -> None:
        current_license = self._local_configs.license_key
        self._prompt_license_key(initial_value=current_license, is_auto_check=False)

    def _prompt_license_key(self, initial_value: str = "", is_auto_check: bool = True) -> None:
        while True:
            license_key = ask_string_custom(
                title="License Key Required",
                prompt="Please enter your license key:",
                parent=self._root,
                initialvalue=initial_value,
                width=60,
            )

            # User cancelled
            if license_key is None:
                if is_auto_check:
                    # Must enter license, cancel closes app
                    UIHelpers.show_blocking_error(
                        root=self._root,
                        message="License key is required to use this application.",
                    )
                # else: Manual change, just close dialog
                return

            # User entered empty/whitespace
            if not license_key.strip():
                # Show error and loop back to prompt
                messagebox.showerror("Invalid Input", "License key cannot be empty. Please try again.")
                continue

            # Valid input - save and validate
            break

        # Retry startup check
        self._root.after(100, lambda: self.check(license_key=license_key, is_auto_check=is_auto_check))

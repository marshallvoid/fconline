import json
from tkinter import messagebox, simpledialog

import aiohttp
from loguru import logger

from app.core.managers.config import config_mgr
from app.core.managers.request import request_mgr
from app.core.managers.update import update_mgr
from app.schemas.app_status import AppStatus
from app.ui.components.dialogs.update_dialog import UpdateDialog
from app.ui.utils.ui_factory import UIFactory
from app.utils.concurrency import run_in_thread

from .base_handler import BaseHandler


class UpdateHandler(BaseHandler):
    def check(self, is_auto_check: bool = True) -> None:
        async def _check() -> None:
            try:
                # Check license first
                license_valid = await self._check_license_key(is_auto_check=is_auto_check)
                if not license_valid:
                    return

                # If license is valid, check for updates
                await self._check_latest_update()

            except Exception as e:
                logger.warning(f"Startup check failed: {e}")

        run_in_thread(coro_func=_check)

    async def _check_license_key(self, is_auto_check: bool) -> bool:
        # Get license key from config
        license_key = self._configs.license_key

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

        # Check application status from Gist
        async with aiohttp.ClientSession(connector=request_mgr.secure_connector) as session:
            async with session.get(self._settings.gist_url, timeout=request_mgr.get_timeout(timeout=10)) as response:
                if not response.ok:
                    return False

                try:
                    gist_text = await response.text()
                    gist_json = json.loads(gist_text)
                    gist_data = AppStatus.model_validate(gist_json)

                except Exception as e:
                    logger.error(f"Failed to check license key: {e}")
                    gist_data = AppStatus()

                # Check global active flag
                if not gist_data.is_active:
                    self._root.after(0, lambda: UIFactory.show_blocking_error(self._root, gist_data.message))
                    return False

                # Check if license is blocked
                if license_key in gist_data.blocked_licenses:
                    # Show error and prompt for new license
                    self._root.after(
                        0,
                        lambda: self._show_license_error_and_retry(
                            title="License Blocked",
                            message=gist_data.blocked_message,
                            initial_value=license_key,
                            is_auto_check=is_auto_check,
                        ),
                    )
                    return False

                # Check if license is valid
                if license_key not in gist_data.valid_licenses:
                    self._root.after(
                        0,
                        lambda: self._show_license_error_and_retry(
                            title="Invalid License",
                            message=gist_data.invalid_license_message,
                            initial_value=license_key,
                            is_auto_check=is_auto_check,
                        ),
                    )
                    return False

        return True

    def _show_license_error_and_retry(self, title: str, message: str, initial_value: str, is_auto_check: bool) -> None:
        messagebox.showerror(title, message)
        self._prompt_license_key(initial_value=initial_value, is_auto_check=is_auto_check)

    async def _check_latest_update(self) -> None:
        has_update, latest_version, release_notes = await update_mgr.check_for_updates()
        if has_update and latest_version:
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
        current_license = self._configs.license_key
        self._prompt_license_key(initial_value=current_license, is_auto_check=False)

    def _prompt_license_key(self, initial_value: str = "", is_auto_check: bool = True) -> None:
        while True:
            license_key = simpledialog.askstring(
                "License Key Required",
                "Please enter your license key:",
                initialvalue=initial_value,
                parent=self._root,
            )

            # User cancelled
            if license_key is None:
                if is_auto_check:
                    # Must enter license, cancel closes app
                    UIFactory.show_blocking_error(self._root, "License key is required to use this application.")
                # else: Manual change, just close dialog
                return

            # User entered empty/whitespace
            if not license_key.strip():
                # Show error and loop back to prompt
                messagebox.showerror("Invalid Input", "License key cannot be empty. Please try again.")
                continue

            # Valid input - save and validate
            break

        # Save to config
        self._configs.license_key = license_key.strip()
        config_mgr.save_configs(configs=self._configs)

        # Retry startup check
        self._root.after(100, lambda: self.check(is_auto_check=is_auto_check))

# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all apprise data, binaries, and hidden imports
apprise_datas, apprise_binaries, apprise_hiddenimports = collect_all('apprise')

a = Analysis(
    ['app/main/ui/app.py'],
    pathex=[os.getcwd()],
    binaries=apprise_binaries,
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else None,
    ] + apprise_datas,
    hiddenimports=[
        # GUI and theming
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'sv_ttk',
        'darkdetect',
        'playsound3',
        'dishka',
        'pydantic_settings',

        # Networking and automation
        'aiohttp',
        'certifi',
        'markdown2',
        'packaging',
        'tkhtmlview',
        'loguru',
        'pydantic',
        'cryptography',
        'cryptography.fernet',
        'playwright',
        'playwright.async_api',
        'browser_use',
        'browser_use.browser',
        'browser_use.browser.types',
        'browser_use.browser.context',
        'browser_use.agent',
        'browser_use.agent.service',
        'browser_use.controller',
        'browser_use.controller.service',
        'browser_use.dom',
        'browser_use.dom.service',

        # HTTP client libraries
        'httpx',
        'httpcore',
        'requests',
        'requests.auth',
        'requests.sessions',
        'requests.models',
        'requests.adapters',

        # Additional runtime libraries
        'shortuuid',

        # Project modules
        'app.main.ui.app',

        'app.core.configs',
        'app.core.configs.settings',

        'app.core.managers',
        'app.core.managers.config',
        'app.core.managers.file',
        'app.core.managers.notifier',
        'app.core.managers.platform',
        'app.core.managers.request',
        'app.core.managers.update',
        'app.core.managers.version',

        'app.core.providers',
        'app.core.providers.configs',
        'app.core.providers.factory',

        'app.infrastructure',
        'app.infrastructure.logging',

        'app.infrastructure.clients',
        'app.infrastructure.clients.main',
        'app.infrastructure.clients.github',

        'app.schemas',
        'app.schemas.app_config',
        'app.schemas.local_config',
        'app.schemas.billboard',
        'app.schemas.spin_response',
        'app.schemas.user_response',

        'app.schemas.enums',
        'app.schemas.enums.account_tag',
        'app.schemas.enums.message_tag',
        'app.schemas.enums.payment_type',

        'app.services',
        'app.services.main',

        'app.services.handlers.login',
        'app.services.handlers.websocket',

        'app.ui',

        'app.ui.windows.main',

        'app.ui.components.notification_icon',

        'app.ui.components.tabs.accounts',
        'app.ui.components.tabs.activity_log',

        'app.ui.components.dialogs.notification',
        'app.ui.components.dialogs.update',
        'app.ui.components.dialogs.upsert_account',

        'app.ui.utils.ui_factory',
        'app.ui.utils.ui_helpers',

        'app.utils',
        'app.utils.concurrency',
        'app.utils.constants',
        'app.utils.helpers',
        'app.utils.sounds',

        'app.utils.decorators',
        'app.utils.decorators.singleton',

        'app.utils.types',
        'app.utils.types.callback',
    ] + apprise_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'selenium',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out None values from datas
a.datas = [item for item in a.datas if item is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [], # Exclude binaries/datas for onedir
    exclude_binaries=True,
    name='FC_Online_Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FC_Online_Automation'
)

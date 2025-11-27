# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['app/main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else None,
        ('.env', '.') if os.path.exists('.env') else None,
    ],
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

        # HTTP client libraries (required by browser_use and langchain)
        'httpx',
        'httpcore',
        'requests',
        'requests.auth',
        'requests.sessions',
        'requests.models',
        'requests.adapters',

        # Additional runtime libraries
        'shortuuid',

        # Project modules (explicit to help PyInstaller discovery)
        'app.main',

        'app.core.configs',
        'app.core.configs.settings',

        'app.core.managers',
        'app.core.managers.config',
        'app.core.managers.file',
        'app.core.managers.notifier',
        'app.core.managers.platform',
        'app.core.managers.request',
        'app.core.managers.update',
        'app.core.managers.version_manager',  # Added new manager

        'app.core.providers',
        'app.core.providers.configs',
        'app.core.providers.factory',

        'app.infrastructure',

        'app.infrastructure.clients',
        'app.infrastructure.clients.internal_client',
        'app.infrastructure.clients.main_client',

        'app.infrastructure.logging',

        'app.schemas',

        'app.schemas.enums',
        'app.schemas.enums.account_tag',
        'app.schemas.enums.message_tag',

        'app.schemas.billboard',
        'app.schemas.configs',
        'app.schemas.spin_response',
        'app.schemas.user_response',

        'app.services',
        'app.services.login_handler',
        'app.services.main_service',
        'app.services.websocket_handler',

        'app.ui',
        'app.ui.components.accounts_tab',
        'app.ui.components.activity_log_tab',
        'app.ui.components.notification_icon',
        'app.ui.components.update_dialog',

        'app.ui.utils.ui_factory',
        'app.ui.utils.ui_helpers',

        'app.ui.windows.main_window',

        'app.utils',

        'app.utils.decorators',
        'app.utils.decorators.singleton',

        'app.utils.types',
        'app.utils.types.callback',

        'app.utils.concurrency',
        'app.utils.constants',
        'app.utils.helpers',
        'app.utils.sounds',
    ],
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
    name='FC_Online_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
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
    name='FC_Online_Tool'
)

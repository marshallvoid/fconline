# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else None,
    ],
    hiddenimports=[
        # GUI and theming
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'sv_ttk',
        'darkdetect',
        'playsound3',
        'apprise',
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
        'src.main',

        'src.core.configs',
        'src.core.configs.settings',

        'src.core.decorators',
        'src.core.decorators.singleton',

        'src.core.managers',
        'src.core.managers.config',
        'src.core.managers.file',
        'src.core.managers.notifier',
        'src.core.managers.platform',
        'src.core.managers.request',

        'src.core.providers',
        'src.core.providers.configs',
        'src.core.providers.factory',

        'src.infrastructure',
        'src.infrastructure.logger',
        'src.infrastructure.client',

        'src.gui',
        'src.gui.main_window',
        'src.gui.accounts_tab',
        'src.gui.activity_log_tab',
        'src.gui.notification_icon',

        'src.services',
        'src.services.main_tool',
        'src.services.login_handler',
        'src.services.websocket_handler',

        'src.schemas',
        'src.schemas.configs',
        'src.schemas.billboard',
        'src.schemas.spin_response',
        'src.schemas.user_response',
        'src.schemas.enum',
        'src.schemas.enum.account_tag',
        'src.schemas.enum.message_tab',

        'src.utils',
        'src.utils.concurrency',
        'src.utils.contants',
        'src.utils.helpers',
        'src.utils.sounds',
        'src.utils.types',
        'src.utils.types.callbacks',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    version='version_info.txt',
    name='FC_Online_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
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
    name='FC_Online_Tool'
)

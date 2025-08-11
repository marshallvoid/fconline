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

        # Networking and automation
        'playwright',
        'playwright.async_api',
        'browser_use',
        'browser_use.browser',
        'browser_use.browser.context',
        'aiohttp',
        'loguru',
        'pydantic',
        'cryptography.fernet',
        'watchdog',
        'winreg',  # Windows-only, safe to include

        # Project modules (explicit to help PyInstaller discovery)
        'src.main',
        'src.models',
        'src.utils',
        'src.utils.credentials',
        'src.utils.platforms',
        'src.infrastructure',
        'src.infrastructure.logger',
        'src.infrastructure.client',
        'src.infrastructure.auto_reload',
        'src.core',
        'src.core.auto_spin',
        'src.core.browser_manager',
        'src.core.fc_automation',
        'src.core.login_handler',
        'src.core.user_info_manager',
        'src.core.websocket_monitor',
        'src.gui',
        'src.gui.main_window',
        'src.gui.control_panel',
        'src.gui.user_info_panel',
        'src.gui.user_settings_panel',
        'src.gui.log_panel',
        'src.gui.header',
        'src.gui.styles',
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
        'faker',
        'fake_useragent',
        'ua_parser',
        'user_agents',
        'pillow',
        'pillow_heif',
        'beautifulsoup4',
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
    name='FC_Online_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

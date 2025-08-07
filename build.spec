# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else None,
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'sv_ttk',
        'darkdetect',
        'browser_use',
        'aiohttp',
        'beautifulsoup4',
        'loguru',
        'pillow',
        'pillow_heif',
        'pydantic',
        'fake_useragent',
        'faker',
        'ua_parser',
        'user_agents',
        'watchdog',
        'asyncio',
        'threading',
        'datetime',
        'tempfile',
        'json',
        'base64',
        'os',
        'platform',
        'sys',
        'cryptography.fernet',
        'src.logger',
        'src.tool',
        'src.gui',
        'src.client',
        'src.types',
        'src.auto_reload',
        'src.utils',
        'src.utils.platform',
        'winreg',  # For Windows registry access
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
    console=True,  # Temporarily enable console for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

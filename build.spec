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
        'browser_use.agent',
        'browser_use.agent.service',
        'browser_use.controller',
        'browser_use.controller.service',
        'browser_use.dom',
        'browser_use.dom.service',
        'aiohttp',
        'loguru',
        'pydantic',
        'cryptography.fernet',
        'watchdog',

        # Langchain dependencies (required by browser_use)
        'langchain_core',
        'langchain_core.callbacks',
        'langchain_core.callbacks.manager',
        'langchain_core.callbacks.base',
        'langchain_core.language_models',
        'langchain_core.language_models.chat_models',
        'langchain_core.language_models.llms',
        'langchain_core.messages',
        'langchain_core.messages.base',
        'langchain_core.messages.ai',
        'langchain_core.messages.human',
        'langchain_core.messages.system',
        'langchain_core.prompts',
        'langchain_core.prompts.base',
        'langchain_core.prompts.chat',
        'langchain_core.runnables',
        'langchain_core.runnables.base',
        'langchain_core.tools',
        'langchain_core.tools.base',
        'langchain_core.utils',
        'langchain_core.outputs',
        'langchain_core.load',

        # HTTP client libraries (required by browser_use and langchain)
        'requests',
        'requests.auth',
        'requests.sessions',
        'requests.models',
        'requests.adapters',
        'httpx',
        'httpcore',

        # Additional dependencies
        'anthropic',
        'openai',
        'tiktoken',

        # Project modules (explicit to help PyInstaller discovery)
        'src.main',
        'src.schemas',
        'src.utils',
        'src.utils.credentials',
        'src.utils.platforms',
        'src.utils.contants',
        'src.infrastructure',
        'src.infrastructure.logger',
        'src.infrastructure.client',
        'src.infrastructure.auto_reload',
        'src.core',
        'src.core.main_tool',
        'src.core.event_config',
        'src.gui',
        'src.gui.main_window',
        'src.gui.components',
        'src.gui.components.event_tab',
        'src.gui.components.activity_log_tab',
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

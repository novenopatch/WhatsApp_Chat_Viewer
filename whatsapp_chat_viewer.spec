# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for WhatsApp Chat Viewer.

Build standalone executables for Windows, macOS, and Linux.

Usage:
    # Build single-file executable (recommended for distribution)
    pyinstaller --onefile whatsapp_chat_viewer.spec

    # Build directory-based executable (faster startup)
    pyinstaller whatsapp_chat_viewer.spec
"""

block_cipher = None

a = Analysis(
    ['build.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include templates directory
        ('src/templates', 'src/templates'),
    ],
    hiddenimports=[
        # Ensure all imports are captured
        'src',
        'src.config',
        'src.constants',
        'src.hash_validator',
        'src.i18n',
        'src.logging_config',
        'src.monitor',
        'src.parser',
        'src.renderer',
        'src.server',
        'src.stats',
        'src.user_detector',
        'src.zip_handler',
        # Pillow/PIL modules for image processing
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        # python-dotenv
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='whatsapp-chat-viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for CLI usage
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path if available
)

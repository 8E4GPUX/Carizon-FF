# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pack_v3.2.1.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Auto_pack.sh', '.'),
    ],
    hiddenimports=[
        'paramiko',
        'customtkinter',
        'openpyxl',
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'threading',
        'tempfile',
        'stat',
        'datetime',
        'typing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='CARIZON数据切分工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

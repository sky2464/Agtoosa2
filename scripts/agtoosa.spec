# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building standalone Agtoosa2 binary."""

import os
from pathlib import Path

block_cipher = None

spec_root = Path(os.path.abspath(SPEC)).parent
repo_root = spec_root.parent

a = Analysis(
    [str(repo_root / 'agtoosa' / '__main__.py')],
    pathex=[str(repo_root)],
    datas=[
        (str(repo_root / 'agtoosa' / 'graph' / 'web'), 'agtoosa/graph/web'),
    ],
    hiddenimports=[
        'agtoosa',
        'agtoosa.core',
        'agtoosa.core.model',
        'agtoosa.core.security',
        'agtoosa.core.context_compiler',
        'agtoosa.core.lifecycle',
        'agtoosa.graph',
        'agtoosa.graph.store',
        'agtoosa.graph.metrics',
        'agtoosa.graph.query',
        'agtoosa.graph.export',
        'agtoosa.graph.visualizer',
        'agtoosa.parser',
        'agtoosa.parser.base',
        'agtoosa.parser.scanner',
        'agtoosa.parser.python_parser',
        'agtoosa.parser.js_ts_parser',
        'agtoosa.parser.shell_parser',
        'agtoosa.parser.doc_parser',
        'agtoosa.parser.polyglot_parser',
        'agtoosa.watcher',
        'agtoosa.watcher.watcher',
        'agtoosa.watcher.hooks',
        'agtoosa.review',
        'agtoosa.review.intelligence',
        'agtoosa.review.memory',
        'agtoosa.review.ci',
        'agtoosa.cli',
        'agtoosa.cli.main',
        'agtoosa.cli.graph_cmd',
        'agtoosa.cli.lifecycle_cmd',
        'agtoosa.mcp',
        'agtoosa.mcp.server',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'pydoc',
        'xmlrpc',
        'curses',
        'tcl',
        'tk',
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
    name='agtoosa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

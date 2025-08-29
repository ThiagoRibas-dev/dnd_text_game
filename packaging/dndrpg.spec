# packaging/dndrpg.spec
# Run: pyinstaller --noconfirm --clean ../packaging/dndrpg.spec
block_cipher = None

from PyInstaller.utils.hooks import collect_submodules

hidden = []
hidden += collect_submodules('pydantic')
hidden += collect_submodules('pydantic_core')
hidden += collect_submodules('py_expression_eval')

a = Analysis(
    ['../src/dndrpg/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('../src/dndrpg/content', 'dndrpg/content'),
        ('../.venv/Lib/site-packages/textual', 'textual'),
        ('../.venv/Lib/site-packages/rich', 'rich'),
        ('../.venv/Lib/site-packages/typing_extensions-4.15.0.dist-info', 'typing_extensions')
        ],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DnD-RPG',
    console=True,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name='dndrpg')

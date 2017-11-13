# -*- mode: python -*-

block_cipher = None


a = Analysis(['setup.py', 'main.py'],
             pathex=['C:\\Users\\Mike\\Dropbox\\CS50 Project\\roguelike'],
             binaries=[],
             datas=['terminal16x16.png','grendel.png','SDL2.dll'],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='setup',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='setup')

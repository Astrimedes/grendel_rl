# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\Users\\Mike\\Dropbox\\CS50 Project\\roguelike'],
             binaries=[('SDL2.dll', '.')],
             datas=[('terminal16x16.png', '.'), ('grendel.png', '.')],
             hiddenimports=['cffi'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['savegame.dat', 'savegame.bak', 'savegame.dir'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='grendel',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='grendel')

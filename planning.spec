# -*- mode: python
# coding: utf-8 -*-

block_cipher = None

a = Analysis(['planning\\app.py'],
             pathex=['C:\\Users\\CassanR\\Perso\\Code\\Python\\planning'],
             binaries=[],
             datas=[('C:\\Users\\CassanR\\Perso\\Code\\Python\\planning\\data', 'data'),
                    ('C:\\Users\\CassanR\\Miniconda3\\envs\\planning\\Lib\\site-packages\\PySide6\\plugins', 'PySide6\\plugins'),
                    ],
             hiddenimports=['PySide6.QtXml'],
             hookspath=["C:\\Users\\CassanR\\Perso\\Code\\Python\\Pyinstaller-hooks"],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
			
			 
pyz = PYZ(a.pure,
          a.zipped_data,
		  cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Planning',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False,
		#  icon='sources\\binaries\\Wallpaper_by_DB.ico'
		)
		  
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Planning')

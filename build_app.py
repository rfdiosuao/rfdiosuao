import PyInstaller.__main__
import os
import shutil

# Clean up previous build
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

if os.path.exists('AutoScriptPro.spec'):
    os.remove('AutoScriptPro.spec')

print("Starting build process...")

PyInstaller.__main__.run([
    'main.py',
    '--name=AutoScriptPro_Updated',
    '--onefile',
    '--noconsole',
    '--clean',
    # Collect customtkinter assets
    '--collect-all=customtkinter',
    # Ensure other deps are included
    '--hidden-import=keyboard',
    '--hidden-import=mouse',
    '--hidden-import=PIL',
    '--hidden-import=clicker_core',
    # Data files (source;dest)
    '--add-data=icon.png;.',
    '--add-data=icon.ico;.',
    # Icon
    '--icon=icon.ico', 
])

print("Build complete. Check the 'dist' folder.")

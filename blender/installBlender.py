import shutil
import os
import json

def main():
    blendDir = '''C:\Program Files\Blender Foundation\Blender\\2.67\scripts\\addons'''
    fromDir = 'io_import_sprites'
    toDir = os.path.join(blendDir, fromDir)
    print(toDir)
    #WARNING Hard coded for gimp2.8
    #if not os.path.exists(location):
    #    messageBox("Gimp 2.8 not found")

    if os.path.exists(toDir):
        shutil.rmtree(toDir)
    shutil.copytree(fromDir, toDir)
    messageBox("Installed successfully")


def messageBox(message):
    import tkMessageBox
    import Tkinter
    window = Tkinter.Tk()
    window.wm_withdraw()
    tkMessageBox.showinfo(title="MESSAGE", message=message)



main()

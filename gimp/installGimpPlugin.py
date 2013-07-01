import shutil
import os
import json

def main():
    filename = 'GimpToSSP.py'
    home = os.path.expanduser("~")
    location = os.path.join(home,'.gimp-2.8','plug-ins')
    
    #WARNING Hard coded for gimp2.8
    if not os.path.exists(location):
        messageBox("Gimp 2.8 not found")
        
    shutil.copy2(filename, os.path.join(location, filename))

    make_config_file()

    messageBox("Installed successfully")


def messageBox(message):
    import tkMessageBox
    import Tkinter
    window = Tkinter.Tk()
    window.wm_withdraw()
    tkMessageBox.showinfo(title="MESSAGE", message=message)

def make_config_file():
    filename = "GimpToSSP.cfg"
    home = os.path.expanduser("~")
    folder = os.path.join(home, "flumpKit")
    configfile = os.path.join(folder, filename)
    if not os.path.exists(folder):
        os.mkdir(folder)

    #json
    installPath = os.path.dirname(os.path.realpath( __file__ ))
    spritePackerPath = os.path.join(installPath, "spriteSheetPacker")
    config = {"spritePackerPath": spritePackerPath, 'outputPath':installPath}
    print "SpritePackerPath: "+spritePackerPath
    f = open(configfile, 'w')
    f.write(json.dumps(config))
    f.close()

main()

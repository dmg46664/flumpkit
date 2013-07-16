#!/usr/bin/env python
# GIMP plugin to export layers as PNGs, then run Sprite Sheet Packer on the
# exported images to generate a texture atlas and map.

#Change: Doesn't save txt files in GIMP bin directory

#History

# Flump ammendments: Daniel Gerson
# Copyright 2012 Pravin Kumar
# License: GPL v3+
# Version 1.0
# Original Authors:
# Pravin Kumar (Aralox) <aralox@gmail.com>
# For the methods export_layers, get_layers_to_export and format_filename:
#   Original Author: Chris Mohler <cr33dog@gmail.com> (Copyright 2009)

import os;
import subprocess
import json
import re
from gimpfu import *

def export_to_ssp(img, path, only_visible, flatten, sspack_dir, texname, mapname):

    #create a folder to save exported layers in
    img_dir = os.path.join(path,"Exported Layers")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    #prepare flump data
    flump = {}
    flump['textureGroups'] = []
    flump_tg = {'scaleFactor':1}
    flump['textureGroups'].append(flump_tg)
    flump_tg['atlases'] = [{'file':'{0}.png'.format(texname), 'textures':[]}]
    flump['movies'] = [{"id": "default", "layers": []}]

    #export layers to files
    imglist_name = os.path.join(path , "ImageList.txt")
    imglist_file = open(imglist_name, 'w')
    export_layers(img, img_dir, only_visible, flatten, imglist_file, flump)
    imglist_file.close()

    json_file = os.path.join(path, "library.json")

    #call sprite sheet packer (command line)
    sspack = os.path.join(sspack_dir, 'sspack.exe')
    path_map = os.path.join(path, mapname) + '.txt'
    path_atlas = os.path.join(path, texname) + '.png'
    
    if os.path.exists(sspack):

        param_img = '/image:' + path_atlas   #eg. /image:C:\Users\Pravin\Desktop\test.png
        param_map = '/map:' + path_map    #eg. /map:C:\Users\Pravin\Desktop\test_map.skin
        param_maxw = '/mw:4096' #default
        param_maxh = '/mh:4096' #default
        param_pad = '/pad:1'    #default
        param_imglist = '/il:' + imglist_name   #eg /il:C:\Users\Pravin\AppData\Roaming\SpriteSheetPacker\FileList.txt
##        pdb.gimp_message([sspack, param_img, param_map, param_maxw, param_maxh, param_pad, param_imglist])
        subprocess.call([sspack, param_img, param_map, param_maxw, param_maxh, param_pad, param_imglist])

    else:
        pdb.gimp_message("sspack.exe was not found in that directory. Texture atlas and map were not created.")


    #add to flump
    add_map_to_flump(flump, path_map)
    with open(json_file, 'w') as outfile:
        json.dump(flump, outfile)
    
    configDic = load_config_file()
    configDic['spritePackerPath'] = sspack_dir
    configDic['outputPath'] = path
    #save configurations for convenience
    config = open(get_config_file(), 'w')
    config.write(json.dumps(configDic))
    config.close()

    return


def add_map_to_flump(flump, path_map):
    with open(path_map) as f:
        lines = f.readlines()
    coords = {}
    for li in lines:
        g = re.search('([\w ]+) = (\d+) (\d+) (\d+) (\d+)', li)
        coords[g.group(1)] = [int(g.group(2)), int(g.group(3)),
                              int(g.group(4)), int(g.group(5)), ]
    flump_textures = flump['textureGroups'][0]['atlases'][0]['textures']
    for texture in flump_textures:
        name = texture['symbol']
        texture['rect'] = coords[name]
    

def get_config_file():
    filename = "GimpToSSP.cfg"
    home = os.path.expanduser("~")
    folder = os.path.join(home, "flumpKit")
    return os.path.join(folder, filename)

def load_config_file():
    json_data=open(get_config_file())
    data = json.load(json_data)
    json_data.close()
    return data

def get_sspack_dir(config):
    if 'spritePackerPath' in config:
        return config['spritePackerPath']
    return os.getcwd()

def get_output_path(config):
    if 'outputPath' in config:
        return config['outputPath']
    return os.getcwd()


#original version also had regex commands in here to clean out whitespace
def format_filename(layer):
    layername = get_file_name(layer)
    filename = layername + '.png'
    return filename

def get_file_name(layer):
    return layer.name.decode('utf-8')

def get_layers_to_export(img, only_visible):
    layers = []

    #Add to list of layers to export depending on visibility
    for layer in img.layers:
        if only_visible and layer.visible:
            layers.append(layer)
        if not only_visible:
            layers.append(layer)

    return layers


#Hide all layers, then show each layer one at a time and save image
#Layer groups are treated as one layer. I cant find enough documentation on layer group functions to do anything else right now
def export_layers(img, path, only_visible, flatten, file, flump):

    #Use a duplicate image cos we dont want to mess up orig layers (visiblity/flattening)
    dupe = img.duplicate()
    savelayers = get_layers_to_export(dupe, only_visible)

    #Hide all layers first
    for layer in dupe.layers:
        layer.visible = 0

    #flump textures and init poses
    flump_textures = flump['textureGroups'][0]['atlases'][0]['textures']
    flump_layers = flump['movies'][0]['layers']
    

    #Show each layer at a time, and save
    for layer in dupe.layers:
        if layer in savelayers:
            layer.visible = 1

            #Generate filename, and write it to a log of exported files (for sspack later)
            filename = format_filename(layer)
            fullpath = os.path.join(path, filename);
            file.write(fullpath + '\n')

            #flump header
            name = get_file_name(layer)
            flump_textures.append({'rect':[layer.offsets[0],layer.offsets[1],layer.width,layer.height],
                                   'origin':[layer.width /2, layer.height/2],
                                   'symbol': name})
            #flump layer
            flump_layer = {'name':name, 'keyframes':[]}
            flump_layers.append(flump_layer)
            flump_layer['keyframes'].append({'ref':name, 'loc':[layer.offsets[0],layer.offsets[1]],
                                             'pivot':[layer.width /2,layer.height/2]})

            #use a a dupe again, so if we want to flatten (replace alpha with back color) we dont mess it up for the others
            tmp = dupe.duplicate()  
            if (flatten):
                tmp.flatten()

            #see the procedure browser under the help menu in gimp, for info on this function
            pdb.file_png_save(tmp, layer, fullpath, filename, 0, 9, 1, 1, 1, 1, 1)

#REGISTER
import sys
##sys.stderr = open( 'c:\\tmp\\gimpstderr.txt', 'w')
##sys.stdout = open( 'c:\\tmp\\gimpstdout.txt', 'w')

config = load_config_file()

#see gimpfu.py for info on register()
register(
    proc_name = "export-to-sprite-sheet-packer",
    blurb =     "Export layers and run Sprite Sheet Packer",
    help =      "Export layers to png files, and run Sprite Sheet Packer to generate a texture atlas image and map",
    author =    "Pravin Kumar aka. Aralox",
    copyright = "Pravin Kumar aka. Aralox",
    date =      "April 2012",
    imagetypes = "*",      # Alternatives: use RGB, RGB*, GRAY*, INDEXED etc.
    function =  export_to_ssp,
	menu =      "<Image>/File/E_xport Layers",
    label =     "E_xport and run Sprite Sheet Packer...",

    #params are tuples of the form (type, name, description, default [, extra])
    params = [
        #Image export parameters
        (PF_IMAGE, "img", "Image", None),
        (PF_DIRNAME, "path", "Save PNGs here", get_output_path(config)),
        (PF_BOOL, "only_visible", "Only Visible Layers?", True),
        (PF_BOOL, "flatten", "Flatten Images? (Replaces alpha channel with background color)", False),

        #Sprite sheet packer parameters
        (PF_DIRNAME, "sspack_dir", "Directory of Sprite Sheet Packer", get_sspack_dir(config)),
        (PF_STRING, "texname", "Texture Atlas Name (this png will be referenced inside map)", "atlas"),
        (PF_STRING, "mapname", "Map Name (skin)", "map")
    ],

    results =   []
	#other parameters of register(): domain, on_query, on_run
	)

main()



#Here for gimp module documentation: http://developer.gimp.org/api/2.0/index.html
#Go to help->procedure browser in Gimp for help on pdb functions
#Note about 'drawables' from http://www.gimp.org/docs/plug-in/sect-image.html:
# "We have all sorts of silly things like masks, channels, and layers,
# but they're all just a bunch of pixels that can be drawn on, so we treat them much the same
# and lump them all in to the category of "drawables". 
# And an image, then, is just what you get when you put some drawables together."

#After putting your values in the register method, save your script. Make sure that it is executable and is located in the .gimp2-6/plug-ins folder.

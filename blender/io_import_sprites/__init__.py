# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

## Interesting way to create the rig for Flump? http://www.cgmasters.net/free-tutorials/environment-animation-in-blender-2-5/

bl_info = {
    "name": "Import Sprites as Planes",
    "author": "Daniel Gerson. Old code from: Florian Meyer (tstscr), mont29, matali",
    "version": (1, 9),
    "blender": (2, 66, 4),
    "location": "File > Import > Images as Planes or Add > Mesh > Images as Planes",
    "description": "Imports images and creates planes with the appropriate aspect ratio. "
                   "The images are mapped to the planes.",
    "warning": "Based on Import Image Plane",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Add_Mesh/Planes_from_Images",
    "tracker_url": "https://projects.blender.org/tracker/index.php?func=detail&aid=21751",
    "category": "Import-Export"}

import bpy
from bpy.types import Operator
from bpy.types import Menu, Panel
import mathutils
import math
import os
import collections
import json

from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty,
                       IntProperty,
                       FloatProperty,
                       CollectionProperty,
                       )

from bpy_extras.object_utils import AddObjectHelper, object_data_add
from bpy_extras.image_utils import load_image
from mathutils import Vector
from mathutils import Quaternion

#the from part represents directory and filenames
#the import part represents a class or method name etc
from bl_ui.space_view3d_toolbar import View3DPanel


##print("LOADING FLUMPKIT!!!!")



# To support reload properly, try to access a package var,
# if it's there, reload everything
if 'bpy' in locals():
##    print("BPY in locals!!!")
    import imp
    if 'io_import_sprites.import_scripts' in locals():
##        imp.reload(io_import_sprites.common)
        imp.reload(io_import_sprites.import_scripts)
        imp.reload(io_import_sprites.export_scripts)
##else: #TODO ---------------------------------------- <-- Something wrong! Shouldn't be commented out.
##    from io_import_sprites.common import (
##            Ms3dImportOperator,
##            Ms3dExportOperator,
##            )
##    print("SUCCESSFULLY INIT LOADED IMPORT_OT_planes_from_json in __init__!!!!")

if 'IMPORT_OT_planes_from_json' not in locals():
    from io_import_sprites.import_scripts import (
            IMPORT_OT_planes_from_json,
            )
    from io_import_sprites.export_scripts import (
            EXPORT_OT_flump_to_json,
            )
    

       
class IMPORT_OT_delete_scene(Operator):
        bl_idname = "import_sprites.delete_scene"
        bl_label = "Delete All Meshes"
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            bpy.ops.object.select_by_type(extend=False, type='MESH')
            bpy.ops.object.delete(use_global=False)
            self.report({'INFO'}, "Deleted {} scenes(s)")
            return {'FINISHED'}


class VIEW3D_PT_flump_kit(View3DPanel, Panel):
    bl_idname = "VIEW3D_PT_flump_kit"
    bl_label = "Flump Kit"
    #~ bl_space_type = 'PROPERTIES'
    #~ bl_region_type = 'WINDOW'
    bl_context = "objectmode"
    
##    filepath = bpy.props.StringProperty(subtype='FILE_PATH') 

    def draw(self, context):
        #~ self.layout.label(text="Hello World")
        layout = self.layout
        col = layout.column(align=True)
        col.operator(IMPORT_OT_planes_from_json.bl_idname)
        col.operator(IMPORT_OT_delete_scene.bl_idname)
        col.operator(EXPORT_OT_flump_to_json.bl_idname)
##        col.prop(self, 'filepath')
        

##class IMPORT_OT_sprites_to_plane:
##    """Create mesh plane(s) from image files with the appropiate aspect ratio"""
##    bl_idname = "import_sprites.to_plane"
##    bl_label = "Import Sprites as Planes"
##    bl_options = {'REGISTER', 'UNDO'}

# -----------------------------------------------------------------------------
# Register
def import_images_button(self, context):
    self.layout.operator(IMPORT_OT_sprites_to_plane.bl_idname, 
                         text="Images as Sprites", icon='TEXTURE') #specfics of the menu item


def register():
    #http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Cookbook/Code_snippets/Interface
    
    bpy.utils.register_module(__name__) #registers everything in this file
    #or do  for example
    #~ bpy.utils.register_class(HelloWorldPanel)
##    bpy.types.INFO_MT_file_import.append(import_images_button) #adds items to menu
##    bpy.types.INFO_MT_mesh_add.append(import_images_button)


def unregister():
    bpy.utils.unregister_module(__name__)
##    bpy.types.INFO_MT_file_import.remove(import_images_button)
##    bpy.types.INFO_MT_mesh_add.remove(import_images_button)


if __name__ == "__main__":
    register()

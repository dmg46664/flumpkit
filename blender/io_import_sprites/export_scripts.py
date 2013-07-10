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

print("LOADING: import_scripts.py!!!!")

from io_import_sprites.common import (
            SpritesFunctions,
            FlumpProps
            )


class EXPORT_OT_flump_to_json(Operator, SpritesFunctions):
        bl_idname = "export_sprites.flump_to_json"
        bl_label = "Export Json"
        bl_options = {'REGISTER', 'UNDO'}
        
        props = bpy.props.PointerProperty(type=FlumpProps)
        
        def execute(self, context):
                self.export_to_json(context)
                return {'FINISHED'}
                
                
        def export_to_json(self, context):
                #~ jsonFile = get_json_file();
                #~ print(jsonFile)
                jsonFile = "C:\\Libraries\\Maven\\tripleplay\\demo\\assets\\src\\main\\resources\\assets\\flump\\library.json"
                json_data=open(jsonFile)
                data = json.load(json_data)
                json_data.close()


                #we now have the file in data.
                #now create a new movies area

                movies = []
                data['movies'] = movies
                movie = {}
                movies.append(movie)
                movie['id'] = 'walk'

                #get movie layers
                #make armature active object (which hence changes the context)
                bpy.context.scene.objects.active = bpy.context.scene.objects['Armature']
                for bone_name in ('Body', 'Gut'):
                        pose_bone = bpy.context.object.pose.bones[bone_name]
                        obj = pose_bone.id_data
                        matrix = obj.matrix_world * pose_bone.matrix
                        loc, rotQ, scale = matrix.decompose()

                        self.report({'INFO'}, 'EXTRACT {0},{1},{2}'.format(loc,rotQ.to_euler(),scale))

                return
                
                
                

               
                armature = self.create_armature()

                #setup screen
                #bpy.data.screens["Default"].(null) = 'TEXTURED'
##               bpy.data.screens["Default"].(null) = 10000

                #create bones and parent them
                depth = 0
                for movie in data['movies']:
                    movie_id = movie['id']
                    self.report({'INFO'}, "movie: "+movie['id'])
                    for layer in movie['layers']:
                        keyframes = layer['keyframes']
                        ref = keyframes[0]['ref']
##                        self.report({'INFO'}, "  layer: "+layer['name']+" "+ref)
                        plane, tex = tex_map[ref]
                        bone_name = layer['name']
                        self.create_bone(armature, bone_name, tex['rect'][2], tex['rect'][3], depth)
                        depth += 0.1
                        self.set_parent_bone(plane, armature, layer['name']) #only single symbol support
                        
                    break #break on first  animation

                for movie in data['movies']:
                    movie_id = movie['id']
##                    self.report({'INFO'}, "movie: "+movie['id'])
                    if not (movie_id =='walk'):
                            continue
##                        else:
##                                self.report({'INFO'}, "WALK")
                    for layer in movie['layers']:
                        keyframes = layer['keyframes']
                        ref = keyframes[0]['ref']
                        plane, tex = tex_map[ref]
                        bone_name = layer['name']
                        for key in keyframes:
                            self.pose_layer(armature, bone_name, plane, tex, key)
                    
                return

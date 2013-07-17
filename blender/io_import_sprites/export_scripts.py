## Author: Daniel Gerson
##GPL 3.0 unless otherwise specified.

import bpy
from bpy.types import Operator
from bpy.types import Menu, Panel
import mathutils
import math
import os
import collections
import json
import re

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
##                self.props = bpy.context.scene.FlumpProps
                self.export_to_json(context)
                return {'FINISHED'}

        #inverts y axis
        def transform_point(self, x, y, width, height):
            return (x, height - y)

        def transform_location(self, x, y):
                return (x, -y)

        #take transform of plane and convert into pivot
        def get_pivot(self, arm_name, obj, width, height):

                #use relative
                #TODO, find by armature name
                if not bpy.data.armatures[0].bones[obj.name].use_relative_parent:
                        tx = width /2.0

                        ox = -obj.location.x +tx
                        oy = -obj.location.y
                        return self.transform_point(ox, oy, width, height)

                tx = width /2.0
                ox = -obj.location.x +tx
                oy = -obj.location.y + (height /2.0)
                return self.transform_point(ox, oy, width, height)
                        
                
        def export_to_json(self, context):
                #~ jsonFile = get_json_file();
                #~ print(jsonFile)
                props = bpy.context.scene.FlumpProps
                jsonFile = props.flump_library
                json_data=open(jsonFile)
                data = json.load(json_data)
                json_data.close()


                #we now have the file in data.
                #now create a new movies area

                movies = []
                data['movies'] = movies
                data['frameRate'] = bpy.context.scene.render.fps
                movie = {}
                movies.append(movie)
                movie['id'] = 'walk'
                movie['layers'] = []
                

                #get layers
                armature_name = 'Armature'
                bpy.context.scene.objects.active = bpy.context.scene.objects[armature_name] #context now armature
                arm = bpy.context.scene.objects.active 
                ob_act = bpy.context.scene.objects.active.animation_data.action
                curves = ob_act.fcurves        
                bone_keys = bpy.context.object.pose.bones.keys() #some of these bones are layers
                layers = (b for b in bone_keys if 'flump_layer' in bpy.context.object.pose.bones[b])

                #Assumes one symbol per layer
                symbols = {}
                for child in arm.children:
                        symbols[child.parent_bone] = child #object, not name
                
                

                layer_frames ={}

                #loop through curves, add keyframes to ALL bones that are influenced by this bone
                for curve_id, curve in enumerate(curves) :
                        obj_name =re.search(r'"(\w+)"', curve.data_path).group(1)
                        if obj_name not in layer_frames:
                                layer_frames[obj_name] = []
                        
                        for key in curve.keyframe_points :                           
                                frame, value = key.co
                                #add frame to ALL objects that share obj_name TODO (parents)
                                layer_frames[obj_name].append(frame)
                                
                                # do something with curve_id, frame and value
##                                self.report({'INFO'}, 'EXTRACT {0},{1},{2}'.format(curve_id, frame, value))

                        layer_frames[obj_name] = sorted(list(set(layer_frames[obj_name])))

                sequence_length = bpy.context.scene.frame_end

                #loop through layer_frames
                for bone_name in layers:

                        frames = layer_frames[bone_name]
                        
                        #add json layer
                        json_layer = {}
                        movie['layers'].append(json_layer)
                        json_layer['name'] = bone_name
                        json_keyframes = []
                        json_layer['keyframes'] = json_keyframes
                        
                        

                        len_frames = len(frames)
                        for i in range(len(frames)):
                                json_frame = {}
                                json_keyframes.append(json_frame)
                                json_frame['index'] = frames[i]
                                nextframe = sequence_length
                                if (i+1 < len_frames):
                                        nextframe = frames[i+1]
                                json_frame['duration'] = nextframe - frames[i]

                                #store frame values
                                bpy.context.scene.frame_set(frames[i])
                                pose_bone = bpy.context.object.pose.bones[bone_name]
                                obj = pose_bone.id_data
                                matrix = obj.matrix_world * pose_bone.matrix
                                loc, rotQ, scale = matrix.decompose()
                                #bounding box
                                local_coords = symbols[bone_name].bound_box[:]
                                coords = [p[:] for p in local_coords]
                                width = coords[0][0] * -2
                                height = coords[0][1] * -2
                                x, y = self.transform_location(loc[0], loc[1])
                                json_frame['loc'] =[x, y]
                                angle = -rotQ.to_euler().z #* math.pi / 180
                                json_frame['skew'] = [angle, angle]
                                json_frame['scale'] = [scale[0], scale[1]]
                                json_frame['pivot'] = self.get_pivot(armature_name, symbols[bone_name],
                                                                     width, height)
                                json_frame['ref'] = symbols[bone_name].name
                                
                                

##                        self.report({'INFO'}, 'EXTRACT {0},{1},{2}'.format(loc,rotQ.to_euler(),scale))

                with open(jsonFile, 'w') as outfile:
                        json.dump(data, outfile)
                
                
                return

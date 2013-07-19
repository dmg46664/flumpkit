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
                                layer_frames[obj_name].append(int(frame))
                                
                                # do something with curve_id, frame and value
##                                self.report({'INFO'}, 'EXTRACT {0},{1},{2}'.format(curve_id, frame, value))

                        layer_frames[obj_name] = sorted(list(set(layer_frames[obj_name])))

                #add parents keyframes to child
                for bone in bpy.data.armatures[0].bones[:]:
                        parents = [p.name for p in bone.parent_recursive]
                        for parent in parents:
                                layer_frames[bone.name].extend(layer_frames[parent])
                        layer_frames[bone.name] = sorted(list(set(layer_frames[bone.name])))

                sequence_length = int(bpy.context.scene.frame_end)

                layer_zdict = {}
                #loop through layer_frames
                for bone_name in layers:

                        frames = layer_frames[bone_name]
                        
                        #add json layer
                        json_layer = {}
                        
                        json_layer['name'] = bone_name
                        json_keyframes = []
                        json_layer['keyframes'] = json_keyframes

                        zdepth = None

                        keyframe_container = {}
                        #old way, straight
                        for i in range(len(frames)):                                
                                nextframe = sequence_length
                                if (i+1 < len(frames)):
                                        nextframe = frames[i+1]

                                json_frame, loc_z = self.create_keyframe(frames[i], bone_name,
                                                                         armature_name, symbols)
                                keyframe_container[frames[i]] = json_frame

                        #fit to curve
                        constants = (sequence_length, armature_name, bone_name, symbols)
                        for i in range(len(frames)):                                
                            nextframe = sequence_length
                            if (i+1 < len(frames)):
                                nextframe = frames[i+1]
                        
                            self.fit_to_curve(frames[i], nextframe,
                                keyframe_container, constants)

                        frames = sorted(list(set(keyframe_container.keys())))
                        for i in range(len(frames)):
                            nextframe = sequence_length
                            if (i+1 < len(frames)):
                                nextframe = frames[i+1]
                            json_frame = keyframe_container[frames[i]]
                            json_keyframes.append(json_frame)  
                            json_frame['duration'] = nextframe - frames[i]


                        #find z depth order (useful to do this at the same time
                        loc, rotQ, scale = self.get_bone_transform(0, bone_name)
                        if zdepth is None: #only run on first keyframe
                                zdepth = loc[2]
                                if zdepth not in layer_zdict:
                                        layer_zdict[zdepth] = []
                                layer_zdict[zdepth].append(json_layer)


                        
                                
        

                #add json layers in correct zdepth order, as determined by first keyframe.
                for z in sorted(list(layer_zdict.keys())): #not thread safe ;-)
                        for item in layer_zdict[z]:
                                movie['layers'].append(item) #json_layer
                                
                                

##                        self.report({'INFO'}, 'EXTRACT {0},{1},{2}'.format(loc,rotQ.to_euler(),scale))

                with open(jsonFile, 'w') as outfile:
                        json.dump(data, outfile)
                
                
                return

        #adds keyframes to match linear to curve.
        def fit_to_curve(self, start_frame, end_frame,
                         keyframe_container, constants):
            #extract constants
            sequence_length, armature_name, bone_name, symbols = constants
            for i in range(start_frame, end_frame):
                transform_start = None
                transform_end = None
                #generate start keyframe
                if start_frame not in keyframe_container:
                    json_start, transform_start = self.create_keyframe(start_frame, bone_name,
                                                             armature_name, symbols)
                    keyframe_container[start_frame] = json_start
                else: #TODO redundant sometimes.
                    transform_start = self.get_bone_transform(start_frame, bone_name)
                #generate end keyframe
                if end_frame not in keyframe_container:
                    json_end, transform_end = self.create_keyframe(end_frame, bone_name,
                                                             armature_name, symbols)
                    keyframe_container[end_frame] = json_end
                else: #TODO redundant sometimes.
                    transform_end = self.get_bone_transform(end_frame, bone_name)
                
                #get transform of frame i
                transform_i = self.get_bone_transform(i, bone_name)

                #interpolate start and end transforms at i
                percent = (i - start_frame)/ (end_frame - start_frame)
                loc = transform_start[0] + (transform_end[0] - transform_start[0]) * percent
                rz_start = transform_start[1].to_euler().z 
                rz_end = transform_end[1].to_euler().z
                rz = rz_start + (rz_end - rz_start) * percent
                scale = transform_start[2] + (transform_end[2] - transform_start[2]) * percent

                #test
                match = True
                if (abs(loc[0] - transform_i[0][0]) > 1): match = False
                if (abs(loc[1] - transform_i[0][1]) > 1): match = False
                ri = transform_i[1].to_euler().z
                if ((ri - rz) % 360 > 1): match = False
                #TODO scale

                if match is True: #matches where it is supposed to be
                    continue

                mid_frame = int((start_frame + end_frame)/2)
                if mid_frame in [start_frame, end_frame]: return

                #recursion
                self.fit_to_curve(start_frame, mid_frame,
                         keyframe_container, constants)

                self.fit_to_curve(mid_frame, end_frame,
                         keyframe_container, constants)

                return
                

                

        def get_bone_transform(self, frame, bone_name):
            bpy.context.scene.frame_set(frame)
            pose_bone = bpy.context.object.pose.bones[bone_name]
            obj = pose_bone.id_data
            matrix = obj.matrix_world * pose_bone.matrix
##            loc, rotQ, scale = matrix.decompose()
            return matrix.decompose()

        def create_keyframe(self, frame, bone_name, armature_name, symbols):
                json_frame = {}                
                json_frame['index'] = frame
                
                #store frame values
                loc, rotQ, scale = self.get_bone_transform(frame, bone_name)
                
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

                return json_frame, (loc, rotQ, scale)

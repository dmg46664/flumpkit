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


class IMPORT_OT_planes_from_json(Operator, SpritesFunctions):
    bl_idname = "import_sprites.to_plane_from_json"
    bl_label = "Import Json"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=FlumpProps)

    def execute(self, context):                
        self.import_from_json(context)
        return {'FINISHED'}
            
    def parent_to_new_group(self, child, parent):
        for line in created_meshes:
            bpy.ops.object.select_pattern(pattern=str(line), case_sensitive=False, extend=True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.select_name(name=str(parent.name))
        bpy.ops.object.parent_set(type='OBJECT')

    #inverts y axis
    def transformPoint(self, x, y, width, height):
        return (x, height - y)

    def set_uv_map(self, context, sx, sy, ex, ey, width, height):
        #target must be active selected object
        obj = bpy.context.object.data
        #sx, sy represents top left co-ordinates in Flump-PlayN
        #ex, ey represent bottom right in Flump-PlayN

        #Remember! Y-axis reversed (coords range from 0 to 1.0)

        _ , ey = self.transformPoint(ex, ey, width, height)
        _ , sy = self.transformPoint(sx, sy, width, height)
        
        #bottom left
        obj.uv_layers["UVMap"].data[0].uv = Vector((sx /width , ey / height))
        #bottom right
        obj.uv_layers["UVMap"].data[1].uv = Vector((ex /width , ey / height))
        #top right
        obj.uv_layers["UVMap"].data[2].uv = Vector((ex /width , sy / height))
        #top left
        obj.uv_layers["UVMap"].data[3].uv = Vector((sx /width , sy / height))



    #target must be active selected object
    def set_origin(self, context, ox, oy, width, height):
        
        #invert Y
        ox,oy = self.transformPoint(ox, oy, width, height)
        
        #object is currently spans from -width/2 to +width/2
        cx = (-width/2) + ox ;
        cy = -(height/2) + oy ;
        
        bpy.context.scene.cursor_location = Vector((cx,cy,0.0))
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    def transform_to_fit_parent_origin(self, context, ox, oy, width, height):
        i = 5
        
    #returns an armature object
    def create_armature(self):
        layersList=(True, False, False, False,
             False, False, False, False, False, False, False,
             False, False, False, False, False, False, False, False, False)
        bpy.ops.object.armature_add(view_align=False, enter_editmode=False,
                                    location=(0, 0, 0), rotation=(0, 0, 0), layers=layersList )
        
        bpy.context.object.data.draw_type = 'ENVELOPE'
        bpy.context.object.draw_type = 'WIRE'
        bpy.ops.object.editmode_toggle()
        bpy.context.object.data.bones["Bone"].name = 'Default'
        return bpy.context.scene.objects.active

    #There will be a bone for each layer in the animation
    def create_bone(self, armature, name, tex_width, tex_height, depth):

        bpy.ops.object.select_pattern(pattern=str(armature.name), case_sensitive=False, extend=True)
        bpy.ops.object.mode_set(mode='EDIT')

        #add bone to armature
        bpy.ops.armature.bone_primitive_add(name="Bone")
        bpy.ops.object.mode_set(mode='EDIT')
        
        armature.data.edit_bones['Bone'].tail.z = 0
        armature.data.edit_bones['Bone'].tail.y = tex_height /2

        bpy.ops.object.mode_set(mode='POSE')
        bpy.context.object.pose.bones["Bone"].location[2] = depth
        bpy.context.object.pose.bones["Bone"].rotation_quaternion[0] = 0
        bpy.context.object.pose.bones["Bone"].rotation_mode = 'AXIS_ANGLE'
        bpy.context.object.pose.bones["Bone"].rotation_mode = 'XYZ'
        bpy.context.object.pose.bones["Bone"].rotation_euler[0] = 0

        #bpy.context.object.rotation_euler[2] = 5.75977
        bpy.context.object.lock_location[0] = True
        bpy.context.object.lock_location[1] = True
        bpy.context.object.lock_location[2] = True
        bpy.context.object.lock_rotation[0] = True
        bpy.context.object.lock_rotation[1] = True
        bpy.context.object.lock_rotation[2] = True

        bpy.ops.object.mode_set(mode='POSE')
        bone = bpy.context.object.pose.bones["Bone"]
        bone.lock_location[2] = True
        bone.lock_rotation[0] = True
        bone.lock_rotation[1] = True

        bone_obj = bpy.context.object.data.bones["Bone"]
        bone_obj.name = name
        

        #set flump_layer property
        bone['flump_layer'] = name ;

        bone_obj.tail_radius = tex_width / 20.0
        bone_obj.head_radius = tex_width /10.0

        
        #bpy.ops.object.parent_set(type='BONE', xmirror=False, keep_transform=False)


            
    def pose_layer(self, armature, bone_name, plane, tex, key):
        
        ox,oy,width,height = tex['rect']
    ##            bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.objects.active = bpy.data.objects[armature.name]
        #bpy.ops.object.select_pattern(pattern=str(armature.name), case_sensitive=False, extend=True)
        bpy.ops.object.mode_set(mode='POSE')

        #set index
        bone = bpy.context.object.pose.bones[bone_name]
        index = key['index']

        
        if 'loc' in key:
            loc = key['loc']
    ##                loc = self.transformPoint(loc[0], loc[1], width, height)
            bone.location.x = loc[0]
            bone.location.y = -loc[1]
            bone.keyframe_insert(data_path="location", frame=index)
            self.report({'INFO'}, "  bone loc: {0} index: {1}".format(bone_name, index))

        scale = None
        
    ##            http://www.senocular.com/flash/tutorials/transformmatrix/
        if 'skew' in key :
            skew = key['skew']
            scale = (1,1)
            if 'scale' in key:
                scale = key['scale']

            #origin
            #ox, oy = self.transformPoint(ox, oy, width , height)

            #work out longest vector
            v = Vector((ox - width, 0.0,0.0))
            if height > width:
                v = Vector((0.0, oy - height, 0.0))
            
            m = mathutils.Matrix.Identity(3)
            m[0][0] = scale[0]
            m[1][1] = scale[1]
            m[0][1] = skew[0]
            m[1][0] = skew[1]

            r = m * v
            avg = v.angle(r)
            c = v.cross(r)

##            #y transform
##            y = Vector((1.0, 0.0, 0.0))
##            v = m * y
##            angle = v.angle(y)
##            c = v.cross(y)
##
##            #x transform
##            x = Vector((0.0, 1.0, 0.0))
##            v = m * x
##            angle2 = v.angle(x)

##            self.report({'INFO'}, "  angle: {0} angle2: {1}".format(angle, angle2))

##            avg = (angle + angle2)/2.0
            if c[2] < 0:
                avg *= -1

            bone.rotation_euler.z = avg
            bone.keyframe_insert(data_path="rotation_euler", frame=index)

        if 'scale' in key:
            if scale is None:
                scale = key['scale']
            bone.scale.x = scale[0]
            bone.scale.y = scale[1]
            bone.keyframe_insert(data_path="scale", frame=index)

        relative_parent = True

        if 'pivot' in key:
            pivot = key['pivot']
            #pivot is actually the same as origin (just updated in case of switching symbols per layer)
            
            #invertY 
            ox, oy = self.transformPoint(pivot[0], pivot[1], width , height)

            #tail position in image coordinates
            tx = width / 2.0
            ty = height / 2.0

            if not relative_parent:
                #set origin
                plane.location.x =  - ox + tx
                plane.location.y =  - oy
            else:
                bpy.data.armatures[armature.name].bones[bone_name].use_relative_parent = True
                bpy.data.armatures[armature.name].bones[bone_name].use_local_location = False
                plane.location.x =  (-width /2 )+ox
                plane.location.y =  (+height/2) - oy
            plane.keyframe_insert(data_path="location", frame=index)

        

    def set_parent_bone(self, obj, armature, bone_name):
        obj.parent = armature
        obj.parent_bone = bone_name
        obj.parent_type = 'BONE'
            
    def import_from_json(self, context):
        #~ jsonFile = get_json_file();
        #~ print(jsonFile)
        props = bpy.context.scene.FlumpProps
        jsonFile = props.flump_library
##                jsonFile = "C:\\tmp\\flumpkit\\demos\\flump\\library.json"
        json_data=open(jsonFile)
        data = json.load(json_data)
        json_data.close()

##                image_path = "C:\\tmp\\flumpkit\\demos\\flump\\atlas0.png"
        atlas_file = data['textureGroups'][0]['atlases'][0]['file']
        image_path = os.path.join(os.path.dirname(jsonFile),atlas_file)
        image = load_image(image_path, "")

        #planes and textures are the same thing at this stage
        textures = data['textureGroups'][0]['atlases'][0]['textures']
        parent = context.scene.objects.active

        tex_map = {}
        tex = self.create_image_texture(self.props, context, image)
        #material
        material = self.create_material_for_texture(self.props, tex)
        for t in textures:
            sx,sy,tex_w,tex_h= t['rect'] #start and end
            ox,oy = t['origin'] #offset

            #create plane
            bpy.context.scene.cursor_location = Vector((0.0,0.0,0.0))
            plane = self.create_image_plane(context, tex_w , tex_h)
            bpy.ops.object.select_pattern(pattern=str(plane.name), case_sensitive=False, extend=True)
            self.set_uv_map(context, sx, sy, sx + tex_w, sy+tex_h, image.size[0], image.size[1])
            bpy.ops.transform.translate(value=(0, 0, 0),
                                        constraint_orientation='GLOBAL')


            self.set_image_options(self.props, image)                        
            
            plane.data.materials.append(material)
            plane.data.uv_textures[0].data[0].image = image
            material.game_settings.use_backface_culling = False
            material.game_settings.alpha_blend = 'ALPHA'
            plane.name = t['symbol']
            tex_map[plane.name] = (plane, t)


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

        last_frame = 0
        for movie in data['movies']:
            movie_id = movie['id']
            self.report({'INFO'}, "movie: "+movie['id'])
            if not (movie_id == props.movie_id):
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
                    if key['index'] + key['duration']> last_frame:
                            last_frame = key['index'] + key['duration']
        bpy.context.scene.frame_end = last_frame
        return

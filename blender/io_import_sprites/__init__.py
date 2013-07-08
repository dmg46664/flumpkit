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

# -----------------------------------------------------------------------------
# Global Vars

DEFAULT_EXT = "*"

EXT_FILTER = getattr(collections, "OrderedDict", dict)((
    (DEFAULT_EXT, ((), "All image formats", "Import all know image (or movie) formats.")),
    ("jpeg", (("jpeg", "jpg", "jpe"), "JPEG ({})", "Joint Photographic Experts Group")),
    ("png", (("png", ), "PNG ({})", "Portable Network Graphics")),
    ("tga", (("tga", "tpic"), "Truevision TGA ({})", "")),
    ("tiff", (("tiff", "tif"), "TIFF ({})", "Tagged Image File Format")),
    ("bmp", (("bmp", "dib"), "BMP ({})", "Windows Bitmap")),
    ("cin", (("cin", ), "CIN ({})", "")),
    ("dpx", (("dpx", ), "DPX ({})", "DPX (Digital Picture Exchange)")),
    ("psd", (("psd", ), "PSD ({})", "Photoshop Document")),
    ("exr", (("exr", ), "OpenEXR ({})", "OpenEXR HDR imaging image file format")),
    ("hdr", (("hdr", "pic"), "Radiance HDR ({})", "")),
    ("avi", (("avi", ), "AVI ({})", "Audio Video Interleave")),
    ("mov", (("mov", "qt"), "QuickTime ({})", "")),
    ("mp4", (("mp4", ), "MPEG-4 ({})", "MPEG-4 Part 14")),
    ("ogg", (("ogg", "ogv"), "OGG Theora ({})", "")),
    ("json", (("json", ), "JSON ({})","Flump Json")),
))

# XXX Hack to avoid allowing videos with Cycles, crashes currently!
VID_EXT_FILTER = {e for ext_k, ext_v in EXT_FILTER.items() if ext_k in {"avi", "mov", "mp4", "ogg"} for e in ext_v[0]}

CYCLES_SHADERS = (
    ('BSDF_DIFFUSE', "Diffuse", "Diffuse Shader"),
    ('EMISSION', "Emission", "Emission Shader"),
    ('BSDF_DIFFUSE_BSDF_TRANSPARENT', "Diffuse & Transparent", "Diffuse and Transparent Mix"),
    ('EMISSION_BSDF_TRANSPARENT', "Emission & Transparent", "Emission and Transparent Mix")
)

# -----------------------------------------------------------------------------
# Misc utils.
def gen_ext_filter_ui_items():
    return tuple((k, name.format(", ".join("." + e for e in exts)) if "{}" in name else name, desc)
                 for k, (exts, name, desc) in EXT_FILTER.items())


def is_image_fn(fn, ext_key, filter_list ):
    if filter_list is None:
        filter_list = EXT_FILTER[ext_key][0]
    if ext_key == DEFAULT_EXT:
        return True  # Using Blender's image/movie filter.
    ext = os.path.splitext(fn)[1].lstrip(".").lower()
    return ext in filter_list


# -----------------------------------------------------------------------------
# Cycles utils.
def get_input_nodes(node, nodes, links):
    # Get all links going to node.
    input_links = {lnk for lnk in links if lnk.to_node == node}
    # Sort those links, get their input nodes (and avoid doubles!).
    sorted_nodes = []
    done_nodes = set()
    for socket in node.inputs:
        done_links = set()
        for link in input_links:
            nd = link.from_node
            if nd in done_nodes:
                # Node already treated!
                done_links.add(link)
            elif link.to_socket == socket:
                sorted_nodes.append(nd)
                done_links.add(link)
                done_nodes.add(nd)
        input_links -= done_links
    return sorted_nodes


def auto_align_nodes(node_tree):
    print('\nAligning Nodes')
    x_gap = 200
    y_gap = 100
    nodes = node_tree.nodes
    links = node_tree.links
    to_node = None
    for node in nodes:
        if node.type == 'OUTPUT_MATERIAL':
            to_node = node
            break
    if not to_node:
        return  # Unlikely, but bette check anyway...

    def align(to_node, nodes, links):
        from_nodes = get_input_nodes(to_node, nodes, links)
        for i, node in enumerate(from_nodes):
            node.location.x = to_node.location.x - x_gap
            node.location.y = to_node.location.y
            node.location.y -= i * y_gap
            node.location.y += (len(from_nodes)-1) * y_gap / (len(from_nodes))
            align(node, nodes, links)

    align(to_node, nodes, links)


def clean_node_tree(node_tree):
    nodes = node_tree.nodes
    for node in nodes:
        if not node.type == 'OUTPUT_MATERIAL':
            nodes.remove(node)
    return node_tree.nodes[0]




# -----------------------------------------------------------------------------
# Operator (This is the class which represents an operator. The menu'ing system knows how to handle stuff inside it.

class SpritesFunctions():
    
    # Callback which will update File window's filter options accordingly to extension setting.
    def update_extensions2(self, context):
        is_cycles = context.scene.render.engine == 'CYCLES'
        if self.extension == DEFAULT_EXT:
            self.filter_image = True
            # XXX Hack to avoid allowing videos with Cycles, crashes currently!
            self.filter_movie = True and not is_cycles
            self.filter_glob = ""
        else:
            self.filter_image = False
            self.filter_movie = False
            if is_cycles:
                # XXX Hack to avoid allowing videos with Cycles!
                flt = ";".join(("*." + e for e in EXT_FILTER[self.extension][0] if e not in VID_EXT_FILTER))
            else:
                flt = ";".join(("*." + e for e in EXT_FILTER[self.extension][0]))
            self.filter_glob = flt
        # And now update space (file select window), if possible.
        space = bpy.context.space_data
        # XXX Can't use direct op comparison, these are not the same objects!
        if (space.type != 'FILE_BROWSER' or space.operator.bl_rna.identifier != self.bl_rna.identifier):
            return
        space.params.use_filter_image = self.filter_image
        space.params.use_filter_movie = self.filter_movie
        space.params.filter_glob = self.filter_glob
        # XXX Seems to be necessary, else not all changes above take effect...
        bpy.ops.file.refresh()
    

    def draw2(self, context):
        engine = context.scene.render.engine
        layout = self.layout

        box = layout.box()
        box.label("Import Options:", icon='FILTER')
        box.prop(self, "extension", icon='FILE_IMAGE')
        box.prop(self, "align")
        box.prop(self, "align_offset")

        row = box.row()
        row.active = bpy.data.is_saved
        row.prop(self, "relative")
        # XXX Hack to avoid allowing videos with Cycles, crashes currently!
        if engine == 'BLENDER_RENDER':
            box.prop(self, "match_len")
            box.prop(self, "use_fields")
            box.prop(self, "use_auto_refresh")

        box = layout.box()
        if engine == 'BLENDER_RENDER':
            box.label("Material Settings: (Blender)", icon='MATERIAL')
            box.prop(self, "use_shadeless")
            box.prop(self, "use_transparency")
            box.prop(self, "alpha_mode")
            row = box.row()
            row.prop(self, "transparency_method", expand=True)
            box.prop(self, "use_transparent_shadows")
        elif engine == 'CYCLES':
            box = layout.box()
            box.label("Material Settings: (Cycles)", icon='MATERIAL')
            box.prop(self, 'shader', expand = True)
            box.prop(self, 'overwrite_node_tree')

        box = layout.box()
        box.label("Plane dimensions:", icon='ARROW_LEFTRIGHT')
        row = box.row()
        row.prop(self, "size_mode", expand=True)
        if self.size_mode == 'ABSOLUTE':
            box.prop(self, "height")
        else:
            box.prop(self, "factor")

    def invoke2(self, context, event):
        self.update_extensions(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

################################################################### When you hit import this gets called
    def execute2(self, context):
        if not bpy.data.is_saved:
            self.relative = False

        # the add utils don't work in this case because many objects are added disable relevant things beforehand
        editmode = context.user_preferences.edit.use_enter_edit_mode
        context.user_preferences.edit.use_enter_edit_mode = False
        if (context.active_object and
            context.active_object.mode == 'EDIT'):
            bpy.ops.object.mode_set(mode='OBJECT')

        self.import_images(context)

        context.user_preferences.edit.use_enter_edit_mode = editmode
        return {'FINISHED'}

    # Main...
    ################################################################### Which calls this in turn
    def import_images(self, context):
        engine = context.scene.render.engine
        import_list, directory = self.generate_paths(self.extension)

        #get blender image objects based on the import_list
        images = (load_image(path, directory) for path in import_list)

        if engine == 'BLENDER_RENDER':
            textures = []
            for img in images:
                self.set_image_options(img)
                textures.append(self.create_image_texture(context, img))

            materials = (self.create_material_for_texture(tex) for tex in textures)

        elif engine == 'CYCLES':
            materials = (self.create_cycles_material(img) for img in images)

        planes = tuple(self.create_image_plane_from_mat(context, mat) for mat in materials)

        context.scene.update()
        if self.align:
            self.align_planes(planes)

        for plane in planes:
            plane.select = True

        self.report({'INFO'}, "Added {} Image Plane(s)".format(len(planes)))

    def create_image_plane(self, context, x, y):
        bpy.ops.mesh.primitive_plane_add('INVOKE_REGION_WIN')
        plane = context.scene.objects.active
        # Why does mesh.primitive_plane_add leave the object in edit mode???
        if plane.mode is not 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        plane.dimensions = x, y, 0.0
        bpy.ops.object.transform_apply(scale=True)
        plane.data.uv_textures.new()
        return plane
        
    def create_image_plane_from_mat(self, context, material):
        engine = context.scene.render.engine
        if engine == 'BLENDER_RENDER':
            img = material.texture_slots[0].texture.image
        elif engine == 'CYCLES':
            nodes = material.node_tree.nodes
            img = next((node.image for node in nodes if node.type == 'TEX_IMAGE'))
        px, py = img.size

        # can't load data
        if px == 0 or py == 0:
            px = py = 1

        if self.size_mode == 'ABSOLUTE':
            y = self.height
            x = px / py * y
        elif self.size_mode == 'DPI':
            fact = 1 / self.factor / context.scene.unit_settings.scale_length * 0.0254
            x = px * fact
            y = py * fact
        else:  # elif self.size_mode == 'DPBU'
            fact = 1 / self.factor
            x = px * fact
            y = py * fact

        plane = create_image_plane(context, 0,0,x,y)
        plane.data.materials.append(material)
        plane.data.uv_textures[0].data[0].image = img

        material.game_settings.use_backface_culling = False
        material.game_settings.alpha_blend = 'ALPHA'
        return plane

    def align_planes(self, planes):
        gap = self.align_offset
        offset = 0
        for i, plane in enumerate(planes):
            offset += (plane.dimensions.x / 2.0) + gap
            if i == 0:
                continue
            move_local = mathutils.Vector((offset, 0.0, 0.0))
            move_world = plane.location + move_local * plane.matrix_world.inverted()
            plane.location += move_world
            offset += (plane.dimensions.x / 2.0)

    def generate_paths(self, extension):
        return (fn.name for fn in self.files if is_image_fn(fn.name, extension)), self.directory

    def get_json_file():
        return (fn.name for fn in self.files if is_image_fn(fn.name, extension, ("json")))[0]
    
    # Internal
    def create_image_texture(self, properties, context, image):
        fn_full = os.path.normpath(bpy.path.abspath(image.filepath))

        # look for texture with importsettings
        for texture in bpy.data.textures:
            if texture.type == 'IMAGE':
                tex_img = texture.image
                if (tex_img is not None) and (tex_img.library is None):
                    fn_tex_full = os.path.normpath(bpy.path.abspath(tex_img.filepath))
                    if fn_full == fn_tex_full:
                        self.set_texture_options(properties, context, texture)
                        return texture

        # if no texture is found: create one
        name_compat = bpy.path.display_name_from_filepath(image.filepath)
        texture = bpy.data.textures.new(name=name_compat, type='IMAGE')
        texture.image = image
        self.set_texture_options(properties, context, texture)
        return texture

    def create_material_for_texture(self, props, texture):
        # look for material with the needed texture
        for material in bpy.data.materials:
            slot = material.texture_slots[0]
            if slot and slot.texture == texture:
                self.set_material_options(props, material, slot)
                return material

        # if no material found: create one
        name_compat = bpy.path.display_name_from_filepath(texture.image.filepath)
        material = bpy.data.materials.new(name=name_compat)
        slot = material.texture_slots.add()
        slot.texture = texture
        slot.texture_coords = 'UV'
        self.set_material_options(props, material, slot)
        return material

    def set_image_options(self, props, image):
        image.alpha_mode = props.alpha_mode
        image.use_fields = props.use_fields

        if props.relative:
            image.filepath = bpy.path.relpath(image.filepath)

    def set_texture_options(self, props, context, texture):
        texture.image.use_alpha = props.use_transparency
        texture.image_user.use_auto_refresh = props.use_auto_refresh
        if props.match_len:
            ctx = context.copy()
            ctx["edit_image"] = texture.image
            ctx["edit_image_user"] = texture.image_user
            bpy.ops.image.match_movie_length(ctx)

    def set_material_options(self, props, material, slot):
        if props.use_transparency:
            material.alpha = 0.0
            material.specular_alpha = 0.0
            slot.use_map_alpha = True
        else:
            material.alpha = 1.0
            material.specular_alpha = 1.0
            slot.use_map_alpha = False
        material.use_transparency = props.use_transparency
        material.transparency_method = props.transparency_method
        material.use_shadeless = props.use_shadeless
        material.use_transparent_shadows = props.use_transparent_shadows

    #--------------------------------------------------------------------------
    # Cycles
    def create_cycles_material(self, image):
        name_compat = bpy.path.display_name_from_filepath(image.filepath)
        material = None
        for mat in bpy.data.materials:
            if mat.name == name_compat and self.overwrite_node_tree:
                material = mat
        if not material:
            material = bpy.data.materials.new(name=name_compat)

        material.use_nodes = True
        node_tree = material.node_tree
        out_node = clean_node_tree(node_tree)

        if self.shader == 'BSDF_DIFFUSE':
            bsdf_diffuse = node_tree.nodes.new('ShaderNodeBsdfDiffuse')
            tex_image = node_tree.nodes.new('ShaderNodeTexImage')
            tex_image.image = image
            tex_image.show_texture = True
            node_tree.links.new(out_node.inputs[0], bsdf_diffuse.outputs[0])
            node_tree.links.new(bsdf_diffuse.inputs[0], tex_image.outputs[0])

        elif self.shader == 'EMISSION':
            emission = node_tree.nodes.new('ShaderNodeEmission')
            lightpath = node_tree.nodes.new('ShaderNodeLightPath')
            tex_image = node_tree.nodes.new('ShaderNodeTexImage')
            tex_image.image = image
            tex_image.show_texture = True
            node_tree.links.new(out_node.inputs[0], emission.outputs[0])
            node_tree.links.new(emission.inputs[0], tex_image.outputs[0])
            node_tree.links.new(emission.inputs[1], lightpath.outputs[0])

        elif self.shader == 'BSDF_DIFFUSE_BSDF_TRANSPARENT':
            bsdf_diffuse = node_tree.nodes.new('ShaderNodeBsdfDiffuse')
            bsdf_transparent = node_tree.nodes.new('ShaderNodeBsdfTransparent')
            mix_shader = node_tree.nodes.new('ShaderNodeMixShader')
            tex_image = node_tree.nodes.new('ShaderNodeTexImage')
            tex_image.image = image
            tex_image.show_texture = True
            node_tree.links.new(out_node.inputs[0], mix_shader.outputs[0])
            node_tree.links.new(mix_shader.inputs[0], tex_image.outputs[1])
            node_tree.links.new(mix_shader.inputs[2], bsdf_diffuse.outputs[0])
            node_tree.links.new(mix_shader.inputs[1], bsdf_transparent.outputs[0])
            node_tree.links.new(bsdf_diffuse.inputs[0], tex_image.outputs[0])

        elif self.shader == 'EMISSION_BSDF_TRANSPARENT':
            emission = node_tree.nodes.new('ShaderNodeEmission')
            lightpath = node_tree.nodes.new('ShaderNodeLightPath')
            bsdf_transparent = node_tree.nodes.new('ShaderNodeBsdfTransparent')
            mix_shader = node_tree.nodes.new('ShaderNodeMixShader')
            tex_image = node_tree.nodes.new('ShaderNodeTexImage')
            tex_image.image = image
            tex_image.show_texture = True
            node_tree.links.new(out_node.inputs[0], mix_shader.outputs[0])
            node_tree.links.new(mix_shader.inputs[0], tex_image.outputs[1])
            node_tree.links.new(mix_shader.inputs[2], emission.outputs[0])
            node_tree.links.new(mix_shader.inputs[1], bsdf_transparent.outputs[0])
            node_tree.links.new(emission.inputs[0], tex_image.outputs[0])
            node_tree.links.new(emission.inputs[1], lightpath.outputs[0])

        auto_align_nodes(node_tree)
        return material


##In order to share properties between multiple panels each of which
## needs to be it's own class, the properties should not be defined
## in each class but rather a separate PropertyGroup
## this way you also have the option of sticking these properties globally
## (the scene) for further interaction between panels and operators
##    http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Cookbook/Code_snippets/Interface
##    http://www.blender.org/documentation/blender_python_api_2_57_release/bpy.types.PropertyGroup.html    
class FlumpProps(bpy.types.PropertyGroup):
##    # -----------
##    # File props.
##    files = CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
##
##    directory = StringProperty(maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
##
##    # Show only images/videos, and directories!
##    filter_image = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
##    filter_movie = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
##    filter_folder = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
##    filter_glob = StringProperty(default="", options={'HIDDEN', 'SKIP_SAVE'})
##
##    # --------
##    # Options.
##    align = BoolProperty(name="Align Planes", default=True, description="Create Planes in a row")
##
##    align_offset = FloatProperty(name="Offset", min=0, soft_min=0, default=0.1, description="Space between Planes")

    t = bpy.types.ImageUser.bl_rna.properties["use_auto_refresh"]
    use_auto_refresh = BoolProperty(name=t.name, default=True, description=t.description)

##    extension = EnumProperty(name="Extension", items=gen_ext_filter_ui_items(),
##                             description="Only import files of this type", update=update_extensions)
##
##    # -------------------
##    # Plane size options.
##    _size_modes = (
##        ('ABSOLUTE', "Absolute", "Use absolute size"),
##        ('DPI', "Dpi", "Use definition of the image as dots per inch"),
##        ('DPBU', "Dots/BU", "Use definition of the image as dots per Blender Unit"),
##    )
##    size_mode = EnumProperty(name="Size Mode", default='ABSOLUTE', items=_size_modes,
##                             description="How the size of the plane is computed")
##
##    height = FloatProperty(name="Height", description="Height of the created plane",
##                           default=1.0, min=0.001, soft_min=0.001, subtype='DISTANCE', unit='LENGTH')
##
##    factor = FloatProperty(name="Definition", min=1.0, default=600.0,
##                           description="Number of pixels per inch or Blender Unit")
##
    # -------------------------
    # Blender material options.
    t = bpy.types.Material.bl_rna.properties["use_shadeless"]
    use_shadeless = BoolProperty(name=t.name, default=True, description=t.description)

    use_transparency = BoolProperty(name="Use Alpha", default=True, description="Use alphachannel for transparency")

    t = bpy.types.Material.bl_rna.properties["transparency_method"]
    items = tuple((it.identifier, it.name, it.description) for it in t.enum_items)
    transparency_method = EnumProperty(name="Transp. Method", description=t.description, items=items)

    t = bpy.types.Material.bl_rna.properties["use_transparent_shadows"]
    use_transparent_shadows = BoolProperty(name=t.name, default=False, description=t.description)
##
##    #-------------------------
##    # Cycles material options.
##    shader = EnumProperty(name="Shader", items=CYCLES_SHADERS, description="Node shader to use")
##
##    overwrite_node_tree = BoolProperty(name="Overwrite Material", default=True,
##                                       description="Overwrite existing Material with new nodetree "
##                                                   "(based on material name)")
##
    # --------------
    # Image Options.
    t = bpy.types.Image.bl_rna.properties["alpha_mode"]
    alpha_mode_items = tuple((e.identifier, e.name, e.description) for e in t.enum_items)
    alpha_mode = EnumProperty(name=t.name, items=alpha_mode_items, default=t.default, description=t.description)

    t = bpy.types.IMAGE_OT_match_movie_length.bl_rna
    match_len = BoolProperty(name=t.name, default=True, description=t.description)

    t = bpy.types.Image.bl_rna.properties["use_fields"]
    use_fields = BoolProperty(name=t.name, default=False, description=t.description)

    relative = BoolProperty(name="Relative", default=True, description="Apply relative paths")







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
        def create_bone(self, armature, name, tex_width, tex_height):

            bpy.ops.object.select_pattern(pattern=str(armature.name), case_sensitive=False, extend=True)
            bpy.ops.object.mode_set(mode='EDIT')

            #add bone to armature
            bpy.ops.armature.bone_primitive_add(name="Bone")
            bpy.ops.object.mode_set(mode='EDIT')
            
            armature.data.edit_bones['Bone'].tail.z = 0
            armature.data.edit_bones['Bone'].tail.y = tex_height /2

            bpy.ops.object.mode_set(mode='POSE')
            bpy.context.object.pose.bones["Bone"].location[0] = 0
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
            bpy.context.object.pose.bones["Bone"].lock_location[2] = True
            bpy.context.object.pose.bones["Bone"].lock_rotation[0] = True
            bpy.context.object.pose.bones["Bone"].lock_rotation[1] = True

            
            bpy.context.object.data.bones["Bone"].name = name

            bpy.context.object.data.bones[name].tail_radius = tex_width / 20.0
            bpy.context.object.data.bones[name].head_radius = tex_width /10.0

            
            #bpy.ops.object.parent_set(type='BONE', xmirror=False, keep_transform=False)


        
        def pose_layer(self, armature, bone_name, plane, tex, key, frame):
            
            ox,oy,width,height = tex['rect']
##            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.objects.active = bpy.data.objects[armature.name]
            #bpy.ops.object.select_pattern(pattern=str(armature.name), case_sensitive=False, extend=True)
            bpy.ops.object.mode_set(mode='POSE')

            
            if 'loc' in key:
                loc = key['loc']
##                loc = self.transformPoint(loc[0], loc[1], width, height)
                bpy.context.object.pose.bones[bone_name].location.x = loc[0]
                bpy.context.object.pose.bones[bone_name].location.y = -loc[1]
                bpy.context.object.pose.bones[bone_name].location.z = 0

            scale = None
            
            if 'skew' in key :
                skew = key['skew']
                scale = (1,1)
                if 'scale' in key:
                    scale = key['scale']
        #http://research.cs.wisc.edu/graphics/Courses/838-s2002/Papers/polar-decomp.pdf
        #http://www.euclideanspace.com/maths/geometry/rotations/conversions/matrixToQuaternion/
        #http://www.flipcode.com/documents/matrfaq.html#Q55

                m = mathutils.Matrix.Identity(4)
                m[0][0] = scale[0]
                m[1][1] = scale[1]
                m[0][1] = skew[0]
                m[1][0] = skew[1]
                m[3][3] = 0
                loc, quat, scale = m.decompose()
                euler = quat.to_euler()
                
                self.report({'INFO'}, "skew! {0},{1},{2}".format(euler.x, euler.y, euler.z))
                bpy.context.object.pose.bones[bone_name].rotation_euler.z = - euler.z

            if 'scale' in key:
                if scale is None:
                    scale = key['scale']
                bpy.context.object.pose.bones[bone_name].scale.x = scale[0]
                bpy.context.object.pose.bones[bone_name].scale.y = scale[1]

            
                
                
            pivot = key['pivot']
            if pivot is not None:
                #invertY 
                ox, oy = self.transformPoint(pivot[0], pivot[1], width , height)

                #tail position in image coordinates
                tx = width / 2.0
                ty = height / 2.0
                #set origin
                plane.location.x =  - ox + tx
                plane.location.y =  - oy


        #row major order

            

        def set_parent_bone(self, obj, armature, bone_name):
            obj.parent = armature
            obj.parent_bone = bone_name
            obj.parent_type = 'BONE'
                
        def import_from_json(self, context):
                #~ jsonFile = get_json_file();
                #~ print(jsonFile)
                jsonFile = "C:\\tmp\\flumpkit\\demos\\flump\\library.json"
                json_data=open(jsonFile)
                data = json.load(json_data)
                json_data.close()

                image_path = "C:\\tmp\\flumpkit\\demos\\flump\\atlas0.png"
                image = load_image(image_path, "")

                #planes and textures are the same thing at this stage
                textures = data['textureGroups'][0]['atlases'][0]['textures']
                parent = context.scene.objects.active

                tex_map = {}
                tex = self.create_image_texture(self.props, context, image)
                #material
                material = self.create_material_for_texture(self.props, tex)
                depth = 0
                for t in textures:
                        sx,sy,tex_w,tex_h= t['rect'] #start and end
                        ox,oy = t['origin'] #offset

                        #create plane
                        bpy.context.scene.cursor_location = Vector((0.0,0.0,0.0))
                        plane = self.create_image_plane(context, tex_w , tex_h)
                        bpy.ops.object.select_pattern(pattern=str(plane.name), case_sensitive=False, extend=True)
                        self.set_uv_map(context, sx, sy, sx + tex_w, sy+tex_h, image.size[0], image.size[1])
                        bpy.ops.transform.translate(value=(0, 0, depth),
                                                    constraint_orientation='GLOBAL')

                        
                        #self.set_origin(context, ox, oy, tex_w, tex_h)
                        self.set_image_options(self.props, image)                        
                        
                        plane.data.materials.append(material)
                        plane.data.uv_textures[0].data[0].image = image
                        material.game_settings.use_backface_culling = False
                        material.game_settings.alpha_blend = 'ALPHA'
                        plane.name = t['symbol']
                        tex_map[plane.name] = (plane, t)                        
                        
                        depth += 0.1
##                        if depth == 0.2: break

                armature = self.create_armature()

                #setup screen
                #bpy.data.screens["Default"].(null) = 'TEXTURED'
##               bpy.data.screens["Default"].(null) = 10000
                
                for movie in data['movies']:
                    movie_id = movie['id']
                    self.report({'INFO'}, "movie: "+movie['id'])
                    for layer in movie['layers']:
                        keyframes = layer['keyframes']
                        ref = keyframes[0]['ref']
                        self.report({'INFO'}, "  layer: "+layer['name']+" "+ref)
                        plane, tex = tex_map[ref]
                        bone_name = layer['name']
                        self.create_bone(armature, bone_name, tex['rect'][2], tex['rect'][3])
                        self.set_parent_bone(plane, armature, layer['name']) #only single symbol support
                        for key in keyframes:
                            self.pose_layer(armature, bone_name, plane, tex, key, 0)
                            break 
                                
                            
                    break #break on first attack animation
                return

        
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

    filepath = bpy.props.StringProperty(subtype='FILE_PATH') 

    def draw(self, context):
        #~ self.layout.label(text="Hello World")
        layout = self.layout
        col = layout.column(align=True)
        col.operator(IMPORT_OT_planes_from_json.bl_idname)
        col.operator(IMPORT_OT_delete_scene.bl_idname)
        col.prop(self, 'filepath')
        

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

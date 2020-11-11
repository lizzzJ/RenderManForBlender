from . import string_utils
from . import filepath_utils
from . import scene_utils
from .prefs_utils import get_pref
from ..rfb_logger import rfb_log
from .. import txmanager3
from ..txmanager3 import core as txcore
from ..txmanager3 import txparams as txparams
from bpy.app.handlers import persistent

import os
import glob
import subprocess
import bpy
import uuid

__RFB_TXMANAGER__ = None

class RfBTxManager(object):

    def __init__(self):        
        fallback_path = string_utils.expand_string(get_pref('path_fallback_textures_path'), 
                                                  asFilePath=True)
        self.txmanager = txcore.TxManager(host_token_resolver_func=self.host_token_resolver_func, 
                                        fallback_path=fallback_path,
                                        host_tex_done_func=self.done_callback)
        self.rman_scene = None

    @property
    def rman_scene(self):
        return self.__rman_scene

    @rman_scene.setter
    def rman_scene(self, rman_scene):
        self.__rman_scene = rman_scene            

    def host_token_resolver_func(self, outpath):
        if self.rman_scene:
            outpath = string_utils.expand_string(outpath, frame=self.rman_scene.bl_frame_current, asFilePath=True)
        else:
            outpath = string_utils.expand_string(outpath, asFilePath=True)
        return outpath

    def done_callback(self, nodeID, txfile):
        bpy.ops.rman_txmgr_list.refresh('EXEC_DEFAULT')
        tokens = nodeID.split('|')
        if len(tokens) < 3:
            return
        node_name,param,param_val = tokens
        from .. import rman_render
        rr = rman_render.RmanRender.get_rman_render()
        if rr.rman_interactive_running:
            for mat in bpy.data.materials:
                if mat.grease_pencil:
                    rr.rman_scene_sync.update_material(mat)

                if not mat.node_tree:
                    continue
                if node_name in mat.node_tree.nodes:
                    rr.rman_scene_sync.update_material(mat)
                    return

            if node_name in bpy.data.objects:
                ob = bpy.data.objects[node_name]
                rr.rman_scene_sync.update_light(ob)

    def get_txfile_from_id(self, nodeID):
        txfile = self.txmanager.get_txfile_from_id(nodeID)
        if not txfile:
            return ''

        if txfile.state in (txmanager3.STATE_EXISTS, txmanager3.STATE_IS_TEX):
            output_tex = txfile.get_output_texture()
        else:
            output_tex = self.txmanager.get_placeholder_tex()
        if self.rman_scene:
            output_tex = string_utils.expand_string(output_tex, frame=self.rman_scene.bl_frame_current, asFilePath=True)
        else:
            output_tex = string_utils.expand_string(output_tex, asFilePath=True)            
        return output_tex
            
    def get_txfile_from_path(self, filepath):
        return self.txmanager.get_txfile_from_path(filepath)                

    def txmake_all(self, blocking=True):
        self.txmanager.txmake_all(start_queue=True, blocking=blocking)                     

def get_txmanager():
    global __RFB_TXMANAGER__
    if __RFB_TXMANAGER__ is None:
        __RFB_TXMANAGER__ = RfBTxManager()
    return __RFB_TXMANAGER__    

def update_texture(node, light=None):
    if hasattr(node, 'bl_idname'):
        if node.bl_idname == "PxrPtexturePatternNode":
            return
        elif node.bl_idname == "PxrOSLPatternNode":
            for input_name, input in node.inputs.items():
                if hasattr(input, 'is_texture') and input.is_texture:
                    prop = input.default_value
                    nodeID = generate_node_id(node, input_name)
                    real_file = filepath_utils.get_real_path(prop)
                    get_txmanager().txmanager.add_texture(nodeID, real_file)    
                    bpy.ops.rman_txmgr_list.add_texture('EXEC_DEFAULT', filepath=real_file)                                                      
            return
        elif node.bl_idname == 'ShaderNodeGroup':
            nt = node.node_tree
            for node in nt.nodes:
                update_texture(node, light=light)
            return

    if hasattr(node, 'prop_meta'):
        for prop_name, meta in node.prop_meta.items():
            if hasattr(node, prop_name):
                prop = getattr(node, prop_name)

                if meta['renderman_type'] == 'page':
                    continue
                else:
                    if 'widget' in meta and meta['widget'] in ['assetidinput', 'fileinput'] and prop_name != 'iesProfile':
                        if prop == '':
                            continue
                        node_name = ''
                        node_type = ''
                        if node.renderman_node_type == 'light':
                            node_name = light.name
                            node_type = light.renderman.get_light_node_name()
                            nodeID = generate_node_id(node, prop_name)
                        elif hasattr(node, 'name'):
                            node_name = node.name
                            node_type = node.bl_label
                            nodeID = generate_node_id(node, prop_name)

                        if node_name != '':       
                            real_file = filepath_utils.get_real_path(prop)
                            txfile = get_txmanager().txmanager.add_texture(nodeID, real_file, nodetype=node_type)    
                            bpy.ops.rman_txmgr_list.add_texture('EXEC_DEFAULT', filepath=real_file, nodeID=nodeID)
                            txmake_all(blocking=False)
                            if txfile:
                                get_txmanager().done_callback(nodeID, txfile)

def generate_node_id(node, prop_name):
    prop = ''
    real_file = ''
    if hasattr(node, prop_name):
        prop = getattr(node, prop_name)
        real_file = filepath_utils.get_real_path(prop)
    nodeID = '%s|%s|%s' % (node.name, prop_name, real_file)
    return nodeID

def get_txfile_from_id(nodeid):
    txfile = get_txmanager().get_txfile_from_id(nodeid)
    if txfile.state in (txmanager3.STATE_EXISTS, txmanager3.STATE_IS_TEX):
        output_tex = txfile.get_output_texture()
    else:
        output_tex = get_txmanager().get_placeholder_tex()
    return string_utils.replace_frame_num(output_tex)

def get_textures(id):
    if id is None or not id.node_tree:
        return

    nt = id.node_tree
    for node in nt.nodes:
        update_texture(node)

def recursive_texture_set(ob):
    mat_set = []
    SUPPORTED_MATERIAL_TYPES = ['MESH', 'CURVE', 'FONT', 'SURFACE']
    if ob.type in SUPPORTED_MATERIAL_TYPES:
        for mat in ob.data.materials:
            if mat:
                mat_set.append(mat)

    for child in ob.children:
        mat_set += recursive_texture_set(child)

    if ob.instance_collection:
        for child in ob.instance_collection.objects:
            mat_set += recursive_texture_set(child)

    return mat_set    

def get_blender_image_path(bl_image):
    if bl_image.packed_file:
        bl_image.unpack()
    real_file = bpy.path.abspath(bl_image.filepath, library=bl_image.library)          
    return real_file 

def add_images_from_image_editor():
    
    # convert images in the image editor
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
        img_path = get_blender_image_path(img)
        if img_path != '' and os.path.exists(img_path): 
            nodeID = str(uuid.uuid1())
            txfile = get_txmanager().txmanager.add_texture(nodeID, img_path)        
            bpy.ops.rman_txmgr_list.add_texture('EXEC_DEFAULT', filepath=img_path, nodeID=nodeID)       
            if txfile:
                get_txmanager().done_callback(nodeID, txfile)  

def parse_scene_for_textures(bl_scene):

    add_images_from_image_editor()

    mats_to_scan = []
    for o in scene_utils.renderable_objects(bl_scene):
        if o.type == 'CAMERA' or o.type == 'EMPTY':
            continue
        elif o.type == 'LIGHT':
            if o.data.renderman.get_light_node():
                update_texture(o.data.renderman.get_light_node(), light=o.data)
        else:
            mats_to_scan += recursive_texture_set(o)

    # cull duplicates by only doing mats once
    for mat in set(mats_to_scan):
        get_textures(mat)    
            
def parse_for_textures(bl_scene):    
    rfb_log().debug("Parsing scene for textures.")                                   
    parse_scene_for_textures(bl_scene)

@persistent
def parse_for_textures_load_cb(bl_scene):
    if bpy.context.engine != 'PRMAN_RENDER':
        return    
    bpy.ops.rman_txmgr_list.parse_scene('EXEC_DEFAULT')

def txmake_all(blocking=True):
    get_txmanager().txmake_all(blocking=blocking)        
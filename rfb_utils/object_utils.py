import bpy
import numpy as np
from .prefs_utils import get_pref
from . import string_utils

def get_db_name(ob, rman_type='', psys=None):
    db_name = ''    

    if psys:
        db_name = '%s|%s-%s' % (ob.name_full, psys.name, psys.settings.type)

    elif rman_type != '' and rman_type != 'NONE':
        if rman_type == 'META':
            db_name = '%s-META' % (ob.name.split('.')[0])
        elif rman_type == 'EMPTY':
            db_name = '%s' % ob.name_full 
        else:
            db_name = '%s-%s' % (ob.name_full, rman_type)
    elif isinstance(ob, bpy.types.Camera):
        db_name = ob.name_full
        return db_name
    elif isinstance(ob, bpy.types.Material):
        mat_name = ob.name_full.replace('.', '_')
        db_name = '%s' % mat_name
    elif isinstance(ob, bpy.types.Object):
        if ob.type == 'MESH':
            db_name = '%s-MESH' % ob.name_full
        elif ob.type == 'LIGHT':
            db_name = '%s-LIGHT' % ob.data.name_full
        elif ob.type == 'CAMERA':
            db_name = ob.name_full
            return db_name
        elif ob.type == 'EMPTY':
            db_name = '%s' % ob.name_full  


    return string_utils.sanitize_node_name(db_name)

def get_group_db_name(ob_inst):
    if isinstance(ob_inst, bpy.types.DepsgraphObjectInstance):
        if ob_inst.is_instance:
            ob = ob_inst.instance_object
            parent = ob_inst.parent
            psys = ob_inst.particle_system
            if psys:
                group_db_name = "%s|%s|%s|%d|%d" % (parent.name_full, ob.name_full, psys.name, ob_inst.persistent_id[1], ob_inst.persistent_id[0])
            else:
                group_db_name = "%s|%s|%d|%d" % (parent.name_full, ob.name_full, ob_inst.persistent_id[1], ob_inst.persistent_id[0])
        else:
            ob = ob_inst.object
            group_db_name = "%s" % (ob.name_full)
    else:
        group_db_name = "%s" % (ob_inst.name_full)

    return string_utils.sanitize_node_name(group_db_name)

def is_portal_light(ob):
    if ob.type != 'LIGHT':
        return False
    rm = ob.data.renderman
    return (rm.renderman_light_role == 'RMAN_LIGHT' and rm.get_light_node_name() == 'PxrPortalLight')

def is_particle_instancer(psys, particle_settings=None):
    psys_settings = particle_settings
    if not psys_settings:
        psys_settings = psys.settings

    if psys_settings.type == 'HAIR' and psys_settings.render_type != 'PATH':
        return True  
    if psys_settings.type == 'EMITTER' and psys_settings.render_type in ['COLLECTION', 'OBJECT']:
        return True

    return False    

def get_meta_family(ob):
    return ob.name.split('.')[0]

def is_subd_last(ob):
    return ob.modifiers and \
        ob.modifiers[len(ob.modifiers) - 1].type == 'SUBSURF'


def is_subd_displace_last(ob):
    if len(ob.modifiers) < 2:
        return False

    return (ob.modifiers[len(ob.modifiers) - 2].type == 'SUBSURF' and
            ob.modifiers[len(ob.modifiers) - 1].type == 'DISPLACE')

def is_fluid(ob):
    for mod in ob.modifiers:
        if mod.type == "FLUID" and mod.domain_settings:
            return True
    return False            

def is_subdmesh(ob):
    rm = ob.renderman
    if not rm:
        return False

    rman_subdiv_scheme = getattr(ob.data.renderman, 'rman_subdiv_scheme', 'none')

    if rm.primitive == 'AUTO' and rman_subdiv_scheme == 'none':
        return (is_subd_last(ob) or is_subd_displace_last(ob))
    else:
        return (rman_subdiv_scheme != 'none')       

# handle special case of fluid sim a bit differently
def is_deforming_fluid(ob):
    if ob.modifiers:
        mod = ob.modifiers[len(ob.modifiers) - 1]
        return mod.type == 'FLUID' and mod.fluid_type == 'DOMAIN'

def _is_deforming_(ob):
    deforming_modifiers = ['ARMATURE', 'MESH_SEQUENCE_CACHE', 'CAST', 'CLOTH', 'CURVE', 'DISPLACE',
                           'HOOK', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'EXPLODE',
                           'SIMPLE_DEFORM', 'SMOOTH', 'WAVE', 'SOFT_BODY',
                           'SURFACE', 'MESH_CACHE', 'FLUID_SIMULATION',
                           'DYNAMIC_PAINT']
    if ob.modifiers:
        # special cases for auto subd/displace detection
        if len(ob.modifiers) == 1 and is_subd_last(ob):
            return False
        if len(ob.modifiers) == 2 and is_subd_displace_last(ob):
            return False

        for mod in ob.modifiers:
            if mod.type in deforming_modifiers:
                return True
    if ob.data and hasattr(ob.data, 'shape_keys') and ob.data.shape_keys:
        return True

    return is_deforming_fluid(ob)

def is_transforming(ob, recurse=False):
    transforming = (ob.animation_data is not None)
    if not transforming and ob.parent:
        transforming = is_transforming(ob.parent, recurse=True)
        if not transforming and ob.parent.type == 'CURVE' and ob.parent.data:
            transforming = ob.parent.data.use_path
    return transforming

def _detect_primitive_(ob):

    if isinstance(ob, bpy.types.ParticleSystem):
        return ob.settings.type

    rm = ob.renderman
    rm_primitive = getattr(rm, 'primitive', 'AUTO')

    if rm_primitive == 'AUTO':
        if ob.type == 'MESH':
            if is_fluid(ob):
                return 'FLUID'            
            return 'MESH'
        elif ob.type == 'VOLUME':
            return 'OPENVDB'
        elif ob.type == 'LIGHT':
            if ob.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':
                return 'LIGHTFILTER'
            return ob.type
        elif ob.type == 'FONT':
            return 'MESH'                       
        elif ob.type in ['CURVE']:
            return 'CURVE'
        elif ob.type == 'SURFACE':
            if get_pref('rman_render_nurbs_as_mesh', True):
                return 'MESH'
            return 'NURBS'
        elif ob.type == "META":
            return "META"
        elif ob.type == 'CAMERA':
            return 'CAMERA'
        elif ob.type == 'EMPTY':
            return 'EMPTY'
        elif ob.type == 'GPENCIL':
            return 'GPENCIL'
        else:
            return ob.type
    else:
        return rm_primitive    

def get_active_material(ob):
    mat = None
    if ob.renderman.rman_material_override:
        mat = ob.renderman.rman_material_override
        
    if mat:
        return mat

    material_slots = getattr(ob, 'material_slots', None)
    if ob.type == 'EMPTY':
        material_slots = getattr(ob.original, 'material_slots', None)    
    if not material_slots:
        return None

    if len(material_slots) > 0:
        for mat_slot in material_slots:
            mat = mat_slot.material
            if mat:
                break
    return mat

def _get_used_materials_(ob):
    if ob.type == 'MESH' and len(ob.data.materials) > 0:
        if len(ob.data.materials) == 1:
            return [ob.data.materials[0]]
        mat_ids = []
        mesh = ob.data
        num_materials = len(ob.data.materials)
        for p in mesh.polygons:
            if p.material_index not in mat_ids:
                mat_ids.append(p.material_index)
            if num_materials == len(mat_ids):
                break
        return [mesh.materials[i] for i in mat_ids]
    else:
        return [ob.active_material]     

def _get_mesh_points_(mesh):
    nvertices = len(mesh.vertices)
    P = np.zeros(nvertices*3, dtype=np.float32)
    mesh.vertices.foreach_get('co', P)
    P = np.reshape(P, (nvertices, 3))
    return P.tolist()

def _get_mesh_(mesh, get_normals=False):

    P = _get_mesh_points_(mesh)
    N = []    

    npolygons = len(mesh.polygons)
    fastnvertices = np.zeros(npolygons, dtype=np.int)
    mesh.polygons.foreach_get('loop_total', fastnvertices)
    nverts = fastnvertices.tolist()

    loops = len(mesh.loops)
    fastvertices = np.zeros(loops, dtype=np.int)
    mesh.loops.foreach_get('vertex_index', fastvertices)
    verts = fastvertices.tolist()

    if get_normals:
        fastsmooth = np.zeros(npolygons, dtype=np.int)
        mesh.polygons.foreach_get('use_smooth', fastsmooth)
        if mesh.use_auto_smooth or True in fastsmooth:
            mesh.calc_normals_split()
            fastnormals = np.zeros(loops*3, dtype=np.float32)
            mesh.loops.foreach_get('normal', fastnormals)
            fastnormals = np.reshape(fastnormals, (loops, 3))
            N = fastnormals.tolist()            
        else:            
            fastnormals = np.zeros(npolygons*3, dtype=np.float32)
            mesh.polygons.foreach_get('normal', fastnormals)
            fastnormals = np.reshape(fastnormals, (npolygons, 3))
            N = fastnormals.tolist()

    return (nverts, verts, P, N)
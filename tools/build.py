"""Build the first PolyForge character. Run with Blender in background mode."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from scipy.interpolate import PchipInterpolator

sys.path.insert(0,str(Path(__file__).resolve().parent))
from horns import horn_profile
import quadruped

parser = argparse.ArgumentParser()
root = Path(__file__).resolve().parents[1]
parser.add_argument("--recipe", type=Path, default=root / "models/minotaur.json")
parser.add_argument("--output", type=Path, help="Default: the selected body family in godot/")
parser.add_argument("--review", type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
recipe = json.loads(args.recipe.read_text())
shape = recipe["shape"]
for key, value in shape.items():
    if not 0.7 <= value <= 1.3:
        raise ValueError(f"{key} outside supported range [0.7, 1.3]")
is_quadruped = recipe["parts"]["body"] == "heavy_quadruped"
model_name = "Bull" if is_quadruped else "Minotaur"
if args.output is None:
    args.output = root / "godot" / (model_name.lower()+".glb")
parts = {"body":"heavy_quadruped" if is_quadruped else "heavy_biped", "head":"bull", "horns":"swept_pair", "feet":"split_hoof", "tail":"tufted"}
if recipe["parts"] != parts or recipe["rest_pose"] != "neutral":
    raise ValueError("Unsupported part or pose in recipe")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
clay = bpy.data.materials.new("Matte clay")
clay.diffuse_color = (0.40, 0.40, 0.40, 1)
clay.use_nodes = True
shader = clay.node_tree.nodes.get("Principled BSDF")
shader.inputs["Base Color"].default_value = clay.diffuse_color
shader.inputs["Roughness"].default_value = 0.87
body = []
details = []
pi = math.pi
SW = shape["shoulder_width"]
CD = shape["chest_depth"]
MU = shape["muzzle_length"]

def mesh(name, vertices, faces, group=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(clay)
    for poly in data.polygons:
        poly.use_smooth = True
    if group is None:
        body.append(obj)
    else:
        details.append((obj, group))
    return obj

def rings(name, rows, group=None):
    sides = len(rows[0])
    faces = []
    for i in range(len(rows)-1):
        for j in range(sides):
            k = (j+1) % sides
            faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
    faces += [tuple(reversed(range(sides))), tuple(range((len(rows)-1)*sides, len(rows)*sides))]
    return mesh(name, np.vstack(rows).tolist(), faces, group)

def interp(keys, density=4):
    values = np.asarray(keys, dtype=float)
    return PchipInterpolator(np.arange(len(keys)), values)(np.linspace(0, len(keys)-1, (len(keys)-1)*density+1))

def sections(name, keys, group=None, exponent=1., sides=32):
    # z, centre x/y, transverse radius, front-to-back radius
    t = np.arange(sides)*2*pi/sides
    cx = np.sign(np.cos(t))*np.abs(np.cos(t))**exponent
    cy = np.sign(np.sin(t))*np.abs(np.sin(t))**exponent
    rows = [np.column_stack((x+w*cx,y+d*cy,np.full(sides,z))) for z,x,y,w,d in interp(keys)]
    return rings(name, rows, group)

def tube(name, keys, group=None, front=(0,-1,0), sides=22):
    # Each cross-section stays perpendicular to its centreline.
    values = interp(keys)
    path = values[:,:3]
    dirs = np.gradient(path, axis=0)
    dirs /= np.linalg.norm(dirs, axis=1)[:,None]
    a = np.cross(np.broadcast_to(front,dirs.shape),dirs)
    a /= np.maximum(np.linalg.norm(a,axis=1)[:,None],1e-9)
    b = np.cross(dirs,a)
    t = np.arange(sides)*2*pi/sides
    rows = [point+np.outer(np.cos(t)*w,u)+np.outer(np.sin(t)*d,v)
            for point,w,d,u,v in zip(path,values[:,3],values[:,4],a,b)]
    return rings(name, rows, group)

def oval(name, loc, scale, group=None, tilt=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler[1] = tilt
    obj.data.materials.append(clay)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if group is None:
        body.append(obj)
    else:
        details.append((obj,group))
    return obj

def mirrored(keys, sign):
    return [(sign*x,y,z,w,d) for x,y,z,w,d in keys]

def sculpt_trunk():
    # Each ring shares one posterior surface from the sacrum to the nape.
    # The first three columns retain the anterior torso and its proportions.
    profile = [
        # height, half width, front depth, rear depth
        (1.63,.04,.04,.06), (1.71,.20,.16,.22), (1.81,.38,.27,.34), (1.93,.52,.39,.43),
        (2.08,.60,.41,.43), (2.28,.56,.36,.38), (2.43,.53,.34,.33),
        (2.66,.60,.375,.37), (2.92,.73,.45,.45), (3.16,.86,.51,.47),
        (3.38,.91,.49,.45), (3.53,.83,.43,.40), (3.66,.56,.36,.35),
        (3.82,.37,.32,.32), (3.97,.31,.25,.26),
    ]
    heights = np.array(profile)[:,0]
    dimensions = PchipInterpolator(heights,np.array(profile)[:,1:],axis=0)
    angle = np.arange(96)*2*pi/96
    flank, depth = np.cos(angle), np.sin(angle)
    back = np.maximum(depth,0)
    rows = []
    for z in np.linspace(heights[0],heights[-1],108):
        width,front_depth,rear_depth = dimensions(z)
        width *= 1+(SW-1)*np.clip((z-2.4)/.8,0,1)
        x = width*flank
        # Mirrored, oblique planes give a broad blade and a tapering lat.
        # Dimensionless transverse positions follow shoulder-width edits.
        u = np.abs(x)/SW
        scapula = .105*np.exp(-((u-.44-.28*(z-3.32))/.245)**2-((z-3.34)/.25)**2)
        lat = .115*np.exp(-((u-.43-.46*(z-2.99))/.245)**2-((z-2.98)/.39)**2)
        erectors = .062*np.exp(-((u-.15)/.115)**2-((z-2.64)/.46)**2)
        groove = -.046*np.exp(-(u/.104)**2-((z-3.08)/.62)**2)
        glutes = .106*np.exp(-((u-.30)/.24)**2-((z-1.99)/.30)**2)
        sacrum = .032*np.exp(-(u/.11)**2-((z-2.19)/.17)**2)
        y = .06 + CD*(np.minimum(depth,0)*front_depth + back*rear_depth
                        + back**1.5*(scapula+lat+erectors+groove+glutes+sacrum))
        rows.append(np.column_stack((x,y,np.full_like(x,z))))
    rings("Trunk",rows)

def sculpt_core():
    sculpt_trunk()
    for s in (-1,1):
        oval("Pectoral",(s*.39*SW,-.285*CD,3.23),(.50*SW,.23*CD,.23),tilt=-s*.13)
        # The upper trapezius slopes into the shoulder and sits under the
        # trunk surface at its medial edge.
        tube("Shoulder slope",mirrored([(.18*SW,.09,3.76,.145,.195),
             (.39*SW,.10,3.65,.163,.216),(.67*SW,.095,3.54,.156,.21),
             (.87*SW,.06,3.49,.10,.145)],s))
        for i in range(3):
            oval("Abdominal plane",(s*(.16-i*.011),(-.315+i*.015)*CD,2.92-i*.165),
                 (.19-i*.014,.083,.131),tilt=-s*.07)
        tube("Oblique",mirrored([(.48,-.225,2.85,.085,.070),(.413,-.233,2.61,.083,.072),
                                 (.32,-.205,2.4,.027,.026)],s))
    oval("Neck",(0,.015,3.77),(.43,.39,.46))

def sculpt_head():
    oval("Skull",(0,-.12,4.03),(.445,.40,.49))
    tube("Nape crest",[(0,.035,4.45,.15,.105),(0,.155,4.37,.145,.145),
                       (0,.235,4.19,.14,.145),(0,.282,4.01,.105,.12),
                       (0,.317,3.85,.065,.075),(0,.32,3.73,.025,.035)],
         front=(1,0,0))
    oval("Jaw",(0,-.33,3.90),(.33,.35,.26))
    oval("Nasal bridge",(0,-.38,4.03),(.265,.37*MU,.286))
    for s in (-1,1):
        oval("Cheek",(s*.279,-.302,4.02),(.192,.217,.24),tilt=s*.22)
        tube("Orbital ridge",mirrored([(.055,-.50,4.22,.078,.085),(.19,-.50,4.26,.105,.11),
            (.315,-.43,4.31,.098,.115),(.408,-.28,4.28,.06,.08)],s))
        oval("Brow crest",(s*.19,-.20,4.38),(.19,.22,.15),tilt=s*.24)

def sculpt_limbs(s):
    off=(SW-1)*.85
    def arm(keys):
        return mirrored([(x+off,y,z,w,d) for x,y,z,w,d in keys],s)
    tube("Arm",arm([(.80,.04,3.46,.26,.25),(.97,.035,3.43,.345,.355),
        (1.10,.04,3.20,.30,.285),(1.17,.03,3.03,.253,.26),(1.22,.025,2.82,.193,.19),
        (1.27,-.045,2.68,.247,.235),(1.32,-.105,2.53,.224,.20),
        (1.37,-.145,2.29,.145,.155),(1.38,-.16,2.19,.135,.134)]))
    oval("Biceps",(s*(1.12+off),-.085,3.05),(.237,.225,.341),tilt=-s*.26)
    oval("Deltoid",(s*(.96+off),.01,3.41),(.345,.337,.337),tilt=-s*.18)
    oval("Palm",(s*(1.39+off),-.16,2.12),(.15,.19,.245),tilt=-s*.065)
    for j,(y,drop) in enumerate([(-.289,.23),(-.205,.275),(-.117,.252),(-.036,.194)]):
        tube("Finger",arm([(1.407,y,2.08,.068,.057),(1.418,y-.015,1.99,.064,.048),
                            (1.395,y-.02,2.02-drop,.051,.044),(1.35,y-.033,1.98-drop,.036,.031)]))
    tube("Thumb",arm([(1.327,-.267,2.21,.082,.082),(1.294,-.32,2.12,.084,.074),
                       (1.267,-.348,2.015,.065,.062),(1.278,-.349,1.967,.045,.043)]))
    tube("Leg",mirrored([(.29,.12,2.32,.095,.12),(.34,.125,2.20,.23,.26),
        (.395,.118,2.06,.313,.344),(.435,.087,1.92,.344,.376),
        (.46,.038,1.78,.335,.36),(.50,-.085,1.55,.265,.291),(.515,-.154,1.34,.205,.226),
        (.53,-.065,1.19,.198,.216),(.55,.12,1.03,.215,.230),
        (.57,.255,.825,.158,.175),(.58,.27,.666,.118,.131),
        (.587,.19,.54,.128,.14),(.598,.032,.335,.163,.17),(.598,-.035,.24,.18,.175)],s))
    oval("Kneecap",(s*.515,-.273,1.34),(.158,.111,.185))

    split_hoof("Foot."+("L" if s==1 else "R"),s,.60*s,0,1)


def split_hoof(foot,s,x0,y0,scale):
    for j in (-1,1):
        # Each toe widens at the ground; the central cleft stays open.
        data=[(.000,.110,-.10,.104,.260),(.058,.111,-.109,.108,.268),
              (.145,.103,-.082,.108,.237),(.23,.086,-.038,.095,.192),
              (.30,.068,-.004,.075,.144),(.336,.050,.019,.05,.09)]
        sections("Cloven toe",[(z*scale,x0+s*j*x*1.22*scale,y0+y*scale,w*1.23*scale,d*1.10*scale) for z,x,y,w,d in data],foot,.72)

def apply_modifier(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def nape_mane():
    # A continuous sheet hugs the rear skull; its lower edge breaks into
    # tapered locks that meet the cheek ruff just behind each ear.
    angles = np.linspace(-1.56,1.56,145)
    profile = np.array([
        # height, transverse radius, depth centre, rear radius
        (3.50,.45,.042,.396), (3.74,.448,.039,.398),
        (3.92,.454,.010,.405), (4.12,.446,-.072,.419),
        (4.28,.406,-.111,.395), (4.41,.305,-.120,.332),
        (4.51,.155,-.125,.19), (4.55,.055,-.13,.11),
    ])
    surface = PchipInterpolator(profile[:,0],profile[:,1:],axis=0)
    divisions = np.array([-1.56,-1.18,-.77,-.33,.15,.61,1.04,1.56])
    tips = np.array([.12,.13,.15,.21,.16,.12,.14])
    sections = np.clip(np.searchsorted(divisions,angles,side="right")-1,0,len(tips)-1)
    across = (angles-divisions[sections])/(divisions[sections+1]-divisions[sections])
    lock = np.sin(np.pi*np.clip(across,0,1))**1.35
    top = 4.51-.23*(abs(angles)/1.56)**1.5
    hem = 3.84+.10*(abs(angles)/1.56)**1.7-tips[sections]*lock
    outer, inner = [], []
    for t in np.linspace(0,1,32):
        z = top+(hem-top)*t
        width,centre,depth = surface(z).T
        # Sweep the locks toward the sides as they descend, with a slight
        # off-centre part to avoid a row of parallel grooves.
        theta = angles+.24*np.sin(1.9*angles+.58)*np.sin(np.pi*t*.78)
        theta += .115*t*t*lock
        edge = np.clip((1.56-abs(angles))/.22,0,1)
        swell = np.sin(np.pi*t)**.66
        relief = .018+.044*swell+.055*lock*(.16+.84*np.sin(np.pi*t*.78))
        outer_radius = edge*relief-(1-edge)*.035
        for rows,radius in ((outer,outer_radius),(inner,outer_radius-.077)):
            rows.append(np.column_stack(((width+radius)*np.sin(theta),
                         centre+(depth+radius)*np.cos(theta),z)))
    height,columns = len(outer),len(angles)
    layer_size = height*columns
    faces = []
    for i in range(height-1):
        for j in range(columns-1):
            a=i*columns+j
            face=(a,a+1,a+1+columns,a+columns)
            faces.append(face)
            faces.append(tuple(v+layer_size for v in reversed(face)))
    border = (list(range(columns)) + list(range(2*columns-1,layer_size,columns))
              + list(range(layer_size-2,layer_size-columns-1,-1))
              + list(range(layer_size-2*columns,0,-columns)))
    for a,b in zip(border,border[1:]+border[:1]):
        faces.append((b,a,a+layer_size,b+layer_size))
    mesh("Swept nape mane",np.vstack(outer+inner).tolist(),faces,"Head")

    # Shorter crown locks overlap the longer nape locks. Their ends fall at
    # different heights and follow the sweep of the existing forelock.
    for root_angle, sweep, start, drop, half_width in [
        (-1.07,-.26,4.34,.37,.095), (-.49,-.29,4.44,.42,.127),
        (-.05,.24,4.49,.39,.124), (.56,.34,4.42,.43,.119),
        (1.13,.22,4.32,.33,.088),
    ]:
        keys = []
        for t,w,thickness,offset in [(0,.52,.024,-.024),(.29,1,.048,.046),
                (.65,.83,.042,.097),(.85,.48,.027,.106),(1,.032,.004,.100)]:
            z = start-drop*t
            width,centre,depth = surface(z)
            phi = root_angle+sweep*t*t
            keys.append(((width+offset)*math.sin(phi),centre+(depth+offset)*math.cos(phi),
                         z,half_width*w,thickness))
        tube("Crown sweep",keys,"Head",front=(math.sin(root_angle),math.cos(root_angle),0))


def head_details(with_mane):
    front_y = -.41-.19*MU
    snout = oval("Bovine nose pad",(0,front_y,3.99),(.284,.191,.156),"Head")
    for s in (-1,1):
        cutter = oval("Nostril cutter",(s*.14,front_y-.160,4.024),(.067,.094,.050),"temp",tilt=-s*.43)
        details.pop()
        cut = snout.modifiers.new("Sculpt nostril","BOOLEAN")
        cut.operation="DIFFERENCE"
        cut.object=cutter
        apply_modifier(snout,cut)
        bpy.data.objects.remove(cutter,do_unlink=True)
        oval("Eye",(s*.245,-.505,4.185),(.107,.070,.066),"Head",tilt=-s*.19)
        oval("Iris relief",(s*.247,-.567,4.186),(.046,.012,.035),"Head")
        oval("Pupil relief",(s*.247,-.577,4.187),(.025,.007,.014),"Head")
        tube("Upper eyelid",mirrored([(.142,-.536,4.188,.025,.025),(.212,-.562,4.215,.038,.027),
            (.278,-.543,4.229,.036,.036),(.346,-.463,4.209,.025,.028)],s),"Head")
        tube("Lower eyelid",mirrored([(.14,-.526,4.177,.018,.021),(.211,-.536,4.143,.028,.026),
            (.286,-.494,4.151,.030,.028),(.328,-.443,4.193,.02,.024)],s),"Head")
        # Flattened leaf-shaped ears with a recessed front surface.
        outer = np.asarray([(.34,-.02,4.22),(.45,-.045,4.29),(.62,-.028,4.28),
                            (.792,-.065,4.227),(.672,-.035,4.13),(.50,-.04,4.080),(.383,-.05,4.144)])
        center=np.array([.525,-.028,4.201])
        rows=[outer,center+(outer-center)*.74+[0,-.042,0],center+(outer-center)*.48+[0,-.013,0],center+(outer-center)*.10]
        verts=np.vstack(rows+[np.array([[.51,.082,4.20]])]); verts[:,0]*=s
        faces=[(i,(i+1)%7,(i+1)%7+7,7+i) for i in range(7)]
        faces += [tuple(x+k for x in f) for k in (7,14) for f in faces[:7]]
        faces += [tuple(range(21,28))]+[(28,(i+1)%7,i) for i in range(7)]
        ear=mesh("Lobed ear",verts.tolist(),faces,"Head")
        sub=ear.modifiers.new("Round pinna","SUBSURF");sub.levels=2;apply_modifier(ear,sub)
        span=shape["horn_span"];rise=shape["horn_rise"]
        horn=horn_profile(span,rise)
        tube("Swept horn",mirrored(horn,s),"Head",sides=32)
        if with_mane:
            for x,y,z,dx,dz,size in [(.29,-.30,4.11,.125,-.25,.095),(.36,-.19,4.15,.135,-.27,.092),
                     (.38,-.03,4.14,.13,-.26,.107),(.33,.11,4.14,.14,-.25,.11),
                     (.34,.16,4.04,.10,-.30,.105)]:
                tube("Cheek ruff",mirrored([(x,y,z,size,size*.65),(x+dx*.55,y+.01,z+dz*.35,size*.86,size*.70),
                    (x+dx,y+.015,z+dz,.009,.009)],s),"Head")
    if with_mane:
        nape_mane()
    oval("Lower lip",(0,front_y+.031,3.841),(.231,.154,.064),"Head")
    for x,y,z,dx,dy,h in [(0,-.27,4.38,.018,-.06,.18),(-.13,-.17,4.39,-.08,.0,.126),
             (.13,-.16,4.39,.067,0,.122),(0,-.011,4.42,.04,.12,.14)]:
        tube("Forelock",[(x,y,z-.065,.125,.105),(x+dx*.5,y+dy*.5,z+.06,.104,.084),
                          (x+dx,y+dy,z+h,.014,.014)],"Head")

def tufted_tail():
    tube("Tail",[(0,.34,2.10,.09,.093),(.10,.54,1.96,.086,.08),(.22,.71,1.69,.068,.068),
                 (.41,.83,1.42,.056,.058),(.64,.83,1.22,.05,.05),(.79,.77,1.08,.042,.045)],"Tail")
    for x,y,z,d in [(.79,.77,1.108,.107),(.81,.79,1.12,.073),(.76,.742,1.10,.066)]:
        tube("Tail tuft",[(x,y,z,.05,.048),(x+.066,y,z-.125,d,d*.74),
                          (x+.074,y-.035,z-.219,d*.75,d*.55),(x+.044,y-.072,z-.32,.005,.006)],"Tail")

def place_parts(items, transform):
    bpy.context.view_layer.update()
    for obj in items:
        obj.data.transform(transform @ obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)


if is_quadruped:
    quadruped.sculpt(rings,tube,SW,CD)
    head_start = len(body)
    sculpt_head()
    head_details(with_mane=False)
    place_parts(body[head_start:]+[obj for obj,_ in details],quadruped.HEAD)
    for label,points in quadruped.legs(SW):
        x,y,_ = points[-1]
        split_hoof("Foot."+label,1 if x>0 else -1,x,y,.83)
    tail_start = len(details)
    tufted_tail()
    place_parts([obj for obj,_ in details[tail_start:]],quadruped.TAIL)
else:
    sculpt_core()
    sculpt_head()
    for sign in (-1,1):
        sculpt_limbs(sign)
    head_details(with_mane=True)
    tufted_tail()
bpy.ops.object.select_all(action="DESELECT")
for obj in body:
    obj.select_set(True)
bpy.context.view_layer.objects.active = body[0]
bpy.ops.object.join()
skin=bpy.context.object
skin.name="Sculpted anatomy"
remesh=skin.modifiers.new("Unify anatomical volumes","REMESH")
remesh.mode="VOXEL";remesh.voxel_size=.022
remesh.use_smooth_shade=True
apply_modifier(skin,remesh)
smooth=skin.modifiers.new("Soften anatomical transitions","SMOOTH")
smooth.factor=.58;smooth.iterations=6;apply_modifier(skin,smooth)
# Relax the union only across the seat and hamstring junction.
if not is_quadruped:
    seat = skin.vertex_groups.new(name="Pelvic blend")
    for vertex in skin.data.vertices:
        x,y,z = vertex.co
        influence = np.clip((y+.01)/.29,0,1)*np.exp(-((z-1.95)/.34)**4)
        if influence > .005:
            seat.add([vertex.index],float(influence),"REPLACE")
    blend = skin.modifiers.new("Pelvic transition","SMOOTH")
    blend.vertex_group = seat.name
    blend.factor = .64
    blend.iterations = 21
    apply_modifier(skin,blend)
    skin.vertex_groups.remove(skin.vertex_groups["Pelvic blend"])
dec=skin.modifiers.new("Reduce surface","DECIMATE");dec.ratio=.34;apply_modifier(skin,dec)

bones={}
def bone(name,start,end,parent=None):
    bones[name]=(Vector(start),Vector(end),parent)
if is_quadruped:
    quadruped.make_bones(bone,SW)
else:
    bone("Pelvis",(0,.06,1.88),(0,.06,2.31))
    bone("Spine",(0,.06,2.31),(0,.07,2.87),"Pelvis")
    bone("Chest",(0,.07,2.87),(0,.06,3.57),"Spine")
    bone("Neck",(0,.06,3.57),(0,-.02,3.84),"Chest")
    bone("Head",(0,-.02,3.84),(0,-.11,4.42),"Neck")
    bone("Tail",(0,.34,2.10),(.43,.83,1.43),"Pelvis")
    for s,side in [(1,"L"),(-1,"R")]:
        off=(SW-1)*.85
        def limb(name,start,end,parent):
            bone(name+"."+side,(s*start[0],*start[1:]),(s*end[0],*end[1:]),parent)
        shoulder=(.94+off,.035,3.45);elbow=(1.22+off,.025,2.82);wrist=(1.38+off,-.15,2.23)
        limb("Clavicle",(.14,.05,3.49),shoulder,"Chest")
        limb("UpperArm",shoulder,elbow,"Clavicle."+side)
        limb("Forearm",elbow,wrist,"UpperArm."+side)
        limb("Hand",wrist,(1.39+off,-.16,1.84),"Forearm."+side)
        hip=(.40,.06,2.05); knee=(.51,-.155,1.34); hock=(.58,.26,.665); foot=(.60,-.01,.29)
        limb("Thigh",hip,knee,"Pelvis")
        limb("Shin",knee,hock,"Thigh."+side)
        limb("Pastern",hock,foot,"Shin."+side)
        limb("Foot",foot,(.60,-.27,.08),"Pastern."+side)

armdata=bpy.data.armatures.new(model_name+" skeleton")
rig=bpy.data.objects.new(model_name+" skeleton",armdata)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode="EDIT")
for name,(head,tail,parent) in bones.items():
    b=armdata.edit_bones.new(name);b.head=head;b.tail=tail
    if parent:
        b.parent=armdata.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")

def attach(obj):
    obj.parent=rig
    mod=obj.modifiers.new("Skeleton","ARMATURE");mod.object=rig

# Blend the nearest four appropriate bones at each anatomical seam.
v=np.asarray([tuple(v.co) for v in skin.data.vertices])
names=[name for name in bones if name!="Tail"]
def smooth_band(values, low, high):
    t = np.clip((values-low)/(high-low),0,1)
    return t*t*(3-2*t)

if is_quadruped:
    idx,weights = quadruped.bind(v,bones,names)
else:
    # Let arm influence fade across the outer ribs. A hard height cutoff here
    # folds the lat into a horizontal crease when the upper arm swings.
    arm_offset = .85*(SW-1)
    inner_ribs = 1-smooth_band(abs(v[:,0])-arm_offset,.78,1.01)
    below_shoulder = 1-smooth_band(v[:,2],3.05,3.52)
    arm_penalty = .95*inner_ribs*below_shoulder
    distances=[]
    for name in names:
        a,b,_=bones[name];a=np.asarray(a);vec=np.asarray(b)-a
        param=np.clip((v-a)@vec/(vec@vec),0,1)
        dist=np.linalg.norm(v-a-param[:,None]*vec,axis=1)
        if "." in name:
            sign=1 if name.endswith(".L") else -1
            dist[v[:,0]*sign<-.015]+=2
            if name.split(".")[0] in ["UpperArm","Forearm","Hand","Clavicle"]:
                dist += arm_penalty
            else:
                dist[(abs(v[:,0])>1.0+(SW-1)*.85)&(v[:,2]>1.62)]+=2
        distances.append(dist)
    ds=np.column_stack(distances)
    idx=np.argsort(ds,axis=1)[:,:4]
    best=np.take_along_axis(ds,idx,axis=1)
    weights=np.exp(-(best-best[:,:1])/.068);weights/=weights.sum(axis=1)[:,None]
    def bind_back(vertices, names, indices, weights):
        # The rib cage carries the blades below the shoulder joint. Blend that
        # continuous sheet into the clavicle and deltoid across the outer border.
        x,y,z = vertices.T
        lateral = abs(x)-.85*(SW-1)
        region = (smooth_band(y,-.03,.175)*(1-smooth_band(lateral,.86,1.10))
                  *smooth_band(z,2.46,2.75)*(1-smooth_band(z,3.54,3.82)))
        rows = np.flatnonzero(region>0)
        if not len(rows):
            return indices,weights
        original = np.zeros((len(rows),len(names)))
        np.put_along_axis(original,indices[rows],weights[rows],axis=1)
        desired = np.zeros_like(original)
        lateral,z = lateral[rows],z[rows]
        arm = .58*smooth_band(lateral,.68,1.04)*smooth_band(z,3.04,3.51)
        collar = .60*smooth_band(lateral,.25,.78)*smooth_band(z,3.13,3.60)*(1-arm)
        rib = smooth_band(z,2.69,3.20)
        desired[:,names.index("Chest")] = rib*(1-arm-collar)
        desired[:,names.index("Spine")] = (1-rib)*(1-arm-collar)
        for sign,side in ((1,"L"),(-1,"R")):
            on_side = x[rows]*sign>0
            desired[:,names.index("Clavicle."+side)] = collar*on_side
            desired[:,names.index("UpperArm."+side)] = arm*on_side
        result = original+(desired-original)*region[rows,None]
        selected = np.argsort(result,axis=1)[:,-4:][:,::-1]
        values = np.take_along_axis(result,selected,axis=1)
        indices[rows] = selected
        weights[rows] = values/values.sum(axis=1)[:,None]
        return indices,weights

    idx,weights = bind_back(v,names,idx,weights)
groups=[skin.vertex_groups.new(name=n) for n in names]
for i,(row,ws) in enumerate(zip(idx,weights)):
    for j,w in zip(row,ws):
        groups[j].add([i],float(w),"REPLACE")
attach(skin)
for obj,name in details:
    group=obj.vertex_groups.new(name=name)
    group.add(list(range(len(obj.data.vertices))),1.0,"REPLACE")
    attach(obj)
# Merge detail objects into the same skinned mesh; each keeps its weights.
bpy.ops.object.select_all(action="DESELECT")
skin.select_set(True)
for obj,_ in details:obj.select_set(True)
bpy.context.view_layer.objects.active=skin
bpy.ops.object.join()
skin.name=model_name+" clay"

# Editable shape targets use the joined mesh's neutral coordinates.
# The rig and the walk are shared by every variation.
skin.shape_key_add(name="Basis")
def add_shape(name, displacement):
    key=skin.shape_key_add(name=name)
    xyz=np.empty(len(key.data)*3,dtype=np.float32)
    key.data.foreach_get("co",xyz)
    coords=xyz.reshape(-1,3)
    coords+=displacement(coords)
    key.data.foreach_set("co",xyz)
    key.slider_min=-1.0
    key.slider_max=1.0

def morph(coords,feature):
    if is_quadruped:
        if feature == "Chest depth":
            delta = np.zeros_like(coords)
            barrel = np.exp(-((coords[:,1]+.62)/.86)**4)*smooth_band(coords[:,2],1.15,1.65)
            delta[:,0] = coords[:,0]*.19*barrel
            delta[:,2] = (coords[:,2]-2.35)*.19*barrel
            return delta
        # Use the same local feature masks on either head mounting.
        inverse = np.asarray(quadruped.HEAD.inverted())
        local = coords@inverse[:3,:3].T+inverse[:3,3]
        displacement = head_morph(local,feature)@np.asarray(quadruped.HEAD)[:3,:3].T
        return displacement*smooth_band(-coords[:,1],1.82,2.02)[:,None]
    return head_morph(coords,feature)

def head_morph(coords,feature):
    x,y,z=coords.T
    delta=np.zeros_like(coords)
    if feature=="Horn span":
        delta[:,0]=np.sign(x)*np.maximum(abs(x)-.37,0)*.36*np.clip((z-4.275)/.07,0,1)
    elif feature=="Muzzle length":
        delta[:,1]=-np.maximum(-y-.32,0)*.42*np.clip((4.21-z)/.08,0,1)*np.clip((z-3.67)/.08,0,1)
    elif feature=="Chest depth":
        delta[:,1]=(y-.06)*.23*np.clip((z-2.38)/.42,0,1)*np.clip((3.76-z)/.28,0,1)*np.clip((1.0-abs(x))/.25,0,1)
    return delta
for feature in ("Horn span","Muzzle length","Chest depth"):
    add_shape(feature,lambda coords: morph(coords,feature))

def axis(axis,angle):
    return Quaternion(Vector(axis),angle)

def reset_pose():
    for p in rig.pose.bones:
        p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion()
        p.location=(0,0,0);p.scale=(1,1,1)

def pose_delta(delta,offset,frame):
    orientations={}
    for n in bones:
        parent=bones[n][2]
        inherited=orientations.get(parent,Quaternion())
        desired=delta.get(n,inherited)
        rest=armdata.bones[n].matrix_local.to_quaternion()
        p=rig.pose.bones[n]
        q=rest.inverted() @ inherited.inverted() @ desired @ rest
        if q.w < 0:q.negate()
        p.rotation_quaternion=q
        p.keyframe_insert("rotation_quaternion",frame=frame,group=n)
        orientations[n]=desired
    p=rig.pose.bones["Pelvis"]
    p.location=armdata.bones["Pelvis"].matrix_local.to_quaternion().inverted() @ Vector(offset)
    p.keyframe_insert("location",frame=frame,group="Pelvis")

def walk_pose(t):
    phase = 2 * pi * t
    # The centre of the support interval is 30 percent into each side's cycle.
    weight = math.cos(phase - .60*pi)
    load = math.cos(2*phase)
    shift = Vector((.175*weight, -.017*load, -.073-.032*load))
    pelvis = axis((0,0,1), .074*weight) @ axis((0,1,0), -.043*weight)
    chest = axis((0,0,1), -.113*weight) @ axis((0,1,0), .038*weight)
    chest @= axis((1,0,0), -.026+.022*math.sin(2*phase-.35))
    delta = {
        "Pelvis": pelvis,
        "Spine": pelvis.slerp(chest, .45),
        "Chest": chest,
        "Neck": chest.slerp(Quaternion(), .58),
        "Head": axis((0,0,1), -.033*math.cos(phase-.75*pi))
                @ axis((1,0,0), -.026*math.cos(2*phase-.42)),
        "Tail": axis((0,0,1), .23*math.cos(phase-.90*pi))
                @ axis((1,0,0), .064*math.sin(2*phase-.8)),
    }
    pivot = bones["Pelvis"][0]
    for sign, side in [(1, "L"), (-1, "R")]:
        f = (t + (0 if sign == 1 else .5)) % 1
        # A full-foot hold, then a rounded swing back to the same footprint.
        u = max(0.0, (f-.60)/.40)
        arc = math.sin(pi*u)**2
        lift = .285*arc
        forward = -.16*arc*(1+.35*math.cos(pi*u))
        pastern = axis((1,0,0), .17*arc*math.cos(pi*u))
        thigh, shin, lower, hoof = [n+"."+side for n in ("Thigh","Shin","Pastern","Foot")]
        hip, knee, _ = bones[thigh]
        hock, foot, _ = bones[lower]
        hip_now = pivot + shift + pelvis @ (hip-pivot)
        foot_goal = foot + Vector((0,forward,lift))
        hock_goal = foot_goal - pastern @ (foot-hock)
        line = hock_goal-hip_now
        distance = line.length
        line.normalize()
        pole = knee-hip
        pole = (pole-line*line.dot(pole)).normalized()
        upper_length = (knee-hip).length
        lower_length = (hock-knee).length
        projection = (upper_length**2-lower_length**2+distance**2)/(2*distance)
        knee_now = hip_now + line*projection + pole*math.sqrt(max(0,upper_length**2-projection**2))
        delta[thigh] = (knee-hip).rotation_difference(knee_now-hip_now)
        delta[shin] = (hock-knee).rotation_difference(hock_goal-knee_now)
        delta[lower] = pastern
        delta[hoof] = axis((1,0,0), .08*arc*math.cos(pi*u))

        # Each distal segment follows the shoulder a little later.
        arm_phase = 2*pi*f-.60*pi
        delta["Clavicle."+side] = chest @ axis((0,1,0), sign*.035*math.cos(arm_phase))
        delta["UpperArm."+side] = chest @ axis((1,0,0), -.32*math.cos(arm_phase-.12))
        delta["Forearm."+side] = chest @ axis((1,0,0), -.14-.39*math.cos(arm_phase-.30))
        delta["Hand."+side] = chest @ axis((1,0,0), -.11-.34*math.cos(arm_phase-.43))
    return delta, shift

scene.frame_start=0
scene.render.fps=24
actions={}
rig.animation_data_create()
for name,end in [("Idle",73),("Walk",89 if is_quadruped else 49)]:
    act=bpy.data.actions.new(name);act.use_fake_user=True
    rig.animation_data.action=act;actions[name]=act
    for frame in range(end):
        t=frame/(end-1)
        if name=="Walk":
            ds,offset=quadruped.walk_pose(t,bones) if is_quadruped else walk_pose(t)
        else:
            breath=math.sin(2*pi*t)
            ds={("Neck" if is_quadruped else "Chest"):axis((1,0,0),.020*breath),"Head":axis((0,0,1),.032*breath),
                "Tail":axis((0,0,1),.082*breath)}
            offset=(0,0,0)
        pose_delta(ds,offset,frame)
    for curve in act.fcurves:
        for key in curve.keyframe_points:key.interpolation="LINEAR"
rig.animation_data.action=None
reset_pose()
scene.frame_set(0)
bpy.context.view_layer.update()
args.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True);skin.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(args.output.resolve()),export_format="GLB",use_selection=True,
    export_animations=True,export_animation_mode="ACTIONS",export_anim_single_armature=True,
    export_rest_position_armature=True,export_yup=True,export_texcoords=False,export_cameras=False,
    export_lights=False)
print("WROTE",args.output,"mesh vertices", len(skin.data.vertices),"bones",len(bones))
if args.review:
    args.review.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str((args.review/(model_name+".blend")).resolve()))

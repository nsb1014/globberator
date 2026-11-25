"""Smooth shell and limb volumes in the same matte clay as the vertebrates."""
import math
from scipy.interpolate import PchipInterpolator
import numpy as np
import bpy
from mathutils import Matrix, Vector
from attachments import attach_part

TAU = math.tau


class Sculpture:
    def __init__(self, material):
        self.material = material
        self.meshes = []
        self.bones = {}

    def bone(self, name, start, end, parent=None):
        self.bones[name] = (Vector(start), Vector(end), parent)

    def surface(self, name, rows):
        n = len(rows[0])
        verts = [p for row in rows for p in row]
        faces = [(i*n+j, i*n+(j+1)%n, (i+1)*n+(j+1)%n, (i+1)*n+j)
                 for i in range(len(rows)-1) for j in range(n)]
        faces += [tuple(reversed(range(n))), tuple(range(len(verts)-n, len(verts)))]
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, [], faces)
        data.update()
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        data.materials.append(self.material)
        for face in data.polygons:
            face.use_smooth = True
        return obj

    def ellipsoid(self, name, center, radii):
        # Traverse front to rear. The X/Z ring winds around the positive Y axis.
        x,y,z = center
        w,d,h = radii
        rows = []
        rings,sides = (24,40) if max(radii) > .22 else (12,20)
        for i in range(rings+1):
            t = .002 + (math.pi-.004)*i/rings
            rows.append([(x+w*math.sin(t)*math.cos(a*TAU/sides), y-d*math.cos(t),
                          z-h*math.sin(t)*math.sin(a*TAU/sides)) for a in range(sides)])
        return self.surface(name, rows)

    def spindle(self, name, start, end, profile, flatten=1, arch=0):
        """Tapered segment with a local cross section perpendicular to its axis."""
        start, end = Vector(start), Vector(end)
        axis = (end-start).normalized()
        u = Vector((0,0,1)).cross(axis)
        if u.length < .001:
            u = axis.cross(Vector((0,1,0)))
        u.normalize()
        v = axis.cross(u)
        rows = []
        times, radii = zip(*profile)
        curve = PchipInterpolator(times,radii)
        for t in np.linspace(0,1,19):
            radius = float(curve(t))
            center = start.lerp(end,t) + arch*math.sin(math.pi*t)*v
            rows.append([center+radius*(u*math.cos(i*TAU/24)+flatten*v*math.sin(i*TAU/24))
                         for i in range(24)])
        return self.surface(name,rows)

    def mount(self, anchor, pieces):
        """Bind all canonical parts to the same transforms as their joint chains."""
        objects = [obj for obj, _ in pieces]
        mounts = []
        for side, transform, instances in attach_part(objects, Matrix.Translation(anchor), anchor):
            for obj, (_, owner) in zip(instances,pieces,strict=True):
                group = obj.vertex_groups.new(name=owner.format(side=side))
                group.add(list(range(len(obj.data.vertices))), 1, "REPLACE")
                self.meshes.append(obj)
            mounts.append((side,transform))
        return mounts


def limb_chain(sculpt, spec, belly_grounded=False, body_height=0.):
    """The same three-segment part serves a pedipalp, feeler or weight-bearing leg."""
    role = spec["role"]
    y = spec["socket_y"]
    origin = Vector((.35 if role != "palp" else .39, y, .64))
    angle = math.radians(spec["sweep"])
    direction = Vector((math.cos(angle),math.sin(angle),0))
    reach = spec["reach"]
    toe_z = {"foot":.034,"palp":.39,"feeler":.25}[role]
    knee_z = {"foot":1.05,"palp":.74,"feeler":.93}[role]
    def station(fraction, height):
        point = origin + direction * (reach*fraction)
        point.z = height
        return point
    joints = [origin, station(.41,knee_z), station(.84,toe_z+.16), station(1,toe_z)]
    if spec.get("center"):
        origin = Vector((0,y,.64+body_height))
        direction = Vector((0,-1,0))
        joints = [origin,Vector((0,y+.37*reach,.42+.42*body_height)),Vector((0,y+.12*reach,.20)),
                  Vector((0,y-.04*reach,toe_z))]
    elif body_height:
        for i,point in enumerate(joints):
            point.z += body_height + (.18*i/3 if belly_grounded else 0)
    sizes = (.132,.096,.057) if role != "feeler" else (.087,.066,.042)
    if role == "palp":
        sizes = (.126,.102,.072)
    names = [spec["id"]+"."+seg for seg in ("Base","Shin","Tip")]
    parts = []
    for i,(a,b,r) in enumerate(zip(joints[:-1],joints[1:],sizes,strict=True)):
        group = names[i]+".{side}"
        part = sculpt.spindle(group,a,b,[(0,.60*r),(.07,1.13*r),(.23,1.05*r),(.58,.80*r),
                             (.83,.62*r),(.94,.74*r),(1,.52*r)],.87, (.055,.035,.025)[i])
        parts.append((part,group))
        parts.append((sculpt.ellipsoid("Articulation",a,(r*.84,r*.84,r*.78)),group))
        if i == 0:
            coxa = sculpt.spindle("Coxal shield",a-direction*.07,a.lerp(b,.36),
                                  [(0,r*.72),(.28,r*1.25),(.64,r*1.10),(1,r*.62)],.86,.016)
            parts.append((coxa,group))
    if role == "foot":
        across = Vector((-direction.y,direction.x,0))
        for fork in (-1,1):
            base = joints[-1] - direction*.065
            claw_tip = joints[-1] + direction*.095 + fork*.036*across
            claw_tip.z = .003
            claw = sculpt.spindle("Tarsal claw",base,claw_tip,
                                   [(0,.025),(.38,.021),(.77,.012),(1,.002)],.7,.018)
            parts.append((claw,names[-1]+".{side}"))
        # A flat ventral patch under the distal tarsus makes the planted area visible.
        heel = joints[-1] - .13*direction
        ball = joints[-1] + .055*direction
        pad = sculpt.spindle("Tarsal pad",heel,ball,[(0,.021),(.23,.048),(.70,.055),(1,.021)])
        for v in pad.data.vertices:
            v.co.z = max(0.,v.co.z)
        parts.append((pad,names[-1]+".{side}"))
    elif role == "palp":
        parts.append((sculpt.ellipsoid("Palp pad",joints[-1],(.058,.079,.051)),names[-1]+".{side}"))
    chains = []
    for side,matrix in sculpt.mount(origin,parts):
        points = [matrix@p for p in joints]
        bones = [n+"."+side for n in names]
        parent = "Carapace"
        for name,a,b in zip(bones,points[:-1],points[1:],strict=True):
            sculpt.bone(name,a,b,parent)
            parent = name
        chains.append((side,bones,points))
    return chains

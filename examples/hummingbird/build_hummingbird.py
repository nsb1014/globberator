"""Build the hummingbird study using Globberator's recipe-space geometry and exporter.

From the checkout run:
    blender -b -t 2 --python-exit-code 1 -P examples/hummingbird/build_hummingbird.py

Dimensions are working units: 1 unit represents 5 cm. +Y up and +Z forward.
"""
from pathlib import Path
import math
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from scipy.interpolate import PchipInterpolator

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "hummingbird"
sys.path.insert(0, str(ROOT))
from polyforge import builder, export, finish, kit, render
from polyforge.kit import V, UP, BACK, RIGHT, smoothstep, lerp

CAMERA = V(0.897, .078, .435).normalized()
BILL_ROOT = V(0,.426,.700)
BILL_TIP = V(0,.526,1.402)
COL = "Plumage"
objects = []
bones = []
anchors = {}


def rgb(value):
    return Vector(builder.hex_rgb(value))


def surface(name, color=None, roughness=.48, metallic=.0, vertex=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.roughness = roughness
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if color is not None:
        bsdf.inputs["Base Color"].default_value = (*rgb(color),1)
        mat.diffuse_color = (*rgb(color),1)
    if vertex:
        attr = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = COL
        mat.node_tree.links.new(attr.outputs["Color"],bsdf.inputs["Base Color"])
    return mat


def mesh(name, verts, faces, material, owner, subdiv=0, painter=None):
    ob = finish.new_object(name,verts,faces)
    b = bmesh.new()
    b.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(b,faces=list(b.faces))
    assert all(e.is_manifold for e in b.edges), name
    assert b.calc_volume(signed=True)>0, name
    b.to_mesh(ob.data)
    b.free()
    ob.data.shade_smooth()
    if subdiv:
        mod = ob.modifiers.new("Sculpt subdivision","SUBSURF")
        mod.levels = mod.render_levels = subdiv
    ob.data.materials.append(material)
    if painter is not None:
        colors = ob.data.color_attributes.new(COL,"FLOAT_COLOR","POINT")
        values = [v for i,p in enumerate(verts) for v in (*painter(V(p),i),1.)]
        colors.data.foreach_set("color", values)
    ob["owner_bone"] = owner
    objects.append(ob)
    return ob


def rings_mesh(name, rings, material, owner, subdiv=0, painter=None):
    count = len(rings[0])
    faces = [tuple(reversed(range(count)))]
    verts = [v for ring in rings for v in ring]
    for k in range(len(rings)-1):
        for i in range(count):
            a = k*count
            j = (i+1) % count
            faces.append((a+i,a+j,a+count+j,a+count+i))
    faces.append(tuple(range(len(verts)-count,len(verts))))
    return mesh(name,verts,faces,material,owner,subdiv,painter)


def oval(name, center, radii, material, owner, normal=None):
    piece = kit.Piece()
    basis = None if normal is None else V(normal).to_track_quat("Z","Y").to_matrix()
    piece.oval(V(center),V(radii),basis,segs=28,rings=16)
    return mesh(name,*piece.cage(),material,owner)


def tube(name, points, radii, mat, owner, paint=None, sides=19):
    piece = kit.Piece()
    piece.loft([V(p) for p in points],radii,sides=sides,up=RIGHT,density=4)
    return mesh(name,*piece.cage(),mat,owner,painter=paint)


def bone(name, parent, head, tail):
    bones.append((name,parent,V(head),V(tail)))


def build_body():
    # Centerline joints and hand-placed sections. Head, neck, breast and
    # abdomen share one continuous, editable subdivision cage.
    stations = [
        (-.365,-.647,.033,.035),(-.338,-.584,.081,.084),
        (-.27,-.451,.146,.133),(-.17,-.298,.205,.183),
        (-.060,-.130,.245,.222),(.025,.035,.237,.231),
        (.103,.179,.201,.204),(.192,.307,.155,.155),
        (.270,.397,.143,.148),(.349,.477,.156,.156),
        (.389,.545,.151,.142),(.406,.611,.127,.114),
        (.420,.669,.087,.072),(.426,.714,.038,.035),
    ]
    rings=[]
    for k,(y,z,w,h) in enumerate(stations):
        prev,nxt=stations[max(k-1,0)],stations[min(k+1,len(stations)-1)]
        tangent = V(0,nxt[0]-prev[0],nxt[1]-prev[1]).normalized()
        dorsal = tangent.cross(RIGHT)
        center=V(0,y,z)
        ring=[]
        for j in range(40):
            a=math.tau*j/40
            x=math.cos(a)
            d=math.sin(a)
            contour=1-.05*d if 2<k<8 else 1
            ring.append(center+RIGHT*(w*x*contour)+dorsal*(h*d))
        rings.append(ring)

    channel_normal=V(0,.87,-.49)
    jade,olive,turquoise,blue,buff=map(rgb,["#16905c","#7ca735","#087e79","#174780","#bca585"])
    def body_color(v, i):
        stored = i % 40
        dorsal=math.sin(math.tau*stored/40)
        upper=smoothstep(-.25,.9,dorsal)
        olive_patch=upper*(.48+.32*smoothstep(.32,.68,v.z))
        green=jade.lerp(olive,olive_patch)
        throat=smoothstep(.08,.42,v.z)*(1-smoothstep(-.54,.19,dorsal))
        throat*=1-.18*smoothstep(.62,.74,v.z)
        throat_color=turquoise.lerp(blue,smoothstep(.18,.64,v.z)*.88)
        rear=(1-smoothstep(-.53,-.29,v.z))*(1-.65*upper)
        gentle=1+.065*math.sin(19*v.z+37*v.x)*math.cos(24*v.y-8*v.z)
        return green.lerp(throat_color,throat).lerp(buff,rear)*gentle
    body = rings_mesh("Continuous head, throat and torso",rings,PLUMAGE,"Body",2,body_color)
    # Build an evaluated cage BVH for physically seated landmarks and plumage.
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=body.evaluated_get(dg)
    body_mesh=evaluated.to_mesh()
    body_vertices=[V(v.co.x,v.co.z,-v.co.y) for v in body_mesh.vertices]
    body_faces=[tuple(p.vertices) for p in body_mesh.polygons]
    body_bvh=BVHTree.FromPolygons(body_vertices,body_faces)
    evaluated.to_mesh_clear()
    return body,body_bvh,channel_normal


def build_bill():
    root=BILL_ROOT
    mid=V(0,.467,.950)
    tip=BILL_TIP
    dark, coral, shade=map(rgb,["#2b3034","#e85f49","#752b29"])
    def bill_color(v, _):
        length=(v.z-root.z)/(tip.z-root.z)
        base=coral.lerp(shade,smoothstep(.29,.93,length)*.37)
        line=math.exp(-((v.y-(.419+.151*(v.z-.70)))/.0045)**2)
        return base.lerp(dark,.16*line + .84*smoothstep(.52,.88,length))
    tube("Coral bill with graphite tip",[root- V(0,.011,.057),root,mid,V(0,.507,1.23), tip],
         [(.045,.031),(.038,.023),(.022,.013),(.010,.007),(.0018,.0011)],
         BILL,"Head",bill_color,24)
    anchors["bill_root"]=root
    anchors["bill_tip"]=tip


def build_eyes(body_tree):
    for side,name in ((1,"Left"),(-1,"Right")):
        probe=V(side*1,.405,.598)
        seat,normal,index,_=body_tree.ray_cast(probe,V(-side,0,0),1)
        assert seat is not None and normal.x*side>.40,(side,seat,normal)
        normal=(normal + V(side*.28,.025,.03)).normalized()
        center=seat-normal*.012
        oval(f"{name} orbital skin",center-normal*.006,(.067,.064,.030),ORBIT,"Head",normal)
        oval(f"{name} glossy eye",center+normal*.010,(.054,.053,.040),EYEBALL,"Head",normal)
        anchors[f"eye_{name.lower()}"]=center


def blade(name,start,end,width,depth,normal,owner,mats,shape=None):
    # Closed feather master. Root and tip remain narrow while chord and
    # thickness form a cambered airfoil in each station.
    start,end=V(start),V(end)
    forward=(end-start).normalized()
    normal=V(normal)
    across=forward.cross(normal).normalized()
    normal=across.cross(forward).normalized()
    rings=[]
    layout=shape or ((0,.12),(.17,.61),(.34,.94),(.53,1),(.71,.87),(.86,.60),(.96,.27),(1,.035))
    for t,w in layout:
        root=start.lerp(end,t)
        root+=normal*(math.sin(math.pi*t)*.018*min(1,(end-start).length))
        thickness=max(.00065,depth*(.48+.52*math.sin(math.pi*t))*(1-.72*t))
        ring=[]
        for i in range(16):
            a=math.tau*i/16
            u=math.cos(a)
            ring.append(root+across*(width*w*u*(1+.16*u))+
                        normal*(thickness*math.sin(a)*(1-.22*u*u)))
        rings.append(ring)
    c0,c1=map(rgb,mats)
    def paint(v,i):
        t=i//16/(len(rings)-1)
        feather_face=math.sin(math.tau*(i%16)/16)
        central=abs(math.cos(math.tau*(i%16)/16))
        line=(1-smoothstep(.025,.31,central))*.14*(.40+.6*smoothstep(0,.55,t))
        return c0.lerp(c1,smoothstep(.12,1,t)).lerp(c1,line)*(1+.08*feather_face)
    return rings_mesh(name,rings,PLUMAGE,owner,1,paint)


def surface_feathers(body_tree,dorsal):
    # Shallow flush coverts bring a readable sculpt rhythm into the iridescent
    # patch. No raised detail crosses the eye seats or the crown silhouette.
    rows = [
        (.56,.283,-.20,22,.023,.051),(.50,.236,-.27,22,.027,.057),
        (.415,.174,-.40,22,.031,.066),(.310,.103,-.45,22,.033,.068),
        (.21,.035,-.55,20,.038,.073),(.105,-.008,-.65,20,.037,.078),
        (-.005,-.075,-.68,18,.038,.078),(-.116,-.137,-.68,18,.038,.075),
        (-.239,-.215,-.68,16,.036,.067),
    ]
    for row,(z,y,lowest,divisions,width,length) in enumerate(rows):
        for k in range(divisions):
            a=math.tau*(k+(.5 if row%2 else 0))/divisions
            shell_normal=RIGHT*math.cos(a)+dorsal*math.sin(a)
            band=math.sin(a)
            upper=lowest+.57 if 1<row<8 else lowest+.24
            if band>upper or band<-.91 or (row<2 and abs(math.cos(a))>.87):
                continue
            seat,n,_,_=body_tree.ray_cast(V(0,y,z)+shell_normal*.65,-shell_normal,.7)
            if seat is None:
                continue
            flow = -V(0,.48,.86)
            flow = (flow-n*flow.dot(n)).normalized()
            # Keep the flanks and neck as a sculpted surface. The feather edge
            # sits just proud of the body while its root is buried.
            delta=flow*length
            root=seat-delta*.36-n*.007
            tip=seat+delta*.64+n*.0048
            tint=("#14578a","#2f96aa") if row<3 else ("#167856","#43a588")
            if (k+row)%4==0:
                tint=("#146776","#35a3a6") if row<4 else ("#137e57","#74b469")
            blade(f"Gorget covert {row+1}.{k+1:02}",root,tip,width*.88,.0048,n,"Body",tint)


def wing(label, control, chord_axis):
    """A sculpted shoulder and airfoil support a laid-out feather fan."""
    start,elbow,wrist,far=map(V,control)
    leading=PchipInterpolator([0,.24,.51,1],[list(p) for p in (start,elbow,wrist,far)],axis=0)
    chord=V(chord_axis).normalized()
    flight_bone=f"{label} flight feathers"
    hinge=f"{label} wing"
    bone(hinge,"Body",start,wrist)
    bone(flight_bone,hinge,wrist,far)

    def position(t,c=0):
        return V(leading(t))+chord*c
    def normal_at(t):
        tangent=V(leading.derivative()(t)).normalized()
        n=tangent.cross(chord).normalized()
        return n if n.dot(CAMERA)>0 else -n

    rings=[]
    for k,(t,width,bulk) in enumerate(((0,.113,.036),(.08,.242,.042),(.19,.278,.038),
                            (.32,.236,.032),(.49,.196,.027),(.68,.154,.018),
                            (.85,.085,.011),(.96,.037,.006),(1,.013,.003))):
        n=normal_at(t)
        ring=[]
        for i in range(24):
            a=math.tau*i/24
            p=position(t,.70*width*(.5+.5*math.cos(a)))+n*(bulk*math.sin(a))
            ring.append(p)
        rings.append(ring)
    shade0,shade1=rgb("#508d45"),rgb("#4a493e")
    wing_skin=rings_mesh(f"{label} shoulder and leading edge",rings,PLUMAGE,hinge,2,
                         lambda _,i:shade0.lerp(shade1,smoothstep(.8,7.4,i//24)))
    anchors[f"wing_{label.lower()}"]=start
    # Span stations and the offsets of the tips along the trailing chord lay
    # out the tapered hand rather than using a circular feather fan.
    primary_specs=[
        (.55,.070,1.02,.038,.063),(.53,.092,.965,.125,.069),(.50,.113,.91,.217,.074),
        (.47,.134,.85,.289,.080),(.43,.151,.786,.357,.084),(.39,.165,.711,.400,.087),
        (.35,.178,.640,.418,.087),(.31,.184,.567,.423,.088),(.27,.181,.493,.418,.085),
        (.23,.173,.416,.401,.080),(.19,.163,.342,.367,.073),
    ]
    for i,(sr,cr,te,ce,width) in enumerate(primary_specs):
        te=min(te,1)
        n=normal_at(sr)
        root=position(sr,cr*.70)-n*.006
        tip=position(te,ce)-n*(.017+.002*(i%3))
        colors=("#4d4b43","#77746e") if i<2 else (
                "#71685c",("#b8ad98","#a99d87","#bdb3a3")[i%3])
        owner=flight_bone if i<6 else hinge
        blade(f"{label} flight feather {i+1:02}",root,tip,width,.010,n,owner,colors)

    for i in range(4):
        t=.045+.043*i
        n=normal_at(t)
        blade(f"{label} inner secondary {i+1:02}",position(t,.092)-n*.009,
              position(t+.138,.287+.018*i)-n*.014,
              .067,.009,n,hinge,("#635e4c","#9f9381"))
    for i in range(11):
        t=.074+.051*i
        n=normal_at(t)
        root=position(t,.058)+n*.016
        tip=position(t+.113,.159-.028*t)+n*.012
        colors=("#4c7843","#847d54") if i<7 else ("#586a47","#9b927f")
        blade(f"{label} median covert {i+1:02}",root,tip,.040,.007,n,hinge,colors)
    for i in range(8):
        t=.040+.048*i
        n=normal_at(t)
        root=position(t,.028)+n*.023
        tip=position(t+.102,.135-.05*t)+n*.019
        blade(f"{label} shoulder covert {i+1:02}",root,tip,.033,.006,n,hinge,
              ("#427b44","#6b9b4a"))
    return wing_skin,start,far


def tail():
    root=V(0,-.323,-.536)
    bone("Tail","Body",root,V(0,-.456,-1.06))
    for i in range(7):
        x=(i-3)/3
        start=root+V(.072*x,.022*(1-abs(x)),.030*abs(x))
        end=V(.142*x,-.487+.040*abs(x),-1.067+.105*abs(x))
        blade(f"Tail rectrix {i+1:02}",start,end,.061,.011,V(.57,.83,0),"Tail",("#4f5e3d","#262c32"))
    for i in range(5):
        x=(i-2)/2
        start=root+V(.057*x,-.029,.037)
        end=V(.082*x,-.416+.015*abs(x),-.766+.031*abs(x))
        blade(f"Undertail covert {i+1:02}",start,end,.044,.009,UP,"Tail",("#aa9473","#c3ad87"))


def feet(body_tree):
    for side,label in ((1,"Left"),(-1,"Right")):
        search=V(side*.105,-.65,-.372)
        seat,_,_,_=body_tree.ray_cast(search,UP,.8)
        assert seat is not None, label
        anchor=seat+UP*.023
        hock=seat+V(side*.014,-.052,-.030)
        ball=hock+V(side*.008,.012,-.055)
        leg=f"{label} leg"
        foot=f"{label} foot"
        bone(leg,"Body",anchor,hock)
        bone(foot,leg,hock,ball)
        # A rounded joint on the leg overlaps the tarsus at its pivot.
        tube(f"{label} lower leg",[anchor,seat,hock],
             [.017,.017,.0095],FOOT,leg,sides=14)
        oval(f"{label} hock",hock,(.011,.011,.011),FOOT,leg)
        tube(f"{label} tarsus",[hock,hock.lerp(ball,.55)-UP*.003,ball],
             [.008,.009,.010],FOOT,foot,sides=14)

        # Three forward toes curl under the ball. The hallux sits medially
        # and sweeps the opposite way. Each toe has a continuous keratin tip.
        for i,(offset,spread,reach) in enumerate(((-.007,-.010,.033),
                                                    (0,0,.044),
                                                    (.007,.012,.036)),1):
            base=ball+V(side*offset,0,.003)
            knee=base+V(side*spread*.55,-.012,reach*.53)
            curl=base+V(side*spread,-.017,reach)
            tip=base+V(side*spread,-.010,reach+.003)
            digit(f"{label} toe {i}",[base,knee,curl,tip],foot)
        digit(f"{label} hallux",[ball+V(-side*.006,0,-.003),
              ball+V(-side*.015,-.007,-.014),ball+V(-side*.021,-.010,-.025),
              ball+V(-side*.023,-.004,-.028)],foot)

        anchors[f"{label} foot seat"]=anchor
        anchors[f"{label} hock"]=hock
        anchors[f"{label} ball"]=ball


def digit(name,points,owner):
    skin,claw=rgb("#6d665d"),rgb("#383a35")
    start=points[2]
    tip=points[3]
    direction=tip-start
    def color(p,_):
        t=(p-start).dot(direction)/direction.length_squared
        return skin.lerp(claw,smoothstep(-.22,.7,t))
    tube(name,points,[.0065,.0058,.0036,.0009],TOE,owner,color,sides=12)


def make_rig():
    rig=bpy.data.objects.new("Hummingbird | hover pose",bpy.data.armatures.new("Hummingbird skeleton"))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,parent,start,end in bones:
        b=rig.data.edit_bones.new(name)
        b.head,b.tail=kit.to_blender(start), kit.to_blender(end)
        if parent:
            b.parent=rig.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front=True
    rig.data.display_type='STICK'
    for ob in objects:
        group=ob.vertex_groups.new(name=ob["owner_bone"])
        group.add(list(range(len(ob.data.vertices))),1.0,'REPLACE')
        ob.parent=rig
        mod=ob.modifiers.new("Hummingbird pose","ARMATURE")
        mod.object=rig
    return rig


def camera_studio():
    scene=bpy.context.scene
    cam=render.setup("workbench",680)
    focus=V(.32,.40,-.016)
    d=kit.to_blender(CAMERA)
    cam.data.type="ORTHO"
    cam.data.ortho_scale=3.55
    cam.location=kit.to_blender(focus)+d*6
    cam.rotation_euler=(-d).to_track_quat("-Z","Y").to_euler()
    scene.render.resolution_x=1050
    scene.render.resolution_y=830
    return cam,focus


def area(name,location,energy,size,color,aim=V(0,.3,0)):
    data=bpy.data.lights.new(name,type="AREA")
    data.energy,data.shape,data.size,data.color=energy,"DISK",size,color
    ob=bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location=kit.to_blender(V(location))
    ob.rotation_euler=(kit.to_blender(aim)-ob.location).to_track_quat("-Z","Y").to_euler()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PLUMAGE=surface("Iridescent satin plumage",roughness=.43,metallic=.24,vertex=True)
    BILL=surface("Coral keratin",roughness=.34,metallic=.04,vertex=True)
    ORBIT=surface("Muted olive eye margin","#5b6542",.72)
    EYEBALL=surface("Black glass eye","#101a1f",.20,.02)
    FOOT=surface("Warm slate tarsi","#68635b",.65)
    TOE=surface("Tapered slate toes and graphite claws",roughness=.55,vertex=True)
    bone("Body",None,(0,-.29,-.45),(0,.18,.25))
    bone("Head","Body",(0,.24,.35),(0,.412,.67))
    body,body_tree,dorsal=build_body()
    build_bill()
    build_eyes(body_tree)
    surface_feathers(body_tree,dorsal)
    # Root the wings on the upper forward thorax and preserve the tip pose.
    for side,label,elbow,wrist,tip,chord in (
        (1,"Left",(.393,.465,-.276),(.717,.703,-.530),(1.480,1.280,-1.226),(.13,-.57,-.81)),
        (-1,"Right",(-.421,.416,-.223),(-.824,.555,-.477),(-1.600,.732,-1.038),(-.12,-.63,-.77)),
    ):
        shoulder,normal,_,_=body_tree.ray_cast(V(side,.215,.014),V(-side,0,0),1)
        assert shoulder is not None and side*normal.x>.35,(label,shoulder,normal)
        wing(label,(shoulder-normal*.038,elbow,wrist,tip),chord)
    tail()
    def buried(point):
        nearest,normal,_,distance=body_tree.find_nearest(point)
        return (point-nearest).dot(normal)
    for name,point in (
        ("Left shoulder",anchors["wing_left"]),("Right shoulder",anchors["wing_right"]),
        ("Bill",BILL_ROOT-V(0,.011,.057)),("Tail",V(0,-.323,-.536)),
    ):
        depth=buried(point)
        assert depth<-.006,(name,depth)
        print("FIT",name,round(-depth*.05*1000,2),"mm inset",flush=True)
    assert buried(anchors["wing_left"]+V(.34,.2,0))>0
    feet(body_tree)
    for label in ("Left","Right"):
        assert buried(anchors[f"{label} foot seat"])<-.006
        hock,ball=anchors[f"{label} hock"],anchors[f"{label} ball"]
        assert buried(hock)>.009 and buried(ball)>.009,(label,buried(hock),buried(ball))
        assert ball.y>hock.y and ball.z<hock.z

    rig=make_rig()
    cam,focus=camera_studio()
    scene=bpy.context.scene
    area("Broad warm key",(2.8,3.2,2.6),470,4.8,(1.0,.925,.80))
    area("Cool fill",(2.4,.45,-3.0),220,3.1,(.66,.83,1.))
    area("Wing rim",(-2.6,2.2,.0),370,3.3,(.80,.93,1.))
    scene.world=bpy.data.worlds.new("Studio fill")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.23
    scene.render.engine="CYCLES"
    scene.cycles.samples=26
    scene.cycles.use_denoising=False
    scene.render.film_transparent=True
    scene.render.image_settings.color_mode="RGBA"
    scene.view_settings.view_transform="AgX"
    for screen in bpy.data.screens:
        for panel in screen.areas:
            if panel.type=="VIEW_3D":
                panel.spaces.active.region_3d.view_perspective="CAMERA"
                panel.spaces.active.overlay.show_overlays=False
                panel.spaces.active.shading.color_type="MATERIAL"
    scene.unit_settings.system="METRIC"
    scene.unit_settings.scale_length=.05
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"hummingbird.blend"))
    # Keep each editable object and its bone. Globberator's normal exporter
    # expects assembled mesh slots, so assign the selected union to one slot
    # while its component objects remain separate in the source scene.
    export_objects=[]
    dg=bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        copy=ob.copy()
        copy.data=ob.data.copy()
        scene.collection.objects.link(copy)
        for mod in list(copy.modifiers):
            if mod.type=="SUBSURF":
                # Bake the shape in the export copy and retain armature skinning.
                evaluated=ob.evaluated_get(dg)
                real=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=dg)
                copy.data=real
                copy.modifiers.remove(mod)
                group=copy.vertex_groups.get(ob["owner_bone"])
                group.add(list(range(len(real.vertices))),1.0,'REPLACE')
                break
        export_objects.append(copy)
    # Reuse Globberator export selection/axis/material conventions with all
    # authoring objects selected via a single joined export mesh.
    for ob in bpy.context.selected_objects:
        ob.select_set(False)
    for ob in export_objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active=export_objects[0]
    bpy.ops.object.join()
    export_mesh=bpy.context.object
    export_mesh.name="Hummingbird plumage and anatomy"
    physical_scale=Matrix.Scale(.05,4)
    rig.data.transform(physical_scale)
    export_mesh.data.transform(physical_scale)
    bpy.context.view_layer.update()
    export.export({"armature":rig,"skin":export_mesh,"parts":None},str(OUT/"hummingbird.glb"),"glb")
    print("EXPORTED", len(objects),"editable meshes and",len(bones),"bones",flush=True)

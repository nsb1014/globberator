"""Heavy quadruped body and locomotion. Head, hooves and tail come from the shared catalog."""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector
from scipy.interpolate import PchipInterpolator


STRIDE = 1.04
DUTY = .66
CYCLES = 2
# Lateral-sequence walk: hind, then fore on the same side.
TOUCHDOWN = {"Hind.L": 0., "Fore.L": .20, "Hind.R": .50, "Fore.R": .70}


def socket(origin, source, scale, pitch=0):
    return (Matrix.Translation(origin) @ Matrix.Rotation(pitch,4,'X')
            @ Matrix.Diagonal((*scale,1)) @ Matrix.Translation(-Vector(source)))


HEAD = socket((0,-2.10,2.32),(0,-.10,4.07),(1.16,1.43,1.28),math.radians(31))
TAIL = socket((0,1.46,2.53),(0,.34,2.10),(.48,.71,1.47))


def leg_sockets(shoulder_width):
    # Each socket describes a bilateral mount, in host rest coordinates.
    return {"shoulders": ("Fore","Chest",Vector((.46*shoulder_width,-1.17,2.10))),
            "hips": ("Hind","Pelvis",Vector((.46,1.11,2.29)))}


DEFAULT_ATTACHMENTS = {
    "shoulders": {"part":"ungulate_leg","profile":"fore"},
    "hips": {"part":"ungulate_leg","profile":"hind"},
}


def sculpt(rings, shoulder_width, chest_depth):
    # A single continuous surface from throat to rump. Underside and withers
    # are independent contours, so a deeper brisket still meets the belly.
    sections=np.array([
        # longitudinal position, half width, underside, topline
        (-2.10,.22,1.96,2.55),(-1.89,.40,1.86,2.72),(-1.60,.51,1.54,2.82),
        (-1.25,.655,1.23,2.97),(-.94,.74,1.23,3.03),(-.54,.77,1.26,2.91),
        (-.10,.78,1.31,2.81),(.36,.70,1.35,2.77),(.75,.64,1.44,2.79),
        (1.03,.68,1.48,2.83),(1.27,.64,1.54,2.79),(1.46,.49,1.71,2.69),
        (1.58,.29,1.91,2.55),(1.64,.05,2.16,2.36)])
    profile=PchipInterpolator(sections[:,0],sections[:,1:],axis=0)
    a=np.linspace(0,2*math.pi,84,endpoint=False)
    side=np.sign(np.cos(a))*np.abs(np.cos(a))**.87
    vertical=-np.sign(np.sin(a))*np.abs(np.sin(a))**.87
    rows=[]
    for y in np.linspace(sections[0,0],sections[-1,0],104):
        width,bottom,top=profile(y)
        shoulder=np.exp(-((y+.98)/.69)**2)
        bottom-=(chest_depth-1)*.72*shoulder
        mid=(top+bottom)*.5
        z=mid+vertical*(top-bottom)*.5
        # The dewlap grows directly out of the ventral neck.
        z-=.24*np.exp(-((y+1.59)/.45)**2)*np.maximum(-vertical,0)**13
        x=width*side*(1+(shoulder_width-1)*shoulder)
        blade=.067*np.exp(-((y+1.03-.29*(z-2.46))/.20)**2-((z-2.49)/.40)**2)
        hip=.053*np.exp(-((y-1.09)/.30)**2-((z-2.35)/.43)**2)
        x+=np.sign(x)*abs(side)**2*(blade+hip)
        rows.append(np.column_stack((x,np.full_like(x,y),z)))
    rings("Withers, rib cage and pelvis",rows)


def make_bones(bone):
    bone("Pelvis",(0,1.11,2.29),(0,.42,2.38))
    bone("Spine",(0,.42,2.38),(0,-.49,2.41),"Pelvis")
    bone("Chest",(0,-.49,2.41),(0,-1.10,2.43),"Spine")
    bone("Neck",(0,-1.10,2.43),(0,-1.92,2.42),"Chest")
    bone("Head",(0,-1.92,2.42),(0,-2.69,2.03),"Neck")
    bone("Tail",TAIL@Vector((0,.34,2.10)),TAIL@Vector((.43,.83,1.43)),"Pelvis")


def bind(vertices,bones,names):
    """Blend each leg into the barrel only inside its anatomical attachment."""
    x,y,z=vertices.T
    weights=np.zeros((len(vertices),len(names)))
    def ramp(value,low,high):
        t=np.clip((value-low)/(high-low),0,1)
        return t*t*(3-2*t)
    # Adjacent axial bones hand the skin across the length of the torso.
    remaining=np.ones(len(vertices))
    for name,low,high in (("Head",-2.08,-1.84),("Neck",-1.66,-1.27),
                          ("Chest",-.69,-.18),("Spine",.24,.85)):
        after=ramp(y,low,high)
        weights[:,names.index(name)]=remaining*(1-after)
        remaining*=after
    weights[:,names.index("Pelvis")]=remaining

    for label in TOUCHDOWN:
        chain=[segment+"."+label for segment in ("Upper","Lower","Cannon","Pastern","Foot")]
        joints=np.array([tuple(bones[name][0]) for name in chain])
        axis_y=np.interp(z,joints[::-1,2],joints[::-1,1])
        # Extend the leg's envelope above the shoulder/stifle into the flank.
        # Keep the underside between the legs attached to the spine.
        lateral=ramp(x*(1 if label.endswith("L") else -1),.06,.40)
        longitudinal=1-ramp(abs(y-axis_y),.20,.57)
        barrel_guard=ramp(y if label.startswith("Hind") else -y,.40,.90)
        influence=lateral*longitudinal*barrel_guard*(1-ramp(z,1.47,2.76))
        weights*=1-influence[:,None]
        remaining=influence
        for i,radius in enumerate((.21,.16,.080,.052)):
            pivot=joints[i+1,2]
            upper=ramp(z,pivot-radius,pivot+radius)
            weights[:,names.index(chain[i])]+=remaining*upper
            remaining=remaining*(1-upper)
        weights[:,names.index(chain[-1])]+=remaining
    indices=np.argsort(weights,axis=1)[:,-4:]
    selected=np.take_along_axis(weights,indices,axis=1)
    return indices,selected/selected.sum(axis=1)[:,None]


def walk_pose(t,bones):
    cycle=t*CYCLES
    phase=2*math.pi*cycle
    heading=Vector((0,-STRIDE*cycle,0))
    shift=heading+Vector((.036*math.sin(phase),0,-.028+.023*math.cos(2*phase)))
    rotate=lambda direction,a: Quaternion(Vector(direction),a)
    pitch=(1,0,0);roll=(0,1,0);yaw=(0,0,1)
    hip=rotate(roll,.022*math.sin(phase))@rotate(yaw,.034*math.sin(phase))
    chest=rotate(roll,-.024*math.sin(phase-.50))@rotate(pitch,.022*math.cos(2*phase))
    delta={"Pelvis":hip,"Spine":hip.slerp(chest,.50),"Chest":chest,
           "Neck":rotate(pitch,.044*math.cos(2*phase-.37)),
           "Head":rotate(pitch,.023*math.cos(2*phase-.58))@rotate(yaw,.021*math.sin(phase)),
           "Tail":rotate(yaw,.16*math.sin(phase-.70))@rotate(pitch,.048*math.cos(phase))}
    # Work out the actual shoulder and hip origins under the moving spine.
    origin={"Pelvis":bones["Pelvis"][0]+shift}
    for name in ("Spine","Chest"):
        parent=bones[name][2]
        origin[name]=origin[parent]+delta[parent]@(bones[name][0]-bones[parent][0])
    for label,touchdown in TOUCHDOWN.items():
        f=(cycle-touchdown)%1
        u=max(0.,(f-DUTY)/(1-DUTY))
        smooth=u**3*(10-15*u+6*u*u)
        arc=math.sin(math.pi*u)**2
        offset_y=STRIDE*(f-DUTY/2-smooth)
        upper,lower,cannon,pastern,hoof=[s+"."+label for s in ("Upper","Lower","Cannon","Pastern","Foot")]
        a,b,parent=bones[upper]
        c,d,_=bones[cannon]
        foot=bones[hoof][0]
        pivot=origin[parent]+delta[parent]@(a-bones[parent][0])
        tilt=rotate(pitch,(.24 if label.startswith("Hind") else -.20)*arc)
        toe_pitch=rotate(pitch,.11*arc*math.cos(math.pi*u))
        foot_goal=foot+heading+Vector((0,offset_y,.178*arc))
        target=foot_goal-tilt@(foot-c)
        axis=target-pivot
        reach=axis.length
        axis.normalize()
        pole=b-a
        pole=(pole-axis*pole.dot(axis)).normalized()
        first=(b-a).length
        second=(c-b).length
        along=(first*first-second*second+reach*reach)/(2*reach)
        if abs(along)>first+1e-5:
            raise ValueError(f"Unreachable {label} hoof at cycle phase {f:.3f}")
        bend=pivot+axis*along+pole*math.sqrt(max(0,first*first-along*along))
        delta[upper]=(b-a).rotation_difference(bend-pivot)
        delta[lower]=(c-b).rotation_difference(target-bend)
        delta[cannon]=tilt
        delta[pastern]=tilt
        delta[hoof]=toe_pitch
    return delta,shift

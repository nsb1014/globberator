"""Fit the catalog horn to the selected subject using visible 2D landmarks.

Landmark windows are the vision interpretation of the supplied lineup. Other
subjects need their own landmark annotation and anatomy recipe.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from horns import horn_profile

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("image",type=Path)
parser.add_argument("--landmarks",type=Path,default=root/"models/reference.json")
parser.add_argument("--recipe",type=Path,default=root/"models/minotaur.json")
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
land=json.loads(args.landmarks.read_text())
im=np.array(Image.open(args.image).convert("RGB").resize(tuple(land["image_size"])),dtype=float)
def tip(box):
    x,y,r,b=box
    py,px=np.where(im[y:b,x:r].mean(axis=2)<145)
    if not len(px):raise ValueError("No dark tip found in the annotated region")
    high=py<=py.min()+2
    return np.array([np.median(px[high])+x,py[high].mean()+y])

def edge(box,side):
    x,y,r,b=box
    # At each row, find the strongest RGB transition across the outer contour.
    gradient=np.linalg.norm(np.diff(im[y:b,x:r],axis=1),axis=2)
    edges=x+np.argmax(gradient,axis=1)
    return np.percentile(edges,20 if side=="left" else 80)
tips=np.array([tip(land[k+"_horn_tip_box"]) for k in ("left","right")])
edges=[edge(land[k+"_horn_edge_box"],k) for k in ("left","right")]
eye_y=np.mean([land["left_eye"][1],land["right_eye"][1]])
px_per_unit=(land["ground_y"]-eye_y)/(4.185-.025)
observed=np.array([(edges[1]-edges[0])/2,(tips[1,0]-tips[0,0])/2,eye_y-tips[:,1].mean()])
def predicted(v):
    keys=np.asarray(horn_profile(*v))
    sample=PchipInterpolator(np.arange(len(keys)),keys)(np.linspace(0,len(keys)-1,120))
    tangent=np.gradient(sample[:,:3],axis=0)
    norm=np.hypot(tangent[:,0],tangent[:,2]).clip(1e-9)
    outside=sample[:,0]+sample[:,3]*abs(tangent[:,2])/norm
    return px_per_unit*np.array([outside.max(),keys[-1,0],keys[-1,2]-4.185])
fit=least_squares(lambda v:predicted(v)-observed,[1.,1.],bounds=(.7,1.3))
recipe=json.loads(args.recipe.read_text())
for name,value in zip(("horn_span","horn_rise"),fit.x):recipe["shape"][name]=round(float(value),4)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(recipe,indent=2)+"\n")
print("Horn landmark RMS in pixels: initial %.2f, fitted %.2f" %
      tuple(np.mean((predicted(v)-observed)**2)**.5 for v in ([1.,1.],fit.x)))
print("Fitted span %.4f, rise %.4f" % tuple(fit.x))

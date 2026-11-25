"""Flat-ground footprint planning in body coordinates (+Y rear), independent of rig or mesh."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Step:
    phase: float
    swing: float
    back: float
    arc: float


class Gait:
    """Order feet by socket position. A planted foot cancels the body's forward travel."""

    def __init__(self, sockets):
        count = len(sockets)
        if count > 8:
            raise ValueError("Locomotion supports up to eight walking feet")
        self.count = count
        # A hop has a flight phase. A biped overlaps support. At a crawl, move
        # one foot at a time and leave a short all-feet-down weight transfer.
        if count < 2:
            self.duty = .58
        elif count == 2:
            self.duty = .60
        else:
            self.duty = 1-.80/count
        self.cycle_frames = max(32, 10*count)
        def rear_first(items):
            return sorted(items,key=lambda name:(-sockets[name][1],name))
        left = rear_first(n for n,p in sockets.items() if p[0] > 1e-5)
        right = rear_first(n for n,p in sockets.items() if p[0] < -1e-5)
        center = rear_first(set(sockets)-set(left)-set(right))
        # Follow a foot with a distant contralateral foot when one is available.
        split = len(right)//2
        right = right[split:]+right[:split]
        order = []
        for i in range(max(len(left),len(right))):
            order.extend(group[i] for group in (left,right) if i < len(group))
        order.extend(center)
        self.touchdown = {name:i/count for i,name in enumerate(order)}

    def profile(self,cycles,stride,legs):
        # Ship bindings and phases with the mesh so Godot can solve the actual
        # rig in real time. The standalone GLB also carries ordinary baked clips.
        return {"cycles":cycles,"stride":stride,"duty":self.duty,
                "legs":[dict(leg,touchdown=self.touchdown[name]) for name,leg in legs.items()]}

    def step(self,name,cycle,stride):
        phase = (cycle-self.touchdown[name])%1
        swing = max(0.,(phase-self.duty)/(1-self.duty))
        blend = swing**3*(10-15*swing+6*swing*swing)
        return Step(phase,swing,stride*(phase-self.duty/2-blend),math.sin(math.pi*swing)**2)

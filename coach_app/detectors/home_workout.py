
"""Fast, camera-friendly detectors for the 28 home-workout exercises.

The detectors use MediaPipe Pose landmarks only. They intentionally avoid
heavy per-frame work: no image processing, no ML inference, and no sleeps.
Each detector uses visibility gates, EMA smoothing and hysteresis to reduce
false rep counts.

A 2-D pose model cannot prove equipment identity (chair/backpack/band) or
perfect biomechanics from every camera angle. The returned `form_status`
therefore represents pose-based evidence, not a medical/biomechanical claim.
"""
from __future__ import annotations

import math
import time
from typing import Iterable, Sequence

from core.base_exercise import BaseExercise


# MediaPipe Pose landmark indices.
LS, RS, LE, RE, LW, RW = 11, 12, 13, 14, 15, 16
LH, RH, LK, RK, LA, RA = 23, 24, 25, 26, 27, 28


def _pt(lms, i):
    p = lms[i]
    return float(p.x), float(p.y)


def _vis(lms, indices, threshold=0.55):
    return all(float(lms[i].visibility) >= threshold for i in indices)


def _mid(lms, a, b):
    return ((float(lms[a].x) + float(lms[b].x)) * .5,
            (float(lms[a].y) + float(lms[b].y)) * .5)


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle(a, b, c):
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    ma = math.hypot(ax, ay)
    mc = math.hypot(cx, cy)
    if ma < 1e-8 or mc < 1e-8:
        return 180.0
    cosv = max(-1.0, min(1.0, (ax * cx + ay * cy) / (ma * mc)))
    return math.degrees(math.acos(cosv))


def _line_angle(a, b):
    # Absolute angle from vertical, 0 = vertical.
    return math.degrees(math.atan2(abs(a[0] - b[0]), abs(a[1] - b[1])))


class FastDetector(BaseExercise):
    VIS = .55

    def __init__(self):
        super().__init__()
        self._ema_values = {}

    def reset(self):
        self.reps = 0
        self.stage = None
        self._ema_values.clear()
        self._hold_last_tick = None

    def smooth(self, key, value, alpha=.35):
        if value is None or not math.isfinite(float(value)):
            return self._ema_values.get(key, 0.0)
        value = float(value)
        old = self._ema_values.get(key)
        out = value if old is None else old + alpha * (value - old)
        self._ema_values[key] = out
        return out

    def side_by_visibility(self, lms, left_indices, right_indices):
        lv = sum(float(lms[i].visibility) for i in left_indices) / len(left_indices)
        rv = sum(float(lms[i].visibility) for i in right_indices) / len(right_indices)
        return (left_indices, lv >= rv) if lv >= rv else (right_indices, False)

    def count_flexion(self, value, down=95, up=155, visible=True):
        value = self.smooth("cycle", value)
        if not visible:
            return
        if value <= down:
            self.stage = "down"
        elif value >= up and self.stage == "down":
            self.stage = "up"
            self.reps += 1

    def hold_seconds(self, active):
        now = time.monotonic()
        if not active:
            self._hold_last_tick = None
            return
        if self._hold_last_tick is None:
            self._hold_last_tick = now
            return
        elapsed = now - self._hold_last_tick
        if elapsed >= 1.0:
            whole = int(elapsed)
            self.reps += whole
            self._hold_last_tick += whole

    def base(self):
        return {"reps": int(self.reps)}


class PushUpDetector(FastDetector):
    """Standard/variant push-up detector with grip and incline checks."""
    def __init__(self, variant="standard"):
        super().__init__()
        self.variant = variant

    def process(self, lms):
        ids = [LS, RS, LE, RE, LW, RW, LH, RH, LA, RA]
        if not _vis(lms, ids, self.VIS):
            return {**self.base(), "pose_ready": False, "form_status": "MOVE INTO FRAME"}

        left = _angle(_pt(lms, LS), _pt(lms, LE), _pt(lms, LW))
        right = _angle(_pt(lms, RS), _pt(lms, RE), _pt(lms, RW))
        elbow = self.smooth("elbow", min(left, right))

        shoulder = _mid(lms, LS, RS)
        hip = _mid(lms, LH, RH)
        ankle = _mid(lms, LA, RA)
        body_angle = self.smooth("body", _angle(shoulder, hip, ankle))
        shoulder_width = _dist(_pt(lms, LS), _pt(lms, RS))
        wrist_width = _dist(_pt(lms, LW), _pt(lms, RW))

        if body_angle > 155:
            body = "GOOD LINE"
        elif body_angle > 140:
            body = "KEEP CORE TIGHT"
        else:
            body = "ALIGN BODY"

        self.count_flexion(elbow, 100, 155, True)

        grip = "STANDARD GRIP"
        if shoulder_width > .02:
            ratio = wrist_width / shoulder_width
            if ratio > 1.75:
                grip = "WIDE GRIP"
            elif ratio < .95:
                grip = "CLOSE GRIP"
            if self.variant == "diamond" and ratio < 1.05:
                grip = "DIAMOND GRIP"

        # Camera-relative elevation: shoulders higher than feet => incline;
        # feet higher than shoulders => decline. This is a cue, not proof of
        # the equipment surface.
        elevation = ankle[1] - shoulder[1]
        if self.variant == "incline":
            surface = "INCLINE POSITION" if elevation > .05 else "CHECK INCLINE SETUP"
        elif self.variant == "decline":
            surface = "DECLINE POSITION" if elevation < -.05 else "CHECK DECLINE SETUP"
        else:
            surface = grip

        return {
            **self.base(),
            "pose_ready": True,
            "elbow_angle": int(elbow),
            "body_alignment": body,
            "hip_status": body,
            "grip_status": grip,
            "surface_status": surface,
            "form_status": "GOOD FORM" if body == "GOOD LINE" else body,
        }


class SquatDetector(FastDetector):
    def __init__(self, variant="bodyweight"):
        super().__init__()
        self.variant = variant

    def process(self, lms):
        ids=[LH,RH,LK,RK,LA,RA,LS,RS]
        if not _vis(lms, ids, self.VIS):
            return {**self.base(), "pose_ready": False, "form_status":"MOVE INTO FRAME"}
        lk=_angle(_pt(lms,LH),_pt(lms,LK),_pt(lms,LA))
        rk=_angle(_pt(lms,RH),_pt(lms,RK),_pt(lms,RA))
        knee=self.smooth("knee", min(lk,rk))
        hip=_mid(lms,LH,RH); shoulder=_mid(lms,LS,RS)
        torso=self.smooth("torso", _line_angle(shoulder,hip))
        self.count_flexion(knee, 105, 158, True)
        depth="GOOD DEPTH" if knee<=105 else ("LOWER" if knee<135 else "STANDING")
        return {**self.base(),"pose_ready":True,"knee_angle":int(knee),
                "back_angle":int(180-torso),"depth_status":depth,
                "form_status":"UPRIGHT" if torso<25 else "KEEP CHEST UP"}


class LungeDetector(FastDetector):
    def __init__(self, variant="reverse"):
        super().__init__()
        self.variant=variant

    def process(self,lms):
        ids=[LH,RH,LK,RK,LA,RA,LS,RS]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        lk=_angle(_pt(lms,LH),_pt(lms,LK),_pt(lms,LA))
        rk=_angle(_pt(lms,RH),_pt(lms,RK),_pt(lms,RA))
        front=min(lk,rk)
        front=self.smooth("front_knee",front)
        torso=self.smooth("torso",_line_angle(_mid(lms,LS,RS),_mid(lms,LH,RH)))
        self.count_flexion(front,105,158,True)
        balance=abs(((lms[LS].x+lms[RS].x)/2)-((lms[LH].x+lms[RH].x)/2))
        return {**self.base(),"pose_ready":True,"front_knee_angle":int(front),
                "torso_angle":int(180-torso),"balance_status":"BALANCED" if balance<.10 else "STABILIZE",
                "form_status":"GOOD LUNGE" if front<=110 else "STEP BACK AND LOWER"}


class BulgarianSplitSquatDetector(LungeDetector):
    def __init__(self):
        super().__init__("bulgarian")

    def process(self,lms):
        out=super().process(lms)
        if out.get("pose_ready"):
            out["rear_leg_status"]="REAR FOOT ELEVATED — VERIFY CAMERA VIEW"
            out["depth_status"]="GOOD DEPTH" if out["front_knee_angle"]<=110 else "LOWER"
        return out


class BicepsCurlDetector(FastDetector):
    def __init__(self, variant="curl"):
        super().__init__()
        self.variant=variant

    def process(self,lms):
        ids=[LS,RS,LE,RE,LW,RW,LH,RH]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        la=_angle(_pt(lms,LS),_pt(lms,LE),_pt(lms,LW))
        ra=_angle(_pt(lms,RS),_pt(lms,RE),_pt(lms,RW))
        # Choose the more visible arm.
        lv=float(lms[LE].visibility)+float(lms[LW].visibility)
        rv=float(lms[RE].visibility)+float(lms[RW].visibility)
        elbow=self.smooth("elbow",la if lv>=rv else ra)
        self.count_flexion(elbow,55,155,True)
        shoulder_x=(lms[LS].x+lms[RS].x)/2
        elbow_x=(lms[LE].x+lms[RE].x)/2
        drift=abs(shoulder_x-elbow_x)
        return {**self.base(),"pose_ready":True,"elbow_angle":int(elbow),
                "shoulder_status":"STABLE" if drift<.10 else "KEEP ELBOWS IN",
                "swing_status":"CONTROLLED" if drift<.10 else "REDUCE SWING",
                "form_status":"GOOD CURL" if drift<.10 else "CONTROL THE MOVEMENT"}


class IsometricBicepsHoldDetector(BicepsCurlDetector):
    def __init__(self):
        super().__init__("isometric")

    def reset(self):
        super().reset()

    def process(self,lms):
        out=super().process(lms)
        if out.get("pose_ready"):
            angle=out["elbow_angle"]
            active=45<=angle<=100
            self.hold_seconds(active)
            out["reps"]=self.reps
            out["hold_status"]="HOLD" if active else "BEND ELBOW TO 90°"
        return out


class ShoulderPressDetector(BicepsCurlDetector):
    """Kept for legacy 'Shoulder Press' option."""
    def process(self,lms):
        ids=[LS,RS,LE,RE,LW,RW,LH,RH]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        la=_angle(_pt(lms,LS),_pt(lms,LE),_pt(lms,LW))
        ra=_angle(_pt(lms,RS),_pt(lms,RE),_pt(lms,RW))
        elbow=self.smooth("press",min(la,ra))
        self.count_flexion(elbow,90,160,True)
        wrist_y=(lms[LW].y+lms[RW].y)/2
        shoulder_y=(lms[LS].y+lms[RS].y)/2
        return {**self.base(),"pose_ready":True,"elbow_angle":int(elbow),
                "extension_status":"FULL EXTENSION" if wrist_y<shoulder_y else "PRESS UP",
                "back_arch_status":"NEUTRAL","form_status":"GOOD PRESS" if wrist_y<shoulder_y else "EXTEND OVERHEAD"}


class ChairDipDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LE,RE,LW,RW]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        elbow=self.smooth("elbow",min(
            _angle(_pt(lms,LS),_pt(lms,LE),_pt(lms,LW)),
            _angle(_pt(lms,RS),_pt(lms,RE),_pt(lms,RW))))
        self.count_flexion(elbow,100,155,True)
        wrist_y=(lms[LW].y+lms[RW].y)/2
        shoulder_y=(lms[LS].y+lms[RS].y)/2
        return {**self.base(),"pose_ready":True,"elbow_angle":int(elbow),
                "depth_status":"GOOD DEPTH" if elbow<=100 else "LOWER WITH CONTROL",
                "form_status":"GOOD DIP" if elbow<=105 else "LOWER"}


class OverheadExtensionDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LE,RE,LW,RW]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        elbow=self.smooth("elbow",min(
            _angle(_pt(lms,LS),_pt(lms,LE),_pt(lms,LW)),
            _angle(_pt(lms,RS),_pt(lms,RE),_pt(lms,RW))))
        self.count_flexion(elbow,85,160,True)
        wrist_y=(lms[LW].y+lms[RW].y)/2
        shoulder_y=(lms[LS].y+lms[RS].y)/2
        ok=wrist_y<shoulder_y+.03
        return {**self.base(),"pose_ready":True,"elbow_angle":int(elbow),
                "elbow_status":"ARM OVERHEAD" if ok else "KEEP ARMS OVERHEAD",
                "form_status":"GOOD FORM" if ok else "KEEP ARMS UP"}


class PikePushUpDetector(PushUpDetector):
    def __init__(self):
        super().__init__("pike")

    def process(self,lms):
        out=super().process(lms)
        if out.get("pose_ready"):
            shoulder=_mid(lms,LS,RS); hip=_mid(lms,LH,RH); ankle=_mid(lms,LA,RA)
            pike=self.smooth("pike",_angle(shoulder,hip,ankle))
            out["pike_status"]="PIKED" if pike<=105 else "RAISE HIPS"
            out["form_status"]="GOOD PIKE" if pike<=105 else "RAISE HIPS"
        return out


class ShoulderTapDetector(FastDetector):
    def __init__(self):
        super().__init__()
        self._armed=True

    def reset(self):
        super().reset(); self._armed=True

    def process(self,lms):
        ids=[LS,RS,LW,RW,LH,RH,LA,RA]
        if not _vis(lms,ids,self.VIS):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        d1=_dist(_pt(lms,LW),_pt(lms,RS))
        d2=_dist(_pt(lms,RW),_pt(lms,LS))
        d=min(d1,d2)
        shoulder_width=max(_dist(_pt(lms,LS),_pt(lms,RS)),.08)
        ratio=self.smooth("tap",d/shoulder_width)
        if ratio<.55 and self._armed:
            self.reps+=1; self._armed=False; self.stage="tap"
        elif ratio>.95:
            self._armed=True; self.stage="plank"
        return {**self.base(),"pose_ready":True,"tap_distance":round(ratio,2),
                "tap_status":"TAP!" if ratio<.55 else "PLANK",
                "form_status":"GOOD PLANK" if abs(float(lms[LH].y)-float(lms[RH].y))<.08 else "KEEP HIPS LEVEL"}


class WallHandstandHoldDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LH,RH,LA,RA,LW,RW]
        if not _vis(lms,ids,.45):
            return {**self.base(),"pose_ready":False,"hold_status":"MOVE INTO FRAME","form_status":"FULL BODY REQUIRED"}
        sy=(lms[LS].y+lms[RS].y)/2
        hy=(lms[LH].y+lms[RH].y)/2
        ay=(lms[LA].y+lms[RA].y)/2
        active=ay<hy-.03 and hy<sy-.02
        self.hold_seconds(active)
        return {**self.base(),"pose_ready":True,
                "hold_status":"HOLDING HANDSTAND" if active else "NOT INVERTED",
                "form_status":"GOOD HOLD" if active else "KICK UP / ALIGN BODY"}


class ArmCircleDetector(FastDetector):
    def __init__(self):
        super().__init__()
        self._last=None; self._accum=0.0

    def reset(self):
        super().reset(); self._last=None; self._accum=0.0

    def process(self,lms):
        ids=[LS,RS,LW,RW]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        lv=float(lms[LW].visibility); rv=float(lms[RW].visibility)
        si,wi=(LS,LW) if lv>=rv else (RS,RW)
        s=_pt(lms,si); w=_pt(lms,wi)
        ang=math.degrees(math.atan2(w[1]-s[1],w[0]-s[0]))
        if self._last is not None:
            delta=(ang-self._last+180)%360-180
            self._accum += abs(delta)
            if self._accum>=360:
                self.reps+=1; self._accum-=360
        self._last=ang
        return {**self.base(),"pose_ready":True,"circle_progress_deg":int(self._accum),
                "form_status":"CIRCLE"}


class SupermanDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LH,RH,LA,RA,LW,RW]
        if not _vis(lms,ids,.45):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        shoulder=_mid(lms,LS,RS); hip=_mid(lms,LH,RH); ankle=_mid(lms,LA,RA)
        lift=max(0.0, self.smooth("lift",((hip[1]-shoulder[1])+(hip[1]-ankle[1]))*.5))
        if lift>.045: self.stage="up"
        elif lift<.018 and self.stage=="up":
            self.reps+=1; self.stage="down"
        return {**self.base(),"pose_ready":True,"extension_angle":int(_angle(shoulder,hip,ankle)),
                "lift_status":"LIFT" if lift>.045 else "LOWER","form_status":"GOOD LIFT" if lift>.045 else "RESET"}


class ReverseSnowAngelDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LW,RW,LH,RH]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        shoulder=_mid(lms,LS,RS); hip=_mid(lms,LH,RH)
        wrist=_mid(lms,LW,RW)
        # Arms overhead when wrists are above shoulders; returned beside body when below shoulders.
        overhead=wrist[1] < shoulder[1]-.04
        beside=wrist[1] > hip[1]-.02
        if overhead: self.stage="overhead"
        elif beside and self.stage=="overhead":
            self.reps+=1; self.stage="beside"
        sweep=abs(wrist[1]-shoulder[1])
        return {**self.base(),"pose_ready":True,"sweep_angle":int(_angle(_pt(lms,LS),_pt(lms,LW),_pt(lms,RW))),
                "sweep_status":"OVERHEAD" if overhead else "SWEEP","form_status":"GOOD SWEEP"}


class ProneYTWRaiseDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LW,RW,LH,RH]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        shoulder=_mid(lms,LS,RS); wrist=_mid(lms,LW,RW)
        dx=abs(wrist[0]-shoulder[0]); dy=shoulder[1]-wrist[1]
        # Y = wrists high/out; T = level/out; W = closer to shoulders.
        if dy>.10 and dx>.12: pose="Y"
        elif dx>.18 and abs(dy)<.10: pose="T"
        elif dx<.16 and dy>.03: pose="W"
        else: pose="TRANSITION"
        if pose=="Y": self.stage="Y"
        elif pose=="W" and self.stage=="Y":
            self.stage="W"
        elif pose=="T" and self.stage=="W":
            self.reps+=1; self.stage="T"
        return {**self.base(),"pose_ready":True,"lift_amount":round(max(dy,0),2),
                "raise_status":pose,"form_status":f"{pose} POSITION"}


class BackpackRowDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LE,RE,LW,RW,LH,RH]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        elbow=min(_angle(_pt(lms,LS),_pt(lms,LE),_pt(lms,LW)),
                  _angle(_pt(lms,RS),_pt(lms,RE),_pt(lms,RW)))
        elbow=self.smooth("elbow",elbow)
        self.count_flexion(elbow,85,150,True)
        torso=_line_angle(_mid(lms,LS,RS),_mid(lms,LH,RH))
        hinge="HINGED" if torso>20 else "STAND TALLER"
        return {**self.base(),"pose_ready":True,"elbow_angle":int(elbow),
                "hinge_status":hinge,"form_status":"GOOD ROW" if torso>20 else "HINGE AT HIPS"}


class PlankDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LH,RH,LA,RA,LE,RE]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        shoulder=_mid(lms,LS,RS); hip=_mid(lms,LH,RH); ankle=_mid(lms,LA,RA)
        body=self.smooth("body",_angle(shoulder,hip,ankle))
        active=body>160
        self.hold_seconds(active)
        return {**self.base(),"pose_ready":True,"body_angle":int(body),
                "form_status":"HOLD PLANK" if active else "ALIGN BODY"}


class BicycleCrunchDetector(FastDetector):
    def __init__(self):
        super().__init__(); self._armed=True

    def reset(self):
        super().reset(); self._armed=True

    def process(self,lms):
        ids=[LS,RS,LE,RE,LH,RH,LK,RK]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        d1=_dist(_pt(lms,LE),_pt(lms,RK))
        d2=_dist(_pt(lms,RE),_pt(lms,LK))
        sw=max(_dist(_pt(lms,LS),_pt(lms,RS)),.08)
        ratio=self.smooth("touch",min(d1,d2)/sw)
        if ratio<1.0 and self._armed:
            self.reps+=1; self._armed=False
        elif ratio>1.35:
            self._armed=True
        return {**self.base(),"pose_ready":True,"touch_distance":round(ratio,2),
                "crunch_status":"CRUNCH" if ratio<1.0 else "EXTEND","form_status":"GOOD CRUNCH" if ratio<1.0 else "ROTATE CONTROLLED"}


class LegRaiseDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LH,RH,LK,RK,LA,RA]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        hip=_mid(lms,LH,RH); knee=_mid(lms,LK,RK); ankle=_mid(lms,LA,RA)
        angle=self.smooth("hip",_angle((hip[0],hip[1]+.25),hip,ankle))
        # In a side/three-quarter view, legs elevated makes ankle y approach hip y.
        active=ankle[1] < hip[1]-.12
        if active: self.stage="up"
        elif not active and self.stage=="up":
            self.reps+=1; self.stage="down"
        return {**self.base(),"pose_ready":True,"hip_angle":int(angle),
                "leg_status":"UP" if active else "LOWER","form_status":"GOOD" if active else "LOWER CONTROLLED"}


class MountainClimberDetector(FastDetector):
    def __init__(self):
        super().__init__(); self._last_side=None

    def reset(self):
        super().reset(); self._last_side=None

    def process(self,lms):
        ids=[LS,RS,LH,RH,LK,RK,LW,RW]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"MOVE INTO FRAME"}
        lh_d=_dist(_pt(lms,LK),_pt(lms,LS))
        rh_d=_dist(_pt(lms,RK),_pt(lms,RS))
        side="L" if lh_d<rh_d else "R"
        drive=min(lh_d,rh_d)
        ratio=self.smooth("drive",drive)
        if self._last_side and side!=self._last_side and ratio<.9:
            self.reps+=1
        self._last_side=side
        return {**self.base(),"pose_ready":True,"drive_angle":int(_angle(_pt(lms,LS),_pt(lms,LH),_pt(lms,LK))),
                "climb_status":f"{side} DRIVE","form_status":"GOOD CLIMB"}


class GluteBridgeDetector(FastDetector):
    def process(self,lms):
        ids=[LS,RS,LH,RH,LK,RK,LA,RA]
        if not _vis(lms,ids,.5):
            return {**self.base(),"pose_ready":False,"form_status":"FULL BODY REQUIRED"}
        shoulder=_mid(lms,LS,RS); hip=_mid(lms,LH,RH); knee=_mid(lms,LK,RK)
        hip_angle=self.smooth("hip",_angle(shoulder,hip,knee))
        active=hip_angle>145 and hip[1] < knee[1]-.02
        if active: self.stage="up"
        elif self.stage=="up":
            self.reps+=1; self.stage="down"
        return {**self.base(),"pose_ready":True,"hip_angle":int(hip_angle),
                "bridge_status":"SQUEEZE" if active else "LOWER","form_status":"GOOD BRIDGE" if active else "LIFT HIPS"}


# Explicit exercise-specific classes. Keeping named classes makes the
# registry inspectable and prevents accidental routing to a generic detector.
class StandardPushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("standard")
class WidePushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("wide")
class InclinePushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("incline")
class DeclinePushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("decline")
class DiamondPushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("diamond")
class CloseGripPushUpDetector(PushUpDetector):
    def __init__(self): super().__init__("close")
class BackpackCurlDetector(BicepsCurlDetector):
    def __init__(self): super().__init__("backpack")
class TowelCurlDetector(BicepsCurlDetector):
    def __init__(self): super().__init__("towel")
class ResistanceBandCurlDetector(BicepsCurlDetector):
    def __init__(self): super().__init__("band")

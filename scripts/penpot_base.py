#!/usr/bin/env python3
"""
Penpot API base helpers for building app screens.
Shared across all app builders (Pulse, Cents, Savor).
"""
import requests, json, uuid, sys, time

BASE = "https://penpot.jakeberrimor.com/api/rpc/command"
EXPORT_URL = "https://penpot.jakeberrimor.com/api/export"
H = {"Content-Type": "application/transit+json"}
FILE_ID = "4b85babb-b10c-8109-8007-b44132d2992f"
PAGE_ID = "4b85babb-b10c-8109-8007-b44132d29930"

TF = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}

def uid(): return str(uuid.uuid4())

def sr(x,y,w,h):
    return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,
            "~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}

def pts(x,y,w,h):
    return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},
            {"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]

def fill(c, a=1.0):
    return {"~:fill-color":c,"~:fill-opacity":a}

def find(arr, key):
    if not isinstance(arr, list): return None
    for i,v in enumerate(arr):
        if v==key and i+1<len(arr): return arr[i+1]
    return None

class PenpotSession:
    def __init__(self):
        self.s = requests.Session()
        self.revn = 0
        self.profile_id = None
        self._login()
    
    def _login(self):
        r = self.s.post(f"{BASE}/login-with-password", headers=H,
            data='["^ ","~:email","spam@jakeberrimor.com","~:password","q25RiI#L"]')
        self.profile_id = find(r.json(), "~:id")
        if self.profile_id:
            self.profile_id = self.profile_id.replace("~u","")
        # Get current revn
        r = self.s.post(f"{BASE}/update-file", headers=H,
            data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:revn",0,"~:vern",0,
                             "~:session-id",f"~u{uid()}","~:changes",[]]))
        self.revn = find(r.json(),"~:revn") or 0
        print(f"Logged in. revn={self.revn}")
    
    def add(self, obj, fid, pid):
        oid = obj["~:id"].replace("~u","")
        r = self.s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
            ["^ ","~:id",f"~u{FILE_ID}","~:revn",self.revn,"~:vern",0,
             "~:session-id",f"~u{uid()}",
             "~:changes",[["^ ","~:type","~:add-obj","~:id",f"~u{oid}",
                 "~:frame-id",f"~u{fid}","~:parent-id",f"~u{pid}",
                 "~:page-id",f"~u{PAGE_ID}","~:index",9999,"~:obj",obj]]]))
        res = r.json()
        self.revn = find(res,"~:revn") or self.revn+1
        err = find(res,"~:explain")
        if err:
            print(f"  ERR add {obj.get('~:name','?')}: {str(err)[:100]}")
            return False
        return True
    
    def add_batch(self, changes):
        """Add multiple objects in a single API call."""
        if not changes:
            return True
        r = self.s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
            ["^ ","~:id",f"~u{FILE_ID}","~:revn",self.revn,"~:vern",0,
             "~:session-id",f"~u{uid()}",
             "~:changes",changes]))
        res = r.json()
        self.revn = find(res,"~:revn") or self.revn+1
        err = find(res,"~:explain")
        if err:
            print(f"  ERR batch: {str(err)[:200]}")
            return False
        return True
    
    def mod(self, obj_id, attrs):
        """Modify existing object attributes."""
        r = self.s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
            ["^ ","~:id",f"~u{FILE_ID}","~:revn",self.revn,"~:vern",0,
             "~:session-id",f"~u{uid()}",
             "~:changes",[["^ ","~:type","~:mod-obj","~:id",f"~u{obj_id}",
                 "~:page-id",f"~u{PAGE_ID}","~:operations",
                 [["^ ","~:type","~:set"] + [item for kv in attrs.items() for item in (f"~:{kv[0]}", kv[1])]]
             ]]]))
        res = r.json()
        self.revn = find(res,"~:revn") or self.revn+1
        err = find(res,"~:explain")
        if err:
            print(f"  ERR mod {obj_id}: {str(err)[:100]}")
            return False
        return True
    
    def export_png(self, obj_id, name, scale=2):
        """Export object as PNG, return local file path."""
        item = ["^ ","~:type","~:png","~:scale",scale,"~:suffix","","~:name",name,
                "~:file-id",f"~u{FILE_ID}","~:page-id",f"~u{PAGE_ID}",
                "~:object-id",f"~u{obj_id}"]
        payload = json.dumps(["^ ","~:cmd","~:export-shapes",
                              "~:profile-id",f"~u{self.profile_id}",
                              "~:wait",True,
                              "~:file-id",f"~u{FILE_ID}","~:exports",[item]])
        r = self.s.post(EXPORT_URL, headers=H, data=payload, timeout=60)
        if r.status_code != 200:
            print(f"  Export failed: {r.status_code}")
            return None
        res = r.json()
        uri_obj = find(res, "~:uri")
        if isinstance(uri_obj, dict):
            img_url = uri_obj.get("~#uri","")
        else:
            img_url = str(uri_obj) if uri_obj else ""
        if not img_url:
            print(f"  Export: no URI in response")
            return None
        img = self.s.get(img_url)
        path = f"/tmp/{name}.png"
        with open(path,"wb") as f:
            f.write(img.content)
        print(f"  Exported {name}: {len(img.content)//1024}KB → {path}")
        return path


class ScreenBuilder:
    """Builds a single 390x844 screen with helper methods."""
    
    def __init__(self, ps, name, x, y, bg_color):
        self.ps = ps  # PenpotSession
        self.name = name
        self.x = x
        self.y = y
        self.w = 390
        self.h = 844
        self.bg = bg_color
        self.fid = uid()  # artboard id
        self.changes = []
        
        # Create the artboard
        obj = {"~:id":f"~u{self.fid}","~:type":"~:frame","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{PAGE_ID}",
               "~:x":x,"~:y":y,"~:width":self.w,"~:height":self.h,
               "~:fills":[fill(bg_color)],"~:clip-content":True,
               "~:selrect":sr(x,y,self.w,self.h),"~:points":pts(x,y,self.w,self.h),
               "~:transform":TF,"~:transform-inverse":TF,"~:shapes":[]}
        self._add_change(obj, PAGE_ID, PAGE_ID)
    
    def _add_change(self, obj, fid, pid):
        oid = obj["~:id"].replace("~u","")
        self.changes.append(["^ ","~:type","~:add-obj","~:id",f"~u{oid}",
            "~:frame-id",f"~u{fid}","~:parent-id",f"~u{pid}",
            "~:page-id",f"~u{PAGE_ID}","~:index",9999,"~:obj",obj])
    
    def flush(self):
        """Send all accumulated changes in one batch."""
        if not self.changes:
            return
        # Split into chunks of 50 changes max
        chunk_size = 50
        for i in range(0, len(self.changes), chunk_size):
            chunk = self.changes[i:i+chunk_size]
            ok = self.ps.add_batch(chunk)
            if not ok:
                print(f"  WARN: batch {i//chunk_size} had errors")
        self.changes = []
        print(f"  Flushed screen {self.name}")
    
    def mkframe(self, name, rx, ry, rw, rh, parent=None, bg=None, r_=0, 
                stroke=None, stroke_w=1, opacity=1.0, clip=False, shadow=None):
        """Create a subframe. rx,ry relative to screen. Returns frame id."""
        fid = uid()
        ax, ay = self.x + rx, self.y + ry
        obj = {"~:id":f"~u{fid}","~:type":"~:frame","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":rw,"~:height":rh,
               "~:fills":[fill(bg, opacity)] if bg else [],
               "~:clip-content":clip,
               "~:selrect":sr(ax,ay,rw,rh),"~:points":pts(ax,ay,rw,rh),
               "~:transform":TF,"~:transform-inverse":TF,"~:shapes":[]}
        if r_:
            obj["~:r1"]=obj["~:r2"]=obj["~:r3"]=obj["~:r4"]=r_
        if stroke:
            obj["~:strokes"]=[{"~:stroke-color":stroke,"~:stroke-opacity":1.0,
                               "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
                               "~:stroke-alignment":"~:inner"}]
        if shadow:
            obj["~:shadow"] = shadow
        self._add_change(obj, self.fid, parent or self.fid)
        return fid
    
    def rect(self, name, rx, ry, rw, rh, color, parent=None, r_=0, 
             opacity=1.0, stroke=None, stroke_w=1):
        """Add a rectangle. rx,ry relative to screen."""
        ax, ay = self.x + rx, self.y + ry
        oid = uid()
        obj = {"~:id":f"~u{oid}","~:type":"~:rect","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":rw,"~:height":rh,
               "~:fills":[fill(color, opacity)],
               "~:selrect":sr(ax,ay,rw,rh),"~:points":pts(ax,ay,rw,rh),
               "~:transform":TF,"~:transform-inverse":TF}
        if r_:
            obj["~:r1"]=obj["~:r2"]=obj["~:r3"]=obj["~:r4"]=r_
        if stroke:
            obj["~:strokes"]=[{"~:stroke-color":stroke,"~:stroke-opacity":1.0,
                               "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
                               "~:stroke-alignment":"~:inner"}]
        self._add_change(obj, self.fid, parent or self.fid)
        return oid
    
    def circle(self, name, rx, ry, d, color, parent=None, opacity=1.0, stroke=None, stroke_w=1):
        """Add a circle. rx,ry relative to screen. d=diameter."""
        ax, ay = self.x + rx, self.y + ry
        oid = uid()
        obj = {"~:id":f"~u{oid}","~:type":"~:circle","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":d,"~:height":d,
               "~:fills":[fill(color, opacity)],
               "~:selrect":sr(ax,ay,d,d),"~:points":pts(ax,ay,d,d),
               "~:transform":TF,"~:transform-inverse":TF}
        if stroke:
            obj["~:strokes"]=[{"~:stroke-color":stroke,"~:stroke-opacity":1.0,
                               "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
                               "~:stroke-alignment":"~:center"}]
        self._add_change(obj, self.fid, parent or self.fid)
        return oid

    def text(self, name, rx, ry, rw, txt, fs=14, fw="400", color="#000000",
             align="left", parent=None, opacity=1.0, ff="Inter"):
        """Add text. Uses old formula positioning - NO vertical-align center at artboard level."""
        ax, ay = self.x + rx, self.y + ry
        th = fs  # tight height
        oid = uid()
        obj = {"~:id":f"~u{oid}","~:type":"~:text","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":rw,"~:height":th,
               "~:fills":[],"~:selrect":sr(ax,ay,rw,th),"~:points":pts(ax,ay,rw,th),
               "~:transform":TF,"~:transform-inverse":TF,
               "~:content":{"~:type":"root","~:children":[
                   {"~:type":"paragraph-set","~:children":[
                       {"~:type":"paragraph","~:text-align":align,"~:paragraph-spacing":0,
                        "~:children":[{"~:text":txt,"~:font-size":str(fs),
                                       "~:font-family":ff,"~:font-weight":str(fw),
                                       "~:line-height":"1.4",
                                       "~:fills":[fill(color, opacity)]}]}]}]}}
        self._add_change(obj, self.fid, parent or self.fid)
        return oid
    
    def text_centered(self, name, rx, ry, rw, rh, txt, fs=14, fw="400", color="#000000",
                      align="center", parent=None, opacity=1.0, ff="Inter"):
        """Text vertically centered in container using OLD FORMULA.
        rx,ry,rw,rh = container bounds relative to screen.
        Uses: ty = cy + (ch - fs*1.4)/2, height=fs*2
        """
        cy = ry
        ch = rh
        ty = cy + (ch - fs * 1.4) / 2
        ax, ay = self.x + rx, self.y + ty
        th = fs * 2
        oid = uid()
        obj = {"~:id":f"~u{oid}","~:type":"~:text","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":rw,"~:height":th,
               "~:fills":[],"~:selrect":sr(ax,ay,rw,th),"~:points":pts(ax,ay,rw,th),
               "~:transform":TF,"~:transform-inverse":TF,
               "~:content":{"~:type":"root","~:children":[
                   {"~:type":"paragraph-set","~:children":[
                       {"~:type":"paragraph","~:text-align":align,"~:paragraph-spacing":0,
                        "~:children":[{"~:text":txt,"~:font-size":str(fs),
                                       "~:font-family":ff,"~:font-weight":str(fw),
                                       "~:line-height":"1.4",
                                       "~:fills":[fill(color, opacity)]}]}]}]}}
        self._add_change(obj, self.fid, parent or self.fid)
        return oid
    
    def text_in_frame(self, name, rx, ry, rw, rh, txt, fs=14, fw="400", color="#000000",
                      align="center", parent=None, opacity=1.0, ff="Inter"):
        """Text with va="center" INSIDE a non-artboard subframe (safe to use va here)."""
        ax, ay = self.x + rx, self.y + ry
        oid = uid()
        obj = {"~:id":f"~u{oid}","~:type":"~:text","~:name":name,
               "~:frame-id":f"~u{self.fid}","~:parent-id":f"~u{parent or self.fid}",
               "~:x":ax,"~:y":ay,"~:width":rw,"~:height":rh,
               "~:fills":[],"~:grow-type":"~:fixed",
               "~:selrect":sr(ax,ay,rw,rh),"~:points":pts(ax,ay,rw,rh),
               "~:transform":TF,"~:transform-inverse":TF,
               "~:content":{"~:type":"root","~:vertical-align":"center",
                            "~:children":[
                   {"~:type":"paragraph-set","~:children":[
                       {"~:type":"paragraph","~:text-align":align,"~:paragraph-spacing":0,
                        "~:children":[{"~:text":txt,"~:font-size":str(fs),
                                       "~:font-family":ff,"~:font-weight":str(fw),
                                       "~:line-height":"1.4",
                                       "~:fills":[fill(color, opacity)]}]}]}]}}
        self._add_change(obj, self.fid, parent or self.fid)
        return oid
    
    def chip(self, name, rx, ry, w, h, txt, fs=11, fw="500", bg_color="#F3F4F6",
             text_color="#52525B", parent=None, r_=16):
        """Create a chip/pill with proper centering using OLD FORMULA."""
        fid = self.mkframe(f"{name}", rx, ry, w, h, parent=parent, bg=bg_color, r_=r_)
        # OLD FORMULA: ty = container_y + (container_h - fs * 1.4) / 2
        self.text_centered(f"{name}_t", rx, ry, w, h, txt, fs=fs, fw=fw,
                          color=text_color, align="center", parent=fid)
        return fid
    
    def icon(self, name, rx, ry, ps, color, parent=None, stroke_w=None):
        """Place a Lucide icon."""
        ax, ay = self.x + rx, self.y + ry
        sys.path.insert(0, "/home/clawdbot/.openclaw/workspace/scripts")
        from lucide_penpot import penpot_icon
        return penpot_icon(name, ax, ay, ps, color,
                          stroke_w=stroke_w,
                          frame_id=self.fid, parent_id=parent or self.fid,
                          add_fn=lambda obj, fid, pid: self._add_change(obj, fid, pid))
    
    def status_bar(self, time_str="9:41", color="#000000"):
        """iOS status bar."""
        self.text("status_time", 30, 14, 50, time_str, fs=15, fw="600", color=color)
        # Signal dots
        for i in range(4):
            h = 4 + i*2
            self.rect(f"signal_{i}", 308+i*6, 20-h, 4, h, color, r_=1)
        # Battery
        self.rect("battery_outer", 340, 14, 25, 11, color, r_=3, opacity=0.0, stroke=color, stroke_w=1)
        self.rect("battery_fill", 342, 16, 18, 7, color, r_=2)
        self.rect("battery_tip", 366, 18, 2, 5, color, r_=1)
    
    def nav_bar(self, items, active_idx=0, bg_color="#FFFFFF", active_color="#4F46E5",
                inactive_color="#9CA3AF", y_pos=790):
        """Bottom navigation bar. items = list of (icon_name, label) tuples."""
        nav_fid = self.mkframe("Nav Bar", 0, y_pos, 390, 54, bg=bg_color)
        # Top border
        self.rect("nav_border", 0, y_pos, 390, 1, inactive_color, parent=nav_fid, opacity=0.2)
        
        slot_w = 390 // len(items)
        for i, (icon_name, label) in enumerate(items):
            col = active_color if i == active_idx else inactive_color
            sx = i * slot_w
            slot_fid = self.mkframe(f"Nav/{label}", sx, y_pos+1, slot_w, 53, parent=nav_fid)
            # Icon
            icon_x = sx + (slot_w - 24) // 2
            self.icon(icon_name, icon_x, y_pos + 8, 24, col, parent=slot_fid)
            # Label
            self.text(f"nav_{label}", sx, y_pos + 35, slot_w, label, fs=10, fw="500",
                     color=col, align="center", parent=slot_fid)
        return nav_fid
    
    def shadow_card(self):
        """Return shadow definition for cards."""
        return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
                 "~:color":{"~:color":"#0A0A0B","~:opacity":0.08},
                 "~:offset-x":0,"~:offset-y":2,"~:blur":16,"~:spread":0,"~:hidden":False}]

    def shadow_card_heavy(self):
        """Heavier shadow for prominent cards."""
        return [{"~:id":f"~u{uid()}","~:style":"~:drop-shadow",
                 "~:color":{"~:color":"#0A0A0B","~:opacity":0.12},
                 "~:offset-x":0,"~:offset-y":4,"~:blur":24,"~:spread":0,"~:hidden":False}]

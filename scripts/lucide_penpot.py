#!/usr/bin/env python3
"""
Lucide → Penpot: SVG path d-string parser + icon placement.
Converts any SVG path to Penpot segment format, scaled to any canvas position.
"""
import re, math, requests, json, uuid

# ─── SVG Path Parser ─────────────────────────────────────────────────────────

def _tokenize(d):
    """Split SVG path d-string into [cmd, num, num, ...] tokens."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    result = []
    for t in tokens:
        if t.isalpha():
            result.append(t)
        else:
            result.append(float(t))
    return result

def _parse_svg_path(d):
    """Parse SVG path d to list of absolute segments: {cmd, args...}"""
    tokens = _tokenize(d)
    segs = []
    i = 0
    cmd = None
    cx, cy = 0.0, 0.0  # current point
    sx, sy = 0.0, 0.0  # start of subpath (for Z)
    px2, py2 = None, None  # prev control point (for S/T)

    n_args = {"M":2,"L":2,"H":1,"V":1,"C":6,"S":4,"Q":4,"T":2,"A":7,"Z":0,
              "m":2,"l":2,"h":1,"v":1,"c":6,"s":4,"q":4,"t":2,"a":7,"z":0}

    while i < len(tokens):
        t = tokens[i]
        if isinstance(t, str):
            cmd = t; i += 1
        elif cmd is None:
            break

        na = n_args.get(cmd.upper(), 0)

        if cmd.upper() == "Z":
            segs.append(("Z",))
            cx, cy = sx, sy
            px2, py2 = None, None
            # cmd stays Z for implicit repeats (rare)
            continue

        if na == 0: i += 1; continue
        if i + na > len(tokens): break

        args = [tokens[i+j] for j in range(na)]
        i += na

        UC = cmd.upper()

        if UC == "M":
            x, y = args
            if cmd == "m": x, y = cx+x, cy+y
            segs.append(("M", x, y))
            cx, cy = x, y; sx, sy = x, y
            # Implicit subsequent coords = L
            cmd = "l" if cmd == "m" else "L"
            px2, py2 = None, None

        elif UC == "L":
            x, y = args
            if cmd == "l": x, y = cx+x, cy+y
            segs.append(("L", x, y))
            cx, cy = x, y; px2, py2 = None, None

        elif UC == "H":
            x = args[0]
            if cmd == "h": x = cx + x
            segs.append(("L", x, cy))
            cx = x; px2, py2 = None, None

        elif UC == "V":
            y = args[0]
            if cmd == "v": y = cy + y
            segs.append(("L", cx, y))
            cy = y; px2, py2 = None, None

        elif UC == "C":
            x1,y1,x2,y2,x,y = args
            if cmd == "c": x1,y1,x2,y2,x,y = cx+x1,cy+y1,cx+x2,cy+y2,cx+x,cy+y
            segs.append(("C", x1,y1, x2,y2, x,y))
            px2, py2 = x2, y2; cx, cy = x, y

        elif UC == "S":
            x2,y2,x,y = args
            if cmd == "s": x2,y2,x,y = cx+x2,cy+y2,cx+x,cy+y
            x1 = 2*cx - (px2 if px2 is not None else cx)
            y1 = 2*cy - (py2 if py2 is not None else cy)
            segs.append(("C", x1,y1, x2,y2, x,y))
            px2, py2 = x2, y2; cx, cy = x, y

        elif UC == "Q":
            qx1,qy1,x,y = args
            if cmd == "q": qx1,qy1,x,y = cx+qx1,cy+qy1,cx+x,cy+y
            # Convert quadratic to cubic
            x1 = cx + 2/3*(qx1-cx); y1 = cy + 2/3*(qy1-cy)
            x2 = x  + 2/3*(qx1-x);  y2 = y  + 2/3*(qy1-y)
            segs.append(("C", x1,y1, x2,y2, x,y))
            px2, py2 = qx1, qy1; cx, cy = x, y

        elif UC == "T":
            x, y = args
            if cmd == "t": x, y = cx+x, cy+y
            qx1 = 2*cx - (px2 if px2 is not None else cx)
            qy1 = 2*cy - (py2 if py2 is not None else cy)
            x1 = cx + 2/3*(qx1-cx); y1 = cy + 2/3*(qy1-cy)
            x2 = x  + 2/3*(qx1-x);  y2 = y  + 2/3*(qy1-y)
            segs.append(("C", x1,y1, x2,y2, x,y))
            px2, py2 = qx1, qy1; cx, cy = x, y

        elif UC == "A":
            rx,ry,phi,large,sweep,x,y = args
            if cmd == "a": x, y = cx+x, cy+y
            # Arc to cubic beziers
            for seg in _arc_to_beziers(cx,cy, rx,ry, phi, int(large), int(sweep), x,y):
                segs.append(seg)
            px2, py2 = None, None; cx, cy = x, y

    return segs

def _arc_to_beziers(x1,y1, rx,ry, phi_deg, fa,fs, x2,y2):
    """Convert SVG arc to list of cubic bezier segments."""
    if x1==x2 and y1==y2: return []
    if rx==0 or ry==0:
        return [("L", x2, y2)]

    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1-x2)/2, (y1-y2)/2
    x1p =  cp*dx + sp*dy
    y1p = -sp*dx + cp*dy

    # Correct radii
    lam = (x1p/rx)**2 + (y1p/ry)**2
    if lam > 1: s=math.sqrt(lam); rx*=s; ry*=s

    num = max(0, rx**2*ry**2 - rx**2*y1p**2 - ry**2*x1p**2)
    den = rx**2*y1p**2 + ry**2*x1p**2
    sq = math.sqrt(num/den) if den else 0
    if fa == fs: sq = -sq

    cxp =  sq * rx*y1p/ry
    cyp = -sq * ry*x1p/rx
    cx = cp*cxp - sp*cyp + (x1+x2)/2
    cy = sp*cxp + cp*cyp + (y1+y2)/2

    def ang(ux,uy,vx,vy):
        n = math.sqrt(ux**2+uy**2)*math.sqrt(vx**2+vy**2)
        if n == 0: return 0
        a = math.acos(max(-1,min(1,(ux*vx+uy*vy)/n)))
        if ux*vy-uy*vx < 0: a = -a
        return a

    th1 = ang(1,0, (x1p-cxp)/rx, (y1p-cyp)/ry)
    dth = ang((x1p-cxp)/rx,(y1p-cyp)/ry, (-x1p-cxp)/rx,(-y1p-cyp)/ry)
    if fs==0 and dth>0: dth -= 2*math.pi
    if fs==1 and dth<0: dth += 2*math.pi

    n_segs = max(1, math.ceil(abs(dth)/(math.pi/2)))
    segs = []
    for i in range(n_segs):
        t1 = th1 + i*dth/n_segs
        t2 = th1 + (i+1)*dth/n_segs
        # Cubic bezier approx for arc segment
        dt = t2 - t1
        k = math.tan(dt/2)*4/3 if abs(dt) < math.pi else 4/3
        ex1 = math.cos(t1); ey1 = math.sin(t1)
        ex2 = math.cos(t2); ey2 = math.sin(t2)
        # Control points in arc-local space
        bx1 = ex1 - k*ey1; by1 = ey1 + k*ex1
        bx2 = ex2 + k*ey2; by2 = ey2 - k*ex2
        # Transform back to canvas
        def tr(ex, ey):
            return (cx + cp*rx*ex - sp*ry*ey,
                    cy + sp*rx*ex + cp*ry*ey)
        p1 = tr(bx1,by1); p2 = tr(bx2,by2); p3 = tr(ex2,ey2)
        segs.append(("C", p1[0],p1[1], p2[0],p2[1], p3[0],p3[1]))
    return segs


# ─── Convert parsed segments to Penpot format ────────────────────────────────

def svg_to_penpot_segs(d, px, py, ps, src_size=24):
    """
    Parse SVG path d-string and convert to Penpot segment list.
    Places icon at canvas position (px,py) with size ps×ps.
    src_size: original viewBox size (Lucide = 24)
    """
    scale = ps / src_size
    raw = _parse_svg_path(d)
    result = []
    for seg in raw:
        cmd = seg[0]
        if cmd == "M":
            x, y = seg[1]*scale+px, seg[2]*scale+py
            result.append({"~:command":"~:move-to","~:params":{"~:x":x,"~:y":y}})
        elif cmd == "L":
            x, y = seg[1]*scale+px, seg[2]*scale+py
            result.append({"~:command":"~:line-to","~:params":{"~:x":x,"~:y":y}})
        elif cmd == "C":
            x1,y1 = seg[1]*scale+px, seg[2]*scale+py
            x2,y2 = seg[3]*scale+px, seg[4]*scale+py
            x, y  = seg[5]*scale+px, seg[6]*scale+py
            result.append({"~:command":"~:curve-to","~:params":{
                "~:c1x":x1,"~:c1y":y1,"~:c2x":x2,"~:c2y":y2,"~:x":x,"~:y":y}})
        elif cmd == "Z":
            result.append({"~:command":"~:close-path"})
    return result


# ─── Lucide icon library ──────────────────────────────────────────────────────
# Each icon = list of SVG d-strings (one per path/circle element)

def _circle_d(cx, cy, r):
    """SVG path d-string for a circle."""
    return (f"M {cx} {cy-r} "
            f"A {r} {r} 0 1 0 {cx+r} {cy} "
            f"A {r} {r} 0 0 0 {cx} {cy-r} Z")

LUCIDE_D = {
    "house": [
        "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8",
        "M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    ],
    "search": [
        "m21 21-4.34-4.34",
        _circle_d(11,11,8),
    ],
    "plus": [
        "M5 12h14",
        "M12 5v14",
    ],
    "arrow-left": [
        "m12 19-7-7 7-7",
        "M19 12H5",
    ],
    "bookmark": [
        "M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z",
    ],
    "ellipsis": [
        _circle_d(12,12,1),
        _circle_d(19,12,1),
        _circle_d(5,12,1),
    ],
    "tag": [
        "M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z",
        _circle_d(7.5,7.5,0.5),
    ],
    "settings": [
        "M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915",
        _circle_d(12,12,3),
    ],
    "more-vertical": [
        _circle_d(12,12,1),
        _circle_d(12,5,1),
        _circle_d(12,19,1),
    ],
    "bold": [
        "M6 12h9a4 4 0 0 1 0 8H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h7a4 4 0 0 1 0 8",
    ],
    "italic": [
        "M19 4h-9",
        "M14 20H5",
        "M15 4 9 20",
    ],
    "list": [
        "M3 12h.01","M3 18h.01","M3 6h.01",
        "M8 12h13","M8 18h13","M8 6h13",
    ],
    "hash": [
        "M4 9h16","M4 15h16",
        "M10 3 8 21","M16 3l-2 18",
    ],
    "star": [
        "M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z",
    ],
    "type": [
        "M4 7V4h16v3",
        "M9 20h6",
        "M12 4v16",
    ],
    "check": [
        "M20 6 9 17l-5-5",
    ],
    "x": [
        "M18 6 6 18","M6 6l12 12",
    ],
    "chevron-down": [
        "m6 9 6 6 6-6",
    ],
    "clock": [
        _circle_d(12,12,10),
        "M12 6v6l4 2",
    ],
    "calendar": [
        "M8 2v4","M16 2v4",
        "M3 10h18",
        "M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    ],
}


# ─── Penpot helper: place icon ────────────────────────────────────────────────

def penpot_icon(name, px, py, ps, color, stroke_w=None,
                session=None, file_id=None, page_id=None,
                frame_id=None, parent_id=None,
                revn_ref=None, add_fn=None):
    """
    Place a Lucide icon in Penpot.
    
    Args:
        name: icon name (must be in LUCIDE_D)
        px, py: canvas position (top-left of bounding box)
        ps: size (square)
        color: stroke color hex
        stroke_w: stroke width in final pixels (default auto = 2*ps/24)
        frame_id, parent_id: Penpot parent context
        add_fn: function(obj, frame_id, parent_id) → adds to Penpot
    
    Returns:
        list of created path object ids
    """
    if name not in LUCIDE_D:
        print(f"  [icon] unknown: {name}")
        return []
    
    # Stroke width: scale 2px from 24-unit space to ps-unit space  
    sw = stroke_w if stroke_w else 2.0 * ps / 24.0

    stroke = [{"~:stroke-color": color, "~:stroke-opacity": 1.0,
               "~:stroke-width": sw, "~:stroke-style": "~:solid",
               "~:stroke-alignment": "~:center",
               "~:stroke-cap-start": "~:round", "~:stroke-cap-end": "~:round"}]

    ids = []
    for d_str in LUCIDE_D[name]:
        segs = svg_to_penpot_segs(d_str, px, py, ps)
        if not segs:
            continue
        # Bounding box from segment coords
        xs = [seg["~:params"]["~:x"] for seg in segs if "~:params" in seg and "~:x" in seg["~:params"]]
        ys = [seg["~:params"]["~:y"] for seg in segs if "~:params" in seg and "~:y" in seg["~:params"]]
        bx = min(xs) if xs else px
        by = min(ys) if ys else py
        bw = max(1.0, max(xs)-min(xs)) if xs else ps
        bh = max(1.0, max(ys)-min(ys)) if ys else ps
        
        TF0 = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}
        def sr(x,y,w,h): return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,
                                   "~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}
        def pts(x,y,w,h): return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},
                                   {"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]
        
        oid = str(uuid.uuid4())
        obj = {"~:id":f"~u{oid}","~:type":"~:path","~:name":f"icon/{name}",
               "~:frame-id":f"~u{frame_id}","~:parent-id":f"~u{parent_id}",
               "~:x":bx,"~:y":by,"~:width":bw,"~:height":bh,
               "~:fills":[],"~:strokes":stroke,
               "~:selrect":sr(bx,by,bw,bh),"~:points":pts(bx,by,bw,bh),
               "~:transform":TF0,"~:transform-inverse":TF0,
               "~:content":segs}
        add_fn(obj, frame_id, parent_id)
        ids.append(oid)
    return ids


# ─── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    s = requests.Session()
    BASE = "https://penpot.jakeberrimor.com/api/rpc/command"
    H = {"Content-Type": "application/transit+json"}
    s.post(f"{BASE}/login-with-password", headers=H,
        data='["^ ","~:email","spam@jakeberrimor.com","~:password","q25RiI#L"]')
    FILE_ID = "4b85babb-b10c-8109-8007-b44132d2992f"
    PAGE_ID = "4b85babb-b10c-8109-8007-b44132d29930"

    def find(arr, key):
        if not isinstance(arr, list): return None
        for i,v in enumerate(arr):
            if v==key and i+1<len(arr): return arr[i+1]
        return None
    def uid(): return str(uuid.uuid4())
    def sr(x,y,w,h): return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,"~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}
    def pts(x,y,w,h): return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},{"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]
    def fill(c,a=1.0): return {"~:fill-color":c,"~:fill-opacity":a}
    TF0 = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}

    revn = 0
    r = s.post(f"{BASE}/update-file", headers=H,
        data=json.dumps(["^ ","~:id",f"~u{FILE_ID}","~:revn",0,"~:vern",0,
                         "~:session-id",f"~u{uid()}","~:changes",[]]))
    revn = find(r.json(),"~:revn") or 0

    def add(obj, fid, pid):
        global revn
        oid = obj["~:id"].replace("~u","")
        r = s.post(f"{BASE}/update-file", headers=H, data=json.dumps(
            ["^ ","~:id",f"~u{FILE_ID}","~:revn",revn,"~:vern",0,"~:session-id",f"~u{uid()}",
             "~:changes",[["^ ","~:type","~:add-obj","~:id",f"~u{oid}",
                 "~:frame-id",f"~u{fid}","~:parent-id",f"~u{pid}",
                 "~:page-id",f"~u{PAGE_ID}","~:index",9999,"~:obj",obj]]]))
        res = r.json(); revn = find(res,"~:revn") or revn+1
        err = find(res,"~:explain")
        if err: print(f"  ERR {obj.get('~:name','?')}")

    # Build icon showcase
    X, Y = 8500, 0
    icons_row1 = ["house","search","plus","arrow-left","bookmark","ellipsis","tag","settings"]
    icons_row2 = ["bold","italic","list","hash","star","check","chevron-down","clock"]
    colors1 = ["#4F46E5","#7C3AED","#10B981","#0A0A0B","#F59E0B","#52525B","#EF4444","#0EA5E9"]

    # Artboard
    cf = uid()
    add({"~:id":f"~u{cf}","~:type":"~:frame","~:name":"LucideShowcase",
         "~:frame-id":f"~u{cf}","~:parent-id":f"~u{PAGE_ID}",
         "~:x":X,"~:y":Y,"~:width":520,"~:height":200,
         "~:fills":[fill("#FFFFFF")],"~:clip-content":True,
         "~:selrect":sr(X,Y,520,200),"~:points":pts(X,Y,520,200),
         "~:transform":TF0,"~:transform-inverse":TF0,"~:shapes":[]}, PAGE_ID, PAGE_ID)

    # BG labels for rows
    for i in range(len(icons_row1)):
        col = colors1[i % len(colors1)]
        # bg circle behind icon
        add({"~:id":f"~u{uid()}","~:type":"~:circle","~:name":"ico_bg",
             "~:frame-id":f"~u{cf}","~:parent-id":f"~u{cf}",
             "~:x":X+14+i*62,"~:y":Y+14,"~:width":40,"~:height":40,
             "~:fills":[fill(col, 0.1)],"~:selrect":sr(X+14+i*62,Y+14,40,40),
             "~:points":pts(X+14+i*62,Y+14,40,40),
             "~:transform":TF0,"~:transform-inverse":TF0}, cf, cf)

    # Row 1: 24px icons
    print("Row 1: 24px icons")
    for i, (name, col) in enumerate(zip(icons_row1, colors1)):
        ix = X + 14+i*62 + 8
        iy = Y + 14 + 8
        penpot_icon(name, ix, iy, 24, col,
                    frame_id=cf, parent_id=cf, add_fn=add)

    # Row 2: 20px icons, different sizes
    print("Row 2: 20px icons")
    for i, name in enumerate(icons_row2):
        ix = X + 14+i*62 + 10
        iy = Y + 100
        penpot_icon(name, ix, iy, 20, "#52525B",
                    frame_id=cf, parent_id=cf, add_fn=add)

    # Row 3: same icons bigger with colors
    print("Row 3: 40px icons")
    for i, (name, col) in enumerate(zip(["house","search","plus","arrow-left"], colors1[:4])):
        ix = X + 20+i*120
        iy = Y + 150
        penpot_icon(name, ix, iy, 40, col,
                    frame_id=cf, parent_id=cf, add_fn=add)

    print(f"Done revn={revn}")

    # Export
    r2 = s.post(f"{BASE}/get-profile", headers=H, data='["^ "]')
    pid2 = find(r2.json(),"~:id").replace("~u","")
    item = ["^ ","~:type","~:png","~:scale",2,"~:suffix","","~:name","LucideShowcase",
            "~:file-id",f"~u{FILE_ID}","~:page-id",f"~u{PAGE_ID}","~:object-id",f"~u{cf}"]
    re2 = s.post("https://penpot.jakeberrimor.com/api/export", headers=H, data=json.dumps(
        ["^ ","~:cmd","~:export-shapes","~:profile-id",f"~u{pid2}",
         "~:file-id",f"~u{FILE_ID}","~:exports",[item]]))
    uri = re2.json().get("~:uri",{}).get("~#uri")
    img_b = s.get(uri).content
    out = "/home/clawdbot/.openclaw/workspace/drafts/lucide_showcase.png"
    open(out,"wb").write(img_b)
    print(f"Exported {len(img_b)//1024}KB → {out}")

"""
app.py — YouTube Intelligence Dashboard Backend
"""
from flask import Flask, jsonify, render_template, request, Response
try:
    from flask_cors import CORS
    _has_cors = True
except ImportError:
    _has_cors = False

import requests, json, csv, io, time, re, os, threading
from datetime import datetime

app = Flask(__name__)
if _has_cors: CORS(app)

CHANNELS = [
    {"id":"UCX6OQ3DkcsbYNE6H8uQQuVA","name":"MrBeast",     "handle":"MrBeast",    "niche":"Challenge",    "color":"#FF0000","tier":"focus"},
    {"id":"UCVjgV3uCkHrHqkvyPbkbVOQ","name":"Mark Rober",   "handle":"MarkRober",  "niche":"Science",      "color":"#4A90D9","tier":"competitor"},
    {"id":"UC9pgQfOXRsp4UKrI8q0zjXQ","name":"Dude Perfect", "handle":"DudePerfect","niche":"Sports/Stunts","color":"#2ECC71","tier":"competitor"},
    {"id":"UCbmNph6atAoGfqLoCL_duAg","name":"Ryan Trahan",  "handle":"ryantrahan", "niche":"Challenge",    "color":"#F39C12","tier":"competitor"},
    {"id":"UCnUYZLuoy1rq1aVMwx4aTzw","name":"Airrack",      "handle":"airrack",    "niche":"Challenge",    "color":"#9B59B6","tier":"competitor"},
    {"id":"UCBcRF18a7Qf58cCRy5xuWwQ","name":"MKBHD",        "handle":"mkbhd",      "niche":"Tech",         "color":"#1ABC9C","tier":"competitor"},
]

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 3600
_dynamic_channels = []
CHANNEL_COLORS = ["#E74C3C","#3498DB","#E67E22","#1ABC9C","#9B59B6","#F1C40F","#E91E63","#00BCD4"]

def cache_get(key):
    with _cache_lock:
        e = _cache.get(key)
        if e and time.time()-e["ts"] < CACHE_TTL: return e["data"]
    return None

def cache_set(key, data):
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}

FALLBACK_STATS = {
    "UCX6OQ3DkcsbYNE6H8uQQuVA": {"subscribers":347000000,"total_views":65000000000,"video_count":820, "grade":"A++"},
    "UCVjgV3uCkHrHqkvyPbkbVOQ": {"subscribers":52000000, "total_views":4200000000, "video_count":130, "grade":"A+"},
    "UC9pgQfOXRsp4UKrI8q0zjXQ": {"subscribers":60000000, "total_views":18000000000,"video_count":380, "grade":"A+"},
    "UCbmNph6atAoGfqLoCL_duAg": {"subscribers":16000000, "total_views":1800000000, "video_count":650, "grade":"A"},
    "UCnUYZLuoy1rq1aVMwx4aTzw": {"subscribers":10500000, "total_views":1200000000, "video_count":420, "grade":"A"},
    "UCBcRF18a7Qf58cCRy5xuWwQ": {"subscribers":18500000, "total_views":4500000000, "video_count":1600,"grade":"A+"},
}

FALLBACK_RECENT = {
    "UCX6OQ3DkcsbYNE6H8uQQuVA":[
        {"title":"I Spent 50 Hours In Solitary Confinement","views":"180M","published":"2025-01-15"},
        {"title":"Ages 1 - 100 Fight For $500,000","views":"220M","published":"2025-02-01"},
        {"title":"World's Most Dangerous Trap!","views":"145M","published":"2025-02-20"},
        {"title":"$1 vs $1,000,000 Hotel Room!","views":"195M","published":"2025-03-05"},
    ],
    "UCVjgV3uCkHrHqkvyPbkbVOQ":[
        {"title":"World's Largest Nerf Gun","views":"48M","published":"2025-01-10"},
        {"title":"I Built a Jet-Powered Suit","views":"62M","published":"2025-02-14"},
        {"title":"Backyard Squirrel Maze","views":"91M","published":"2025-03-01"},
    ],
    "UC9pgQfOXRsp4UKrI8q0zjXQ":[
        {"title":"Overtime 23 | Dude Perfect","views":"31M","published":"2025-01-20"},
        {"title":"World Record Edition | Dude Perfect","views":"44M","published":"2025-02-10"},
        {"title":"Giant Trick Shots","views":"28M","published":"2025-03-02"},
    ],
    "UCbmNph6atAoGfqLoCL_duAg":[
        {"title":"I Survived on $0.01 for 30 Days","views":"22M","published":"2025-01-25"},
        {"title":"The Penny Challenge","views":"18M","published":"2025-02-18"},
    ],
    "UCnUYZLuoy1rq1aVMwx4aTzw":[
        {"title":"I Challenged MrBeast","views":"14M","published":"2025-02-05"},
        {"title":"Last To Leave Wins $100,000","views":"11M","published":"2025-03-01"},
    ],
    "UCBcRF18a7Qf58cCRy5xuWwQ":[
        {"title":"The Best Smartphones of 2025","views":"9M","published":"2025-01-28"},
        {"title":"Apple Vision Pro: 6 Months Later","views":"12M","published":"2025-02-20"},
        {"title":"Why I Left Samsung","views":"8M","published":"2025-03-08"},
    ],
}

def format_count(n):
    try:
        n=int(n)
        if n>=1_000_000_000: return f"{n/1_000_000_000:.1f}B"
        if n>=1_000_000:     return f"{n/1_000_000:.1f}M"
        if n>=1_000:         return f"{n/1_000:.1f}K"
        return str(n)
    except: return "N/A"

def get_all_channel_defs(): return CHANNELS + _dynamic_channels

def build_channel_data(ch):
    s = FALLBACK_STATS.get(ch["id"],{"subscribers":0,"total_views":0,"video_count":0,"grade":"N/A"}).copy()
    subs=s.get("subscribers",0); views=s.get("total_views",0); vids=s.get("video_count",0)
    avg=int(views/vids) if vids else 0
    return {
        "id":ch["id"],"name":ch["name"],"handle":ch["handle"],"niche":ch["niche"],
        "color":ch["color"],"tier":ch["tier"],"thumbnail":"",
        "subscribers":subs,"subscribers_fmt":format_count(subs),
        "total_views":views,"total_views_fmt":format_count(views),
        "video_count":vids,"avg_views_per_video":avg,"avg_views_fmt":format_count(avg),
        "grade":s.get("grade","N/A"),"source":"curated",
        "recent_videos":FALLBACK_RECENT.get(ch["id"],[]),
        "views_per_sub":round(views/subs,1) if subs else 0,
        "yt_url":f"https://youtube.com/@{ch['handle']}",
    }

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/channels")
def api_channels():
    niche_f = request.args.get("niche","").strip().lower()
    tier_f  = request.args.get("tier","").strip().lower()
    date_from = request.args.get("date_from","")
    date_to   = request.args.get("date_to","")

    cached = cache_get("all_channels")
    if not cached:
        cached = [build_channel_data(ch) for ch in get_all_channel_defs()]
        cache_set("all_channels", cached)

    data = cached
    if niche_f: data = [c for c in data if c["niche"].lower()==niche_f]
    if tier_f:  data = [c for c in data if c["tier"].lower()==tier_f]
    if date_from or date_to:
        import copy
        data = copy.deepcopy(data)
        for ch in data:
            v = ch.get("recent_videos",[])
            if date_from: v=[x for x in v if x.get("published","")>=date_from]
            if date_to:   v=[x for x in v if x.get("published","")<=date_to]
            ch["recent_videos"]=v
    return jsonify(data)

@app.route("/api/summary")
def api_summary():
    channels=json.loads(api_channels().data)
    mb=next((c for c in channels if c["id"]=="UCX6OQ3DkcsbYNE6H8uQQuVA"),None)
    comps=[c for c in channels if c["tier"]=="competitor"]
    if not mb: return jsonify({"error":"no data"})
    avg=sum(c.get("subscribers",0) for c in comps)/max(len(comps),1)
    lead=mb.get("subscribers",0)/max(avg,1)
    return jsonify({
        "mrbeast_subs":mb.get("subscribers_fmt","N/A"),
        "mrbeast_views":mb.get("total_views_fmt","N/A"),
        "mrbeast_grade":mb.get("grade","N/A"),
        "sub_lead_vs_avg_competitor":f"{lead:.1f}x",
        "total_channels_tracked":len(channels),
        "last_updated":datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    })

@app.route("/api/search", methods=["POST"])
def api_search():
    global _dynamic_channels
    body=request.get_json(force=True) or {}
    handle=body.get("handle","").strip().lstrip("@")
    if not handle: return jsonify({"error":"handle required"}),400

    all_defs=get_all_channel_defs()
    existing=next((c for c in all_defs if c["handle"].lower()==handle.lower()),None)
    if existing: return jsonify({"status":"already_tracked","channel":build_channel_data(existing)})

    name=handle
    channel_id=f"CUSTOM_{handle.upper()}"
    try:
        oe=requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/@{handle}&format=json",timeout=6)
        if oe.status_code==200: name=oe.json().get("author_name",handle)
    except: pass

    used={c["color"] for c in all_defs}
    color=next((c for c in CHANNEL_COLORS if c not in used),"#888888")
    new_ch={"id":channel_id,"name":name,"handle":handle,"niche":"Unknown","color":color,"tier":"custom"}
    FALLBACK_STATS[channel_id]={"subscribers":0,"total_views":0,"video_count":0,"grade":"N/A"}
    FALLBACK_RECENT[channel_id]=[]
    _dynamic_channels.append(new_ch)
    with _cache_lock:
        _cache.pop("all_channels",None); _cache.pop("summary",None)
    return jsonify({"status":"added","channel":build_channel_data(new_ch)})

@app.route("/api/remove", methods=["POST"])
def api_remove():
    global _dynamic_channels
    body=request.get_json(force=True) or {}
    handle=body.get("handle","").strip().lstrip("@")
    _dynamic_channels=[c for c in _dynamic_channels if c["handle"].lower()!=handle.lower()]
    with _cache_lock:
        _cache.pop("all_channels",None); _cache.pop("summary",None)
    return jsonify({"status":"removed"})

@app.route("/api/export/csv")
def api_export_csv():
    niche_f=request.args.get("niche","").strip().lower()
    tier_f =request.args.get("tier","").strip().lower()
    data=cache_get("all_channels") or []
    if niche_f: data=[c for c in data if c["niche"].lower()==niche_f]
    if tier_f:  data=[c for c in data if c["tier"].lower()==tier_f]
    out=io.StringIO()
    fields=["name","handle","niche","tier","subscribers","total_views","video_count","avg_views_per_video","grade","views_per_sub","yt_url"]
    w=csv.DictWriter(out,fieldnames=fields)
    w.writeheader()
    for ch in data: w.writerow({k:ch.get(k,"") for k in fields})
    out.seek(0)
    return Response(out.getvalue(),mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=beast_intel_export.csv"})

@app.route("/api/niches")
def api_niches():
    return jsonify(sorted(set(c["niche"] for c in get_all_channel_defs())))

@app.route("/api/refresh")
def api_refresh():
    with _cache_lock: _cache.clear()
    return jsonify({"status":"cache cleared"})

if __name__=="__main__":
    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port,debug=os.environ.get("FLASK_ENV")!="production")

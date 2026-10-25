"""Wednesday school-trip check (children go to Mausund skole by boat on Wednesdays).
Writes school.json for the screen and for the Tuesday-evening notification.
Limits set by Edvardas: MET orange/red warning, gusts >= 20 m/s or feels-like <= -15 C
between 06 and 10 on Wednesday, or a cancelled morning boat from Sørburøy."""
import json, datetime, urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Oslo"); LAT, LON = 63.9769, 9.0637
UA = {"User-Agent": "sorburoy-tv/1.0 github.com/imgroupeu-lgtm"}

def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

now = datetime.datetime.now(TZ)
wed = (now + datetime.timedelta(days=(2 - now.weekday()) % 7)).date()
w0 = datetime.datetime.combine(wed, datetime.time(6), TZ); w1 = datetime.datetime.combine(wed, datetime.time(10), TZ)
out = {"updated": now.isoformat(timespec="minutes"), "date": wed.isoformat(), "reasons": [], "notes": []}

try:
    d = get(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=wind_speed_10m,wind_gusts_10m,apparent_temperature"
            f"&wind_speed_unit=ms&timezone=Europe%2FOslo&forecast_days=7")
    H = d["hourly"]; idx = [i for i, t in enumerate(H["time"]) if t.startswith(wed.isoformat()) and 6 <= int(t[11:13]) <= 10]
    out["wind"] = round(max(H["wind_speed_10m"][i] for i in idx)); out["gust"] = round(max(H["wind_gusts_10m"][i] for i in idx))
    out["feels"] = round(min(H["apparent_temperature"][i] for i in idx))
    if out["gust"] >= 20: out["reasons"].append(f"gūsiai iki {out['gust']} m/s")
    if out["feels"] <= -15: out["reasons"].append(f"jutiminė temperatūra {out['feels']} °C")
except Exception as e:
    out["notes"].append(f"orų prognozės gauti nepavyko ({type(e).__name__})")

LV = {"yellow": "geltonas", "orange": "oranžinis", "red": "raudonas"}
try:
    j = get(f"https://api.met.no/weatherapi/metalerts/2.0/current.json?lat={LAT}&lon={LON}")
    out["alerts"] = []
    for f in j.get("features", []):
        a, b = f.get("when", {}).get("interval", [None, None])
        if not a: continue
        a, b = datetime.datetime.fromisoformat(a), datetime.datetime.fromisoformat(b)
        if a <= w1 and b >= w0:
            lv = (f["properties"].get("awareness_level", "").split(";") + ["", ""])[1].strip()
            title = f["properties"].get("eventAwarenessName") or f["properties"].get("event")
            out["alerts"].append({"level": lv, "event": title})
            if lv in ("orange", "red"): out["reasons"].append(f"MET {LV[lv]} įspėjimas: {title}")
except Exception as e:
    out["notes"].append(f"MET įspėjimų gauti nepavyko ({type(e).__name__})")

try:
    q = ('{stopPlace(id:"NSR:StopPlace:42925"){estimatedCalls(numberOfDepartures:60,timeRange:604800,'
         'whiteListed:{lines:["ATB:Line:2_820"]}){aimedDepartureTime cancellation destinationDisplay{frontText}}}}')
    d = get("https://api.entur.io/journey-planner/v3/graphql", json.dumps({"query": q}).encode(),
            {"Content-Type": "application/json", "ET-Client-Name": "imgroupeu-sorburoy-tv"})
    boats = [c for c in d["data"]["stopPlace"]["estimatedCalls"] if c["aimedDepartureTime"]
             and c["aimedDepartureTime"][:10] == wed.isoformat() and int(c["aimedDepartureTime"][11:13]) < 10]
    out["boats"] = [{"time": c["aimedDepartureTime"][11:16], "to": c["destinationDisplay"]["frontText"], "cancelled": c["cancellation"]} for c in boats]
    if any(c["cancellation"] for c in boats): out["reasons"].append("rytinis keltas atšauktas")
except Exception as e:
    out["notes"].append(f"kelto duomenų gauti nepavyko ({type(e).__name__})")

out["verdict"] = "bad" if out["reasons"] else ("warn" if out.get("alerts") or out.get("gust", 0) >= 15 else "ok")
with open("school.json", "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))

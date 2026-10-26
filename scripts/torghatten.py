"""Torghatten (operator of AtB boats Dyrøy–Øyrekken) service messages.
Reads the server-rendered data of torghatten.no/en/our-routes/deviations and keeps
announcements for the Frøya island routes, incl. cancelled departures. Writes torghatten.json."""
import json, re, datetime, urllib.request

URL = "https://www.torghatten.no/en/our-routes/deviations"
LINES = re.compile(r"Øyrekken|Mausund|Sula|Dyrøy|Froan|Sørburøy", re.I)

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (sorburoy-tv; github.com/imgroupeu-lgtm)"})
page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
data = json.loads(m.group(1)) if m else {}
ann = data.get("props", {}).get("pageProps", {}).get("trafficAnnouncements", []) or []
items = []
for a in ann:
    if not LINES.search(a.get("lineName", "") or ""):
        continue
    info = a.get("info") or {}
    items.append({
        "line": a.get("lineName"), "type": a.get("#type"),
        "text": (info.get("description") or "").strip(),
        "updated": a.get("updatedAt") or a.get("createdAt"),
        "departures": [{
            "from": d["departure"].get("departureQuayName"), "to": d["departure"].get("arrivalQuayName"),
            "dep": d["departure"].get("departureTime"), "arr": d["departure"].get("arrivalTime"),
            "cancelled": d.get("isCancelled", False) and not d.get("isRestored", False)}
            for d in (a.get("changedDepartures") or []) if d.get("departure")]})
out = {"updated": datetime.datetime.utcnow().isoformat(timespec="minutes") + "Z", "source": URL,
       "announcements_total": len(ann), "items": items}
json.dump(out, open("torghatten.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:1200])

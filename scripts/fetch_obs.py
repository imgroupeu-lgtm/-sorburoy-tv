"""Fetch latest wind observations for Halten fyr and Bogøya from MET Norway Frost
and write obs.json next to index.html. Runs in GitHub Actions; the client ID comes
from the FROST_CLIENT_ID repository secret and is never written to the repo."""
import base64, json, os, sys, urllib.request, urllib.parse, urllib.error, datetime

CLIENT_ID = os.environ.get("FROST_CLIENT_ID", "").strip()
STATIONS = {"SN71850": "Halten fyr", "SN65930": "Bogøya"}
ELEMENTS = {
    "wind_speed": "speed",
    "max(wind_speed_of_gust PT10M)": "gust",
    "max(wind_speed_of_gust PT1H)": "gust1h",
    "wind_from_direction": "dir",
    "air_temperature": "temp",
}

def get(params):
    url = "https://frost.met.no/observations/v0.jsonld?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{CLIENT_ID}:".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    if not CLIENT_ID:
        sys.exit("FROST_CLIENT_ID secret is missing")
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "stations": []}
    for sid, name in STATIONS.items():
        st = {"id": sid, "name": name}
        for el, key in ELEMENTS.items():
            try:
                d = get({"sources": sid, "elements": el, "referencetime": "latest", "maxage": "PT3H"})
                item = d["data"][0]
                st[key] = item["observations"][0]["value"]
                st.setdefault("time", item["referenceTime"])
            except urllib.error.HTTPError as e:  # element not measured here, or no recent value
                body = e.read().decode("utf-8", "replace")[:160]
                st.setdefault("errors", []).append(f"{el}: HTTP {e.code} {body}")
            except Exception as e:
                st.setdefault("errors", []).append(f"{el}: {type(e).__name__}")
        if "gust" not in st and "gust1h" in st:
            st["gust"] = st["gust1h"]
        st.pop("gust1h", None)
        out["stations"].append(st)
    with open("obs.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()

"""Read AtB 'Driftsavvik – hurtigbåt og ferge' and keep notices that concern route 820/825
or the Øyrekken islands. Writes avvik.json for the screen."""
import json, re, html, datetime, urllib.request
from html.parser import HTMLParser

URL = "https://www.atb.no/driftsavvik/hurtigbat-og-ferge/"
KEYS = re.compile(r"\b(820|825)\b|Øyrekken|Froan|Sørburøy|Sauøy|Mausund|Sula|Dyrøy|Halten|Bogøy", re.I)

class Blocks(HTMLParser):
    """Split the page into blocks at h2/h3/h4 headings; collect text under each."""
    def __init__(self):
        super().__init__(); self.blocks=[]; self.cur=None; self.inh=False; self.skip=0
    def handle_starttag(self, t, a):
        if t in ("script","style","nav","footer","header"): self.skip+=1
        if t in ("h2","h3","h4"): self.inh=True; self.cur={"title":"","text":""}; self.blocks.append(self.cur)
    def handle_endtag(self, t):
        if t in ("script","style","nav","footer","header") and self.skip: self.skip-=1
        if t in ("h2","h3","h4"): self.inh=False
    def handle_data(self, d):
        if self.skip or not self.cur: return
        d=" ".join(d.split())
        if not d: return
        if self.inh: self.cur["title"]=(self.cur["title"]+" "+d).strip()
        else: self.cur["text"]=(self.cur["text"]+" "+d).strip()

req = urllib.request.Request(URL, headers={"User-Agent":"sorburoy-tv/1.0 (github.com/imgroupeu-lgtm)"})
page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8","replace")
p = Blocks(); p.feed(page)
items=[]
for b in p.blocks:
    blob=b["title"]+" "+b["text"]
    if KEYS.search(blob):
        m=re.search(r"(\d{1,2})\.\s*(jan|feb|mar|apr|mai|jun|jul|aug|sep|okt|nov|des)\w*\.?\s*(\d{4})(?:\s*kl\.?\s*(\d{1,2})[.:](\d{2}))?", blob, re.I)
        pub=None
        if m:
            mon=["jan","feb","mar","apr","mai","jun","jul","aug","sep","okt","nov","des"].index(m.group(2).lower()[:3])+1
            pub=datetime.datetime(int(m.group(3)),mon,int(m.group(1)),int(m.group(4) or 0),int(m.group(5) or 0)).isoformat()
        items.append({"title":html.unescape(b["title"])[:160],"text":html.unescape(b["text"])[:400],"published":pub})
out={"updated":datetime.datetime.utcnow().isoformat(timespec="minutes")+"Z","source":URL,"blocks_seen":len(p.blocks),"items":items}
json.dump(out, open("avvik.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:1500])

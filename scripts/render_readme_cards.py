#!/usr/bin/env python3
import json, os
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"cards"; DATA=ROOT/"data"/"contributions.json"
BG,INK,GOLD,BLUE,MUTED,LINE="#0B0C0E","#F0E8DA","#63D6E2","#63D6E2","#BEB09A","#4A4640"
PANEL="#17191D"
def svg(w,h,title,body):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title><defs><style>text{{font-family:Inter,Arial,sans-serif}}.serif{{font-family:Georgia,serif}}@keyframes rise{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}.enter{{animation:rise .8s ease both}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style></defs>{body}</svg>'''
def save(name,w,h,title,body):
 OUT.mkdir(exist_ok=True); (OUT/name).write_text(svg(w,h,title,body),encoding="utf-8")
def load():
 return json.loads(DATA.read_text()) if DATA.exists() else {"total":0,"weeks":[]}
def flatten(d):
 return sorted([x for w in d.get("weeks",[]) for x in w.get("contributionDays",[])],key=lambda x:x["date"])
def streaks(days):
 active={date.fromisoformat(x["date"]) for x in days if x.get("contributionCount",0)>0}; today=date.today(); cur=0; p=today if today in active else today-timedelta(days=1)
 while p in active: cur+=1; p-=timedelta(days=1)
 best=run=0; prev=None
 for p in sorted(active):
  run=run+1 if prev and p==prev+timedelta(days=1) else 1; best=max(best,run); prev=p
 return len(active),cur,best
def main():
 d=load(); days=flatten(d); total=d.get("total",0)
 body=f'<rect width="1200" height="330" rx="24" fill="{BG}"/><circle cx="1040" cy="155" r="112" fill="{GOLD}" opacity=".18"/><text x="62" y="58" fill="{INK}" font-size="14" letter-spacing="4">HITEN BORKAR / ENGINEERING PORTFOLIO</text><text x="62" y="150" fill="{INK}" font-size="70" class="serif enter">Building systems</text><text x="62" y="224" fill="{INK}" font-size="70" class="serif enter">that solve real problems.</text><text x="65" y="275" fill="{MUTED}" font-size="19">Computer Science Engineer · Full-stack · Applied ML · Data</text><rect x="850" y="28" width="315" height="275" rx="18" fill="{PANEL}" stroke="{LINE}"/><text x="866" y="48" fill="{GOLD}" font-size="9" letter-spacing="2">ASCII / PORTRAIT</text>'
 for i,line in enumerate(PORTRAIT_ASCII):
  body+=f'<text x="866" y="{65+i*6.7:.1f}" fill="{GOLD if i%7==0 else INK}" font-family="monospace" font-size="6.5" xml:space="preserve">{escape(line)}</text>'
 body+=f'<path d="M875 143 Q925 117 978 143" fill="none" stroke="{BLUE}" stroke-width="2.5" opacity=".95"><animate attributeName="opacity" values=".2;1;.2" dur="2.8s" repeatCount="indefinite"/></path><path d="M65 310 H760" stroke="{GOLD}" stroke-width="1" opacity=".6"/><text x="65" y="310" fill="{INK}" font-size="12">GITHUB CONTRIBUTIONS · {total:,}</text>'
 save("hero.svg",1200,330,"Hiten Borkar",body)
 months=defaultdict(int)
 for x in days: months[x["date"][:7]]+=x.get("contributionCount",0)
 keys=sorted(months)[-12:]; vals=[months[k] for k in keys]; mx=max(vals or [1]) or 1
 active,cur,best=streaks(days)
 body=f'<rect width="1200" height="310" rx="22" fill="{PANEL}"/><text x="42" y="48" fill="{INK}" font-size="26" class="serif">A year in motion</text><text x="42" y="75" fill="{MUTED}" font-size="13">MONTHLY CONTRIBUTIONS · LAST 12 MONTHS</text>'
 for i,(k,v) in enumerate(zip(keys,vals)):
  x=48+i*68; h=140*v/mx; y=245-h
  body+=f'<rect x="{x}" y="{y:.1f}" width="43" height="{h:.1f}" rx="6" fill="{BLUE if v==mx else INK}"><animate attributeName="height" from="0" to="{h:.1f}" dur=".7s" begin="{i*.04}s" fill="freeze"/></rect><text x="{x+21}" y="265" text-anchor="middle" fill="{MUTED}" font-size="9">{k[5:]}</text>'
 body+=f'<text x="900" y="112" fill="{INK}" font-size="38" class="serif">{cur}</text><text x="900" y="136" fill="{MUTED}" font-size="12">CURRENT STREAK</text><text x="1030" y="112" fill="{INK}" font-size="38" class="serif">{active}</text><text x="1030" y="136" fill="{MUTED}" font-size="12">ACTIVE DAYS</text><text x="900" y="198" fill="{INK}" font-size="26" class="serif">{best} days</text><text x="900" y="220" fill="{MUTED}" font-size="12">BEST STREAK</text>'
 save("activity.svg",1200,310,"Monthly contributions and streaks",body)
 bydate={x["date"]:x.get("contributionCount",0) for x in days}; today=date.today(); start=today-timedelta(days=363); start-=timedelta(days=start.weekday()); mx=max(bydate.values() or [1]) or 1
 pal=["#25282B","#39464A","#526B70","#398B9A",BLUE]
 body=f'<rect width="1200" height="190" rx="22" fill="{BG}"/><text x="38" y="42" fill="{BG}" font-size="23" class="serif">Consistency, in cyan.</text><text x="38" y="65" fill="#BEB09A" font-size="12">DAILY CONTRIBUTIONS · LAST 52 WEEKS</text>'
 for i in range(364):
  day=start+timedelta(days=i); n=bydate.get(day.isoformat(),0); level=0 if n==0 else min(4,1+int(4*n/mx)); body+=f'<rect x="{40+(i//7)*15}" y="{86+(i%7)*13}" width="10" height="9" rx="2" fill="{pal[level]}"/>'
 body+=f'<text x="1050" y="113" fill="{GOLD}" font-size="34" class="serif">{total:,}</text><text x="1050" y="136" fill="{BG}" font-size="11">TOTAL CONTRIBUTIONS</text>'
 save("heatmap.svg",1200,190,"GitHub contribution graph",body)
 def tile(file,label,sub,num,color):
  b=f'<rect width="380" height="190" rx="20" fill="{color}"/><text x="28" y="42" fill="{BG if color in (INK,GOLD) else INK}" font-size="12" letter-spacing="3">{escape(label)}</text><text x="28" y="91" fill="{BG if color==INK else INK}" font-size="27" class="serif">{escape(sub)}</text><text x="28" y="154" fill="{BG if color==INK else INK}" font-size="12">EXPLORE PROJECTS ↗</text><text x="335" y="166" text-anchor="end" fill="{BG if color==GOLD else GOLD if color==INK else INK}" font-size="44" class="serif">{num}</text>'
  save(file,380,190,label,b)
 tile("build.svg","BUILD","Software & systems","01",BG); tile("data.svg","DATA","ML & analytics","02",INK); tile("explore.svg","EXPLORE","Ideas & research","03",GOLD)
 def repo(file,title,desc,stack,num):
  b=f'<rect width="560" height="170" rx="18" fill="#17191D" stroke="{LINE}"/><text x="28" y="42" fill="{INK}" font-size="12">FEATURED PROJECT / {num}</text><text x="28" y="82" fill="{INK}" font-size="27" class="serif">{escape(title)}</text><text x="28" y="111" fill="{MUTED}" font-size="13">{escape(desc)}</text><text x="28" y="145" fill="{BLUE}" font-size="12">{escape(stack)}</text>'
  save(file,560,170,title,b)
 repo("repo-traffic.svg","Smart Traffic Management","Predictive congestion and alternate routing for Nagpur.","React · FastAPI · XGBoost · Leaflet","01")
 repo("repo-ipl.svg","IPL Crunch ’26","Ball-by-ball IPL analytics from raw Cricsheet JSON.","Python · Pandas · Plotly · SciPy","02")
 repo("repo-blindspot.svg","The Blind Spot","AI-assisted analysis of assumptions and decision biases.","JavaScript · HTML · CSS","03")
 repo("repo-rental.svg","Vehicle Rental System","Flask app with booking rules and automated tests.","Python · Flask · SQLite · pytest","04")
 print("Rendered SVG cards; STATIC mode:",os.getenv("STATIC","0"))
if __name__=="__main__": main()

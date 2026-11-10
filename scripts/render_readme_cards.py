#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"cards"; DATA=ROOT/"data"/"contributions.json"; REPOS=ROOT/"data"/"repos.json"
BG,INK,CYAN,BLUE,TAUPE,LINE="#0B0C0E","#F0E8DA","#63D6E2","#398B9A","#BEB09A","#4A4640"; PANEL="#17191D"
PORTRAIT_ASCII=["       .-==========-.","     .'  .------.  '.","    /   /  /\\\\   \\\\   \\\\","   |   |  /  \\\\   |   |","   |   | |    |  |   |","   |   | | <> |  |   |","   |   |  \\\\__/   |   |","    \\\\   \\\\______/   /","     '.          .'","       \\\\  ____  /","        \\\\______/","       /  /  \\\\  \\\\","      /__/    \\\\__\\\\"]
def svg(w,h,title,body):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title><defs><style>text{{font-family:Inter,Arial,sans-serif}}.serif{{font-family:Georgia,serif}}@keyframes rise{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}@keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}.enter{{animation:rise .8s ease both}}.pulse{{animation:pulse 2.8s ease-in-out infinite}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style></defs>{body}</svg>'''
def save(name,w,h,title,body):
 OUT.mkdir(exist_ok=True); (OUT/name).write_text(svg(w,h,title,body),encoding="utf-8")
def read_json(path,default):
 try: return json.loads(path.read_text(encoding="utf-8"))
 except (OSError,ValueError): return default
def flatten(data):
 return sorted([d for week in data.get("weeks",[]) for d in week.get("contributionDays",[])],key=lambda x:x["date"])
def activity_stats(days):
 counts={d["date"]:int(d.get("contributionCount",0)) for d in days}
 active={date.fromisoformat(k) for k,v in counts.items() if v>0}; today=date.today()
 cursor=today if today in active else today-timedelta(days=1); current=0
 while cursor in active: current+=1; cursor-=timedelta(days=1)
 best=run=0; previous=None
 for day in sorted(active):
  run=run+1 if previous and day==previous+timedelta(days=1) else 1; best=max(best,run); previous=day
 busiest=max(days,key=lambda d:int(d.get("contributionCount",0)),default={"date":"—","contributionCount":0})
 monthly=defaultdict(int)
 for d in days: monthly[d["date"][:7]]+=int(d.get("contributionCount",0))
 return counts,len(active),current,best,busiest,monthly
def render_hero(total):
 body=f'<rect width="1200" height="350" rx="24" fill="{BG}"/><circle cx="1005" cy="172" r="132" fill="{CYAN}" opacity=".10"/><text x="58" y="55" fill="{CYAN}" font-size="13" letter-spacing="4">HITEN BORKAR / ENGINEERING PORTFOLIO</text><text x="58" y="139" fill="{INK}" font-size="66" class="serif enter">Building systems</text><text x="58" y="210" fill="{INK}" font-size="66" class="serif enter">that solve real problems.</text><text x="61" y="258" fill="{TAUPE}" font-size="18">Computer Science Engineer · Full-stack · Applied ML · Data</text><path d="M60 292 H740" stroke="{LINE}" stroke-width="1"/><text x="60" y="321" fill="{CYAN}" font-size="12" letter-spacing="2">GITHUB CONTRIBUTIONS · {total:,} IN THE LAST YEAR</text><rect x="850" y="27" width="315" height="296" rx="18" fill="{PANEL}" stroke="{LINE}"/><text x="868" y="48" fill="{CYAN}" font-size="9" letter-spacing="2">ASCII / PORTRAIT</text>'
 for i,line in enumerate(PORTRAIT_ASCII): body+=f'<text x="870" y="{83+i*15}" fill="{CYAN if i in (5,6) else INK}" font-family="monospace" font-size="12" xml:space="preserve">{escape(line)}</text>'
 body+=f'<path d="M880 171 Q932 145 984 171" fill="none" stroke="{CYAN}" stroke-width="2.5" class="pulse"/><text x="868" y="290" fill="{TAUPE}" font-size="10">INK / CYAN / SYSTEMS</text>'
 save("hero.svg",1200,350,"Hiten Borkar — engineering portfolio",body)
def render_activity(total,active,current,best,busiest,monthly):
 keys=sorted(monthly)[-12:]
 if not keys: keys=[(date.today()-timedelta(days=30*i)).strftime("%Y-%m") for i in range(11,-1,-1)]
 values=[monthly.get(k,0) for k in keys]; maximum=max(values or [1]) or 1
 body=f'<rect width="1200" height="330" rx="22" fill="{PANEL}" stroke="{LINE}"/><text x="42" y="44" fill="{INK}" font-size="26" class="serif">A year in motion</text><text x="42" y="70" fill="{TAUPE}" font-size="12" letter-spacing="1">MONTHLY CONTRIBUTIONS · LAST 12 MONTHS</text><path d="M42 256 H850" stroke="{LINE}" stroke-width="1"/>'
 for i,(key,value) in enumerate(zip(keys,values)):
  x=48+i*67; height=142*value/maximum; y=255-height; fill=CYAN if value==maximum and value>0 else "#59636B"
  body+=f'<rect x="{x}" y="{y:.1f}" width="42" height="{height:.1f}" rx="6" fill="{fill}"><animate attributeName="height" from="0" to="{height:.1f}" dur=".65s" begin="{i*.045:.2f}s" fill="freeze"/></rect>'
  if value: body+=f'<text x="{x+21}" y="{y-8:.1f}" text-anchor="middle" fill="{INK}" font-size="10">{value}</text>'
  body+=f'<text x="{x+21}" y="278" text-anchor="middle" fill="{TAUPE}" font-size="10">{datetime.strptime(key,"%Y-%m").strftime("%b")}</text>'
 busy_date=busiest.get("date","—")
 try: busy_date=datetime.strptime(busy_date,"%Y-%m-%d").strftime("%d %b")
 except ValueError: pass
 busy_count=int(busiest.get("contributionCount",0))
 metrics=[(900,100,str(total),"CONTRIBUTIONS"),(1045,100,str(active),"ACTIVE DAYS"),(900,181,str(current),"CURRENT STREAK"),(1045,181,str(best),"BEST STREAK"),(900,253,str(busy_count),f"BUSIEST DAY · {busy_date}")]
 for x,y,value,label in metrics: body+=f'<text x="{x}" y="{y}" fill="{CYAN}" font-size="31" class="serif">{escape(value)}</text><text x="{x}" y="{y+19}" fill="{TAUPE}" font-size="10">{escape(label)}</text>'
 body+=f'<text x="42" y="310" fill="{TAUPE}" font-size="10">PEAK MONTH · {escape(max(keys,key=lambda k:monthly.get(k,0)))} · {max(values or [0])} CONTRIBUTIONS</text>'
 save("activity.svg",1200,330,"GitHub monthly activity and contribution analysis",body)
def render_heatmap(total,counts):
 start=date.today()-timedelta(days=363); start-=timedelta(days=start.weekday()); maximum=max(counts.values() or [1]) or 1
 palette=["#25282B","#39464A","#526B70","#398B9A",CYAN]
 body=f'<rect width="1200" height="205" rx="22" fill="{BG}" stroke="{LINE}"/><text x="38" y="37" fill="{INK}" font-size="23" class="serif">Consistency, in cyan.</text><text x="38" y="58" fill="{TAUPE}" font-size="11" letter-spacing="1">DAILY CONTRIBUTIONS · LAST 52 WEEKS</text>'
 month_seen=set()
 for i in range(364):
  day=start+timedelta(days=i); col=i//7
  if day.day<=7 and day.month not in month_seen:
   month_seen.add(day.month); body+=f'<text x="{40+col*15}" y="78" fill="{TAUPE}" font-size="9">{day.strftime("%b")}</text>'
  count=counts.get(day.isoformat(),0); level=0 if count==0 else min(4,1+int(4*count/maximum))
  body+=f'<rect x="{40+col*15}" y="{86+(i%7)*13}" width="10" height="9" rx="2" fill="{palette[level]}"><title>{day.isoformat()}: {count} contributions</title></rect>'
 body+=f'<text x="1038" y="117" fill="{INK}" font-size="31" class="serif">{total:,}</text><text x="1038" y="137" fill="{TAUPE}" font-size="10">IN THE LAST YEAR</text>'
 for j,color in enumerate(palette): body+=f'<rect x="{1038+j*22}" y="157" width="14" height="10" rx="2" fill="{color}"/>'
 body+=f'<text x="1038" y="183" fill="{TAUPE}" font-size="9">LESS</text><text x="1132" y="183" fill="{TAUPE}" font-size="9">MORE</text>'
 save("heatmap.svg",1200,205,"GitHub contribution heatmap",body)
def render_languages(repos):
 totals=defaultdict(int)
 for repo in repos.values():
  for language,amount in repo.get("languages",{}).items(): totals[language]+=int(amount)
 top=sorted(totals.items(),key=lambda x:x[1],reverse=True)[:6]; total_bytes=sum(totals.values()) or 1
 body=f'<rect width="1200" height="225" rx="22" fill="{PANEL}" stroke="{LINE}"/><text x="42" y="43" fill="{INK}" font-size="25" class="serif">The code behind the work</text><text x="42" y="69" fill="{TAUPE}" font-size="11" letter-spacing="1">LANGUAGE DISTRIBUTION · FEATURED PUBLIC REPOSITORIES</text>'
 colors=[CYAN,"#BEB09A","#8D9AA4","#68727D","#A7B8B4","#59636B"]
 for i,(language,amount) in enumerate(top):
  y=104+i*19; width=560*amount/total_bytes
  body+=f'<text x="42" y="{y+10}" fill="{INK}" font-size="11">{escape(language)}</text><rect x="170" y="{y}" width="560" height="10" rx="5" fill="#25282B"/><rect x="170" y="{y}" width="{width:.1f}" height="10" rx="5" fill="{colors[i]}"/><text x="750" y="{y+10}" fill="{TAUPE}" font-size="10">{100*amount/total_bytes:.1f}%</text>'
 if not top: body+=f'<text x="42" y="125" fill="{TAUPE}" font-size="14">Language data will appear after the first repository sync.</text>'
 body+=f'<text x="900" y="120" fill="{CYAN}" font-size="32" class="serif">{len(totals)}</text><text x="900" y="141" fill="{TAUPE}" font-size="11">LANGUAGES DETECTED</text>'
 save("languages.svg",1200,225,"Programming language distribution",body)
def render_tile(file,label,subtitle,num,start,end,fg):
 body=f'<defs><linearGradient id="tilebg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/></linearGradient></defs><rect width="380" height="190" rx="20" fill="url(#tilebg)"/><path d="M24 14 H356" stroke="{CYAN}" stroke-width="2" opacity=".9"/><text x="28" y="42" fill="{fg}" font-size="12" letter-spacing="3">{escape(label)}</text><text x="28" y="91" fill="{fg}" font-size="27" class="serif">{escape(subtitle)}</text><text x="28" y="154" fill="{fg}" font-size="12">EXPLORE PROJECTS ↗</text><text x="335" y="166" text-anchor="end" fill="{CYAN if fg==INK else INK}" font-size="44" class="serif">{num}</text>'
 save(file,380,190,label,body)
def render_repo_cards(repos):
 items=[("repo-traffic.svg","SMART_TRAFFIC_MANAGEMENT_SYSTEM","Smart Traffic Management","Predictive congestion and alternate routing for Nagpur.","React · FastAPI · XGBoost · Leaflet"),("repo-ipl.svg","IPL_CRUNCH","IPL Crunch ’26","Ball-by-ball IPL analytics from raw Cricsheet JSON.","Python · Pandas · Plotly · SciPy"),("repo-blindspot.svg","PROMPTWARS","The Blind Spot","AI-assisted analysis of assumptions and decision biases.","JavaScript · HTML · CSS"),("repo-rental.svg","VEHICLE-RENTAL-SYSTEM","Vehicle Rental System","Flask app with booking rules and automated tests.","Python · Flask · SQLite · pytest")]
 for i,(file,key,title,desc,stack) in enumerate(items,1):
  data=repos.get(key,{}); stars=int(data.get("stargazers_count",0)); forks=int(data.get("forks_count",0)); updated=data.get("updated_at","—")
  try: updated=datetime.fromisoformat(updated.replace("Z","+00:00")).strftime("%b %Y")
  except (ValueError,TypeError): updated="—"
  body=f'<defs><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#202329"/><stop offset="1" stop-color="#111317"/></linearGradient></defs><rect width="560" height="170" rx="18" fill="url(#card)" stroke="{LINE}"/><rect x="0" y="22" width="3" height="126" rx="2" fill="{CYAN}"/><text x="28" y="37" fill="{CYAN}" font-size="10">FEATURED PROJECT / {i:02d}</text><text x="28" y="72" fill="{INK}" font-size="25" class="serif">{escape(title)}</text><text x="28" y="98" fill="{TAUPE}" font-size="12">{escape(desc)}</text><text x="28" y="125" fill="{CYAN}" font-size="11">{escape(stack)}</text><text x="28" y="151" fill="{TAUPE}" font-size="10">★ {stars}   FORKS {forks}   UPDATED {escape(updated)}</text>'
  save(file,560,170,title,body)
def main():
 contrib=read_json(DATA,{"total":0,"weeks":[]}); days=flatten(contrib); counts,active,current,best,busiest,monthly=activity_stats(days); total=int(contrib.get("total",sum(counts.values()))); repos=read_json(REPOS,{})
 render_hero(total); render_activity(total,active,current,best,busiest,monthly); render_heatmap(total,counts); render_languages(repos)
 render_tile("build.svg","BUILD","Software & systems","01",BG,PANEL,INK)
 render_tile("data.svg","DATA","ML & analytics","02","#F0E8DA","#D7CBBB",BG)
 render_tile("explore.svg","EXPLORE","Ideas & research","03",CYAN,"#279EAD",BG)
 render_repo_cards(repos)
 print(f"Rendered profile cards: {len(days)} contribution days, {total} contributions, {len(repos)} repositories.")
if __name__=="__main__": main()

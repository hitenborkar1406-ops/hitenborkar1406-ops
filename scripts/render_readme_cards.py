#!/usr/bin/env python3
import json, base64
from pathlib import Path
from collections import defaultdict
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"cards"; DATA=ROOT/"data"/"contributions.json"; REPOS=ROOT/"data"/"repos.json"
BG,INK,CYAN,BLUE,TAUPE,LINE="#F1F3F4","#20252B","#E4002B","#9CC6E0","#53616B","#D4DDE3"; PANEL="#F1F3F4"
ASCII_ART=ROOT/"data"/"ascii_art.txt"
def svg(w,h,title,body):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title><defs><style>text{{font-family:Inter,Arial,sans-serif}}.serif{{font-family:Georgia,serif}}@keyframes rise{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}@keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}@keyframes reveal{{from{{opacity:0}}to{{opacity:1}}}}.portrait-row{{opacity:1}}.enter{{animation:rise .8s ease both}}.pulse{{animation:pulse 2.8s ease-in-out infinite}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}}}</style></defs>{body}</svg>'''
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
 photo_path=ROOT/"assets"/"hero-anime.webp"
 if not photo_path.exists():
  raise FileNotFoundError(f"Missing hero portrait image: {photo_path}")
 photo_b64=base64.b64encode(photo_path.read_bytes()).decode("ascii")
 image_x,image_y,image_size=690,105,420
 body=f'<defs><clipPath id="portraitClip"><rect x="{image_x}" y="{image_y}" width="{image_size}" height="{image_size}" rx="8"/></clipPath></defs><rect width="1200" height="630" rx="24" fill="{BG}"/><text x="58" y="72" fill="{CYAN}" font-size="13" letter-spacing="4">HITEN BORKAR / ENGINEERING PORTFOLIO</text><text x="58" y="174" fill="{INK}" font-size="58" class="serif enter">Building systems</text><text x="58" y="238" fill="{INK}" font-size="46" class="serif enter">that solve real problems.</text><text x="61" y="292" fill="{TAUPE}" font-size="17">Computer Science Engineer</text><text x="61" y="320" fill="{TAUPE}" font-size="17">Full-stack · Applied ML · Data</text><path d="M60 358 H535" stroke="{LINE}" stroke-width="1"/><text x="60" y="397" fill="{CYAN}" font-size="12" letter-spacing="2">LAST 12 MONTHS ON GITHUB</text><text x="60" y="465" fill="{INK}" font-size="54" class="serif">{total:,}</text><text x="60" y="495" fill="{TAUPE}" font-size="12">CONTRIBUTIONS</text><text x="60" y="570" fill="{TAUPE}" font-size="11">POLAR WHITE / GLACIER BLUE / RACING RED</text><image x="{image_x}" y="{image_y}" width="{image_size}" height="{image_size}" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)" href="data:image/webp;base64,{photo_b64}"/>'
 save("hero.svg",1200,630,"Hiten Borkar — anime portrait and engineering portfolio",body)

def render_activity(total,days_count,active,current,best,busiest,monthly):
 keys=sorted(monthly)[-12:]
 if not keys: keys=[(date.today()-timedelta(days=30*i)).strftime("%Y-%m") for i in range(11,-1,-1)]
 values=[monthly.get(k,0) for k in keys]
 maximum=max(values or [1]) or 1
 best_month=max(keys,key=lambda k:monthly.get(k,0))
 best_value=monthly.get(best_month,0)
 body=f'<rect width="1200" height="430" rx="22" fill="{PANEL}" stroke="{LINE}"/><text x="54" y="52" fill="{TAUPE}" font-size="13" letter-spacing="2">THE LAST 12 MONTHS ON GITHUB</text><text x="54" y="132" fill="{INK}" font-size="65" class="serif">{total:,}</text><text x="258" y="132" fill="{CYAN}" font-size="65" font-style="italic" class="serif">contributions</text><path d="M835 55 V385" stroke="{LINE}" stroke-width="1"/>'
 baseline=342
 for i,(key,value) in enumerate(zip(keys,values)):
  x=58+i*63
  height=0 if maximum==0 or value==0 else max(8,190*(value/maximum)**0.62)
  y=baseline-height
  fill=CYAN if key==best_month and value>0 else BLUE
  body+=f'<rect x="{x}" y="{y:.1f}" width="48" height="{height:.1f}" rx="6" fill="{fill}"><animate attributeName="height" from="0" to="{height:.1f}" dur=".7s" begin="{i*.04:.2f}s" fill="freeze"/></rect>'
  if key==best_month and value>0:
   body+=f'<text x="{x+24}" y="{y-12:.1f}" text-anchor="middle" fill="{CYAN}" font-size="13">{value:,}</text>'
  body+=f'<text x="{x+24}" y="374" text-anchor="middle" fill="{TAUPE}" font-size="12">{datetime.strptime(key,"%Y-%m").strftime("%b")}</text>'
 busy_date=busiest.get("date","—")
 try: busy_date=datetime.strptime(busy_date,"%Y-%m-%d").strftime("%d %b")
 except (ValueError,TypeError): pass
 busy_count=int(busiest.get("contributionCount",0))
 right=[
  (875,130,str(current),"CURRENT STREAK · AND LONGEST"),
  (875,252,f"{active} / {days_count}","DAYS WITH A CONTRIBUTION"),
  (875,365,str(busy_count),f"BUSIEST DAY · {busy_date}")
 ]
 for x,y,value,label in right:
  body+=f'<text x="{x}" y="{y}" fill="{INK}" font-size="48" class="serif">{escape(value)}</text><text x="{x}" y="{y+23}" fill="{TAUPE}" font-size="12">{escape(label)}</text>'
 body+=f'<text x="54" y="410" fill="{TAUPE}" font-size="10" letter-spacing="1">PEAK MONTH · {datetime.strptime(best_month,"%Y-%m").strftime("%B %Y").upper()} · {best_value:,} CONTRIBUTIONS</text>'
 save("activity.svg",1200,430,"GitHub activity over the last 12 months",body)

def render_heatmap(total,counts):
 today=date.today()
 start=today-timedelta(days=363)
 start-=timedelta(days=(start.weekday()+1)%7)
 day_count=(today-start).days+1
 columns=(day_count+6)//7
 maximum=max(counts.values() or [1]) or 1
 palette=["#E3E8EC","#D2E3EF","#B6D7EB","#9CC6E0","#E4002B"]
 body=f'<rect width="1200" height="270" rx="22" fill="{PANEL}" stroke="{LINE}"/><text x="42" y="48" fill="{INK}" font-size="30" class="serif">Every day, <tspan fill="{CYAN}" font-style="italic">in sunshine.</tspan></text><text x="1015" y="45" fill="{TAUPE}" font-size="11" letter-spacing="2">REFRESHED DAILY</text><text x="42" y="77" fill="{TAUPE}" font-size="10" letter-spacing="1">LAST 52 WEEKS · DAILY CONTRIBUTIONS</text>'
 month_seen=set()
 for offset in range(day_count):
  day=start+timedelta(days=offset)
  col=offset//7
  row=(day.weekday()+1)%7
  x=42+col*17
  y=96+row*17
  if day.day==1 and day.month not in month_seen:
   month_seen.add(day.month)
   body+=f'<text x="{x}" y="91" fill="{TAUPE}" font-size="9">{day.strftime("%b")}</text>'
  count=counts.get(day.isoformat(),0)
  level=0 if count==0 else 1 if count<=2 else 2 if count<=5 else 3 if count<=10 else 4
  day_label=day.strftime("%A, %B %-d, %Y")
  contribution_label=f"{count} GitHub contribution" + ("" if count==1 else "s")
  body+=f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{palette[level]}" aria-label="{day_label}: {contribution_label}"><title>{day_label}: {contribution_label}</title></rect>'
 body+=f'<text x="1015" y="135" fill="{CYAN}" font-size="34" class="serif">{total:,}</text><text x="1015" y="155" fill="{TAUPE}" font-size="10">CONTRIBUTIONS</text><text x="1015" y="192" fill="{TAUPE}" font-size="10">LESS</text>'
 for j,color in enumerate(palette):
  body+=f'<rect x="{1050+j*22}" y="180" width="15" height="12" rx="3" fill="{color}"/>'
 body+=f'<text x="1162" y="192" fill="{TAUPE}" font-size="10">MORE</text><text x="42" y="252" fill="{TAUPE}" font-size="10">SUNDAY</text><text x="122" y="252" fill="{TAUPE}" font-size="10">MONDAY → SATURDAY</text>'
 save("heatmap.svg",1200,270,"GitHub contribution heatmap — refreshed daily",body)

def render_heatmap_html(total,days):
 # GitHub README images do not expose per-cell SVG <title> reliably.
 # Individual HTML <img title="..."> elements provide native day-by-day hover tooltips.
 today=max((date.fromisoformat(d["date"]) for d in days),default=date.today())
 start=today-timedelta(days=363)
 start-=timedelta(days=(start.weekday()+1)%7)
 day_map={d["date"]:int(d.get("contributionCount",0)) for d in days}
 palette=["#E3E8EC","#D2E3EF","#B6D7EB","#9CC6E0","#E4002B"]
 for level,color in enumerate(palette):
  body=f'<rect width="16" height="16" rx="4" fill="{color}"/>'
  save(f"heatmap-cell-{level}.svg",16,16,f"Contribution level {level}",body)
 weeks=((today-start).days+7)//7
 version=today.strftime("%Y%m%d")
 rows=[]
 month_cells=[]
 for col in range(weeks):
  week_start=start+timedelta(days=col*7)
  label=week_start.strftime("%b") if week_start.day<=7 else ""
  month_cells.append(f'<td align="left"><sub>{label}</sub></td>')
 rows.append("<tr>"+"".join(month_cells)+"</tr>")
 for weekday in range(7):
  cells=[]
  for col in range(weeks):
   day=start+timedelta(days=col*7+weekday)
   if day>today or day.isoformat() not in day_map:
    cells.append("<td></td>")
    continue
   count=day_map[day.isoformat()]
   level=0 if count==0 else 1 if count<=2 else 2 if count<=5 else 3 if count<=10 else 4
   label=day.strftime("%A, %B %-d, %Y")
   contribution=f"{count} contribution" + ("" if count==1 else "s")
   tooltip=f"{label}: {contribution}"
   src=f"cards/heatmap-cell-{level}.svg?v={version}"
   cells.append(f'<td title="{escape(tooltip, {chr(34): "&quot;"})}" align="center"><img src="{src}" width="13" height="13" alt="" title="{escape(tooltip, {chr(34): "&quot;"})}"/></td>')
  rows.append("<tr>"+"".join(cells)+"</tr>")
 table='<table border="0" cellpadding="1" cellspacing="2">\n'+"\n".join(rows)+"\n</table>"
 block=f'<p><strong>Every day, <em>in sunshine.</em></strong> &nbsp; <sub>LAST 52 WEEKS · DAILY CONTRIBUTIONS · REFRESHED DAILY</sub></p>\n<p><strong>{total:,}</strong> contributions</p>\n'+table
 readme=ROOT/"README.md"
 if readme.exists():
  content=readme.read_text(encoding="utf-8")
  begin="<!-- DAILY-HEATMAP:START -->"; end="<!-- DAILY-HEATMAP:END -->"
  if begin in content and end in content:
   before,rest=content.split(begin,1); _,after=rest.split(end,1)
   readme.write_text(before+begin+"\n"+block+"\n"+end+after,encoding="utf-8")
  else:
   print("README heatmap markers missing; skipped inline tooltip grid update.")

def render_languages(repos):
 totals=defaultdict(int)
 for repo in repos.values():
  for language,amount in repo.get("languages",{}).items(): totals[language]+=int(amount)
 top=sorted(totals.items(),key=lambda x:x[1],reverse=True)[:6]; total_bytes=sum(totals.values()) or 1
 body=f'<rect width="1200" height="225" rx="22" fill="{PANEL}" stroke="{LINE}"/><text x="42" y="43" fill="{INK}" font-size="25" class="serif">The code behind the work</text><text x="42" y="69" fill="{TAUPE}" font-size="11" letter-spacing="1">LANGUAGE DISTRIBUTION · FEATURED PUBLIC REPOSITORIES</text>'
 colors=[BLUE,"#86B8D8",CYAN,BLUE,"#6FA7CB",BLUE]
 for i,(language,amount) in enumerate(top):
  y=104+i*19; width=560*amount/total_bytes
  body+=f'<text x="42" y="{y+10}" fill="{INK}" font-size="11">{escape(language)}</text><rect x="170" y="{y}" width="560" height="10" rx="5" fill="#DCE4E9"/><rect x="170" y="{y}" width="{width:.1f}" height="10" rx="5" fill="{colors[i]}"/><text x="750" y="{y+10}" fill="{TAUPE}" font-size="10">{100*amount/total_bytes:.1f}%</text>'
 if not top: body+=f'<text x="42" y="125" fill="{TAUPE}" font-size="14">Language data will appear after the first repository sync.</text>'
 body+=f'<text x="900" y="120" fill="{CYAN}" font-size="32" class="serif">{len(totals)}</text><text x="900" y="141" fill="{TAUPE}" font-size="11">LANGUAGES DETECTED</text>'
 save("languages.svg",1200,225,"Programming language distribution",body)
def render_tile(file,label,subtitle,num,start,end,fg):
 body=f'<defs><linearGradient id="tilebg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/></linearGradient></defs><rect width="380" height="190" rx="20" fill="url(#tilebg)"/><path d="M24 14 H356" stroke="{CYAN}" stroke-width="2" opacity=".9"/><text x="28" y="42" fill="{fg}" font-size="12" letter-spacing="3">{escape(label)}</text><text x="28" y="91" fill="{fg}" font-size="27" class="serif">{escape(subtitle)}</text><text x="28" y="154" fill="{fg}" font-size="12">EXPLORE PROJECTS ↗</text><text x="335" y="166" text-anchor="end" fill="{CYAN}" font-size="44" class="serif">{num}</text>'
 save(file,380,190,label,body)
def render_repo_cards(repos):
 items=[("repo-traffic.svg","SMART_TRAFFIC_MANAGEMENT_SYSTEM","Smart Traffic Management","Predictive congestion and alternate routing for Nagpur.","React · FastAPI · XGBoost · Leaflet"),("repo-ipl.svg","IPL_CRUNCH","IPL Crunch ’26","Ball-by-ball IPL analytics from raw Cricsheet JSON.","Python · Pandas · Plotly · SciPy"),("repo-blindspot.svg","PROMPTWARS","The Blind Spot","AI-assisted analysis of assumptions and decision biases.","JavaScript · HTML · CSS"),("repo-rental.svg","VEHICLE-RENTAL-SYSTEM","Vehicle Rental System","Flask app with booking rules and automated tests.","Python · Flask · SQLite · pytest")]
 for i,(file,key,title,desc,stack) in enumerate(items,1):
  data=repos.get(key,{}); stars=int(data.get("stargazers_count",0)); forks=int(data.get("forks_count",0)); updated=data.get("updated_at","—")
  try: updated=datetime.fromisoformat(updated.replace("Z","+00:00")).strftime("%b %Y")
  except (ValueError,TypeError): updated="—"
  body=f'<defs><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F1F3F4"/><stop offset="1" stop-color="#E4EEF4"/></linearGradient></defs><rect width="560" height="170" rx="18" fill="url(#card)" stroke="{LINE}"/><rect x="0" y="22" width="3" height="126" rx="2" fill="{CYAN}"/><text x="28" y="37" fill="{CYAN}" font-size="10">FEATURED PROJECT / {i:02d}</text><text x="28" y="72" fill="{INK}" font-size="25" class="serif">{escape(title)}</text><text x="28" y="98" fill="{TAUPE}" font-size="12">{escape(desc)}</text><text x="28" y="125" fill="{CYAN}" font-size="11">{escape(stack)}</text><text x="28" y="151" fill="{TAUPE}" font-size="10">★ {stars}   FORKS {forks}   UPDATED {escape(updated)}</text>'
  save(file,560,170,title,body)
def main():
 contrib=read_json(DATA,{"total":0,"weeks":[]}); days=flatten(contrib); counts,active,current,best,busiest,monthly=activity_stats(days); total=int(contrib.get("total",sum(counts.values()))); repos=read_json(REPOS,{})
 render_hero(total); render_activity(total,len(days),active,current,best,busiest,monthly); render_heatmap(total,counts); render_heatmap_html(total,days); render_languages(repos)
 render_tile("build.svg","BUILD","Software & systems","01","#F1F3F4","#E3EEF5","#20252B")
 render_tile("data.svg","DATA","ML & analytics","02","#F1F3F4","#D8EAF5","#20252B")
 render_tile("explore.svg","EXPLORE","Ideas & research","03","#F1F3F4","#C7E0F0","#20252B")
 render_repo_cards(repos)
 print(f"Rendered profile cards: {len(days)} contribution days, {total} contributions, {len(repos)} repositories.")
if __name__=="__main__": main()

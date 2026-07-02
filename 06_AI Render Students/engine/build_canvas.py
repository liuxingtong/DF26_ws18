"""
build_canvas.py 交互式 HTML 画布:orbit 找角度,存角度,导出 massing / ControlNet 图。
生成自含单档 out/<slug>/canvas.html(内联 Three.js):真实卫星底 + 各体制体块;
导出模式 massing / depth / normal / segmentation / canny 作 AI 参考图或 ControlNet 条件图。
几何由 05 实算注入,零 AI,不联网(除抓一次卫星底)。
跑:python run.py canvas [slug]
"""
import base64, json, sys, os
from pathlib import Path
HERE = Path(__file__).resolve().parent           # engine/
ROOT = HERE.parent                                # 06 根
sys.path.insert(0, str(HERE))                     # engine 在路径上,可 import settings / ws05
import settings
import ws05
import prompt_gen
import massing as _massing   # 复用卫星抓取

OUT = ROOT / "out"
WEB = ROOT / "web"                    # 内置 three.min.js / OrbitControls.js


def _origin(recs):
    minx = min(p.bounds[0] for r in recs for p in ws05.C._polys(r["geom"]))
    miny = min(p.bounds[1] for r in recs for p in ws05.C._polys(r["geom"]))
    maxx = max(p.bounds[2] for r in recs for p in ws05.C._polys(r["geom"]))
    maxy = max(p.bounds[3] for r in recs for p in ws05.C._polys(r["geom"]))
    return minx, miny, maxx, maxy


def _regime_polys(recs, ox, oy, simplify=1.0):
    """study 楼(整个街区)→ 局部坐标多边形,in=1(全实心)。"""
    out = []
    for r in recs:
        for poly in ws05.C._polys(r["geom"]):
            ps = poly.simplify(simplify)
            xy = [[round(x - ox, 1), round(y - oy, 1)] for x, y in list(ps.exterior.coords)[:-1]]
            if len(xy) >= 3:
                out.append({"p": xy, "h": round(float(r["h"]), 1), "sh": r["sh"], "in": 1})
    return out


def _context_polys(recs, ox, oy, simplify=2.0):
    """周边语境楼 → 局部坐标多边形(粗简化省档案;跨体制不变,只嵌一次)。无 sh、in=0(透明)。"""
    out = []
    for r in recs:
        for poly in ws05.C._polys(r["geom"]):
            ps = poly.simplify(simplify)
            xy = [[round(x - ox, 1), round(y - oy, 1)] for x, y in list(ps.exterior.coords)[:-1]]
            if len(xy) >= 3:
                out.append({"p": xy, "h": round(float(r["h"]), 1)})
    return out


def build_geometry(slug, regimes=None):
    regimes = regimes or settings.REGIMES
    rr, regs = ws05.regime_recs(slug, regimes)
    cf_rr, cf_scen = ws05.counterfactual_recs(slug)
    context_recs = ws05.load_context_recs(slug)                  # 周边语境(透明,跨体制不变),没有则 []
    base = rr.get("current") or next(iter(rr.values()))
    smnx, smny, smxx, smxy = _origin(base)                       # study bounds(现状 footprint,稳定)
    # 原点 = study+周边 最小角;全场景 bounds = study∪周边
    if context_recs:
        cmnx, cmny, cmxx, cmxy = _origin(context_recs)
        ox, oy = min(smnx, cmnx), min(smny, cmny)
        fmxx, fmxy = max(smxx, cmxx), max(smxy, cmxy)
    else:
        ox, oy = smnx, smny
        fmxx, fmxy = smxx, smxy
    data = {name: _regime_polys(recs, ox, oy) for name, recs in rr.items()}
    cf_keys = []
    for name, recs in cf_rr.items():
        key = "cf_" + name
        cf_keys.append(key)
        data[key] = _regime_polys(recs, ox, oy)
    context = _context_polys(context_recs, ox, oy) if context_recs else []
    labels = {name: ws05.regime_label(regs, name) for name in rr}
    labels.update({"cf_" + name: ws05.counterfactual_label(cf_scen, name) for name in cf_rr})
    # 卫星底 = 全场景(study + 周边环),factor=1;local 相对 (ox,oy)
    sat, satext = None, None
    try:
        sat, local = ws05.C.ground_sat(ox, oy, fmxx, fmxy, OUT / slug / "ground_scene.jpg", factor=1.0)
        satext = [local[0], local[1], local[2], local[3]]        # ground_sat local 已相对 (ox,oy)
    except Exception as e:
        print("  卫星底跳过:", e)
    rings = ws05.C.study_poly_rings(slug)                        # study 街区多边形(UTM 环)= 红线
    study_poly = ([[[round(x - ox, 1), round(y - oy, 1)] for x, y in ring] for ring in rings]
                  if rings else None)
    regime_keys = list(rr.keys())
    return {"regimes": regime_keys + cf_keys, "regimeKeys": regime_keys, "counterfactualKeys": cf_keys,
            "labels": labels, "colors": ws05.C.SH_COLOR,
            "sh_label": {k: v.split("(")[0] for k, v in ws05.C.SH_LABEL.items()},
            "data": data, "context": context, "sat": sat, "satExtent": satext,
            "studyPoly": study_poly,
            "bounds": [smnx - ox, smny - oy, smxx - ox, smxy - oy],   # study extent(相机取景)
            "scene": [0, 0, fmxx - ox, fmxy - oy]}                    # 全场景(深度范围)


CSS = """
:root{--accent:#0f5e63;--ink:#1a1f22;--muted:#717b80;--line:#e6e9ea;--bg:#eef1f0;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.6 "Helvetica Neue","PingFang SC","Microsoft YaHei",system-ui,sans-serif;height:100vh;overflow:hidden;}
#stage{position:fixed;inset:0;} #cv{width:100%;height:100%;display:block;}
.panel{position:fixed;top:12px;left:12px;width:270px;max-height:calc(100vh - 24px);overflow:auto;
 background:rgba(255,255,255,.94);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:12px;
 padding:12px 13px;box-shadow:0 2px 12px rgba(0,0,0,.1);}
.panel h1{font-size:14px;margin:0 0 3px;} .panel .sub{font-size:11.5px;color:var(--muted);margin:0 0 10px;}
.grp{margin:10px 0 4px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.row{display:flex;flex-wrap:wrap;gap:5px;}
button{font:inherit;font-size:12px;border:1px solid var(--line);background:#fff;color:var(--ink);
 border-radius:16px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,.05);}
button:hover{background:#f2f6f6;} button.on{background:var(--accent);border-color:var(--accent);color:#fff;}
button.big{width:100%;border-radius:9px;padding:8px;margin-top:5px;font-weight:600;}
button.acc{background:var(--accent);color:#fff;border-color:var(--accent);}
.ang{display:flex;align-items:center;gap:6px;margin-top:5px;font-size:12px;}
.ang a{color:var(--accent);cursor:pointer;text-decoration:underline;flex:1;}
.ang .x{color:#c0654a;cursor:pointer;}
.legend{display:flex;flex-wrap:wrap;gap:6px 10px;margin-top:6px;font-size:11.5px;}
.legend i{width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:-1px;}
.hint{position:fixed;right:12px;bottom:10px;font-size:11.5px;color:#5a6468;background:rgba(255,255,255,.7);
 padding:2px 8px;border-radius:6px;} #prm{font-size:11.5px;color:#333;margin-top:6px;white-space:pre-wrap;
 max-height:120px;overflow:auto;background:#f6f8f8;border:1px solid var(--line);border-radius:7px;padding:7px;}
.note{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.5;}
.rep{display:inline-block;margin:0 0 4px;color:var(--accent);text-decoration:none;font-size:12px;
 border:1px solid var(--line);border-radius:14px;padding:4px 11px;background:#fff;}
.rep:hover{background:#f2f6f6;}
"""


def viewer_js(geom):
    return "const GEOM=%s;\n" % json.dumps(geom, separators=(",", ":")) + r"""
const COL=GEOM.colors;
let scene,cam,renderer,controls,ground,boundary,groups={},cur=GEOM.regimes[0],mode="massing",saved=[];
let matDepth,matNormal,edges=[],ctxMeshes=[],ctxEdges=[];
const edgeMat=new THREE.LineBasicMaterial({color:0xffffff});   // canny:白色硬边
function init(){
  const st=document.getElementById("stage"),w=st.clientWidth,h=st.clientHeight;
  scene=new THREE.Scene(); scene.background=new THREE.Color(0xeef1f0);
  cam=new THREE.PerspectiveCamera(48,w/h,1,20000); cam.up.set(0,0,1);
  renderer=new THREE.WebGLRenderer({canvas:document.getElementById("cv"),antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(w,h);
  if(THREE.sRGBEncoding!==undefined)renderer.outputEncoding=THREE.sRGBEncoding;
  scene.add(new THREE.HemisphereLight(0xffffff,0xc6d0d3,0.95));
  scene.add(new THREE.AmbientLight(0xffffff,0.45));
  const dl=new THREE.DirectionalLight(0xffffff,0.65); dl.position.set(0.6,-1,1.4); scene.add(dl);
  const b=GEOM.bounds, cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2, span=Math.max(b[2]-b[0],b[3]-b[1]);
  // 卫星地面
  if(GEOM.sat){const tx=new THREE.TextureLoader().load(GEOM.sat); if(THREE.sRGBEncoding!==undefined)tx.encoding=THREE.sRGBEncoding;
    const se=GEOM.satExtent, gw=se[2]-se[0], gh=se[3]-se[1];
    ground=new THREE.Mesh(new THREE.PlaneGeometry(gw,gh),new THREE.MeshBasicMaterial({map:tx}));
    ground.position.set((se[0]+se[2])/2,(se[1]+se[3])/2,-0.3); scene.add(ground);}
  // 红色研究范围边界 = study 街区多边形(整个 study 都实心),z 略高于地面
  if(GEOM.studyPoly){const zz=0.3; boundary=new THREE.Group();
    for(const ring of GEOM.studyPoly){
      const pts=ring.map(p=>new THREE.Vector3(p[0],p[1],zz));
      boundary.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0xe02424})));}
    scene.add(boundary);}
  // 各体制的体块(分组,切换可见)
  for(const name of GEOM.regimes){
    const g=new THREE.Group(); g.visible=(name===cur); scene.add(g); groups[name]=g;
    for(const r of GEOM.data[name]){
      const sh=new THREE.Shape(); r.p.forEach((pt,i)=> i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
      const geo=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
      const m=new THREE.MeshLambertMaterial({color:new THREE.Color(COL[r.sh]||"#c9c4bd")});
      const mesh=new THREE.Mesh(geo,m); mesh.scale.z=r.h; mesh.userData=r; g.add(mesh);
      const el=new THREE.LineSegments(new THREE.EdgesGeometry(geo,15),edgeMat);  // 硬边(随 mesh 缩放)
      el.visible=false; el.userData=r; mesh.add(el); edges.push(el);
    }
  }
  // 周边语境体块(透明,跨体制不变 → 只建一次,始终可见)
  if(GEOM.context && GEOM.context.length){const g=new THREE.Group(); scene.add(g);
    for(const r of GEOM.context){
      const sh=new THREE.Shape(); r.p.forEach((pt,i)=> i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
      const geo=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
      const m=new THREE.MeshLambertMaterial({color:new THREE.Color("#c9c4bd")});
      const mesh=new THREE.Mesh(geo,m); mesh.scale.z=r.h; mesh.userData={in:0,sh:"context"}; g.add(mesh); ctxMeshes.push(mesh);
      const el=new THREE.LineSegments(new THREE.EdgesGeometry(geo,15),edgeMat);
      el.visible=false; el.userData={in:0}; mesh.add(el); ctxEdges.push(el);
    }
  }
  // 深度:自定义 shader,把**场景实际距离范围**映射成灰阶(近=白、远=黑) 正经 ControlNet depth
  matDepth=new THREE.ShaderMaterial({uniforms:{uNear:{value:1},uFar:{value:1000}},
    vertexShader:"varying float vD; void main(){vec4 mv=modelViewMatrix*vec4(position,1.0); vD=-mv.z; gl_Position=projectionMatrix*mv;}",
    fragmentShader:"uniform float uNear,uFar; varying float vD; void main(){float d=clamp((vD-uNear)/(uFar-uNear),0.0,1.0); float g=1.0-d; gl_FragColor=vec4(g,g,g,1.0);}"});
  matNormal=new THREE.MeshNormalMaterial();
  cam.position.set(cx+span*0.5,cy-span*0.75,span*0.6);
  controls=new THREE.OrbitControls(cam,renderer.domElement); controls.target.set(cx,cy,30);
  controls.enableDamping=true; controls.dampingFactor=.08; controls.update();
  applyMode(); window.addEventListener("resize",onresize); animate();
}
function onresize(){const st=document.getElementById("stage");cam.aspect=st.clientWidth/st.clientHeight;
  cam.updateProjectionMatrix();renderer.setSize(st.clientWidth,st.clientHeight);}
function animate(){requestAnimationFrame(animate);controls.update();
  if(mode==="depth"){const s=GEOM.scene||GEOM.bounds,span=Math.max(s[2]-s[0],s[3]-s[1]);
    const dist=cam.position.distanceTo(controls.target);
    matDepth.uniforms.uNear.value=Math.max(1,dist-span*0.75); matDepth.uniforms.uFar.value=dist+span*0.75;}
  renderer.render(scene,cam);}
// —— 模式:材质切换(massing 素模 / depth / normal / segmentation)——
function styleMesh(m,massing,seg,canny){
  const inside=m.userData.in!==0;                          // in=1 study 实心 / in=0 周边透明
  if(massing){ m.material.color.set("#c9c4bd");
    m.material.transparent=!inside; m.material.opacity=inside?1.0:0.30; }
  else{ m.material.transparent=false; m.material.opacity=1.0;
    if(seg) m.material.color.set(COL[m.userData.sh]||"#999");
    else if(canny) m.material.color.set(0x000000); }       // 黑面遮挡,只留白色硬边
  m.material.needsUpdate=true;
}
function applyMode(){
  const massing=(mode==="massing"), seg=(mode==="segmentation"), canny=(mode==="canny");
  scene.overrideMaterial = (mode==="depth")?matDepth : (mode==="normal")?matNormal : null;
  if(ground) ground.visible = massing;                     // 只有 massing 显示卫星;条件图要干净底
  if(boundary) boundary.visible = massing;                 // 红线只在 massing 显示
  // 背景:massing 浅灰,normal/seg 白,depth/canny 黑
  scene.background=new THREE.Color(massing?0xeef1f0:((mode==="normal"||seg)?0xffffff:0x000000));
  for(const name in groups) for(const m of groups[name].children){ if(m.isMesh) styleMesh(m,massing,seg,canny); }
  for(const m of ctxMeshes) styleMesh(m,massing,seg,canny);   // 周边语境同规则(depth/normal/seg/canny 都含,给 ControlNet 语境)
  edgeMat.color.set(canny?0xffffff:0x2b2b2b);               // canny 白硬边;massing 深灰勾透明周边
  for(const el of edges) el.visible = canny;                        // study 实心:只有 canny 显硬边
  for(const el of ctxEdges) el.visible = canny || massing;          // 周边透明:massing 勾轮廓 + canny 硬边
  document.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("on",b.dataset.mode===mode));
}
function setRegime(name){cur=name; for(const k in groups)groups[k].visible=(k===cur);
  document.querySelectorAll("[data-reg]").forEach(b=>b.classList.toggle("on",b.dataset.reg===name));
  document.getElementById("prm").textContent=GEOM.prompts?GEOM.prompts[name]:"";}
function setMode(m){mode=m;applyMode();}
// —— 导出 ——
function dl(name){renderer.render(scene,cam);
  renderer.domElement.toBlob(bl=>{const a=document.createElement("a");a.href=URL.createObjectURL(bl);
    a.download=name;a.click();},"image/png");}
function exportCurrent(){dl(`${GEOM.slug}_${cur}_${mode}.png`);}
const MODES=["massing","depth","normal","segmentation","canny"];
async function exportAllModes(a){const keep=mode;
  for(const m of MODES){setMode(m);await new Promise(r=>setTimeout(r,120));dl(`${GEOM.slug}_${cur}_${a!==undefined?("ang"+a+"_"):""}${m}.png`);}
  setMode(keep);}
function saveAngle(){saved.push({p:cam.position.toArray(),t:controls.target.toArray()});renderAngles();}
function gotoAngle(i){const a=saved[i];cam.position.fromArray(a.p);controls.target.fromArray(a.t);controls.update();}
function delAngle(i){saved.splice(i,1);renderAngles();}
function renderAngles(){const el=document.getElementById("angs");el.innerHTML=saved.map((a,i)=>
  `<div class="ang"><a onclick="gotoAngle(${i})">角度 ${i+1}</a><span class="x" onclick="delAngle(${i})"></span></div>`).join("")||
  '<div class="note">还没保存角度。转到满意的视角,点「保存当前角度」。</div>';}
async function exportAllSaved(){if(!saved.length){alert("先保存至少一个角度");return;}
  for(let i=0;i<saved.length;i++){gotoAngle(i);await new Promise(r=>setTimeout(r,150));await exportAllModes(i+1);}}
window.addEventListener("DOMContentLoaded",()=>{init();
  document.querySelectorAll("[data-reg]").forEach(b=>b.onclick=()=>setRegime(b.dataset.reg));
  document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
  setRegime(cur);});
"""


HTML = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>07 %s — 互动画布:找角度 导出 massing / ControlNet</title>
<style>%s</style></head><body>
<div id="stage"><canvas id="cv"></canvas></div>
<div class="panel">
  <h1>%s 互动画布</h1>
  <p class="sub">拖拽转视角 保存角度 导出 massing / 深度 / 法线 / 分色 / 边缘(作 AI 参考图或 ControlNet 条件图)。</p>
  <a class="rep" href="report.html">看完整报告 report.html</a>

  <div class="grp">权力体制</div>
  <div class="row">%s</div>

  <div class="grp">反事实高度情景</div>
  <div class="row">%s</div>

  <div class="grp">导出模式</div>
  <div class="row">
    <button data-mode="massing" class="on">体块 massing</button>
    <button data-mode="depth">深度 depth</button>
    <button data-mode="normal">法线 normal</button>
    <button data-mode="segmentation">分色 seg</button>
    <button data-mode="canny">边缘 canny</button>
  </div>
  <div class="legend">%s</div>

  <div class="grp">角度</div>
  <button class="big acc" onclick="saveAngle()">保存当前角度</button>
  <div id="angs"></div>

  <div class="grp">导出</div>
  <button class="big" onclick="exportCurrent()">导出当前视图</button>
  <button class="big" onclick="exportAllModes()">当前角度 全部 5 模式</button>
  <button class="big" onclick="exportAllSaved()">所有保存角度 × 全部模式</button>

  <div class="grp">提示词(与导出图配对)</div>
  <div id="prm"></div>
  <div class="note">导出的 PNG 命名 <code>%s_&lt;体制&gt;_&lt;模式&gt;.png</code>;
  条件图(depth/normal/seg)不含卫星底、干净可直接喂 ControlNet。massing 含真实卫星地面。</div>
</div>
<div class="hint">拖拽=旋转 滚轮=缩放 右键=平移</div>
<script>%s</script>
<script>%s</script>
<script>%s</script>
</body></html>"""


def build(slug=None):
    slug = slug or settings.SLUG
    geom = build_geometry(slug)
    geom["slug"] = slug
    regime_prompts = {r: d["prompt"] for r, d in prompt_gen.build_all(slug, settings.REGIMES).items()}
    cf_prompts = {
        key: "反事实高度情景:%s。Footprint 与角色标签不变,只按 power_scenarios.yaml 重分配高度。"
        % geom["labels"][key]
        for key in geom.get("counterfactualKeys", [])
    }
    geom["prompts"] = {**regime_prompts, **cf_prompts}
    three = (WEB / "three.min.js").read_text(encoding="utf-8")
    orbit = (WEB / "OrbitControls.js").read_text(encoding="utf-8")
    place = geom["labels"].get(geom["regimes"][0], slug)
    site_name = ws05.C.site_meta(slug)["name"]
    reg_btns = "".join('<button data-reg="%s"%s>%s</button>' % (
        r, ' class="on"' if r == geom["regimes"][0] else "", geom["labels"][r]) for r in geom["regimeKeys"])
    cf_btns = "".join('<button data-reg="%s">%s</button>' % (r, geom["labels"][r])
                      for r in geom.get("counterfactualKeys", []))
    legend = "".join('<span><i style="background:%s"></i>%s</span>' % (geom["colors"][sh], geom["sh_label"].get(sh, sh))
                     for sh in ["state", "developer", "resident", "unknown"])
    html = HTML % (site_name, CSS, site_name, reg_btns, cf_btns, legend, slug, three, orbit, viewer_js(geom))
    p = OUT / slug / "canvas.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print("写了:", p.relative_to(ROOT), "| %.2f MB" % (p.stat().st_size / 1e6))
    return p


if __name__ == "__main__":
    try:                                   # Windows 控制台 cp950 会崩,强制 utf-8
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1:
        build(sys.argv[1])
    else:
        for s in settings.REPORT_SITES if hasattr(settings, "REPORT_SITES") else [settings.SLUG]:
            print("=== %s ===" % s); build(s)

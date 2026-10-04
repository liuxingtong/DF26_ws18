import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import { BarChart3, Check, ChevronLeft, ChevronRight, Download, Layers3, MapPin, Search, X } from 'lucide-react'
import ExperimentDashboard from './ExperimentDashboard'

const DATA_FILES = ['buildings', 'zones', 'streets', 'heritage_proxy', 'public_spaces']
const initialLayers = { buildings:true, zones:true, streets:true, heritage_proxy:true, official:true }

function useReviewData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([
      fetch('/data/review_cases.json').then(r => r.json()),
      ...DATA_FILES.map(name => fetch(`/data/${name}.geojson`).then(r => r.json()))
    ]).then(([review, ...layers]) => setData({ review, layers:Object.fromEntries(DATA_FILES.map((name,i)=>[name,layers[i]])) })).catch(e => setError(e.message))
  }, [])
  return { data, error }
}

function EvidenceRow({ label, children, strong=false }) {
  return <div className="evidence-row"><span>{label}</span><b className={strong ? 'accent-value' : ''}>{children || '—'}</b></div>
}

function ReviewMap({ data, selected, selectedBids, onToggleBid, layers }) {
  const host = useRef(null)
  const mapRef = useRef(null)
  const layerRef = useRef({})
  useEffect(() => {
    if (!host.current || mapRef.current) return
    const map = L.map(host.current, { zoomControl:false, attributionControl:false, preferCanvas:true })
    L.control.zoom({ position:'bottomright' }).addTo(map)
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])
  useEffect(() => {
    const map = mapRef.current
    if (!map || !data) return
    Object.values(layerRef.current).forEach(layer => map.removeLayer(layer))
    const candidateIds = new Set(selected?.candidates.map(c => c.bid) || [])
    const styleBuilding = feature => {
      const id = String(feature.properties.bid)
      if (selectedBids.includes(id)) return { color:'#1769e0', weight:2, fillColor:'#1769e0', fillOpacity:.78 }
      if (candidateIds.has(id)) return { color:'#d18100', weight:1.5, fillColor:'#ffd98e', fillOpacity:.62 }
      return { color:'#9ca6b5', weight:.45, fillColor:'#dfe4ea', fillOpacity:.6 }
    }
    layerRef.current.streets = L.geoJSON(data.layers.streets, { style:{ color:'#aab3bf', weight:2.2, opacity:.72 } })
    layerRef.current.zones = L.geoJSON(data.layers.zones, { style:{ color:'#468be8', weight:1.1, dashArray:'5 4', fillOpacity:0 } })
    layerRef.current.buildings = L.geoJSON(data.layers.buildings, { style:styleBuilding, onEachFeature:(feature, layer) => {
      const id=String(feature.properties.bid)
      layer.bindTooltip(`BID ${id} · ${feature.properties.stakeholder}`, { sticky:true })
      if(candidateIds.has(id)) layer.on('click',()=>onToggleBid(id))
    } })
    layerRef.current.heritage_proxy = L.geoJSON(data.layers.heritage_proxy, { style:{ color:'#9a4fbd', weight:1.1, fillColor:'#c998dc', fillOpacity:.18 } })
    layerRef.current.official = L.layerGroup(data.review.reviews.map(r => L.circleMarker([r.location[1],r.location[0]], { radius:r.id===selected?.id?7:4, color:r.review_required?'#d18100':'#2b8a5a', weight:2, fillColor:'#fff', fillOpacity:1 }).bindTooltip(`${r.name}<br>${r.address}`)))
    Object.entries(layerRef.current).forEach(([name,layer]) => { if(layers[name]) layer.addTo(map) })
    if(selected) map.setView([selected.location[1], selected.location[0]], 19, { animate:false })
    else map.fitBounds(layerRef.current.buildings.getBounds(), { padding:[20,20] })
  }, [data, selected, selectedBids, layers, onToggleBid])
  return <div className="map-host" ref={host} aria-label="打浦桥数据复核地图" />
}

function ReviewWorkspace({ onShowResults }) {
  const { data, error } = useReviewData()
  const [onlyAmbiguous, setOnlyAmbiguous] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [layerState, setLayerState] = useState(initialLayers)
  const [showLayers, setShowLayers] = useState(true)
  const [reviews, setReviews] = useState(() => JSON.parse(localStorage.getItem('dapuqiao-review-v3') || '{}'))
  const records = data?.review.reviews || []
  const visible = useMemo(() => records.filter(r => (!onlyAmbiguous || r.review_required) && `${r.name}${r.address}${r.id}`.toLowerCase().includes(search.toLowerCase())), [records, onlyAmbiguous, search])
  const selected = records.find(r => r.id === selectedId) || visible[0] || records[0]
  const current = reviews[selected?.id] || { status:'pending', bids:selected?.suggested_bids || [], note:'' }
  const reviewedCount = Object.values(reviews).filter(r => r.status !== 'pending').length

  useEffect(() => { if(selected && selected.id !== selectedId) setSelectedId(selected.id) }, [selected, selectedId])
  useEffect(() => { localStorage.setItem('dapuqiao-review-v3', JSON.stringify(reviews)) }, [reviews])
  const updateCurrent = patch => setReviews(prev => ({ ...prev, [selected.id]:{ ...current, ...patch } }))
  const toggleBid = bid => updateCurrent({ bids:current.bids.includes(bid) ? current.bids.filter(x=>x!==bid) : [...current.bids,bid] })
  const move = delta => {
    const i=visible.findIndex(r=>r.id===selected.id)
    const next=visible[(i+delta+visible.length)%visible.length]
    if(next) setSelectedId(next.id)
  }
  const exportReview = () => {
    const payload={ exported_at:new Date().toISOString(), source_generated_at:data.review.generated_at, reviews }
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='dapuqiao_review_annotations.json'; a.click(); URL.revokeObjectURL(a.href)
  }
  if(error) return <main className="loading error">数据加载失败：{error}</main>
  if(!data) return <main className="loading">正在加载本地空间数据…</main>

  return <div className="app-shell">
    <header className="topbar">
      <h1>打浦桥数据审核</h1>
      <div className="source-note">官方名录 · 高德地理编码 · 本地建筑轮廓</div>
      <label className="search"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="搜索名称、地址或编号" /></label>
      <button className="text-button active">审核</button>
      <button className="text-button" onClick={onShowResults}><BarChart3 size={16}/>实验结果</button>
      <button className="text-button" onClick={exportReview}><Download size={16}/>导出</button>
    </header>

    <aside className="queue">
      <label className="switch-row"><span>仅显示歧义项</span><input type="checkbox" checked={onlyAmbiguous} onChange={e=>setOnlyAmbiguous(e.target.checked)}/></label>
      <div className="queue-meta">{visible.length} 项待检查</div>
      <div className="queue-list">
        {visible.map(r => {
          const state=reviews[r.id]?.status || 'pending'
          return <button key={r.id} className={`queue-item ${r.id===selected.id?'selected':''}`} onClick={()=>setSelectedId(r.id)}>
            <span><strong>{r.name}</strong><small>{r.address}</small></span>
            <i className={`status ${state}`} aria-label={state}>{state==='accepted'?<Check size={14}/>:state==='excluded'?<X size={14}/>:''}</i>
          </button>
        })}
      </div>
    </aside>

    <section className="map-panel">
      <ReviewMap data={data} selected={selected} selectedBids={current.bids} onToggleBid={toggleBid} layers={layerState}/>
      <button className="layers-trigger" onClick={()=>setShowLayers(v=>!v)}><Layers3 size={16}/>图层</button>
      {showLayers && <div className="layers-menu">
        {[['buildings','建筑'],['zones','更新单元'],['heritage_proxy','现有遗产代理'],['official','官方点位'],['streets','道路']].map(([key,label])=><label key={key}><input type="checkbox" checked={layerState[key]} onChange={()=>setLayerState(s=>({...s,[key]:!s[key]}))}/>{label}</label>)}
      </div>}
    </section>

    <aside className="inspector">
      <div className="inspector-head"><div><span>遗产复核</span><h2>{selected.name}</h2></div><div className="pager"><button onClick={()=>move(-1)} aria-label="上一项"><ChevronLeft/></button><span>{visible.findIndex(r=>r.id===selected.id)+1} / {visible.length}</span><button onClick={()=>move(1)} aria-label="下一项"><ChevronRight/></button></div></div>
      <section className="evidence-section">
        <h3>官方记录</h3>
        <EvidenceRow label="名称">{selected.name}</EvidenceRow>
        <EvidenceRow label="地址">{selected.address}</EvidenceRow>
        <EvidenceRow label="来源">黄浦区第二批文物保护点名单</EvidenceRow>
      </section>
      <section className="evidence-section">
        <h3>高德地理编码结果</h3>
        <EvidenceRow label="标准地址">{selected.amap_formatted_address}</EvidenceRow>
        <EvidenceRow label="解析等级">{selected.amap_level}</EvidenceRow>
        <EvidenceRow label="坐标"><span className="mono">{selected.location.map(n=>n.toFixed(6)).join(', ')}</span></EvidenceRow>
        <EvidenceRow label="最近建筑距离" strong>{selected.candidates[0] ? `${selected.candidates[0].distance_m} m` : '无候选'}</EvidenceRow>
        <EvidenceRow label="同名 POI">{selected.amap_poi_name}</EvidenceRow>
        <EvidenceRow label="现状 AOI">{selected.amap_aoi_name}</EvidenceRow>
        <EvidenceRow label="AOI 面积">{selected.amap_aoi_area_m2 ? `${selected.amap_aoi_area_m2} m²` : null}</EvidenceRow>
      </section>
      <section className="evidence-section">
        <h3>预标注判断</h3>
        <EvidenceRow label="状态" strong>{selected.review_required ? '仍需人工复核' : '已预标注'}</EvidenceRow>
        <EvidenceRow label="进入优化">{selected.include_in_optimization ? '是' : '否（暂时冻结）'}</EvidenceRow>
        <EvidenceRow label="置信度">{{high:'高',medium:'中',review:'待复核'}[selected.evidence_confidence]}</EvidenceRow>
        <p style={{margin:'8px 0 0',padding:'9px 10px',background:'#f4f7fb',borderLeft:'3px solid #6f94c8',color:'#536173',fontSize:12,lineHeight:1.55}}>{selected.evidence_reason}</p>
      </section>
      {!!selected.online_evidence?.length && <section className="evidence-section">
        <h3>联网佐证</h3>
        <div style={{display:'grid',gap:10}}>{selected.online_evidence.map((item,i)=><article key={i} style={{fontSize:12,lineHeight:1.5}}>
          <a href={item.url} target="_blank" rel="noreferrer" style={{color:'#1769e0',fontWeight:600}}>{item.title}</a>
          <span style={{marginLeft:6,color:'#7b8796'}}>· {item.tier}</span>
          <div style={{color:'#536173'}}>{item.note}</div>
        </article>)}</div>
      </section>}
      <section className="evidence-section candidates">
        <h3>候选建筑 <span>{current.bids.length} 已选</span></h3>
        <div className="candidate-head"><span>建筑ID</span><span>距离</span><span>主体代理</span><span>原代理</span></div>
        {selected.candidates.map(c=><label key={c.bid} className={current.bids.includes(c.bid)?'chosen':''}><input type="checkbox" checked={current.bids.includes(c.bid)} onChange={()=>toggleBid(c.bid)}/><b>BID {c.bid}</b><span>{c.distance_m} m</span><span>{c.stakeholder}</span><span>{c.in_existing_proxy?'是':'否'}</span></label>)}
      </section>
      <section className="evidence-section">
        <h3>审核判断</h3>
        <textarea value={current.note} onChange={e=>updateCurrent({note:e.target.value})} placeholder="记录建筑范围、地址歧义或排除原因" />
      </section>
      <div className="actions">
        <button className="primary" onClick={()=>updateCurrent({status:'accepted'})}>接受所选建筑</button>
        <button onClick={()=>updateCurrent({status:'uncertain'})}>无法确认</button>
        <button onClick={()=>updateCurrent({status:'excluded',bids:[]})}>排除记录</button>
        <button className="save" onClick={exportReview}>保存审核</button>
      </div>
    </aside>
    <footer className="statusbar"><span>审核进度</span><div className="progress"><i style={{width:`${records.length?reviewedCount/records.length*100:0}%`}}/></div><b>{reviewedCount} / {records.length}</b><span className="current"><MapPin size={14}/>当前：{selected.name}</span><span>坐标：WGS84</span></footer>
  </div>
}

function App() {
  const [view, setView] = useState(() => window.location.hash === '#results' ? 'results' : 'review')
  const show = next => {
    setView(next)
    window.location.hash = next === 'results' ? 'results' : 'review'
  }
  return view === 'results'
    ? <ExperimentDashboard onShowReview={() => show('review')}/>
    : <ReviewWorkspace onShowResults={() => show('results')}/>
}

export default App

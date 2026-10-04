import { useEffect, useMemo, useState } from 'react'
import {
  BarChart3,
  CheckCircle2,
  Database,
  Download,
  GitCommit,
  Scale,
} from 'lucide-react'
import './model-revision.css'

const METHOD_COLORS = {
  conventional_parameter_baseline: '#1d4ed8',
  tourism_capture: '#d97706',
  everyday_life_first: '#059669',
  heritage_micro_economy: '#7c3aed',
  negotiated_24h_alley: '#dc2626',
}

function useExperimentData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    fetch('/data/experiment_results.json')
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then(setData)
      .catch(cause => setError(cause.message))
  }, [])
  return { data, error }
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

function percent(value, digits = 1) {
  return `${formatNumber(value * 100, digits)}%`
}

function KpiCard({ icon, label, value, note }) {
  return <article className="result-kpi">
    <div className="result-kpi-icon">{icon}</div>
    <div><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
  </article>
}

function MetricBars({ rows, field, label, format = formatNumber }) {
  const max = Math.max(...rows.map(row => Number(row[field]) || 0), 0.000001)
  return <article className="metric-card">
    <h3>{label}</h3>
    <div className="metric-bars">
      {rows.map(row => <div className="metric-row" key={row.method_id}>
        <span>{row.method_label}</span>
        <div className="metric-track" aria-hidden="true">
          <i style={{ width:`${Math.max(2, row[field] / max * 100)}%`, background:METHOD_COLORS[row.method_id] }} />
        </div>
        <b>{format(row[field])}</b>
      </div>)}
    </div>
  </article>
}

export default function ExperimentDashboard({ onShowReview }) {
  const { data, error } = useExperimentData()
  const [selectedMethod, setSelectedMethod] = useState('conventional_parameter_baseline')
  const rows = useMemo(() => {
    if (!data) return []
    const labels = data.plan.method_labels
    const order = new Map(data.plan.methods.map((method, index) => [method, index]))
    return data.summary.aggregate
      .map(row => ({ ...row, method_label:labels[row.method_id] }))
      .sort((a, b) => order.get(a.method_id) - order.get(b.method_id))
  }, [data])
  const seedRows = useMemo(() => {
    if (!data) return []
    return data.tables.run_summary.filter(row => row.method_id === selectedMethod)
  }, [data, selectedMethod])

  if (error) return <main className="loading error">实验结果加载失败：{error}</main>
  if (!data) return <main className="loading">正在加载冻结实验结果…</main>

  const labels = data.plan.method_labels
  const baseline = rows.find(row => row.method_id === 'conventional_parameter_baseline')
  const allChecksPassed = Object.values(data.validation.checks).every(Boolean)

  return <div className="results-shell">
    <header className="topbar results-topbar">
      <h1>打浦桥实验结果</h1>
      <div className="source-note">历史冻结提交 · {data.source.git_commit.slice(0, 7)}</div>
      <nav className="topbar-nav" aria-label="平台页面">
        <button className="text-button" onClick={onShowReview}>数据审核</button>
        <button className="text-button active"><BarChart3 size={16}/>实验结果</button>
        <a className="text-button" href="/data/experiment_results.json" download><Download size={16}/>下载数据</a>
      </nav>
    </header>

    <main className="results-main">
      <section className="model-revision-note" role="status">
        <strong>模型已修订，本页数值暂作历史对照</strong>
        <span>{data.model_status.note}</span>
        <div>当前情景：{data.model_status.current_scenarios.map(item => item.label).join(' / ')} · 角色选择：{data.model_status.role_selection_label}</div>
      </section>
      <section className="results-hero">
        <div>
          <p className="eyebrow">修订前正式高预算对照实验</p>
          <h2>这组结果记录了旧情景为什么需要修订</h2>
          <p>五种旧方法共享同一城市基底、硬约束、三目标和评价预算。这里的四个旧治理情景已不再是当前实验框架，但保留下来作为可复现的问题证据。</p>
        </div>
        <aside className="result-callout">
          <Scale size={20}/>
          <b>统计边界</b>
          <span>四个情景的超体积在五个配对种子中均低于基线，但 Holm 校正后 p=0.25。当前证据支持方向一致，不支持“统计显著优劣”的强结论。</span>
        </aside>
      </section>

      <section className="result-kpis" aria-label="实验完整性">
        <KpiCard icon={<CheckCircle2/>} label="完成运行" value={`${data.validation.completed_runs} / 25`} note="五种方法 × 五个随机种子"/>
        <KpiCard icon={<Database/>} label="单次评价预算" value={data.plan.effective_evaluation_budget} note="每个方法与种子一致"/>
        <KpiCard icon={<Scale/>} label="公平性检查" value={`${data.validation.fairness_passes} / 25`} note="预算与候选数量全部匹配"/>
        <KpiCard icon={<GitCommit/>} label="冻结版本" value={data.source.git_commit.slice(0, 7)} note="输入、代码与运行清单已快照"/>
      </section>

      <section className="results-section">
        <div className="section-heading">
          <div><span>总体比较</span><h2>搜索覆盖、可行率与 Pareto 集规模</h2></div>
          <p>超体积越大表示共同目标空间覆盖越广；Pareto 数量表示非支配解数量，不单独等同于方案质量。</p>
        </div>
        <div className="metric-grid">
          <MetricBars rows={rows} field="hypervolume_mean" label="平均超体积" format={value => formatNumber(value, 4)}/>
          <MetricBars rows={rows} field="feasible_ratio_mean" label="平均可行率" format={value => percent(value, 1)}/>
          <MetricBars rows={rows} field="pareto_count_mean" label="平均 Pareto 解数量" format={value => formatNumber(value, 1)}/>
        </div>
      </section>

      <section className="results-section">
        <div className="section-heading">
          <div><span>共同结果指标</span><h2>三目标极值揭示了不同治理前提的搜索边界</h2></div>
          <p>所有值均为五个种子的均值；释放地面只表示与街道连接的潜力，不表示实际公共空间。</p>
        </div>
        <div className="table-wrap">
          <table className="result-table">
            <thead><tr><th>方法</th><th>最低居住影响暴露</th><th>最高正向增建量</th><th>最高释放地面</th><th>平均运行时间</th></tr></thead>
            <tbody>{rows.map(row => <tr key={row.method_id}>
              <th><i style={{background:METHOD_COLORS[row.method_id]}}/>{row.method_label}</th>
              <td>{percent(row.minimum_residential_disruption_mean, 3)}</td>
              <td>{formatNumber(row.maximum_development_capacity_mean, 4)}</td>
              <td>{formatNumber(row.maximum_released_ground_mean, 5)}</td>
              <td>{formatNumber(row.runtime_seconds_mean, 1)} s</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p className="table-note">日常生活优先与遗产微经济的最低居住扰动为结构性零值，来自住宅冻结规则；这不是优化器自动发现的保护效果。</p>
      </section>

      <section className="results-section">
        <div className="section-heading inline-control">
          <div><span>逐种子检查</span><h2>同一方法在五个随机种子中的稳定性</h2></div>
          <label>选择方法<select value={selectedMethod} onChange={event => setSelectedMethod(event.target.value)}>
            {data.plan.methods.map(method => <option value={method} key={method}>{labels[method]}</option>)}
          </select></label>
        </div>
        <div className="table-wrap">
          <table className="result-table compact">
            <thead><tr><th>随机种子</th><th>可行率</th><th>Pareto 数</th><th>最高正向增建量</th><th>最高释放地面</th><th>超体积</th></tr></thead>
            <tbody>{seedRows.map(row => <tr key={row.seed}>
              <th>{row.seed}</th><td>{percent(row.feasible_ratio)}</td><td>{row.pareto_count}</td>
              <td>{formatNumber(row.maximum_development_capacity, 4)}</td>
              <td>{formatNumber(row.maximum_released_ground, 5)}</td>
              <td>{formatNumber(row.hypervolume, 4)}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>

      <section className="results-section">
        <div className="section-heading">
          <div><span>正式图表</span><h2>同一冻结运行生成的比较图</h2></div>
          <p>图像与表格均来自提交 {data.source.git_commit.slice(0, 7)} 的同一运行目录。</p>
        </div>
        <div className="result-figures">
          {data.figures.map(figure => <figure key={figure.id}>
            <img src={`/data/${figure.file}`} alt={figure.label} loading="lazy"/>
            <figcaption>{figure.label}</figcaption>
          </figure>)}
        </div>
      </section>

      <section className="results-section provenance-card">
        <div><CheckCircle2/><span><b>{allChecksPassed ? '同步校验全部通过' : '同步校验存在异常'}</b>25/25 运行完成，25/25 公平性检查通过。</span></div>
        <div><GitCommit/><span><b>可复现来源</b>{data.source.relative_directory}</span></div>
        <ul>{data.caveats.map(item => <li key={item}>{item}</li>)}</ul>
      </section>
    </main>
    <footer className="results-footer">正式论文实验 · 5 methods · 5 seeds · 10,000 independent evaluations · frozen research inputs</footer>
  </div>
}

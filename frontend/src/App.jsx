import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Command,
  FileCheck2,
  Filter,
  Inbox,
  LockKeyhole,
  MoreHorizontal,
  Network,
  Play,
  Radio,
  Search,
  ShieldCheck,
  Sparkles,
  TimerReset,
  TrendingUp,
  UserRound,
  X,
  Zap,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const baseCases = [
  {
    id: 'EXC-24091',
    customer: 'Maya Patel',
    initials: 'MP',
    amount: 1250,
    currency: 'GBP',
    rail: 'ACH',
    intent: 'Authorised scam',
    age: 18,
    confidence: 94,
    risk: 12,
    merchant: 'Northwind Supplies Ltd',
    merchantShort: 'Northwind',
    paymentDate: '02 Jan 2026',
    requestId: 'IR-ACH-8F41C2',
    route: 'Payment intelligence / claimant history / rail rules',
    thought: "User stated 'Northwind' and '£1,250'. Found closest match 'Northwind Supplies Ltd'. Date tolerance accepted (+0 day deviation). Cross-referencing trading names...",
    behavior: 'Customer has historical high reliability. 0 past buyer\'s remorse claims in 12 months.',
  },
  {
    id: 'EXC-24088',
    customer: 'Jordan Lee',
    initials: 'JL',
    amount: 73000,
    currency: 'GBP',
    rail: 'WIRE',
    intent: 'Unauthorised',
    age: 47,
    confidence: 89,
    risk: 28,
    merchant: 'Northwind Supplies Ltd',
    merchantShort: 'Northwind',
    paymentDate: '20 Jul 2026',
    requestId: 'IR-WIR-2B01A9',
    route: 'Identity signal / velocity monitor / analyst queue',
    thought: "User stated 'I did not make' and '£73,000'. Found exact amount match. Account velocity is elevated; routing to senior analyst for confirmation...",
    behavior: 'Customer profile is stable. One device-change event detected before the claim.',
  },
  {
    id: 'EXC-24083',
    customer: 'Sam Rivera',
    initials: 'SR',
    amount: 3200,
    currency: 'GBP',
    rail: 'RTP',
    intent: 'No remedy',
    age: 68,
    confidence: 97,
    risk: 8,
    merchant: 'Cedar Works Inc',
    merchantShort: 'Cedar Works',
    paymentDate: '05 Sep 2026',
    requestId: 'N/A',
    route: 'Instant rail finality / no-recall policy',
    thought: "Payment is an RTP transaction. Rail finality policy supersedes claim narrative. Recovery request is blocked; preserve evidence for review...",
    behavior: 'Customer has no prior disputes. Finality is rail-driven, not a fraud-risk finding.',
  },
  {
    id: 'EXC-24079',
    customer: 'Alex Morgan',
    initials: 'AM',
    amount: 9000,
    currency: 'GBP',
    rail: 'ACH',
    intent: 'Erroneous',
    age: 32,
    confidence: 91,
    risk: 19,
    merchant: 'Blue Oak Services Ltd',
    merchantShort: 'Blue Oak',
    paymentDate: '25 Jul 2026',
    requestId: 'IR-ACH-35D8AA',
    route: 'Claim semantics / beneficiary match / deadline guard',
    thought: "User stated 'wrong payment' and 'Blue Oak'. Match confidence is high. Return-of-funds remedy is available within the configured window...",
    behavior: 'Customer history is clean. Repeated beneficiary appears in normal account activity.',
  },
  {
    id: 'EXC-24073',
    customer: 'Taylor Kim',
    initials: 'TK',
    amount: 7950,
    currency: 'USD',
    rail: 'ACH',
    intent: 'Erroneous',
    age: 12,
    confidence: 96,
    risk: 9,
    merchant: 'John Doe Plumbing LLC',
    merchantShort: 'John Doe Plumbing',
    paymentDate: '15 Sep 2026',
    requestId: 'IR-ACH-91E2D0',
    route: 'Voice transcript / beneficiary vector / amount tolerance',
    thought: "User stated 'plumber' and '8,000'. Found closest match 'John Doe Plumbing LLC' for $7,950. Date tolerance accepted (+1 day deviation). Cross-referencing trading names...",
    behavior: 'Customer has a stable payment pattern. No prior dispute clustering detected.',
  },
]

const classificationData = [
  { name: 'Unauthorised', bot: 42, human: 8 },
  { name: 'Erroneous', bot: 31, human: 5 },
  { name: 'Scam', bot: 23, human: 7 },
  { name: 'No remedy', bot: 18, human: 3 },
]

const volatilityData = [
  { time: '08:00', resolved: 14, escalated: 4, noRemedy: 2 },
  { time: '10:00', resolved: 19, escalated: 7, noRemedy: 3 },
  { time: '12:00', resolved: 17, escalated: 9, noRemedy: 5 },
  { time: '14:00', resolved: 26, escalated: 6, noRemedy: 4 },
  { time: '16:00', resolved: 23, escalated: 11, noRemedy: 8 },
  { time: '18:00', resolved: 31, escalated: 8, noRemedy: 6 },
]

function getState(age, rail) {
  if (rail === 'RTP' || rail === 'FEDNOW' || age > 60) return 'No-Remedy'
  if (age >= 46) return 'Escalated'
  return 'Simulated Request Raised'
}

function getSla(age, rail) {
  if (rail === 'RTP' || rail === 'FEDNOW') return { label: 'Rail finality', tone: 'red', progress: 100 }
  if (age > 60) return { label: 'Window exceeded', tone: 'red', progress: 100 }
  if (age >= 46) return { label: `${60 - age}d remaining`, tone: 'amber', progress: (age / 60) * 100 }
  return { label: `${60 - age}d remaining`, tone: 'green', progress: (age / 60) * 100 }
}

function StatusPill({ state }) {
  const config = {
    'Simulated Request Raised': { icon: CheckCircle2, className: 'status-green' },
    Escalated: { icon: AlertTriangle, className: 'status-amber' },
    'No-Remedy': { icon: LockKeyhole, className: 'status-red' },
  }[state]
  const Icon = config.icon
  return <span className={`status-pill ${config.className}`}><Icon size={13} />{state}</span>
}

function MetricCard({ label, value, detail, icon: Icon, accent }) {
  return (
    <article className="metric-card">
      <div className="metric-heading"><span>{label}</span><span className={`metric-icon ${accent}`}><Icon size={17} /></span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  )
}

function VoiceAssistantPanel({ onTranscriptionComplete }) {
  const [voiceState, setVoiceState] = useState('idle')
  const [elapsed, setElapsed] = useState(0)
  const [transcript, setTranscript] = useState('')
  const [scenario, setScenario] = useState('A')

  useEffect(() => {
    if (voiceState !== 'listening') return undefined
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [voiceState])

  const scenarios = {
    A: { label: 'Within 60 days', transcript: 'I sent around eight thousand to the plumber last Tuesday.', delay: 1100, payload: { query: 'John Doe Plumbing', age: 12, caseId: 'EXC-24073' } },
    B: { label: 'Over 60 days', transcript: 'I had a wrong charge of five hundred dollars back in June.', delay: 900, payload: { query: 'wrong charge', age: 68, caseId: 'EXC-24079' } },
    C: { label: 'Escalation trigger', transcript: "No, that's not the right account, none of those are mine!", delay: 700, payload: { query: 'EXC-24088', age: 47, caseId: 'EXC-24088' } },
  }

  const startVoiceCapture = () => {
    setTranscript('')
    setElapsed(0)
    setVoiceState('listening')
  }

  const stopVoiceCapture = () => {
    const activeScenario = scenarios[scenario]
    setVoiceState('processing')
    window.setTimeout(() => {
      setTranscript(activeScenario.transcript)
      setVoiceState('success')
      onTranscriptionComplete(activeScenario.transcript, activeScenario.payload)
    }, activeScenario.delay)
  }

  const formatTime = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`
  return (
    <section className={`voice-panel voice-${voiceState}`}>
      <div className="voice-panel-header"><div><span className="eyebrow"><Radio size={13} /> Multimodal intake</span><h2>Voice dispute assistant</h2></div><span className="voice-api-badge"><Zap size={12} /> Realtime stub</span></div>
      <div className="voice-panel-body">
        <div className="voice-control">
          {voiceState === 'processing' ? <div className="voice-spinner"><span /></div> : voiceState === 'listening' ? <div className="waveform">{Array.from({ length: 18 }, (_, index) => <i key={index} style={{ animationDelay: `${index * 55}ms`, height: `${10 + ((index * 17) % 28)}px` }} />)}</div> : <button className="voice-mic" onClick={startVoiceCapture} aria-label="Start voice capture"><Radio size={24} /></button>}
          <div className="voice-state-copy">{voiceState === 'idle' && <><strong>Click to speak your dispute</strong><span>Voice intake is encrypted in transit</span></>}{voiceState === 'listening' && <><strong>Listening... speak now</strong><span className="voice-timer">{formatTime} · live audio capture</span></>}{voiceState === 'processing' && <><strong>AI transcribing & analyzing narrative...</strong><span>Mapping voice to IntakeAI.extract</span></>}{voiceState === 'success' && <><strong>Transcript captured</strong><span>Candidate search triggered automatically</span></>}</div>
          {voiceState === 'listening' && <button className="voice-stop" onClick={stopVoiceCapture}>Stop capture</button>}
          {voiceState === 'success' && <button className="voice-retry" onClick={startVoiceCapture}>Capture again</button>}
        </div>
        <div className="scenario-picker"><span>Demo scenario</span>{Object.entries(scenarios).map(([key, item]) => <button key={key} className={scenario === key ? 'active' : ''} onClick={() => setScenario(key)}>{key} <small>{item.label}</small></button>)}</div>
        {voiceState === 'success' && <div className="voice-transcript"><div className="transcript-bubble"><UserRound size={14} /><span>{transcript}</span></div><div className="voice-trigger"><Bot size={14} /><span>Searching candidate payments for your account...</span><CheckCircle2 size={14} /></div></div>}
      </div>
    </section>
  )
}

function App() {
  const [age, setAge] = useState(18)
  const [selectedId, setSelectedId] = useState('EXC-24091')
  const [query, setQuery] = useState('')
  const [railFilter, setRailFilter] = useState('All rails')
  const [auditOpen, setAuditOpen] = useState(false)

  const cases = useMemo(() => baseCases.map((item) => ({ ...item, state: getState(age, item.rail), sla: getSla(age, item.rail) })), [age])
  const filteredCases = useMemo(() => cases.filter((item) => {
    const matchesQuery = `${item.id} ${item.customer} ${item.merchantShort}`.toLowerCase().includes(query.toLowerCase())
    return matchesQuery && (railFilter === 'All rails' || item.rail === railFilter)
  }), [cases, query, railFilter])
  const selectedCase = cases.find((item) => item.id === selectedId) || cases[0]
  const safeCount = cases.filter((item) => item.state === 'Simulated Request Raised').length
  const escalatedCount = cases.filter((item) => item.state === 'Escalated').length
  const noRemedyCount = cases.filter((item) => item.state === 'No-Remedy').length
  const sandboxTone = noRemedyCount > 0 ? 'red' : escalatedCount > 0 ? 'amber' : 'green'
  const auditRecommendation = selectedCase.state === 'No-Remedy'
    ? 'Preserve evidence and route to policy exception review. Do not raise a recovery request.'
    : selectedCase.state === 'Escalated'
      ? 'Hold for senior analyst review before the SLA window closes.'
      : 'Safe to approve simulated interbank recovery request.'
  const handleTranscriptionComplete = (_text, payload) => {
    setAge(payload.age)
    setQuery(payload.query)
    setSelectedId(payload.caseId)
  }

  return (
    <div className={`app-shell theme-${sandboxTone}`}>
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><Command size={19} /></div>
          <div><strong>UC—02</strong><span>Payment intelligence</span></div>
        </div>
        <div className="workspace-switcher"><span className="live-dot" />Operations workspace<ChevronDown size={14} /></div>
        <nav className="nav-stack">
          <div className="nav-label">Control centre</div>
          <button className="nav-item active"><Inbox size={17} />Exception queue<span className="nav-count">24</span></button>
          <button className="nav-item"><Activity size={17} />Live orchestration<span className="nav-live">LIVE</span></button>
          <button className="nav-item"><ShieldCheck size={17} />Policy controls</button>
          <div className="nav-label nav-label-spaced">Observability</div>
          <button className="nav-item"><TrendingUp size={17} />Risk analytics</button>
          <button className="nav-item"><FileCheck2 size={17} />Audit ledger</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="model-status"><span className="model-pulse" /><div><strong>Agent mesh healthy</strong><small>4 deterministic nodes online</small></div></div>
          <div className="profile"><div className="profile-avatar">RK</div><div><strong>Riya Kapoor</strong><small>Principal operator</small></div><MoreHorizontal size={16} /></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div><div className="eyebrow"><span className="live-dot" />Operations / Exception queue</div><h1>Core payment exceptions</h1><p>Human-in-the-loop recovery control for high-signal disputes.</p></div>
          <div className="top-actions"><div className="system-time"><span>EU/UK production replica</span><strong>20 Sep 2026 · 09:42:18</strong></div><button className="icon-button"><Search size={17} /></button><button className="operator-button"><div className="profile-avatar small">RK</div><ChevronDown size={14} /></button></div>
        </header>

        <section className={`sandbox-panel sandbox-${sandboxTone}`}>
          <div className="sandbox-copy"><div className="sandbox-title"><TimerReset size={17} />Regulatory sandbox <span>●</span></div><h2>Simulate transaction age <em>(SLA tester)</em></h2><p>Warp the case clock to validate every deadline guard before a human approves.</p></div>
          <div className="sandbox-control"><div className="sandbox-scale"><span>10 days</span><strong>{age > 60 ? 'DAY 68 · WINDOW EXCEEDED' : `DAY ${age} · ${age >= 46 ? 'APPROACHING DEADLINE' : 'WITHIN SAFE WINDOW'}`}</strong><span>70 days</span></div><input aria-label="Simulate transaction age" type="range" min="10" max="70" value={age} onChange={(event) => setAge(Number(event.target.value))} /><div className="scale-ticks"><span>Safe</span><span>60-day threshold</span><span>Finality / no remedy</span></div></div>
          <div className="sandbox-readout"><div className={`readout-orb orb-${sandboxTone}`}><Clock3 size={21} /></div><div><span>Recovery posture</span><strong>{sandboxTone === 'green' ? 'Automatic path' : sandboxTone === 'amber' ? 'Analyst attention' : 'No-remedy active'}</strong></div></div>
        </section>

        <VoiceAssistantPanel onTranscriptionComplete={handleTranscriptionComplete} />

        <section className="metrics-grid">
          <MetricCard label="Escalated cases" value={String(8 + escalatedCount)} detail="+3.2% vs previous shift" icon={AlertTriangle} accent="amber" />
          <MetricCard label="Active simulated requests" value={String(17 + safeCount)} detail="92% within SLA window" icon={Zap} accent="green" />
          <MetricCard label="No-remedy decisions" value={String(4 + noRemedyCount)} detail="Rail finality + expired SLA" icon={LockKeyhole} accent="red" />
          <article className="metric-card voice-card"><div className="metric-heading"><span>Voice agent activity</span><span className="voice-wave"><i /><i /><i /><i /><i /></span></div><div className="voice-readout"><div className="voice-avatar"><Radio size={16} /></div><div><strong>03</strong><span>active calls</span></div><small>+12% live</small></div><div className="voice-bar"><span style={{ width: '68%' }} /></div></article>
        </section>

        <section className="content-grid">
          <div className="queue-column">
            <div className="section-heading"><div><div className="eyebrow">Prioritised work queue</div><h2>Cases requiring orchestration</h2></div><button className="secondary-button"><Filter size={15} /> Filters <span>2</span></button></div>
            <div className="queue-toolbar"><div className="search-field"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search case, customer or beneficiary" /></div><div className="rail-tabs">{['All rails', 'ACH', 'WIRE', 'RTP'].map((rail) => <button key={rail} className={railFilter === rail ? 'selected' : ''} onClick={() => setRailFilter(rail)}>{rail}</button>)}</div></div>
            <div className="table-wrap"><table><thead><tr><th>Case / customer</th><th>Disputed amount</th><th>Rail</th><th>Classification</th><th>State</th><th>SLA clock</th><th /></tr></thead><tbody>{filteredCases.map((item) => <tr key={item.id} className={item.id === selectedId ? 'row-selected' : ''} onClick={() => setSelectedId(item.id)}><td><div className="case-cell"><div className="customer-avatar">{item.initials}</div><div><strong>{item.id}</strong><span>{item.customer}</span></div></div></td><td><strong>{item.currency} {item.amount.toLocaleString()}</strong><span className="muted-cell">{item.merchantShort}</span></td><td><span className="rail-chip"><span />{item.rail}</span></td><td><span className="classification">{item.intent}</span><span className="confidence"><span style={{ width: `${item.confidence}%` }} />{item.confidence}% match</span></td><td><StatusPill state={item.state} /></td><td><div className="sla-cell"><span className={`sla-dot dot-${item.sla.tone}`} />{item.sla.label}</div></td><td><button className="row-action" onClick={(event) => { event.stopPropagation(); setSelectedId(item.id); setAuditOpen(true) }}><ArrowUpRight size={15} /></button></td></tr>)}</tbody></table></div>
            <div className="table-footer"><span>Showing {filteredCases.length} of 24 cases</span><span className="footer-page">1 <span>/</span> 6 <ChevronDown size={13} /></span></div>

            <div className="chart-grid"><article className="chart-card"><div className="chart-heading"><div><span className="eyebrow">Human oversight</span><h3>Classification overrides</h3></div><button className="more-button"><MoreHorizontal size={16} /></button></div><div className="legend"><span><i className="legend-swatch swatch-cyan" />AI initial</span><span><i className="legend-swatch swatch-lilac" />Human adjustment</span></div><div className="chart-height"><ResponsiveContainer width="100%" height="100%"><BarChart data={classificationData} barGap={7} margin={{ top: 8, right: 4, left: -23, bottom: 0 }}><CartesianGrid stroke="#223240" vertical={false} /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#748697', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#607283', fontSize: 10 }} /><Tooltip cursor={{ fill: '#162431' }} contentStyle={{ background: '#101c28', border: '1px solid #2b3d4e', borderRadius: 8, fontSize: 11 }} /><Bar dataKey="bot" fill="#58d4cd" radius={[3, 3, 0, 0]} /><Bar dataKey="human" fill="#9c8cf5" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div></article><article className="chart-card"><div className="chart-heading"><div><span className="eyebrow">Last 12 hours</span><h3>Triage volatility</h3></div><span className="chart-live"><span />Live</span></div><div className="legend"><span><i className="legend-line line-green" />Auto-resolved</span><span><i className="legend-line line-amber" />Escalated</span><span><i className="legend-line line-red" />No-remedy</span></div><div className="chart-height"><ResponsiveContainer width="100%" height="100%"><LineChart data={volatilityData} margin={{ top: 8, right: 4, left: -23, bottom: 0 }}><CartesianGrid stroke="#223240" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#748697', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#607283', fontSize: 10 }} /><Tooltip contentStyle={{ background: '#101c28', border: '1px solid #2b3d4e', borderRadius: 8, fontSize: 11 }} /><Line type="monotone" dataKey="resolved" stroke="#58d4cd" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="escalated" stroke="#eab76a" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="noRemedy" stroke="#ef747c" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></article></div>
          </div>

          <aside className="audit-column"><div className="section-heading compact"><div><div className="eyebrow"><span className="live-dot" />Selected case</div><h2>Deep-dive audit</h2></div><button className="more-button"><MoreHorizontal size={18} /></button></div><div className="selected-case-card"><div className="selected-top"><div className="customer-avatar large">{selectedCase.initials}</div><div><strong>{selectedCase.id}</strong><span>{selectedCase.customer} · {selectedCase.paymentDate}</span></div><button className="more-button"><MoreHorizontal size={16} /></button></div><div className="selected-amount"><span>{selectedCase.currency} disputed</span><strong>{selectedCase.amount.toLocaleString()}</strong><span className="beneficiary">to {selectedCase.merchant}</span></div><div className="selected-meta"><span><small>Rail</small><strong>{selectedCase.rail}</strong></span><span><small>Claim type</small><strong>{selectedCase.intent}</strong></span><span><small>Match</small><strong className="text-green">{selectedCase.confidence}%</strong></span></div><div className="selected-status"><StatusPill state={selectedCase.state} /><span className={`sla-inline ${selectedCase.sla.tone}`}><Clock3 size={13} />{selectedCase.sla.label}</span></div></div>
            <div className="cognitive-card"><div className="card-title"><div className="title-icon cyan"><BrainCircuit size={16} /></div><div><strong>AI cognitive routing</strong><span>Vector match context · deterministic trace</span></div><span className="verified-tag"><CheckCircle2 size={12} />verified</span></div><div className="similarity-row"><div className="similarity-ring"><strong>{selectedCase.confidence}%</strong><span>match</span></div><div className="similarity-copy"><span>Cosine similarity</span><strong>{selectedCase.merchantShort} ↔ claim entity</strong><div className="similarity-bar"><span style={{ width: `${selectedCase.confidence}%` }} /></div><small>Top 1 of 48 candidate payments</small></div></div><div className="terminal-box"><div className="terminal-top"><span><i /><i /><i /></span><small>reasoning_trace.log</small><span>09:41:52</span></div><p><b>route</b> <span>{selectedCase.route}</span></p><p><b>match</b> <span>{selectedCase.thought}</span></p><p><b>guard</b> <span>60-day policy gate: <em>{selectedCase.state === 'No-Remedy' ? 'BLOCKED' : selectedCase.state === 'Escalated' ? 'REVIEW' : 'PASS'}</em></span></p></div></div>
            <div className="verdict-card"><div className="verdict-header"><div className="agent-badge"><Bot size={18} /></div><div><strong>Agentic smart audit verdict</strong><span>Multi-agent pre-flight · 3 checks complete</span></div><Sparkles size={16} className="sparkle" /></div><div className="verdict-grid"><div className="risk-badge"><span>Fraud risk</span><strong>{selectedCase.risk}%</strong><small>{selectedCase.risk < 20 ? 'LOW RISK' : 'MODERATE RISK'}</small></div><div className="behavior-flag"><span>Behavioral flag</span><strong>{selectedCase.behavior}</strong></div></div><div className="recommendation"><span>System recommendation</span><p>{auditRecommendation}</p></div><div className="agent-chain"><span><CheckCircle2 size={13} />Match agent</span><span><CheckCircle2 size={13} />Policy agent</span><span><CheckCircle2 size={13} />Risk agent</span></div></div><button className="primary-button" onClick={() => setAuditOpen(true)}><FileCheck2 size={16} />Open operator review <ArrowUpRight size={15} /></button></aside>
        </section>
      </main>

      {auditOpen && <div className="modal-backdrop" onClick={() => setAuditOpen(false)}><div className="review-modal" onClick={(event) => event.stopPropagation()}><div className="modal-header"><div><span className="eyebrow">Human approval checkpoint</span><h2>{selectedCase.id} · final review</h2></div><button className="icon-button" onClick={() => setAuditOpen(false)}><X size={17} /></button></div><div className="modal-body"><div className="modal-callout"><ShieldCheck size={20} /><div><strong>Agentic pre-audit complete</strong><span>Three deterministic policy and evidence checks passed. Your approval is still required to raise a simulated request.</span></div></div><div className="modal-facts"><span><small>Customer</small><strong>{selectedCase.customer}</strong></span><span><small>Amount</small><strong>{selectedCase.currency} {selectedCase.amount.toLocaleString()}</strong></span><span><small>Outcome</small><strong>{selectedCase.state}</strong></span><span><small>Request ID</small><strong>{selectedCase.requestId}</strong></span></div><div className="modal-disclaimer"><AlertTriangle size={16} /><span>Simulated interbank recovery only. No guaranteed recovery. Receiving institution may decline.</span></div></div><div className="modal-footer"><button className="secondary-button" onClick={() => setAuditOpen(false)}>Return to queue</button><button className="primary-button" disabled={selectedCase.state === 'No-Remedy'} onClick={() => setAuditOpen(false)}><CheckCircle2 size={16} />{selectedCase.state === 'No-Remedy' ? 'Request blocked by policy' : 'Approve simulated request'}</button></div></div></div>}
    </div>
  )
}

export default App

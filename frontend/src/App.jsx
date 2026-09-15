import { useEffect, useState } from 'react'
import { Activity, ArrowRight, CheckCircle2, CircleAlert, RefreshCw, Send, ShieldCheck, Timer } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api')
const initial = { order_id: 'ORD-1003', merchant_id: 'MERCHANT-READY', partner_id: 'PARTNER-BUSY', location: 'Airport', issue_type: 'partner_unavailable', issue_severity: 'high', customer_priority: 'standard', current_status: 'awaiting_pickup' }

function App() {
  const [form, setForm] = useState(initial)
  const [incident, setIncident] = useState(null)
  const [resolution, setResolution] = useState(null)
  const [trace, setTrace] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function request(path, options) {
    try {
      const response = await fetch(`${API}${path}`, options)
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`)
      return data
    } catch (e) {
      if (e instanceof TypeError) throw new Error('Backend service unavailable. Please try again.')
      throw e
    }
  }

  async function createIncident(event) {
    event.preventDefault(); setBusy(true); setError(''); setResolution(null)
    try { const data = await request('/incidents', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(form) }); setIncident(data); setTrace([]) } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function resolve() {
    if (!incident) return; setBusy(true); setError('')
    try { const data = await request(`/incidents/${incident.id}/resolve`, { method: 'POST' }); setResolution(data); setIncident({...incident, status: data.status}); setTrace(await request(`/incidents/${incident.id}/trace`)) } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { if (!incident || !resolution) return; }, [incident, resolution])
  const update = (key, value) => setForm({...form, [key]: value})
  return <main className="shell">
    <header className="masthead"><div><p className="kicker">OPERATIONS / AUTONOMOUS CONTROL</p><h1>Delivery resolution<br/><em>in motion.</em></h1></div><div className="status"><span className="pulse"/> SYSTEM READY</div></header>
    <section className="grid">
      <form className="panel intake" onSubmit={createIncident}><div className="panel-head"><div><span className="eyebrow">01 / Intake</span><h2>Open an incident</h2></div><Activity size={20}/></div><label>Order ID<input value={form.order_id} onChange={e=>update('order_id',e.target.value)}/></label><div className="two"><label>Merchant<input value={form.merchant_id} onChange={e=>update('merchant_id',e.target.value)}/></label><label>Partner<input value={form.partner_id} onChange={e=>update('partner_id',e.target.value)}/></label></div><label>Location<input value={form.location} onChange={e=>update('location',e.target.value)}/></label><label>Issue<select value={form.issue_type} onChange={e=>update('issue_type',e.target.value)}><option value="traffic_disruption">Traffic disruption</option><option value="merchant_delay">Merchant delay</option><option value="partner_unavailable">Partner unavailable</option><option value="address_problem">Address problem</option><option value="sla_risk">SLA risk</option><option value="combined_disruption">Combined disruption</option></select></label><button className="primary" disabled={busy}><Send size={16}/> Create incident <ArrowRight size={16}/></button></form>
      <section className="panel command"><div className="panel-head"><div><span className="eyebrow">02 / Command</span><h2>Resolution brief</h2></div><ShieldCheck size={20}/></div>{error && <p className="error"><CircleAlert size={16}/>{error}</p>}{!incident ? <div className="empty"><Timer size={34}/><p>Awaiting an incident signal.</p><small>Create an incident to activate the agent workflow.</small></div> : <><div className="incident-line"><div><span className="eyebrow">ACTIVE INCIDENT</span><strong>{incident.id.slice(0,8)} / {incident.order_id}</strong></div><span className={`badge ${incident.status}`}>{incident.status}</span></div>{resolution ? <div className="resolution"><span className="eyebrow">SELECTED ACTION</span><h3>{resolution.decision?.action?.replaceAll('_',' ')}</h3><p>{resolution.reasoning_summary}</p><div className="impact"><span>Confidence</span><strong>{Math.round((resolution.decision?.confidence || 0)*100)}%</strong><span>Verification</span><strong>{resolution.verification?.resolved ? 'RESOLVED' : 'ESCALATED'}</strong></div></div> : <button className="primary resolve" disabled={busy} onClick={resolve}><RefreshCw size={16}/> Run autonomous resolution</button>}</>}</section>
    </section>
    <section className="panel timeline"><div className="panel-head"><div><span className="eyebrow">03 / Trace</span><h2>Agent execution timeline</h2></div><span className="count">{trace.length} events</span></div>{trace.length === 0 ? <p className="muted">Trace events will appear after resolution.</p> : <div className="events">{trace.map((event,index)=><div className="event" key={`${event.event}-${index}`}><div className="node"><CheckCircle2 size={16}/></div><div><strong>{event.tool_name || event.agent_name || event.event.replaceAll('_',' ')}</strong><p>{event.message || event.status}</p></div><time>{new Date(event.timestamp).toLocaleTimeString()}</time></div>)}</div>}</section>
  </main>
}
export default App

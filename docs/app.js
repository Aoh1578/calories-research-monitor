const state = { data: null, entries: [] };
const $ = (id) => document.getElementById(id);
const fields = ['sourceFilter','nodeFilter','evidenceFilter','bookUseFilter','statusFilter','sortBy','searchBox'];
const fmt = (s) => s || 'unknown';
const esc = (s='') => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

fetch('data.json', {cache: 'no-store'})
  .then(r => r.json())
  .then(data => { state.data = data; state.entries = data.entries || []; init(); })
  .catch(err => { $('timeline').innerHTML = `<p class="empty">Failed to load data.json: ${esc(err.message)}</p>`; });

function unique(arr) { return [...new Set(arr.filter(Boolean))].sort(); }
function setOptions(id, values) { const sel = $(id); values.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }); }
function nodeLabel(id) { return (state.data.nodes || []).find(n => n.id === id)?.label || id; }
function claimLabel(id) { return (state.data.claims || []).find(c => c.id === id)?.claim || id; }

function init() {
  $('totalCount').textContent = state.entries.length;
  $('lastUpdated').textContent = `Last updated: ${state.data.last_updated || 'never'}`;
  setOptions('sourceFilter', unique(state.entries.map(e => e.source_type)));
  setOptions('nodeFilter', (state.data.nodes || []).map(n => n.id));
  setOptions('evidenceFilter', unique(state.entries.map(e => e.evidence_level)));
  setOptions('bookUseFilter', unique(state.entries.map(e => e.book_use)));
  setOptions('statusFilter', unique(state.entries.map(e => e.status)));
  fields.forEach(id => $(id).addEventListener(id === 'searchBox' ? 'input' : 'change', render));
  render();
}

function matches(e) {
  const q = $('searchBox').value.trim().toLowerCase();
  if ($('sourceFilter').value && e.source_type !== $('sourceFilter').value) return false;
  if ($('nodeFilter').value && !(e.cascade_nodes || []).includes($('nodeFilter').value)) return false;
  if ($('evidenceFilter').value && e.evidence_level !== $('evidenceFilter').value) return false;
  if ($('bookUseFilter').value && e.book_use !== $('bookUseFilter').value) return false;
  if ($('statusFilter').value && e.status !== $('statusFilter').value) return false;
  if (!q) return true;
  const hay = [e.title, e.summary, e.mechanism, e.journal, ...(e.authors||[]), ...(e.key_findings||[]), ...(e.limitations||[]), ...(e.cascade_nodes||[]), ...(e.claim_tags||[])].join(' ').toLowerCase();
  return hay.includes(q);
}

function render() {
  const sortBy = $('sortBy').value;
  const entries = state.entries.filter(matches).sort((a,b) => {
    const ka = sortBy === 'added' ? a.date_found : a.date_published;
    const kb = sortBy === 'added' ? b.date_found : b.date_published;
    return String(kb || '').localeCompare(String(ka || ''));
  });
  $('empty').hidden = entries.length !== 0;
  $('timeline').innerHTML = entries.map(card).join('');
  const breakdown = state.entries.reduce((acc,e) => { acc[e.source_type || 'unknown'] = (acc[e.source_type || 'unknown'] || 0) + 1; return acc; }, {});
  $('breakdown').textContent = `Total ${state.entries.length} · ` + Object.entries(breakdown).map(([k,v]) => `${k}: ${v}`).join(' · ');
}

function listBlock(label, arr) {
  if (!arr || !arr.length) return '';
  return `<div class="detail"><strong>${esc(label)}</strong><ul>${arr.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
}

function card(e) {
  const rel = (e.relevance || '').toLowerCase();
  return `<article class="card">
    <div class="badges">
      <span class="badge source">${esc(e.source_type || 'unknown')}</span>
      <span class="badge ${rel}">${esc(e.relevance || 'unrated')}</span>
      <span class="badge">${esc(e.evidence_level || 'evidence unknown')}</span>
      <span class="badge">${esc(e.status || 'needs_human_review')}</span>
    </div>
    <h2>${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title)}</h2>
    <div class="meta">
      <span>Published ${esc(fmt(e.date_published))}</span><span>·</span><span>Added ${esc(fmt(e.date_found))}</span>
      ${e.journal ? `<span>·</span><span>${esc(e.journal)}</span>` : ''}
      ${e.doi ? `<span>·</span><span>DOI ${esc(e.doi)}</span>` : ''}
    </div>
    <div class="meta">${esc((e.authors || []).join(', '))}</div>
    <div class="tags">${(e.cascade_nodes||[]).map(n => `<span class="tag" title="${esc(nodeLabel(n))}">${esc(n)}</span>`).join('')}</div>
    <div class="tags">${(e.claim_tags||[]).map(c => `<span class="tag" title="${esc(claimLabel(c))}">${esc(c)}</span>`).join('')}</div>
    <p class="summary">${esc(e.summary || '')}</p>
    <div class="detail-grid">
      ${listBlock('Key findings', e.key_findings)}
      ${e.mechanism ? `<div class="detail"><strong>Mechanism</strong>${esc(e.mechanism)}</div>` : ''}
      ${listBlock('Limitations', e.limitations)}
      ${e.medical_caution ? `<div class="detail"><strong>Medical caution</strong>${esc(e.medical_caution)}</div>` : ''}
      ${e.generalizability ? `<div class="detail"><strong>Generalizability</strong>${esc(e.generalizability)}</div>` : ''}
      ${e.book_use ? `<div class="detail"><strong>Book use</strong>${esc(e.book_use)} · ${esc(e.claim_relation || 'background')}</div>` : ''}
    </div>
  </article>`;
}

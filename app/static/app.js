const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
const state = { campaign: null, records: [], preview: null, page: 1 };

async function api(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(options.headers || {}) } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || 'No se pudo completar la operación');
  return body;
}

function toast(message, type = '') {
  const node = $('#toast'); if (!node) return;
  node.textContent = message; node.className = `toast show ${type}`;
  clearTimeout(node.timer); node.timer = setTimeout(() => node.className = 'toast', 3500);
}

function money(value) { return `S/ ${Number(value).toFixed(2)}`; }
function selectedKeys() { return $$('.service-select:checked').map(input => input.value); }

async function loadStoredCount() {
  if (!$('#stored-count')) return;
  try { const data = await api('/api/ofertas'); $('#stored-count').textContent = `Registros DWO: ${data.rows.length}${data.mode === 'demo' ? ' (demo)' : ''}`; } catch (_) {}
}

function updateCalculation() {
  if (!$('#discount-value')) return;
  const type = $('#discount-type').value;
  const value = Number($('#discount-value').value || 0);
  $('#calculation-label').textContent = type === 'fixed' ? `${money(value)} menos por mes` : `${value.toFixed(2)}% menos por mes`;
  $$('.service-row').forEach(row => {
    const charge = Number(row.dataset.charge);
    const discount = type === 'fixed' ? value : charge * value / 100;
    $('.discount', row).textContent = money(Math.max(discount, 0));
    $('.new', row).textContent = money(Math.max(charge - discount, 0));
  });
}

function renderCampaign(data) {
  state.campaign = data.campaign; state.records = data.records;
  $('#campaign-name').value = data.campaign.name;
  $('#campaign-source').value = document.body.textContent.includes('SIMULACIÓN LOCAL') ? 'Simulación local' : 'PVUDB Oracle';
  const tbody = $('#services-table tbody'); tbody.innerHTML = '';
  data.records.forEach(record => {
    const row = document.createElement('tr'); row.className = 'service-row'; row.dataset.charge = record.charge_with_tax;
    row.innerHTML = `<td><input class="service-select" type="checkbox" value="${escapeHtml(record.key)}" aria-label="Seleccionar ${escapeHtml(record.service_name)}"></td><td><strong>${escapeHtml(record.plan_name)}</strong><span class="tag">${escapeHtml(record.solution || record.plan)}</span></td><td><strong>${escapeHtml(record.service_name)}</strong><span class="muted">${escapeHtml(record.service_type)}</span></td><td class="money">${money(record.charge_with_tax)}</td><td class="money discount">—</td><td class="money new">—</td><td><span class="tag">SNCODE ${escapeHtml(record.sncode)}</span></td>`;
    tbody.appendChild(row);
  });
  $$('.service-select').forEach(input => input.addEventListener('change', updateSelection));
  $('#campaign-message').textContent = `${data.records.length} servicio(s) cargados correctamente.`;
  $('#campaign-message').className = 'status-line success'; updateCalculation(); updateSelection();
}

function updateSelection() {
  const count = selectedKeys().length;
  $('#selection-count').textContent = `${count} seleccionado${count === 1 ? '' : 's'} de ${state.records.length}`;
  $('#preview-button').disabled = !count;
  if ($('#select-all')) $('#select-all').checked = count > 0 && count === state.records.length;
}

function offerPayload() { return { campaign: state.campaign?.code, selected_keys: selectedKeys(), discount_type: $('#discount-type').value, discount_value: $('#discount-value').value, period: $('#period').value }; }

async function previewOffer() {
  try {
    $('#preview-button').disabled = true;
    const data = await api('/api/ofertas/previsualizar', { method: 'POST', body: JSON.stringify(offerPayload()) });
    state.preview = data; $('#preview-campaign').textContent = `Campaña ${state.campaign.code} · ${state.campaign.name} · ${data.operations.length} registro(s)`;
    const labels = [['new','Nuevos'],['update','Por actualizar'],['unchanged','Sin cambios'],['errors','Errores']];
    $('#preview-counts').innerHTML = labels.map(([key,label]) => `<div class="metric"><strong>${data.counts[key]}</strong><span>${label}</span></div>`).join('');
    $('#preview-list').innerHTML = data.operations.map(item => `<div class="preview-item"><div><strong>${escapeHtml(item.service_name)}</strong><span class="muted">${escapeHtml(item.key)} · ${item.period} meses</span></div><div><span class="money discount">-${money(item.discount_value)}</span><strong class="money new">${money(item.new_charge)}</strong></div></div>`).join('');
    $('#write-warning').textContent = data.mode === 'demo' ? 'Esta confirmación solo modifica la simulación en memoria; no realiza COMMIT en DWO.' : (data.write_enabled ? 'La operación se revalidará y ejecutará en una transacción DWO.' : 'La escritura DWO está deshabilitada por configuración.');
    $('#save-button').disabled = data.mode !== 'demo' && !data.write_enabled;
    $('#preview-dialog').showModal();
  } catch (error) { toast(error.message, 'error'); } finally { updateSelection(); }
}

async function saveOffer() {
  const button = $('#save-button'); button.disabled = true; button.textContent = 'Procesando…';
  try {
    const data = await api('/api/ofertas/guardar', { method: 'POST', body: JSON.stringify(offerPayload()) });
    $('#preview-dialog').close();
    const r = data.result; toast(`${data.mode === 'demo' ? 'Simulación actualizada' : 'Transacción confirmada'}: ${r.inserted} nuevos, ${r.updated} actualizados, ${r.unchanged} sin cambios.`);
    loadStoredCount();
  } catch (error) { toast(error.message, 'error'); } finally { button.disabled = false; button.textContent = 'Confirmar y guardar'; }
}

function resetOffer() {
  state.campaign = null; state.records = []; state.preview = null;
  $('#campaign-form')?.reset(); if ($('#campaign-name')) $('#campaign-name').value = ''; if ($('#campaign-source')) $('#campaign-source').value = 'Sin consulta';
  const tbody = $('#services-table tbody'); if (tbody) tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Busca una campaña para cargar sus servicios.</td></tr>';
  if ($('#campaign-message')) $('#campaign-message').textContent = ''; updateSelection();
}

async function loadOffersInto(selectId) {
  const select = $(selectId); if (!select) return;
  try { const data = await api('/api/ofertas'); data.rows.forEach(row => { const option = document.createElement('option'); option.value = row.llave; option.textContent = `${row.campana} · ${row.dsc_plan || row.llave} (${row.llave})`; select.appendChild(option); }); } catch (error) { toast(error.message, 'error'); }
}

async function loadHistory() {
  if (!$('#history-table')) return;
  const q = encodeURIComponent($('#history-query').value); const s = encodeURIComponent($('#history-state').value);
  try {
    const data = await api(`/api/ofertas?q=${q}&state=${s}&page=${state.page}`);
    $('#history-table tbody').innerHTML = data.rows.length ? data.rows.map(row => `<tr><td><span class="tag">${escapeHtml(row.llave || '')}</span></td><td><strong>${escapeHtml(String(row.campana || ''))}</strong><span class="muted">${escapeHtml(row.dsc_campana || '')}</span></td><td><strong>${escapeHtml(row.dsc_plan || '')}</strong><span class="muted">SNCODE ${escapeHtml(String(row.sncode || ''))}</span></td><td>${money(row.dscto || 0)}</td><td><span class="status-badge">${escapeHtml(row.estado_np || '')}</span></td><td>${escapeHtml(formatDate(row.fecha_carga))}</td></tr>`).join('') : '<tr class="empty-row"><td colspan="6">No se encontraron registros.</td></tr>';
    $('#page-label').textContent = `Página ${state.page}`; $('#prev-page').disabled = state.page === 1; $('#next-page').disabled = data.rows.length < 20;
  } catch (error) { toast(error.message, 'error'); }
}

function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value ?? ''; return div.innerHTML; }
function formatDate(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('es-PE'); }

document.addEventListener('DOMContentLoaded', () => {
  loadStoredCount();
  $('#campaign-form')?.addEventListener('submit', async event => { event.preventDefault(); const code = $('#campaign-code').value.trim(); $('#campaign-message').textContent = 'Consultando campaña…'; $('#campaign-message').className = 'status-line'; try { renderCampaign(await api(`/api/campanas/${encodeURIComponent(code)}`)); } catch (error) { $('#campaign-message').textContent = error.message; $('#campaign-message').className = 'status-line error'; } });
  ['#discount-type','#discount-value','#period'].forEach(selector => $(selector)?.addEventListener('input', updateCalculation));
  $('#select-all')?.addEventListener('change', event => { $$('.service-select').forEach(input => input.checked = event.target.checked); updateSelection(); });
  $('#preview-button')?.addEventListener('click', previewOffer); $('#save-button')?.addEventListener('click', saveOffer); $('#new-button')?.addEventListener('click', resetOffer);
  loadOffersInto('#validity-key'); loadOffersInto('#state-key');
  $('#validity-form')?.addEventListener('submit', async event => { event.preventDefault(); try { await api(`/api/ofertas/${encodeURIComponent($('#validity-key').value)}/vigencia`, { method: 'PATCH', body: JSON.stringify({ starts_on: $('#starts-on').value, ends_on: $('#ends-on').value }) }); toast('Vigencia actualizada en la simulación.'); } catch (error) { toast(error.message, 'error'); } });
  $('#state-form')?.addEventListener('submit', async event => { event.preventDefault(); try { await api(`/api/ofertas/${encodeURIComponent($('#state-key').value)}/estado`, { method: 'PATCH', body: JSON.stringify({ state: $('#new-state').value, note: $('#state-note').value }) }); toast('Estado actualizado en la simulación.'); } catch (error) { toast(error.message, 'error'); } });
  $('#history-form')?.addEventListener('submit', event => { event.preventDefault(); state.page = 1; loadHistory(); });
  $('#prev-page')?.addEventListener('click', () => { state.page = Math.max(1, state.page - 1); loadHistory(); });
  $('#next-page')?.addEventListener('click', () => { state.page += 1; loadHistory(); });
  loadHistory();
});


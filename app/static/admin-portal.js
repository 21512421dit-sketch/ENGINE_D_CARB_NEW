(() => {
  'use strict';
  const body = document.getElementById('submissionRows');
  const count = document.getElementById('submissionCount');
  if (!body || !count) return;
  let latestId = body.querySelector('tr[data-id]')?.dataset.id || '';
  const text = value => document.createTextNode(value == null ? '' : String(value));
  const cell = value => { const td = document.createElement('td'); td.append(text(value)); return td; };
  const render = data => {
    count.textContent = `${data.total} records`;
    body.replaceChildren();
    if (!data.rows.length) {
      const tr = document.createElement('tr'); tr.className = 'empty-row';
      const td = cell('No consented requests match these filters.'); td.colSpan = 7; tr.append(td); body.append(tr); return;
    }
    data.rows.forEach(row => {
      const tr = document.createElement('tr'); tr.dataset.id = row.id;
      tr.append(cell(new Intl.DateTimeFormat('en-IN', {dateStyle:'medium', timeStyle:'short'}).format(new Date(row.created_at))));
      tr.append(cell(row.name || 'Not provided'));
      tr.append(cell([row.phone, row.email].filter(Boolean).join(' · ')));
      tr.append(cell(row.form_kind.replaceAll('_', ' ')));
      tr.append(cell(row.employee));
      tr.append(cell(row.result.indicative_cost ? new Intl.NumberFormat('en-IN', {style:'currency', currency:'INR', maximumFractionDigits:0}).format(row.result.indicative_cost) : row.result.quotation?.status?.replaceAll('_',' ') || 'Received'));
      const td = document.createElement('td'), details = document.createElement('details'), summary = document.createElement('summary'), pre = document.createElement('pre');
      summary.textContent = 'View'; pre.textContent = JSON.stringify(row.details, null, 2); details.append(summary, pre); td.append(details); tr.append(td); body.append(tr);
    });
    latestId = String(data.rows[0].id);
  };
  const refresh = async () => {
    try {
      const response = await fetch(`/admin/submissions.json?${new URLSearchParams(location.search)}`, {headers:{'Accept':'application/json'}});
      if (!response.ok) return;
      const data = await response.json();
      if (String(data.rows[0]?.id || '') !== latestId || count.textContent !== `${data.total} records`) render(data);
    } catch (_) {}
  };
  setInterval(refresh, 10000);
})();

(() => {
  'use strict';
  const body = document.getElementById('submissionRows');
  const count = document.getElementById('submissionCount');
  if (!body || !count) return;
  let latestId = body.querySelector('tr[data-id]')?.dataset.id || '';
  const text = value => document.createTextNode(value == null ? '' : String(value));
  const cell = value => { const td = document.createElement('td'); td.append(text(value)); return td; };
  const dialog = document.getElementById('detailsDialog');
  const dialogTitle = document.getElementById('detailsDialogTitle');
  const dialogList = document.getElementById('detailsDialogList');
  const showDetails = (customer, fields) => {
    dialogTitle.textContent = customer || 'Request details'; dialogList.replaceChildren();
    fields.forEach(field => {
      const item = document.createElement('div'), term = document.createElement('dt'), description = document.createElement('dd');
      term.append(text(field.label)); description.append(text(field.value)); item.append(term, description); dialogList.append(item);
    });
    dialog.showModal();
  };
  body.addEventListener('click', event => {
    const button = event.target.closest('.details-button');
    if (!button) return;
    showDetails(button.dataset.customer, JSON.parse(button.dataset.details));
  });
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  document.querySelectorAll('.centre-contact-delete').forEach(form => form.addEventListener('submit', event => {
    if (!window.confirm('Remove this WhatsApp number from the centre?')) event.preventDefault();
  }));
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
      const td = document.createElement('td'), detailsButton = document.createElement('button');
      detailsButton.type = 'button'; detailsButton.className = 'details-button'; detailsButton.textContent = 'View details';
      detailsButton.dataset.customer = row.name || 'Customer request'; detailsButton.dataset.details = JSON.stringify(row.details_display);
      td.append(detailsButton);
      if (row.quotation_pdf_url) {
        const actions = document.createElement('div'); actions.className = 'quote-admin-actions';
        const view = document.createElement('a'); view.href = row.quotation_pdf_url; view.target = '_blank'; view.rel = 'noopener'; view.textContent = 'View PDF';
        const download = document.createElement('a'); download.href = `${row.quotation_pdf_url}?download=1`; download.textContent = 'Download';
        actions.append(view, download); td.append(actions);
      }
      tr.append(td); body.append(tr);
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

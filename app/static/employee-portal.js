(() => {
  'use strict';
  const panels = [...document.querySelectorAll('[data-panel]')];
  document.querySelectorAll('[data-workspace]').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('[data-workspace]').forEach(item => item.classList.toggle('active', item === button));
    panels.forEach(panel => { const active = panel.dataset.panel === button.dataset.workspace; panel.hidden = !active; panel.classList.toggle('active', active); });
  }));

  const batteryForm = document.getElementById('employeeBatteryForm');
  const mode = batteryForm.elements.solution_type;
  const application = batteryForm.elements.application_key;
  const host = batteryForm.querySelector('[data-battery-fields]');
  const status = batteryForm.querySelector('.form-status');
  let schemas = {};
  const option = (value, label) => { const item = document.createElement('option'); item.value = value; item.textContent = label; return item; };
  const updateConditions = () => host.querySelectorAll('[data-show-when]').forEach(wrapper => {
    const rule = JSON.parse(wrapper.dataset.showWhen);
    const visible = String(batteryForm.elements[rule.field]?.value || '') === String(rule.value);
    wrapper.hidden = !visible;
    const control = wrapper.querySelector('input,select,textarea');
    control.disabled = !visible;
    control.required = visible && control.dataset.schemaRequired === 'true';
  });
  const renderFields = schema => {
    host.replaceChildren();
    schema.fields.forEach(field => {
      let control;
      if (field.type === 'hidden') {
        control = document.createElement('input'); control.type = 'hidden'; control.name = field.name; control.value = field.value || ''; host.append(control); return;
      }
      const wrapper = document.createElement('label'); if (field.type === 'textarea') wrapper.className = 'wide';
      wrapper.append(document.createTextNode(`${field.label}${field.required ? ' *' : ''}`));
      const selectOptions = Array.isArray(field.options) ? field.options : [];
      if (field.type === 'select' && selectOptions.length) {
        control = document.createElement('select'); control.append(option('', 'Select'));
        selectOptions.forEach(item => control.append(option(typeof item === 'string' ? item : item.value, typeof item === 'string' ? item : item.label)));
      } else if (field.type === 'select') {
        control = document.createElement('input'); control.type = 'text';
        control.placeholder = `Enter ${field.label.toLowerCase()} manually…`;
        control.autocomplete = 'off';
      } else if (field.type === 'textarea') control = document.createElement('textarea');
      else { control = document.createElement('input'); control.type = field.type || 'text'; }
      control.name = field.name;
      if (field.pattern) control.pattern = field.pattern;
      if (field.min !== undefined) control.min = field.min;
      if (field.max !== undefined) control.max = field.max;
      if (field.required) { control.required = true; control.dataset.schemaRequired = 'true'; }
      if (field.show_when) wrapper.dataset.showWhen = JSON.stringify(field.show_when);
      wrapper.append(control); host.append(wrapper);
    });
    updateConditions();
  };
  fetch('/api/form-schemas', {headers:{Accept:'application/json'}}).then(response => response.json()).then(data => {
    schemas = data;
    Object.entries(data).forEach(([key, schema]) => mode.append(option(key, schema.label)));
  }).catch(() => { status.textContent = 'The form catalogue could not be loaded. Refresh and try again.'; status.className = 'form-status error'; });
  mode.addEventListener('change', () => {
    application.replaceChildren(option('', mode.value ? 'Select an application' : 'Select a requirement first'));
    application.disabled = !mode.value; host.replaceChildren();
    Object.entries(schemas[mode.value]?.applications || {}).forEach(([key, schema]) => application.append(option(key, schema.label)));
  });
  application.addEventListener('change', () => {
    const schema = schemas[mode.value]?.applications?.[application.value];
    if (!schema) return host.replaceChildren();
    batteryForm.elements.application.value = schema.label;
    batteryForm.elements.battery_type.value = schemas[mode.value].label;
    renderFields(schema);
  });
  host.addEventListener('change', updateConditions);
  batteryForm.addEventListener('submit', async event => {
    event.preventDefault(); status.textContent = 'Preparing quotation…'; status.className = 'form-status';
    const payload = Object.fromEntries(new FormData(batteryForm)); payload.consent = payload.consent === 'true';
    try {
      const response = await fetch('/api/quotations', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not prepare the quotation.');
      status.textContent = `${data.quotation.number} prepared — ${data.quotation.status.replaceAll('_', ' ')}.`; status.className = 'form-status success';
    } catch (error) { status.textContent = error.message; status.className = 'form-status error'; }
  });

  const engineForm = document.getElementById('employeeEngineForm');
  const engineStatus = engineForm.querySelector('.form-status');
  const switchEngineKind = () => {
    const kind = engineForm.elements.enquiryType.value;
    ['service', 'machine'].forEach(name => {
      const section = engineForm.querySelector(`[data-engine-${name}]`), active = kind === name;
      section.hidden = !active;
      section.querySelectorAll('input,select,textarea').forEach(control => control.disabled = !active);
    });
  };
  engineForm.elements.enquiryType.forEach(item => item.addEventListener('change', switchEngineKind)); switchEngineKind();
  engineForm.addEventListener('submit', async event => {
    event.preventDefault(); engineStatus.textContent = 'Preparing quotation…'; engineStatus.className = 'form-status';
    const payload = Object.fromEntries(new FormData(engineForm)); payload.consent = payload.consent === 'true';
    try {
      const response = await fetch('/api/engine-d-carb/quotations', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not prepare the quotation.');
      engineStatus.textContent = data.indicative_cost ? `Indicative service cost: ${new Intl.NumberFormat('en-IN', {style:'currency', currency:'INR', maximumFractionDigits:0}).format(data.indicative_cost)}.` : 'Machine enquiry recorded.';
      engineStatus.className = 'form-status success';
    } catch (error) { engineStatus.textContent = error.message; engineStatus.className = 'form-status error'; }
  });
})();

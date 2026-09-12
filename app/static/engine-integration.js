(() => {
  'use strict';
  const form = document.getElementById('enquiryForm');
  if (!form) return;

  const submit = form.querySelector('.enquiry-submit, button[type="submit"]');
  const emailQuote = form.elements.emailQuote;
  const serviceEmail = form.elements.serviceEmail;
  const serviceGrid = document.querySelector('#serviceFields .form-grid');
  const serviceDetails = document.getElementById('serviceDetails')?.closest('.field');
  const centreField = document.createElement('div');
  centreField.className = 'field full engine-centre-field';
  centreField.innerHTML = `<label for="selectedCentre">Nearest service centre <span>*</span></label>
    <select id="selectedCentre" name="selectedCentre" required disabled>
      <option value="">Loading service centres…</option>
    </select>
    <div class="engine-centre-preview" id="engineCentrePreview" aria-live="polite">Choose the centre most convenient for your visit.</div>`;
  serviceGrid?.insertBefore(centreField, serviceDetails || null);
  const centreSelect = centreField.querySelector('select');
  const centrePreview = centreField.querySelector('.engine-centre-preview');
  let centres = [];

  const syncCentreState = () => {
    const isService = form.elements.enquiryType?.value === 'service';
    centreSelect.disabled = !isService || !centres.length;
    centreSelect.required = isService;
    submit.disabled = isService && !centres.length;
    if (serviceEmail) serviceEmail.required = isService && emailQuote?.checked;
  };
  form.querySelectorAll('input[name="enquiryType"]').forEach(input => input.addEventListener('change', syncCentreState));
  emailQuote?.addEventListener('change', syncCentreState);
  centreSelect.addEventListener('change', () => {
    const centre = centres.find(item => item.key === centreSelect.value);
    centrePreview.textContent = centre ? centre.address : 'Choose the centre most convenient for your visit.';
  });
  fetch('/api/engine-d-carb/centres', {headers:{'Accept':'application/json'}})
    .then(response => response.ok ? response.json() : Promise.reject(new Error('Unable to load service centres.')))
    .then(data => {
      centres = data.centres || [];
      centreSelect.replaceChildren(new Option('Select your nearest centre', ''));
      centres.forEach(centre => centreSelect.add(new Option(centre.name, centre.key)));
      syncCentreState();
    })
    .catch(failure => {
      centreSelect.replaceChildren(new Option('Service centres unavailable', ''));
      centrePreview.textContent = `${failure.message} Please refresh the page or contact Engine D-Carb.`;
      syncCentreState();
    });
  const consent = document.createElement('label');
  consent.className = 'engine-consent';
  consent.innerHTML = `<input type="checkbox" name="consent" value="true" required>
    <span>I consent to Engine D-Carb and Care4Earth Enterprises storing the details I submit for 24 months to prepare and manage my quotation and analyze service demand. My information will not be sold or used for promotional marketing. I can request correction or deletion using the contact details on this website.</span>`;
  submit.before(consent);

  form.addEventListener('submit', async event => {
    if (form.dataset.backendSaved === 'true') {
      delete form.dataset.backendSaved;
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    const error = document.getElementById('enquiryError');
    if (!form.reportValidity()) {
      error.textContent = 'Complete the required fields and accept the data-storage consent.';
      error.classList.add('visible');
      return;
    }
    const payload = Object.fromEntries(new FormData(form));
    payload.consent = payload.consent === 'true';
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    const originalLabel = submit.textContent;
    submit.textContent = 'Saving enquiry…';
    try {
      const response = await fetch('/api/engine-d-carb/quotations', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'},
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to save the enquiry.');
      form.dataset.backendSaved = 'true';
      form.requestSubmit();
      const enquiryType = payload.enquiryType;
      const title = document.getElementById('quoteTitle');
      const greeting = document.getElementById('quoteGreeting');
      if (enquiryType === 'machine') {
        title.textContent = `Thank you, ${payload.representativeName}. Your machine enquiry has been received.`;
        greeting.textContent = 'Our machine sales team will review your business requirements and contact you about the most suitable Engine D-Carb configuration. Select Continue to send the prepared enquiry on WhatsApp.';
      } else {
        title.textContent = `Thank you, ${payload.customerName}. Your vehicle service enquiry has been received.`;
        const cost = result.indicative_cost
          ? ` The current tentative estimate is ${new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR', maximumFractionDigits: 0}).format(result.indicative_cost)}; the service team will confirm the final price.`
          : '';
        greeting.textContent = `Your vehicle details are ready for ${result.centre.name}.${cost} The two WhatsApp messages are prepared and will be sent automatically after the WhatsApp connection is configured.`;
        const actions = document.querySelector('#quoteResult .quote-actions');
        const whatsapp = document.getElementById('quoteWhatsApp');
        whatsapp.removeAttribute('href');
        whatsapp.removeAttribute('target');
        whatsapp.setAttribute('aria-disabled', 'true');
        whatsapp.textContent = 'WhatsApp setup pending';
        let messagePanel = document.getElementById('engineMessagePreview');
        if (!messagePanel) {
          messagePanel = document.createElement('div');
          messagePanel.id = 'engineMessagePreview';
          messagePanel.className = 'engine-message-preview';
          actions?.before(messagePanel);
        }
        messagePanel.replaceChildren();
        const heading = document.createElement('strong');
        heading.textContent = 'Prepared customer message';
        const message = document.createElement('pre');
        message.textContent = result.messages.customer;
        const copy = document.createElement('button');
        copy.type = 'button';
        copy.className = 'quote-action';
        copy.textContent = 'Copy customer message';
        copy.addEventListener('click', async () => {
          if (navigator.clipboard) await navigator.clipboard.writeText(result.messages.customer);
          else {
            const box = document.createElement('textarea');
            box.value = result.messages.customer;
            document.body.append(box);
            box.select();
            document.execCommand('copy');
            box.remove();
          }
          copy.textContent = 'Customer message copied';
        });
        messagePanel.append(heading, message, copy);
      }
      if (payload.emailQuote === 'true') {
        const delivery = result.email_delivery || [];
        const delivered = delivery.length === 2 && delivery.every(item => item.status === 'sent');
        greeting.textContent += delivered
          ? ' The quotation was emailed to you and a copy was sent to Engine D-Carb.'
          : ' Your enquiry was saved, but email delivery could not be completed. Please contact Engine D-Carb if you do not receive it.';
        const manualEmail = document.getElementById('quoteEmail');
        if (manualEmail) manualEmail.hidden = true;
      }
      form.hidden = true;
      document.getElementById('quoteResult')?.focus({preventScroll: true});
    } catch (failure) {
      error.textContent = failure.message;
      error.classList.add('visible');
      error.focus?.();
    } finally {
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
      submit.textContent = originalLabel;
      syncCentreState();
    }
  }, true);
})();

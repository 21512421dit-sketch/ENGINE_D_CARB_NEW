(() => {
  'use strict';
  const form = document.getElementById('enquiryForm');
  if (!form) return;

  const submit = form.querySelector('.enquiry-submit, button[type="submit"]');
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
        greeting.textContent = `Your vehicle details are ready for the Engine D-Carb service team.${cost} Select Continue to request confirmation and the nearest service-centre details.`;
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
    }
  }, true);
})();

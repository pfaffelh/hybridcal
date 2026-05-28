// Submit + correction form handlers (Alpine x-data factories).
// Extracted from an inline <script> so the page can run under a CSP
// without script-src 'unsafe-inline'.
async function postToWeb3Forms(form) {
  const formData = new FormData(form);
  const response = await fetch('https://api.web3forms.com/submit', {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
    body: formData,
  });
  return response.json();
}

function makeFormState(scrollTarget) {
  return {
    status: 'idle', // 'idle' | 'submitting' | 'success' | 'error'
    async submit(event) {
      this.status = 'submitting';
      try {
        const result = await postToWeb3Forms(event.target);
        if (result.success) {
          this.status = 'success';
          if (scrollTarget === 'top') {
            window.scrollTo({ top: 0, behavior: 'smooth' });
          } else if (scrollTarget === 'self') {
            event.target.closest('[x-data]')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        } else {
          console.error('Web3Forms error:', result);
          this.status = 'error';
        }
      } catch (err) {
        console.error('Submit error:', err);
        this.status = 'error';
      }
    },
  };
}

function submitForm() { return makeFormState('top'); }
function correctionForm() { return makeFormState('self'); }

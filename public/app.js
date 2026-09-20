document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const selectedFileLabel = document.getElementById('selectedFile');
  const sampleCards = document.querySelectorAll('.sample-card');
  const useApiCheck = document.getElementById('useApiCheck');
  const generateBtn = document.getElementById('generateBtn');

  const statusCard = document.getElementById('statusCard');
  const progressBar = document.getElementById('progressBar');
  const resultBox = document.getElementById('resultBox');
  const errorBox = document.getElementById('errorBox');
  const errorMessage = document.getElementById('errorMessage');
  const resultMarketName = document.getElementById('resultMarketName');
  const downloadDocxBtn = document.getElementById('downloadDocxBtn');
  const downloadJsonBtn = document.getElementById('downloadJsonBtn');

  let selectedFileData = null; // { filename, base64 }
  let selectedSampleName = null;
  let generatedResult = null; // { filename, docx_base64, audit_json }

  // Drag and drop handlers
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  });

  function handleFileSelect(file) {
    if (!file.name.endsWith('.docx')) {
      alert('Please upload a valid Microsoft Word (.docx) document.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Str = e.target.result.split(',')[1];
      selectedFileData = {
        filename: file.name,
        base64: base64Str
      };
      selectedSampleName = null;
      clearSampleActiveState();

      selectedFileLabel.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      selectedFileLabel.style.display = 'inline-block';
    };
    reader.readAsDataURL(file);
  }

  // Sample cards click handler
  sampleCards.forEach(card => {
    card.addEventListener('click', () => {
      clearSampleActiveState();
      card.classList.add('active');
      selectedSampleName = card.getAttribute('data-sample');
      selectedFileData = null;
      fileInput.value = '';
      selectedFileLabel.textContent = `Selected Preset: ${selectedSampleName}`;
      selectedFileLabel.style.display = 'inline-block';
    });
  });

  function clearSampleActiveState() {
    sampleCards.forEach(b => b.classList.remove('active'));
  }

  // Stage status updater
  function setStage(stageId, status) {
    const el = document.getElementById(stageId);
    if (!el) return;
    el.className = `pipeline-step ${status}`;
  }

  function resetStages() {
    ['stageParse', 'stageAi', 'stagePayload', 'stageRender'].forEach(id => {
      setStage(id, '');
    });
    progressBar.style.width = '0%';
    resultBox.classList.add('hidden');
    errorBox.classList.add('hidden');
  }

  // Generate Report Action
  generateBtn.addEventListener('click', async () => {
    if (!selectedFileData && !selectedSampleName) {
      alert('Please select or upload an input DOCX file first.');
      return;
    }

    statusCard.classList.remove('hidden');
    statusCard.scrollIntoView({ behavior: 'smooth' });
    resetStages();

    generateBtn.disabled = true;

    try {
      // Stage 1: Parse
      setStage('stageParse', 'running');
      progressBar.style.width = '25%';

      const payload = {
        use_api: useApiCheck.checked
      };

      if (selectedFileData) {
        payload.file_data = selectedFileData.base64;
        payload.filename = selectedFileData.filename;
      } else if (selectedSampleName) {
        payload.sample_name = selectedSampleName;
      }

      // Stage 2: AI Generation
      setTimeout(() => {
        setStage('stageParse', 'success');
        setStage('stageAi', 'running');
        progressBar.style.width = '50%';
      }, 500);

      // Stage 3 & 4
      setTimeout(() => {
        setStage('stageAi', 'success');
        setStage('stagePayload', 'running');
        setStage('stageRender', 'running');
        progressBar.style.width = '85%';
      }, 1200);

      // Send Request to API endpoint (with fallback to /.netlify/functions/generate)
      let apiEndpoint = '/api/generate';
      let response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const contentType = response.headers.get('content-type') || '';
      if (!response.ok || contentType.includes('text/html')) {
        // Fallback to Netlify function direct path if redirect returned HTML
        apiEndpoint = '/.netlify/functions/generate';
        response = await fetch(apiEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      const resData = await response.json();

      if (!response.ok || !resData.success) {
        throw new Error(resData.error || 'Server returned an error');
      }

      // Complete stages
      setStage('stagePayload', 'success');
      setStage('stageRender', 'success');
      progressBar.style.width = '100%';

      generatedResult = resData;
      resultMarketName.textContent = `Report generated for: ${resData.market_name}`;
      resultBox.classList.remove('hidden');

    } catch (err) {
      console.error(err);
      errorMessage.textContent = err.message || 'An unexpected error occurred.';
      errorBox.classList.remove('hidden');
    } finally {
      generateBtn.disabled = false;
    }
  });

  // Download DOCX file trigger
  downloadDocxBtn.addEventListener('click', () => {
    if (!generatedResult || !generatedResult.docx_base64) return;

    const byteCharacters = atob(generatedResult.docx_base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    });

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = generatedResult.filename || 'generated_report.docx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  // Download JSON audit trigger
  downloadJsonBtn.addEventListener('click', () => {
    if (!generatedResult || !generatedResult.audit_json) return;

    const str = JSON.stringify(generatedResult.audit_json, null, 2);
    const blob = new Blob([str], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = (generatedResult.filename || 'report').replace('.docx', '.json');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
});

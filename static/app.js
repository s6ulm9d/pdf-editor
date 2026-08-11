document.addEventListener('DOMContentLoaded', () => {
    // Tabs
    const tabSingle = document.getElementById('tabSingle');
    const tabBulk = document.getElementById('tabBulk');
    const modeSingleSection = document.getElementById('modeSingleSection');
    const modeBulkSection = document.getElementById('modeBulkSection');

    // Single elements
    const dropZoneSingle = document.getElementById('dropZoneSingle');
    const pdfFileInput = document.getElementById('pdfFileInput');
    const fileInfo = document.getElementById('fileInfo');
    const analysisSection = document.getElementById('analysisSection');
    const modeBadge = document.getElementById('modeBadge');
    const pagesCount = document.getElementById('pagesCount');
    const imagesCount = document.getElementById('imagesCount');
    const vectorsCount = document.getElementById('vectorsCount');
    const fieldInputsContainer = document.getElementById('fieldInputsContainer');
    const addFieldBtn = document.getElementById('addFieldBtn');
    const executeEditBtn = document.getElementById('executeEditBtn');
    const nlInstruction = document.getElementById('nlInstruction');
    const downloadBtn = document.getElementById('downloadBtn');

    // Bulk elements
    const bulkPdfInput = document.getElementById('bulkPdfInput');
    const bulkPdfInfo = document.getElementById('bulkPdfInfo');
    const bulkDataInput = document.getElementById('bulkDataInput');
    const bulkDataInfo = document.getElementById('bulkDataInfo');
    const bulkMappingContainer = document.getElementById('bulkMappingContainer');
    const addBulkMapBtn = document.getElementById('addBulkMapBtn');
    const executeBulkBtn = document.getElementById('executeBulkBtn');
    const bulkResultsBox = document.getElementById('bulkResultsBox');
    const bulkSummaryText = document.getElementById('bulkSummaryText');
    const downloadZipBtn = document.getElementById('downloadZipBtn');

    // Email Dispatch elements
    const sendEmailToggle = document.getElementById('sendEmailToggle');
    const emailConfigBox = document.getElementById('emailConfigBox');
    const emailColSelect = document.getElementById('emailColSelect');
    const emailSubjectInput = document.getElementById('emailSubjectInput');
    const emailBodyInput = document.getElementById('emailBodyInput');

    // Shared UI
    const statusAlert = document.getElementById('statusAlert');
    const statusText = document.getElementById('statusText');
    const validationResults = document.getElementById('validationResults');
    const emptyState = document.getElementById('emptyState');

    let currentFile = null;
    let bulkPdfFile = null;
    let bulkDataFile = null;
    let availableColumns = [];
    let detectedPdfFields = [];

    // Email toggle handler
    sendEmailToggle.addEventListener('change', () => {
        emailConfigBox.style.display = sendEmailToggle.checked ? 'block' : 'none';
    });

    // Tab Switcher
    tabSingle.addEventListener('click', () => {
        tabSingle.classList.add('active');
        tabBulk.classList.remove('active');
        modeSingleSection.style.display = 'block';
        modeBulkSection.style.display = 'none';
        resetOutputDisplays();
    });

    tabBulk.addEventListener('click', () => {
        tabBulk.classList.add('active');
        tabSingle.classList.remove('active');
        modeBulkSection.style.display = 'block';
        modeSingleSection.style.display = 'none';
        resetOutputDisplays();
    });

    function resetOutputDisplays() {
        validationResults.style.display = 'none';
        bulkResultsBox.style.display = 'none';
        emptyState.style.display = 'block';
        statusAlert.style.display = 'none';
    }

    // --- SINGLE PDF HANDLERS ---
    pdfFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleSingleFile(e.target.files[0]);
        }
    });

    async function handleSingleFile(file) {
        if (file.type !== 'application/pdf') {
            alert('Please select a valid PDF file.');
            return;
        }
        currentFile = file;
        fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

        const formData = new FormData();
        formData.append('file', file);
        showStatus('Analyzing PDF structure...', 'info');

        try {
            const resp = await fetch('/pdf/analyze', { method: 'POST', body: formData });
            const data = await resp.json();

            if (resp.ok) {
                analysisSection.style.display = 'block';
                modeBadge.textContent = data.mode;
                pagesCount.textContent = data.total_pages;
                imagesCount.textContent = data.total_images;
                vectorsCount.textContent = data.total_drawings;

                if (data.candidate_fields && data.candidate_fields.length > 0) {
                    fieldInputsContainer.innerHTML = '';
                    data.candidate_fields.slice(0, 4).forEach(cand => {
                        const label = cand.text.split(':')[0].trim();
                        if (label.length < 25) {
                            createFieldRow(label, '');
                        }
                    });
                }
                showStatus('PDF analyzed successfully.', 'success');
            } else {
                showStatus(`Analysis failed: ${data.detail}`, 'danger');
            }
        } catch (err) {
            showStatus(`Error analyzing PDF: ${err.message}`, 'danger');
        }
    }

    function createFieldRow(key = '', val = '') {
        const row = document.createElement('div');
        row.className = 'field-row';
        row.innerHTML = `
            <input type="text" class="input-field key-input" placeholder="Field name (e.g. Name, Date)" value="${key}">
            <input type="text" class="input-field val-input" placeholder="New replacement value" value="${val}">
            <button class="btn-icon remove-row-btn">&times;</button>
        `;
        row.querySelector('.remove-row-btn').addEventListener('click', () => row.remove());
        fieldInputsContainer.appendChild(row);
    }

    addFieldBtn.addEventListener('click', () => createFieldRow());

    executeEditBtn.addEventListener('click', async () => {
        if (!currentFile) {
            alert('Please upload a PDF template file first.');
            return;
        }

        const changes = {};
        fieldInputsContainer.querySelectorAll('.field-row').forEach(row => {
            const k = row.querySelector('.key-input').value.trim();
            const v = row.querySelector('.val-input').value.trim();
            if (k && v) changes[k] = v;
        });

        const formData = new FormData();
        formData.append('file', currentFile);
        if (Object.keys(changes).length > 0) {
            formData.append('changes_json', JSON.stringify(changes));
        }

        const nlVal = nlInstruction.value.trim();
        if (nlVal) formData.append('instruction', nlVal);

        if (Object.keys(changes).length === 0 && !nlVal) {
            alert('Please specify at least one field change or instruction.');
            return;
        }

        showStatus('Executing targeted mutation and running validation...', 'info');

        try {
            const resp = await fetch('/pdf/edit', { method: 'POST', body: formData });
            const data = await resp.json();

            if (resp.ok && data.success) {
                emptyState.style.display = 'none';
                validationResults.style.display = 'block';
                bulkResultsBox.style.display = 'none';
                downloadBtn.href = data.download_url;
                showStatus('Mutation completed & 100% validated!', 'success');
            } else {
                validationResults.style.display = 'none';
                showStatus(`Mutation rejected: ${data.reason || data.message || 'Unsafe edit'}`, 'danger');
            }
        } catch (err) {
            showStatus(`Error executing edit: ${err.message}`, 'danger');
        }
    });

    // --- BULK EXCEL/CSV HANDLERS ---
    bulkPdfInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            bulkPdfFile = e.target.files[0];
            bulkPdfInfo.textContent = `PDF Template: ${bulkPdfFile.name}`;

            // Analyze PDF for candidate fields
            const formData = new FormData();
            formData.append('file', bulkPdfFile);
            try {
                const resp = await fetch('/pdf/analyze', { method: 'POST', body: formData });
                const data = await resp.json();
                if (resp.ok && data.text_spans) {
                    const uniqueSpans = new Set();
                    data.text_spans.forEach(s => {
                        const txt = s.text.trim();
                        if (txt.length >= 2 && txt.length < 35 && !uniqueSpans.has(txt)) {
                            uniqueSpans.add(txt);
                        }
                    });
                    detectedPdfFields = Array.from(uniqueSpans);
                }
            } catch (err) {
                console.error("PDF analysis failed", err);
            }
            renderBulkMappingRows();
        }
    });

    bulkDataInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            bulkDataFile = e.target.files[0];
            bulkDataInfo.textContent = `Data File: ${bulkDataFile.name}`;

            // Parse columns from Excel/CSV file
            const formData = new FormData();
            formData.append('file', bulkDataFile);
            showStatus('Reading Excel/CSV headers...', 'info');

            try {
                const resp = await fetch('/pdf/parse-columns', { method: 'POST', body: formData });
                const data = await resp.json();

                if (resp.ok && data.columns) {
                    availableColumns = data.columns;
                    populateEmailColSelect();
                    showStatus(`Found ${availableColumns.length} columns in ${bulkDataFile.name}`, 'success');
                    renderBulkMappingRows();
                } else {
                    showStatus(`Failed to parse file headers: ${data.detail}`, 'danger');
                }
            } catch (err) {
                showStatus(`Error reading columns: ${err.message}`, 'danger');
            }
        }
    });

    function populateEmailColSelect() {
        emailColSelect.innerHTML = `<option value="">-- Select Email Column --</option>`;
        availableColumns.forEach(col => {
            const isEmailCol = col.toLowerCase().includes('email') || col.toLowerCase().includes('mail');
            const isSel = isEmailCol ? 'selected' : '';
            emailColSelect.innerHTML += `<option value="${col}" ${isSel}>${col}</option>`;
        });
    }

    function createBulkMapRow(pdfField = '', selectedCol = '') {
        const row = document.createElement('div');
        row.className = 'field-row align-center';

        // Target PDF Field Selector
        let pdfFieldOptions = ``;
        if (detectedPdfFields.length === 0) {
            pdfFieldOptions = `<option value="">-- Upload Template PDF First --</option>`;
        } else {
            pdfFieldOptions = `<option value="">-- Select Target PDF Field --</option>`;
            detectedPdfFields.forEach(f => {
                const isSel = (f === pdfField) ? 'selected' : '';
                pdfFieldOptions += `<option value="${f}" ${isSel}>${f}</option>`;
            });
        }

        // Excel Column Selector
        let colOptions = ``;
        if (availableColumns.length === 0) {
            colOptions = `<option value="">-- Upload Excel/CSV File First --</option>`;
        } else {
            colOptions = `<option value="">-- Select Excel Column --</option>`;
            availableColumns.forEach(col => {
                const isSelected = (col === selectedCol || col.toLowerCase() === pdfField.toLowerCase() || pdfField.toLowerCase().includes(col.toLowerCase())) ? 'selected' : '';
                colOptions += `<option value="${col}" ${isSelected}>${col}</option>`;
            });
        }

        row.innerHTML = `
            <select class="input-field target-pdf-field">
                ${pdfFieldOptions}
            </select>
            <span class="mapping-arrow">➔</span>
            <select class="input-field excel-col-select">
                ${colOptions}
            </select>
            <button class="btn-icon remove-row-btn">&times;</button>
        `;

        row.querySelector('.remove-row-btn').addEventListener('click', () => row.remove());
        bulkMappingContainer.appendChild(row);
    }

    function renderBulkMappingRows() {
        bulkMappingContainer.innerHTML = '';
        if (detectedPdfFields.length === 0) {
            createBulkMapRow('', '');
            return;
        }

        const fieldsToMap = detectedPdfFields.slice(0, 5);
        fieldsToMap.forEach(f => {
            const matchedCol = availableColumns.find(c => c.toLowerCase() === f.toLowerCase() || f.toLowerCase().includes(c.toLowerCase()) || c.toLowerCase().includes(f.toLowerCase())) || '';
            createBulkMapRow(f, matchedCol);
        });
    }

    // Initial render before PDF/Data upload
    renderBulkMappingRows();

    addBulkMapBtn.addEventListener('click', () => createBulkMapRow());

    executeBulkBtn.addEventListener('click', async () => {
        if (!bulkPdfFile) {
            alert('Please upload a base PDF template file.');
            return;
        }
        if (!bulkDataFile) {
            alert('Please upload an Excel (.xlsx) or CSV (.csv) data file.');
            return;
        }

        const mappings = {};
        const rows = bulkMappingContainer.querySelectorAll('.field-row');
        rows.forEach(r => {
            const pdfF = r.querySelector('.target-pdf-field').value.trim();
            const colSel = r.querySelector('.excel-col-select').value.trim();
            if (pdfF && colSel) {
                mappings[pdfF] = colSel;
            }
        });

        const formData = new FormData();
        formData.append('pdf_file', bulkPdfFile);
        formData.append('data_file', bulkDataFile);
        if (Object.keys(mappings).length > 0) {
            formData.append('mappings_json', JSON.stringify(mappings));
        }

        // Email Dispatch options
        if (sendEmailToggle.checked) {
            formData.append('send_email', 'true');
            const emailColVal = emailColSelect.value.trim();
            if (!emailColVal) {
                alert('Please select the Recipient Email Column from your Excel/CSV sheet.');
                return;
            }
            formData.append('email_column', emailColVal);
            formData.append('email_subject', emailSubjectInput.value.trim());
            formData.append('email_body', emailBodyInput.value.trim());

            const senderEmail = document.getElementById('smtpSenderEmail').value.trim();
            const senderPass = document.getElementById('smtpSenderPassword').value.trim();
            const host = document.getElementById('smtpHost').value.trim();
            const port = document.getElementById('smtpPort').value.trim();

            // Always send smtp_json so backend can merge with env vars
            formData.append('smtp_json', JSON.stringify({
                sender_email: senderEmail,
                sender_password: senderPass,
                host: host || 'smtp.hostinger.com',
                port: parseInt(port) || 587
            }));
        }

        showStatus('Submitting bulk job...', 'info');

        try {
            const resp = await fetch('/pdf/edit-bulk', { method: 'POST', body: formData });
            const data = await resp.json();

            if (!resp.ok || !data.success) {
                bulkResultsBox.style.display = 'none';
                showStatus(`Bulk generation failed: ${data.detail || data.reason || 'Processing error'}`, 'danger');
                executeBulkBtn.disabled = false;
                return;
            }

            // Job accepted — start polling for status
            const jobId = data.job_id;
            const pollUrl = data.poll_url;
            showStatus('⏳ Processing PDFs in background... please wait.', 'info');

            const pollInterval = setInterval(async () => {
                try {
                    const statusResp = await fetch(pollUrl);
                    const statusData = await statusResp.json();

                    if (statusData.status === 'done') {
                        clearInterval(pollInterval);
                        executeBulkBtn.disabled = false;
                        emptyState.style.display = 'none';
                        validationResults.style.display = 'none';
                        bulkResultsBox.style.display = 'block';
                        downloadZipBtn.href = statusData.download_url;

                        let summary = `Successfully generated <strong>${statusData.generated_count}</strong> of ${statusData.total_rows} customized PDFs!`;
                        if (sendEmailToggle.checked) {
                            if (statusData.sent_emails_count > 0) {
                                summary += `<br>✅ Dispatched <strong>${statusData.sent_emails_count}</strong> emails successfully!`;
                            }
                            if (statusData.failed_emails_count > 0) {
                                summary += `<br>❌ <strong>${statusData.failed_emails_count}</strong> email(s) failed:`;
                                (statusData.email_errors || []).forEach(e => {
                                    summary += `<br>&nbsp;&nbsp;• Row ${e.row} (${e.recipient}): ${e.error}`;
                                });
                            }
                            if (!statusData.sent_emails_count && !statusData.failed_emails_count) {
                                summary += `<br>⚠️ No emails were sent. Check that the email column name matches your Excel/CSV header exactly.`;
                            }
                        }
                        bulkSummaryText.innerHTML = summary;
                        showStatus('✅ Bulk PDFs generated and ready for download!', 'success');

                    } else if (statusData.status === 'failed') {
                        clearInterval(pollInterval);
                        executeBulkBtn.disabled = false;
                        bulkResultsBox.style.display = 'none';
                        showStatus(`Bulk generation failed: ${statusData.error || 'Unknown error'}`, 'danger');
                    }
                    // else still 'processing' - keep polling
                } catch (pollErr) {
                    clearInterval(pollInterval);
                    executeBulkBtn.disabled = false;
                    showStatus(`Error checking job status: ${pollErr.message}`, 'danger');
                }
            }, 2000); // poll every 2 seconds

        } catch (err) {
            executeBulkBtn.disabled = false;
            showStatus(`Error during bulk generation: ${err.message}`, 'danger');
        }
    });


    // Test SMTP Button Handler
    const testSmtpBtn = document.getElementById('testSmtpBtn');
    const testSmtpResult = document.getElementById('testSmtpResult');

    if (testSmtpBtn) {
        testSmtpBtn.addEventListener('click', async () => {
            const senderEmail = document.getElementById('smtpSenderEmail').value.trim();
            const senderPass = document.getElementById('smtpSenderPassword').value.trim();
            const host = document.getElementById('smtpHost').value.trim();
            const port = document.getElementById('smtpPort').value.trim();

            testSmtpResult.style.color = '#e2e8f0';
            testSmtpResult.textContent = '⏳ Testing connection...';

            const formData = new FormData();
            formData.append('sender_email', senderEmail);
            formData.append('sender_password', senderPass);
            formData.append('smtp_host', host || 'smtp.hostinger.com');
            formData.append('smtp_port', port || '465');

            try {
                const resp = await fetch('/pdf/test-smtp', { method: 'POST', body: formData });
                const data = await resp.json();
                if (resp.ok && data.success) {
                    testSmtpResult.style.color = '#4ade80';
                    testSmtpResult.textContent = `✅ ${data.message}`;
                } else {
                    testSmtpResult.style.color = '#f87171';
                    testSmtpResult.textContent = `❌ ${data.error || 'Connection failed'}`;
                }
            } catch (err) {
                testSmtpResult.style.color = '#f87171';
                testSmtpResult.textContent = `❌ Test error: ${err.message}`;
            }
        });
    }

    function showStatus(msg, type) {
        statusAlert.style.display = 'block';
        statusAlert.className = `status-alert ${type}`;
        statusText.textContent = msg;
    }
});

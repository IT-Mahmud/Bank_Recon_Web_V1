// static/parser_tabs.js - Modularized JS for parser_tabs.html

function showTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(function(pane) {
        pane.style.display = 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.removeAttribute('data-active');
    });
    document.getElementById('pane-' + tabId).style.display = 'block';
    document.getElementById('btn-' + tabId).setAttribute('data-active','1');
}

document.querySelectorAll('.parser-form').forEach(function(form) {
    if(form.id === "reconcile-form" || form.id === "bft-reconcile-form" || form.id === "bank-tally-reconcile-form") return;

    const fileInput = form.querySelector('.file-input');
    const sheetRow = form.querySelector('[id$="-sheetRow"]');
    const sheetSelect = form.querySelector('.sheet-select');
    const parseBtn = form.querySelector('.parser-parse-btn');
    const msgDiv = form.nextElementSibling;
    const uploadedDiv = msgDiv.nextElementSibling;
    let sheetNames = [];
    const parserId = form.id.replace('form-','');

    let bankSelect = null;
    if (parserId === "bank") {
        bankSelect = form.querySelector('#bank-bankSelect');
    }

    function updateParseButtonState() {
        if (parserId === "bank") {
            parseBtn.disabled = !(fileInput.files.length && bankSelect && bankSelect.value);
        } else {
            if (sheetSelect && sheetSelect.style.display !== 'none') {
                parseBtn.disabled = !(fileInput.files.length && sheetSelect.value);
            } else {
                parseBtn.disabled = !fileInput.files.length;
            }
        }
    }

    if (parserId === "bank" && bankSelect) {
        bankSelect.addEventListener('change', updateParseButtonState);
    }

    fileInput.addEventListener('change', function(e) {
        sheetSelect.innerHTML = "";
        msgDiv.textContent = "";
        uploadedDiv.textContent = "";
        parseBtn.disabled = true;
        sheetRow.style.display = "none";
        if (!fileInput.files.length) {
            updateParseButtonState();
            return;
        }

        const file = fileInput.files[0];
        if (parserId === "bank" && file.name.endsWith('.csv')) {
            sheetRow.style.display = "none";
            updateParseButtonState();
            return;
        }

        var reader = new FileReader();
        reader.onload = function(e) {
            var data = new Uint8Array(e.target.result);
            var workbook = XLSX.read(data, {type: 'array'});
            sheetNames = workbook.SheetNames;

            if (sheetNames.length === 1 && parserId === "bank") {
                sheetRow.style.display = "none";
                sheetSelect.innerHTML = "";
                var opt = document.createElement('option');
                opt.value = sheetNames[0];
                opt.text = sheetNames[0];
                sheetSelect.appendChild(opt);
                sheetSelect.value = sheetNames[0];
                updateParseButtonState();
            } else if (sheetNames.length) {
                sheetSelect.innerHTML = "";
                sheetNames.forEach(function(name) {
                    var opt = document.createElement('option');
                    opt.value = name;
                    opt.text = name;
                    sheetSelect.appendChild(opt);
                });
                sheetRow.style.display = "flex";
                updateParseButtonState();
            }
        };
        reader.readAsArrayBuffer(file);
    });

    sheetSelect && sheetSelect.addEventListener('change', function() {
        updateParseButtonState();
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        parseBtn.disabled = true;
        msgDiv.textContent = "";
        uploadedDiv.textContent = "";

        var fileField = fileInput.name;
        var sheetName = sheetSelect && sheetSelect.style.display !== "none" ? sheetSelect.value : "";
        var file = fileInput.files[0];

        var bankName = "";
        if (parserId === "bank" && bankSelect) {
            bankName = bankSelect.value;
            if (!bankName) {
                msgDiv.innerText = "Please select a bank.";
                parseBtn.disabled = false;
                return;
            }
        }

        if (!file || (sheetSelect && sheetSelect.style.display !== "none" && !sheetName)) {
            msgDiv.innerText = "Please select file and sheet.";
            parseBtn.disabled = false;
            return;
        }
        var formData = new FormData();
        formData.append(fileField, file);
        if (sheetName) formData.append('sheet_name', sheetName);
        if (parserId === "bank" && bankName) formData.append('bank_name', bankName);

        var parserRoute = {
            finance: '/parse_finance',
            bank: '/parse_bank',
            tally: '/parse_tally'
        }[parserId];

        fetch(parserRoute, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(resp => {
            msgDiv.textContent = resp.msg || "";
            if (resp.success && resp.uploaded_filename) {
                uploadedDiv.innerHTML = "<b>Uploaded Filename:</b> " + resp.uploaded_filename;
            } else {
                uploadedDiv.innerHTML = "";
            }
            parseBtn.disabled = false;
        })
        .catch(err => {
            msgDiv.textContent = "Error uploading or parsing file.";
            parseBtn.disabled = false;
        });
    });

    updateParseButtonState();
});

// --- Account dropdown logic for Bank-Fin Match ---
// const bankTableSelect = document.getElementById('bank-table-select');
// const accountNumberSelect = document.getElementById('account-number-select');

// function fetchAndSetAccounts() {
//     const bank_table = bankTableSelect.value;
//     accountNumberSelect.innerHTML = '<option value="">Loading...</option>';
//     fetch('/get_accounts', {
//         method: 'POST',
//         headers: {'Content-Type': 'application/x-www-form-urlencoded'},
//         body: `bank_table=${encodeURIComponent(bank_table)}`
//     })
//     .then(resp => resp.json())
//     .then(data => {
//         accountNumberSelect.innerHTML = '';
//         if(data.success && data.accounts.length > 0){
//             accountNumberSelect.innerHTML = '<option value="">-- Select Account --</option>';
//             data.accounts.forEach(function(acct){
//                 const opt = document.createElement('option');
//                 opt.value = acct;
//                 opt.text = acct;
//                 accountNumberSelect.appendChild(opt);
//             });
//         } else {
//             accountNumberSelect.innerHTML = '<option value="">No accounts found</option>';
//         }
//     })
//     .catch(() => {
//         accountNumberSelect.innerHTML = '<option value="">Error</option>';
//     });
// }

// if (bankTableSelect) {
//     fetchAndSetAccounts();
//     bankTableSelect.addEventListener('change', fetchAndSetAccounts);
// }



const bankCodeSelect = document.getElementById('bank-code-select');
const accountNumberSelect = document.getElementById('account-number-select');

function fetchAndSetAccounts() {
    const bank_code = bankCodeSelect.value;
    accountNumberSelect.innerHTML = '<option value="">Loading...</option>';
    fetch('/get_accounts', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `bank_code=${encodeURIComponent(bank_code)}`
    })
    .then(resp => resp.json())
    .then(data => {
        accountNumberSelect.innerHTML = '';
        if(data.success && data.accounts.length > 0){
            accountNumberSelect.innerHTML = '<option value="">-- Select Account --</option>';
            data.accounts.forEach(function(acct){
                const opt = document.createElement('option');
                opt.value = acct;
                opt.text = acct;
                accountNumberSelect.appendChild(opt);
            });
        } else {
            accountNumberSelect.innerHTML = '<option value="">No accounts found</option>';
        }
    })
    .catch(() => {
        accountNumberSelect.innerHTML = '<option value="">Error</option>';
    });
}

if (bankCodeSelect) {
    fetchAndSetAccounts();
    bankCodeSelect.addEventListener('change', fetchAndSetAccounts);
}




// --- FINAL MINIMAL RECONCILE SCRIPT (UPDATED) ---
// document.getElementById('reconcile-form').addEventListener('submit', function(e) {
//     e.preventDefault();
//     const btn = document.getElementById('reconcile-btn');
//     btn.disabled = true;
//     btn.textContent = 'Reconciling...';
//     const resultDiv = document.getElementById('reconcile-result');
//     resultDiv.textContent = 'Working...';

//     // const bank_table = bankTableSelect.value;
//     // const account_number = accountNumberSelect.value;
//     // const bank_code = bankTableSelect.selectedOptions[0].getAttribute('data-code');
//     // const fin_table = 'fin_data';

//     // const formData = new URLSearchParams();
//     // formData.append('bank_table', bank_table);
//     // formData.append('fin_table', fin_table);
//     // formData.append('bank_code', bank_code);
//     // formData.append('account_number', account_number);

//     const bank_code = document.getElementById('bank-code-select').value;
//     const account_number = document.getElementById('account-number-select').value;

//     const formData = new URLSearchParams();
//     formData.append('bank_code', bank_code);
//     formData.append('account_number', account_number);


//     fetch('/reconcile', {
//         method: 'POST',
//         headers: {'Content-Type': 'application/x-www-form-urlencoded'},
//         body: formData
//     })
//     .then(resp => resp.json())
//     .then(data => {
//         if(data.success) {
//             resultDiv.innerText =
//                 `Matched: ${data.matched_count}\n` +
//                 `Unmatched (Bank): ${data.unmatched_bank_count}\n` +
//                 `Unmatched (Finance): ${data.unmatched_finance_count}`;
//         } else {
//             resultDiv.innerText = data.msg || 'Unknown error';
//         }
//     })
//     .catch(err => {
//         resultDiv.innerText = `Error: ${err}`;
//     })
//     .finally(() => {
//         btn.disabled = false;
//         btn.textContent = 'Reconcile';
//     });
// });



document.getElementById('reconcile-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = document.getElementById('reconcile-btn');
    btn.disabled = true;
    btn.textContent = 'Reconciling...';
    const resultDiv = document.getElementById('reconcile-result');
    resultDiv.textContent = 'Working...';

    const bank_code = document.getElementById('bank-code-select').value;
    const account_number = document.getElementById('account-number-select').value;

    const formData = new URLSearchParams();
    formData.append('bank_code', bank_code);
    formData.append('account_number', account_number);

    fetch('/reconcile', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: formData.toString()
    })
    .then(resp => resp.json())
    .then(data => {
        if(data.success) {
            resultDiv.innerText =
                `Matched: ${data.matched_count}\n` +
                `Unmatched (Bank): ${data.unmatched_bank_count}\n` +
                `Unmatched (Finance): ${data.unmatched_finance_count}`;
        } else {
            resultDiv.innerText = data.msg || 'Unknown error';
        }
    })
    .catch(err => {
        resultDiv.innerText = 'Error: ' + err;
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Reconcile';
    });
});




// --- Account dropdown logic for Bank-Fin-Tally Match ---
const bftBankSelect = document.getElementById('bft-bank-code-select');
const bftAcctSelect = document.getElementById('bft-account-number-select');

function fetchBFTAccounts() {
    bftAcctSelect.innerHTML = '<option value="">Loading...</option>';
    fetch('/get_bft_accounts', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: `bank_code=${encodeURIComponent(bftBankSelect.value)}`
    })
    .then(r => r.json())
    .then(d => {
        bftAcctSelect.innerHTML = '';
        if(d.success && d.accounts.length) {
            bftAcctSelect.innerHTML = '<option value="">-- Select Account --</option>';
            d.accounts.forEach(a => {
                const opt = document.createElement('option');
                opt.value = a;
                opt.text = a;
                bftAcctSelect.appendChild(opt);
            });
        } else {
            bftAcctSelect.innerHTML = '<option value="">No accounts found</option>';
        }
    })
    .catch(() => {
        bftAcctSelect.innerHTML = '<option value="">Error</option>';
    });
}

if (bftBankSelect) {
    fetchBFTAccounts();
    bftBankSelect.addEventListener('change', fetchBFTAccounts);
}

document.getElementById('bft-reconcile-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = document.getElementById('bft-reconcile-btn');
    btn.disabled = true;
    btn.textContent = 'Reconciling...';
    const resultDiv = document.getElementById('bft-reconcile-result');
    resultDiv.textContent = 'Working...';

    const bank_code = bftBankSelect.value;
    const account_number = bftAcctSelect.value;

    const formData = new URLSearchParams();
    formData.append('bank_code', bank_code);
    formData.append('account_number', account_number);

    fetch('/reconcile_bft', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: formData
    })
    .then(resp => resp.json())
    .then(data => {
        if(data.success) {
            resultDiv.innerText =
                `Matched: ${data.matched_count}\n` +
                `Unmatched (BF): ${data.unmatched_bf_count}\n` +
                `Unmatched (Tally): ${data.unmatched_tally_count}`;
        } else {
            resultDiv.innerText = data.msg || 'Unknown error';
        }
    })
    .catch(err => {
        resultDiv.innerText = `Error: ${err}`;
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Reconcile';
    });
});

// --- Account dropdown logic for Bank-Tally Match ---
const btBankSelect = document.getElementById('bank-tally-bank-code-select');
const btAcctSelect = document.getElementById('bank-tally-account-number-select');

function fetchBTAccounts() {
    btAcctSelect.innerHTML = '<option value="">Loading...</option>';
    fetch('/get_accounts', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        // body: `bank_table=${btBankSelect.value === "MDB" ? "mdb_data" : "mtb_data"}`
        body: `bank_code=${encodeURIComponent(btBankSelect.value)}`

    })
    .then(r => r.json())
    .then(d => {
        btAcctSelect.innerHTML = '';
        if(d.success && d.accounts.length) {
            btAcctSelect.innerHTML = '<option value="">-- Select Account --</option>';
            d.accounts.forEach(a => {
                const opt = document.createElement('option');
                opt.value = a;
                opt.text = a;
                btAcctSelect.appendChild(opt);
            });
        } else {
            btAcctSelect.innerHTML = '<option value="">No accounts found</option>';
        }
    })
    .catch(() => {
        btAcctSelect.innerHTML = '<option value="">Error</option>';
    });
}

if (btBankSelect) {
    fetchBTAccounts();
    btBankSelect.addEventListener('change', fetchBTAccounts);
}

document.getElementById('bank-tally-reconcile-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = document.getElementById('bank-tally-reconcile-btn');
    btn.disabled = true;
    btn.textContent = 'Reconciling...';
    const resultDiv = document.getElementById('bank-tally-reconcile-result');
    resultDiv.textContent = 'Working...';

    const bank_code = btBankSelect.value;
    const account_number = btAcctSelect.value;

    const formData = new URLSearchParams();
    formData.append('bank_code', bank_code);
    formData.append('account_number', account_number);

    fetch('/bank_tally/reconcile', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: formData
    })
    .then(resp => resp.json())
    .then(data => {
        if(data.success) {
            resultDiv.innerText = `Matched: ${data.matched_count}`;
        } else {
            resultDiv.innerText = data.msg || 'Unknown error';
        }
    })
    .catch(err => {
        resultDiv.innerText = `Error: ${err}`;
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Reconcile';
    });
});

let currentModule    = null;
let moduleConfig     = null;
let rotationMapping  = null; // Stores inspected supervisor/collector mapping
let balancingPortfolios = []; // Stores inspected portfolio list

const PROGRAM_META = {
  neglect:   { title: 'الإهمال',              icon: '⏰', color: '#fb923c' },
  errors:    { title: 'أخطاء النظام',         icon: '🔴', color: '#ef4444' },
  targets:   { title: 'عملاء مستهدفة',        icon: '🎯', color: '#22c55e' },
  contact:   { title: 'توصل وعدم توصل',       icon: '📞', color: '#6366f1' },
  rotation:  { title: 'السحب والتدوير',       icon: '🔄', color: '#e67e22' },
  balancing: { title: 'سحب وتوزيع المحافظ',  icon: '⚖️', color: '#8b5cf6' },
};

document.addEventListener('DOMContentLoaded', () => {
  updateDate();
  setInterval(updateDate, 60000);
});

function updateDate() {
  const el = document.getElementById('headerDate');
  if (!el) return;
  const now  = new Date();
  const opts = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  el.textContent = now.toLocaleDateString('ar-SA', opts);
}

async function launchProgram(key) {
  currentModule = key;
  const meta = PROGRAM_META[key];

  try {
    const res = await fetch(`/api/config/${key}`);
    moduleConfig = await res.json();
  } catch(e) {
    showToast('⚠️ تعذّر الاتصال بالسيرفر. الرجاء التأكد من تشغيل ملف «تشغيل_واجهة_الموقع.bat»');
    return;
  }

  buildUploadForm(meta, moduleConfig);
  document.getElementById('modalOverlay').classList.add('active');
}

function buildUploadForm(meta, cfg) {
  document.getElementById('modalIcon').textContent  = meta.icon;
  document.getElementById('modalTitle').textContent = meta.title;

  const btn = document.getElementById('modalRunBtn');
  btn.style.background = `linear-gradient(135deg,${meta.color}cc,${meta.color})`;
  btn.style.boxShadow  = `0 4px 20px ${meta.color}44`;

  const zone = document.getElementById('modalFilesZone');
  zone.innerHTML = '';

  cfg.files.forEach(f => {
    const wrap = document.createElement('div');
    wrap.className = 'file-row';
    wrap.innerHTML = `
      <label class="file-label">
        ${f.required ? '<span class="req-star">*</span>' : ''} ${f.label}
      </label>
      <div class="file-drop" id="drop_${f.key}" onclick="document.getElementById('inp_${f.key}').click()">
        <svg viewBox="0 0 24 24" fill="none" width="22" height="22">
          <path d="M12 16V8m0 0l-3 3m3-3l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M20 16.7A5 5 0 0016 8h-.5A8 8 0 104 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span class="drop-text" id="dt_${f.key}">اضغط لاختيار ملف Excel</span>
      </div>
      <input type="file" id="inp_${f.key}" accept=".xlsx,.xls"
             onchange="onFileSelected('${f.key}')" style="display:none"/>
    `;
    zone.appendChild(wrap);
  });

  // Reset rotation container
  const rotContainer = document.getElementById('rotationOptionsContainer');
  if (rotContainer) {
    rotContainer.style.display = 'none';
    document.getElementById('rotationSupervisor').innerHTML = '';
    document.getElementById('rotationCollector').innerHTML = '';
    document.getElementById('rotationCollector').disabled = true;
    document.getElementById('rotationPreview').textContent = '';
  }
  rotationMapping = null;

  // Reset balancing container
  const balContainer = document.getElementById('balancingOptionsContainer');
  if (balContainer) {
    balContainer.style.display = 'none';
    document.getElementById('balSourceList').innerHTML = '';
    document.getElementById('balTargetList').innerHTML = '';
    document.getElementById('balancingPreview').textContent = '';
  }
  balancingPortfolios = [];
}

function onFileSelected(key) {
  const inp  = document.getElementById(`inp_${key}`);
  const drop = document.getElementById(`drop_${key}`);
  const txt  = document.getElementById(`dt_${key}`);
  if (inp.files[0]) {
    txt.textContent = '✅ ' + inp.files[0].name;
    drop.classList.add('has-file');

    if (currentModule === 'rotation' && key === 'portfolio') {
      inspectRotationFile(inp.files[0]);
    }
    if (currentModule === 'balancing' && key === 'portfolio') {
      inspectBalancingFile(inp.files[0]);
    }
  }
}

async function inspectRotationFile(file) {
  const preview = document.getElementById('rotationPreview');
  const container = document.getElementById('rotationOptionsContainer');
  const supSelect = document.getElementById('rotationSupervisor');
  const colSelect = document.getElementById('rotationCollector');

  preview.textContent = '⏳ جاري قراءة وتحديد المشرفين والمحصلين من الملف...';
  preview.style.color = '#38bdf8';
  container.style.display = 'block';
  supSelect.innerHTML = '<option value="">-- اختر المشرف --</option>';
  colSelect.innerHTML = '<option value="">-- اختر المحصل --</option>';
  supSelect.disabled = true;
  colSelect.disabled = true;

  const form = new FormData();
  form.append('portfolio', file);

  try {
    const res = await fetch('/api/rotation/inspect', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok || data.error) {
      preview.textContent = '❌ خطأ: ' + (data.error || 'فشل فحص الملف');
      preview.style.color = '#f87171';
      return;
    }

    rotationMapping = data.supervisors;
    
    // Populate supervisors
    supSelect.innerHTML = '<option value="">-- اختر المشرف --</option>';
    Object.keys(rotationMapping).sort().forEach(sup => {
      const opt = document.createElement('option');
      opt.value = sup;
      opt.textContent = sup;
      supSelect.appendChild(opt);
    });

    supSelect.disabled = false;
    preview.textContent = '💡 تم تحميل قائمة المشرفين بنجاح. الرجاء اختيار المشرف.';
    preview.style.color = '#8b949e';
  } catch(e) {
    preview.textContent = '❌ خطأ في الاتصال: ' + e.message;
    preview.style.color = '#f87171';
  }
}

function onRotationSupervisorChanged() {
  const sup = document.getElementById('rotationSupervisor').value;
  const colSelect = document.getElementById('rotationCollector');
  const preview = document.getElementById('rotationPreview');

  colSelect.innerHTML = '<option value="">-- اختر المحصل --</option>';
  colSelect.disabled = true;
  
  if (!sup || !rotationMapping || !rotationMapping[sup]) {
    preview.textContent = '💡 الرجاء اختيار المشرف.';
    preview.style.color = '#8b949e';
    return;
  }

  const cols = rotationMapping[sup].sort();
  cols.forEach(col => {
    const opt = document.createElement('option');
    opt.value = col;
    opt.textContent = col;
    colSelect.appendChild(opt);
  });

  colSelect.disabled = false;
  preview.textContent = '💡 الرجاء اختيار المحصل المسحوب لتوزيعه.';
  preview.style.color = '#8b949e';
}

function onRotationCollectorChanged() {
  const sup = document.getElementById('rotationSupervisor').value;
  const col = document.getElementById('rotationCollector').value;
  const preview = document.getElementById('rotationPreview');

  if (!sup || !col) {
    preview.textContent = '💡 الرجاء اختيار المحصل المسحوب لتوزيعه.';
    preview.style.color = '#8b949e';
    return;
  }

  // Count target collectors pool
  const allCols = rotationMapping[sup];
  const poolSize = allCols.filter(c => c !== col).length;

  if (poolSize === 0) {
    preview.textContent = `⚠️ لا يوجد محصلين آخرين تحت المشرف '${sup}' للتوزيع عليهم!`;
    preview.style.color = '#f87171';
  } else {
    preview.textContent = `✅ سيتم سحب محفظة المحصل وتوزيعها بالتساوي على ${poolSize} محصلين تحت المشرف '${sup}'.`;
    preview.style.color = '#4ade80';
  }
}

// ── Balancing helpers ──────────────────────────────────────────────────────
async function inspectBalancingFile(file) {
  const container = document.getElementById('balancingOptionsContainer');
  const srcList   = document.getElementById('balSourceList');
  const tgtList   = document.getElementById('balTargetList');
  const preview   = document.getElementById('balancingPreview');

  container.style.display = 'block';
  srcList.innerHTML = '';
  tgtList.innerHTML = '';
  preview.textContent = '⏳ جاري قراءة المحافظ من الملف...';
  preview.style.color = '#38bdf8';

  const form = new FormData();
  form.append('portfolio', file);

  try {
    const res  = await fetch('/api/balancing/inspect', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok || data.error) {
      preview.textContent = '❌ خطأ: ' + (data.error || 'فشل فحص الملف');
      preview.style.color = '#f87171';
      return;
    }

    balancingPortfolios = data.portfolios || [];
    const counts        = data.collector_counts || {};

    balancingPortfolios.forEach(p => {
      const cnt  = counts[p] || 0;
      const txt  = `${p}  (${cnt} محصل)`;
      [srcList, tgtList].forEach(sel => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = txt;
        sel.appendChild(opt);
      });
    });

    preview.textContent = '💡 اختر المحافظ المصدر (يسار) والمحافظ الهدف (يمين). يمكنك اختيار أكثر من واحدة بـ Ctrl.';
    preview.style.color = '#8b949e';
  } catch(e) {
    preview.textContent = '❌ خطأ في الاتصال: ' + e.message;
    preview.style.color = '#f87171';
  }
}

function onBalancingChanged() {
  const srcSel  = document.getElementById('balSourceList');
  const tgtSel  = document.getElementById('balTargetList');
  const preview = document.getElementById('balancingPreview');

  const srcVals = Array.from(srcSel.selectedOptions).map(o => o.value);
  const tgtVals = Array.from(tgtSel.selectedOptions).map(o => o.value);

  if (!srcVals.length) {
    preview.textContent = '💡 اختر محافظ المصدر (السحب منها) لمعاينة العملية.';
    preview.style.color = '#8b949e';
    return;
  }

  const overlap = srcVals.filter(v => tgtVals.includes(v));
  if (overlap.length) {
    preview.innerHTML = `⚠️ المحافظ التالية مختارة كمصدر وهدف في نفس الوقت — يرجى تصحيح الاختيار:<br><strong style="color:#f87171">${overlap.join(' | ')}</strong>`;
    preview.style.color = '#f87171';
    return;
  }

  let targetText = "";
  if (!tgtVals.length) {
    targetText = `محصلي <strong style="color:#4ade80">بقية المحافظ تلقائياً (توزيع متوازن)</strong>`;
  } else {
    targetText = `محصلي: <strong style="color:#4ade80">${tgtVals.join(' | ')}</strong>`;
  }

  preview.innerHTML =
    `✅ سيتم سحب فائض العملاء من: <strong style="color:#c084fc">${srcVals.join(' | ')}</strong><br>` +
    `وتوزيعهم بتوازن ذكي على ${targetText}`;
  preview.style.color = '#8b949e';
}

async function runProgram() {
  if (!currentModule || !moduleConfig) return;

  for (const f of moduleConfig.files) {
    if (f.required) {
      const inp = document.getElementById(`inp_${f.key}`);
      if (!inp || !inp.files[0]) {
        showToast(`⚠️ الرجاء اختيار ملف: ${f.label}`);
        return;
      }
    }
  }

  // Handle Rotation specific inputs
  let supervisor = '';
  let collector  = '';
  if (currentModule === 'rotation') {
    supervisor = document.getElementById('rotationSupervisor').value;
    collector  = document.getElementById('rotationCollector').value;
    if (!supervisor || !collector) {
      showToast('⚠️ الرجاء تحديد المشرف والمحصل المسحوب أولاً');
      return;
    }
  }

  // Handle Balancing specific inputs
  let srcPorts = [];
  let tgtPorts = [];
  if (currentModule === 'balancing') {
    const srcSel = document.getElementById('balSourceList');
    const tgtSel = document.getElementById('balTargetList');
    srcPorts = Array.from(srcSel.selectedOptions).map(o => o.value);
    tgtPorts = Array.from(tgtSel.selectedOptions).map(o => o.value);
    const overlap = srcPorts.filter(v => tgtPorts.includes(v));
    if (!srcPorts.length) {
      showToast('⚠️ الرجاء اختيار المحافظ المصدر');
      return;
    }
    if (overlap.length) {
      showToast('⚠️ لا يمكن أن تكون المحفظة مصدراً وهدفاً في نفس الوقت');
      return;
    }
  }

  closeModal();
  showProgress();

  const form = new FormData();
  for (const f of moduleConfig.files) {
    const inp = document.getElementById(`inp_${f.key}`);
    if (inp && inp.files[0]) form.append(f.key, inp.files[0]);
  }

  if (currentModule === 'rotation') {
    form.append('supervisor', supervisor);
    form.append('collector', collector);
  }

  if (currentModule === 'balancing') {
    form.append('source_portfolios', srcPorts.join('|'));
    form.append('target_portfolios', tgtPorts.join('|'));
  }

  try {
    const res  = await fetch(`/api/run/${currentModule}`, { method: 'POST', body: form });
    const data = await res.json();

    hideProgress();

    if (!res.ok || data.error) {
      showError(data.error || 'حدث خطأ غير متوقع');
      return;
    }

    showResult(data);

  } catch(e) {
    hideProgress();
    showError('تعذّر الاتصال بالسيرفر: ' + e.message);
  }
}

function showProgress() {
  const meta = PROGRAM_META[currentModule];
  document.getElementById('progressOverlay').classList.add('active');
  document.getElementById('progressTitle').textContent = `جاري تشغيل ${meta.title}...`;
  document.getElementById('progressBar').style.width = '0%';
  let pct = 0;
  window._progTimer = setInterval(() => {
    pct = Math.min(pct + Math.random() * 8, 88);
    document.getElementById('progressBar').style.width = pct + '%';
  }, 300);
}

function hideProgress() {
  clearInterval(window._progTimer);
  document.getElementById('progressBar').style.width = '100%';
  setTimeout(() => {
    document.getElementById('progressOverlay').classList.remove('active');
  }, 500);
}

function showResult(data) {
  const meta = PROGRAM_META[currentModule];

  let statsHtml = '';
  for (const [k, v] of Object.entries(data.stats || {})) {
    statsHtml += `<div class="stat-row"><span class="stat-key">${k}</span><span class="stat-val">${v}</span></div>`;
  }

  document.getElementById('resultIcon').textContent  = meta.icon;
  document.getElementById('resultStats').innerHTML   = statsHtml || '<p style="color:var(--muted)">لا توجد إحصائيات</p>';
  document.getElementById('resultFilename').textContent = data.file;
  document.getElementById('resultDownloadBtn').onclick = () => {
    window.location.href = `/api/download/${encodeURIComponent(data.file)}`;
  };
  document.getElementById('resultOverlay').classList.add('active');
}

function showError(msg) {
  document.getElementById('errorMsg').textContent = msg;
  document.getElementById('errorOverlay').classList.add('active');
}

function closeModal()        { document.getElementById('modalOverlay').classList.remove('active'); }
function closeResultOverlay(){ document.getElementById('resultOverlay').classList.remove('active'); }
function closeErrorOverlay() { document.getElementById('errorOverlay').classList.remove('active'); }

document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeModal(); closeResultOverlay(); closeErrorOverlay(); } });

function showToast(msg) {
  const old = document.querySelector('.toast');
  if (old) old.remove();
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('show')));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 3500);
}

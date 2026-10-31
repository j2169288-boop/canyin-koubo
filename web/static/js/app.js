(function () {
  const $ = (id) => document.getElementById(id);
  const toastEl = $('toast');
  let styles = [];
  let versions = [];
  let lastEstimate = null;
  let selectedStyles = [];

  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 1800);
  }

  async function api(path, opts = {}) {
    const r = await fetch(path, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    if (r.status === 401) {
      location.href = '/login';
      throw new Error('unauthorized');
    }
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.ok === false) {
      throw new Error(data.error || ('HTTP ' + r.status));
    }
    return data;
  }

  function switchTab(tab) {
    document.querySelectorAll('.page').forEach((p) => p.classList.toggle('active', p.dataset.tab === tab));
    document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  }

  document.querySelectorAll('.tabs button').forEach((b) => {
    b.addEventListener('click', () => switchTab(b.dataset.tab));
  });

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast('已复制');
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      toast('已复制');
    }
  }

  function collectStore() {
    const dishes = $('dishes').value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    const sell_points = $('sell_points').value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    return {
      name: $('name').value.trim(),
      city: $('city').value.trim(),
      category: $('category').value.trim(),
      dishes,
      avg_price: $('avg_price').value.trim(),
      sell_points,
      goal: $('goal').value,
      group_price: $('group_price').value.trim(),
      reference_script: $('reference_script').value.trim(),
      preferred_styles: selectedStyles.slice(),
      avatar: {
        appearance_zh: $('av_appearance_zh').value.trim(),
        outfit_zh: $('av_outfit_zh').value.trim(),
        scene_zh: $('av_scene_zh').value.trim(),
        camera_zh: $('av_camera_zh').value.trim(),
        appearance_en: $('av_appearance_en').value.trim(),
        outfit_en: $('av_outfit_en').value.trim(),
        scene_en: $('av_scene_en').value.trim(),
        camera_en: $('av_camera_en').value.trim(),
      },
    };
  }

  function fillStore(s) {
    $('name').value = s.name || '';
    $('city').value = s.city || '';
    $('category').value = s.category || '';
    $('dishes').value = (s.dishes || []).join('\n');
    $('avg_price').value = s.avg_price || '';
    $('sell_points').value = (s.sell_points || []).join('\n');
    $('goal').value = s.goal || '拉新到店';
    $('group_price').value = s.group_price || '';
    $('reference_script').value = s.reference_script || '';
    selectedStyles = (s.preferred_styles || []).slice();
    renderStyleChips();
    const av = s.avatar || {};
    $('av_appearance_zh').value = av.appearance_zh || '';
    $('av_outfit_zh').value = av.outfit_zh || '';
    $('av_scene_zh').value = av.scene_zh || '';
    $('av_camera_zh').value = av.camera_zh || '';
    $('av_appearance_en').value = av.appearance_en || '';
    $('av_outfit_en').value = av.outfit_en || '';
    $('av_scene_en').value = av.scene_en || '';
    $('av_camera_en').value = av.camera_en || '';
  }

  function renderStyleChips() {
    const box = $('styleChips');
    box.innerHTML = '';
    styles.forEach((st) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip' + (selectedStyles.includes(st.id) ? ' on' : '');
      b.textContent = st.name;
      b.title = st.desc || '';
      b.addEventListener('click', () => {
        if (selectedStyles.includes(st.id)) {
          selectedStyles = selectedStyles.filter((x) => x !== st.id);
        } else {
          selectedStyles.push(st.id);
        }
        renderStyleChips();
      });
      box.appendChild(b);
    });
  }

  async function refreshStoreList() {
    const data = await api('/api/stores');
    const sel = $('storeSelect');
    const cur = sel.value;
    sel.innerHTML = '<option value="">（新建）</option>';
    (data.stores || []).forEach((n) => {
      const o = document.createElement('option');
      o.value = n;
      o.textContent = n;
      sel.appendChild(o);
    });
    if (cur) sel.value = cur;
  }

  function renderResults() {
    const scriptsBox = $('scriptsBox');
    const segsBox = $('segsBox');
    const promptsBox = $('promptsBox');
    if (!versions.length) {
      scriptsBox.innerHTML = '<div class="banner info">请先在「店铺」页生成方案</div>';
      return;
    }
    scriptsBox.innerHTML = '';
    segsBox.innerHTML = '';
    promptsBox.innerHTML = '';

    versions.forEach((v, i) => {
      const card = document.createElement('div');
      card.className = 'version-card';
      card.innerHTML =
        '<h3>版本 ' + (i + 1) + ' · ' + (v.style_name || '') + ' <span class="hint">(' + (v.source || '') + ')</span></h3>' +
        '<div><strong>钩子</strong><div>' + esc(v.hook) + '</div></div>' +
        '<div style="margin-top:8px"><strong>正文</strong><div>' + esc(v.body) + '</div></div>' +
        '<div style="margin-top:8px"><strong>CTA</strong><div>' + esc(v.cta) + '</div></div>';
      const row = document.createElement('div');
      row.className = 'btn-row';
      const b1 = document.createElement('button');
      b1.className = 'btn btn-sm btn-secondary';
      b1.type = 'button';
      b1.textContent = '复制完整文案';
      b1.addEventListener('click', () => copyText(v.full_script || ''));
      row.appendChild(b1);
      card.appendChild(row);
      scriptsBox.appendChild(card);

      const segCard = document.createElement('div');
      segCard.className = 'card';
      segCard.innerHTML = '<h2>版本 ' + (i + 1) + ' · ' + esc(v.style_name) + '</h2>';
      (v.segments || []).forEach((seg) => {
        const item = document.createElement('div');
        item.className = 'seg-item';
        item.innerHTML =
          '<div class="seg-meta">片段 ' + seg.index + ' · ' + seg.chars + '字 · 约 ' + seg.seconds + ' 秒</div>' +
          '<div>' + esc(seg.text) + '</div>';
        const br = document.createElement('div');
        br.className = 'btn-row';
        const cb = document.createElement('button');
        cb.className = 'btn btn-sm btn-secondary';
        cb.type = 'button';
        cb.textContent = '复制本段';
        cb.addEventListener('click', () => copyText(seg.text));
        br.appendChild(cb);
        item.appendChild(br);
        segCard.appendChild(item);
      });
      segsBox.appendChild(segCard);

      const pCard = document.createElement('div');
      pCard.className = 'card';
      pCard.innerHTML = '<h2>版本 ' + (i + 1) + ' · 视频提示词</h2>';
      (v.segments || []).forEach((seg) => {
        const vp = seg.video_prompt || {};
        const item = document.createElement('div');
        item.className = 'seg-item';
        item.innerHTML =
          '<div class="seg-meta">片段 ' + seg.index + ' · 9:16 i2v + lip-sync</div>' +
          '<div style="white-space:pre-wrap;font-size:.85rem">' + esc(vp.explain_zh || '') + '</div>' +
          '<div class="prompt-box">' + esc(vp.prompt_en || '') + '</div>';
        const br = document.createElement('div');
        br.className = 'btn-row';
        const cb = document.createElement('button');
        cb.className = 'btn btn-sm btn-primary';
        cb.type = 'button';
        cb.textContent = '复制英文 Prompt';
        cb.addEventListener('click', () => copyText(vp.prompt_en || ''));
        br.appendChild(cb);
        item.appendChild(br);
        pCard.appendChild(item);
      });
      promptsBox.appendChild(pCard);
    });
  }

  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function runEstimate() {
    const store = collectStore();
    const budget = Number($('budget').value);
    $('budgetLabel').textContent = String(budget);
    const assumptions = {
      cpm_low: Number($('cpm_low').value),
      cpm_mid: Number($('cpm_mid').value),
      cpm_high: Number($('cpm_high').value),
      ctr_low: Number($('ctr_low').value),
      ctr_mid: Number($('ctr_mid').value),
      ctr_high: Number($('ctr_high').value),
      to_store_low: Number($('ts_low').value),
      to_store_mid: Number($('ts_mid').value),
      to_store_high: Number($('ts_high').value),
    };
    const data = await api('/api/ad-estimate', {
      method: 'POST',
      body: JSON.stringify({ budget, assumptions, goal: store.goal }),
    });
    lastEstimate = data.estimate;
    const e = data.estimate;
    const box = $('adResult');
    box.innerHTML =
      '<div class="metrics">' +
      '<div class="metric"><div class="k">曝光（低/中/高）</div><div class="v">' +
      e.impressions.low + ' / ' + e.impressions.mid + ' / ' + e.impressions.high +
      '</div></div>' +
      '<div class="metric"><div class="k">点击（低/中/高）</div><div class="v">' +
      e.clicks.low + ' / ' + e.clicks.mid + ' / ' + e.clicks.high +
      '</div></div>' +
      '<div class="metric"><div class="k">到店/核销（低/中/高）</div><div class="v">' +
      e.to_store_or_redeem.low + ' / ' + e.to_store_or_redeem.mid + ' / ' + e.to_store_or_redeem.high +
      '</div></div></div>' +
      '<div class="banner danger" style="margin-top:10px">' + esc(e.disclaimer) + '</div>' +
      '<h3 style="margin-top:12px">定向建议</h3><ul id="tgt"></ul>' +
      '<h3>投放时段</h3><ul id="slots"></ul>';
    const tgt = box.querySelector('#tgt');
    Object.keys(e.targeting || {}).forEach((k) => {
      const li = document.createElement('li');
      li.textContent = k + '：' + e.targeting[k];
      tgt.appendChild(li);
    });
    const slots = box.querySelector('#slots');
    (e.time_slots || []).forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      slots.appendChild(li);
    });
  }

  // events
  $('nVersions').addEventListener('input', () => {
    $('nLabel').textContent = $('nVersions').value;
  });
  $('budget').addEventListener('input', () => {
    $('budgetLabel').textContent = $('budget').value;
  });

  $('btnLoadStore').addEventListener('click', async () => {
    const name = $('storeSelect').value;
    if (!name) return toast('请先选择店铺');
    try {
      const data = await api('/api/stores/' + encodeURIComponent(name));
      fillStore(data.store);
      toast('已加载');
    } catch (e) {
      toast(e.message);
    }
  });

  $('btnExample').addEventListener('click', async () => {
    try {
      const data = await api('/api/example');
      fillStore(data.store);
      toast('已填入示例（非真实门店）');
    } catch (e) {
      toast(e.message);
    }
  });

  $('btnSave').addEventListener('click', async () => {
    try {
      const store = collectStore();
      if (!store.name) return toast('请填店名');
      await api('/api/stores', { method: 'POST', body: JSON.stringify(store) });
      const files = $('photos').files;
      if (files && files.length) {
        const fd = new FormData();
        for (let i = 0; i < files.length; i++) fd.append('photos', files[i]);
        const r = await fetch('/api/stores/' + encodeURIComponent(store.name) + '/photos', {
          method: 'POST',
          credentials: 'same-origin',
          body: fd,
        });
        if (r.status === 401) location.href = '/login';
      }
      await refreshStoreList();
      $('storeSelect').value = store.name;
      toast('已保存');
    } catch (e) {
      toast(e.message);
    }
  });

  $('btnGenerate').addEventListener('click', async () => {
    const btn = $('btnGenerate');
    btn.disabled = true;
    try {
      const store = collectStore();
      const data = await api('/api/generate', {
        method: 'POST',
        body: JSON.stringify({
          store,
          n: Number($('nVersions').value),
          use_llm: $('useLlm').checked,
          style_ids: selectedStyles.length ? selectedStyles : null,
        }),
      });
      versions = data.versions || [];
      renderResults();
      await runEstimate();
      switchTab('scripts');
      toast('生成完成 · ' + versions.length + ' 版');
    } catch (e) {
      toast(e.message);
    } finally {
      btn.disabled = false;
    }
  });

  $('btnEstimate').addEventListener('click', async () => {
    try {
      await runEstimate();
      toast('已更新估算');
    } catch (e) {
      toast(e.message);
    }
  });

  $('btnExportMd').addEventListener('click', async () => {
    try {
      const data = await api('/api/export/markdown', {
        method: 'POST',
        body: JSON.stringify({
          store: collectStore(),
          versions,
          ad_estimate: lastEstimate,
        }),
      });
      const blob = new Blob([data.markdown], { type: 'text/markdown;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = data.filename || 'koubo.md';
      a.click();
      URL.revokeObjectURL(a.href);
      toast('已导出');
    } catch (e) {
      toast(e.message);
    }
  });

  $('btnLogout').addEventListener('click', async () => {
    await api('/api/logout', { method: 'POST', body: '{}' });
    location.href = '/login';
  });

  async function init() {
    try {
      const me = await api('/api/me');
      if (!me.authed) {
        location.href = '/login';
        return;
      }
      $('llmStatus').textContent = me.llm ? 'LLM 已配置' : '模板引擎（可配 API Key）';
      $('useLlm').checked = !!me.llm;
      const meta = await api('/api/styles');
      styles = meta.styles || [];
      if (!selectedStyles.length) {
        selectedStyles = styles.slice(0, 3).map((s) => s.id);
      }
      renderStyleChips();
      const av = meta.default_avatar || {};
      if (!$('av_appearance_zh').value) {
        fillStore({ avatar: av, preferred_styles: selectedStyles });
        // clear name fields after default avatar fill
        $('name').value = '';
        $('city').value = '';
        $('category').value = '';
        $('dishes').value = '';
        $('avg_price').value = '';
        $('sell_points').value = '';
      }
      if (meta.assumptions) {
        $('cpm_low').value = meta.assumptions.cpm_low;
        $('cpm_mid').value = meta.assumptions.cpm_mid;
        $('cpm_high').value = meta.assumptions.cpm_high;
        $('ctr_low').value = meta.assumptions.ctr_low;
        $('ctr_mid').value = meta.assumptions.ctr_mid;
        $('ctr_high').value = meta.assumptions.ctr_high;
        $('ts_low').value = meta.assumptions.to_store_low;
        $('ts_mid').value = meta.assumptions.to_store_mid;
        $('ts_high').value = meta.assumptions.to_store_high;
      }
      await refreshStoreList();
    } catch (e) {
      if (String(e.message) !== 'unauthorized') toast(e.message);
    }
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  }

  init();
})();

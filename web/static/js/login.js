(function () {
  const pwd = document.getElementById('password');
  const btn = document.getElementById('btnLogin');
  const err = document.getElementById('err');
  const toast = document.getElementById('toast');

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 1800);
  }

  async function doLogin() {
    err.classList.add('hidden');
    btn.disabled = true;
    try {
      const r = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ password: pwd.value }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.ok) {
        err.textContent = data.error || '登录失败';
        err.classList.remove('hidden');
        return;
      }
      showToast('登录成功');
      const next = new URLSearchParams(location.search).get('next') || '/';
      location.href = next;
    } catch (e) {
      err.textContent = '网络错误';
      err.classList.remove('hidden');
    } finally {
      btn.disabled = false;
    }
  }

  btn.addEventListener('click', doLogin);
  pwd.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doLogin();
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
})();

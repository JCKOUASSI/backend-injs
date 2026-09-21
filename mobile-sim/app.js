// QR Badge Mobile - Simulation Web (remplace Flutter en sandbox)
// Se connecte à l'API Django INJS-LMD sur port 8000
let API_BASE = '';
let accessToken = localStorage.getItem('qr_access') || '';
let refreshToken = localStorage.getItem('qr_refresh') || '';
let deviceId = localStorage.getItem('qr_device_id') || 'web-sim-' + Math.random().toString(36).substring(2,9);
localStorage.setItem('qr_device_id', deviceId);
let heartbeatTimer = null;
let currentPosition = null;
let html5QrCode = null;

function detectApiBase(){
  const input = document.getElementById('apiUrl');
  let val = input.value.trim();
  if(val){
    API_BASE = val.replace(/\/$/, '');
    return API_BASE;
  }
  // En preview Arena, le front est sur 3000 et proxy /api vers 8000.
  // Si on est sur port 5000, on peut utiliser relative /api qui sera proxyfié par notre server.js
  // Sinon, fallback vers localhost:8000
  const host = window.location.hostname;
  if(host.includes('e2b.app')){
    // Preview: même origine, /api est proxy vers 8000 via server.js
    API_BASE = '';
  } else if(window.location.port === '5000' || window.location.port === '5001'){
    API_BASE = '';
  } else {
    API_BASE = 'http://localhost:8000';
  }
  return API_BASE;
}

function apiUrl(path){
  const base = API_BASE || '';
  if(base === ''){
    return path; // relative, sera proxy
  }
  return base + path;
}

function showScreen(id){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function setSplashStatus(txt){
  const el = document.getElementById('splash-status');
  if(el) el.textContent = txt;
}

async function apiFetch(path, opts={}){
  const url = apiUrl(path);
  const headers = opts.headers || {};
  headers['Content-Type'] = 'application/json';
  if(accessToken){
    headers['Authorization'] = 'Bearer ' + accessToken;
  }
  try{
    const res = await fetch(url, {
      method: opts.method || 'GET',
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const text = await res.text();
    let data = {};
    try{ data = text ? JSON.parse(text) : {}; }catch(e){ data = {raw:text}; }
    if(res.status === 401 && !path.includes('/auth/login/') && !path.includes('/token/refresh/') && refreshToken){
      // tentative refresh
      console.log('401, tentative refresh...');
      const refreshed = await refreshAccess();
      if(refreshed){
        headers['Authorization'] = 'Bearer ' + accessToken;
        const retry = await fetch(url, {
          method: opts.method || 'GET',
          headers,
          body: opts.body ? JSON.stringify(opts.body) : undefined,
        });
        const t2 = await retry.text();
        let d2 = {};
        try{ d2 = t2 ? JSON.parse(t2) : {}; }catch(e){ d2 = {raw:t2}; }
        d2._status = retry.status;
        if(!retry.ok) throw {status:retry.status, data:d2};
        d2._status = retry.status;
        return d2;
      }
    }
    data._status = res.status;
    if(!res.ok){
      throw {status:res.status, data};
    }
    return data;
  }catch(err){
    if(err.status) throw err;
    throw {status:0, data:{detail:'Connexion impossible: '+err.message}};
  }
}

async function refreshAccess(){
  if(!refreshToken) return false;
  try{
    const res = await fetch(apiUrl('/api/auth/token/refresh/'),{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({refresh: refreshToken})
    });
    const data = await res.json();
    if(res.ok && data.access){
      accessToken = data.access;
      if(data.refresh) refreshToken = data.refresh;
      localStorage.setItem('qr_access', accessToken);
      localStorage.setItem('qr_refresh', refreshToken);
      return true;
    }
  }catch(e){ console.error('refresh failed', e); }
  return false;
}

async function init(){
  detectApiBase();
  document.getElementById('apiInfo').textContent = API_BASE || '/api (proxy -> :8000)';
  document.getElementById('apiUrl').value = API_BASE;
  setSplashStatus('Vérification API...');
  try{
    await fetch(apiUrl('/api/health/'));
    setSplashStatus('API joignable ✓');
  }catch(e){
    setSplashStatus('API non joignable, tentative avec proxy /api');
    API_BASE = '';
  }
  await new Promise(r=>setTimeout(r, 800));
  if(accessToken){
    setSplashStatus('Session existante, vérification...');
    try{
      await loadMe();
      showScreen('home');
      loadDashboard();
    }catch(e){
      showScreen('login');
    }
  }else{
    showScreen('login');
  }
}

async function loadMe(){
  const data = await apiFetch('/api/auth/me/');
  return data;
}

async function loadDashboard(){
  try{
    const me = await apiFetch('/api/auth/me/');
    document.getElementById('userName').textContent = me.username || me.email || 'Utilisateur';
    document.getElementById('userRole').textContent = 'Rôle: ' + (me.role || me.groups?.[0] || '—');
    document.getElementById('userEmail').textContent = me.email || '';
    
    // badge status
    try{
      const status = await apiFetch('/api/scan/secure/check-status/');
      document.getElementById('badgeStatus').innerHTML = '<pre>'+JSON.stringify(status, null, 2)+'</pre>';
    }catch(e){
      document.getElementById('badgeStatus').textContent = 'Non badgeable ou erreur: ' + (e.data?.detail || e.data?.message || e.status);
    }

    // seances du jour
    try{
      const seances = await apiFetch('/api/presences/seances-edt/du-jour/');
      if(Array.isArray(seances) && seances.length){
        document.getElementById('seancesDuJour').innerHTML = seances.map(s=>`<div style="padding:8px;border-bottom:1px solid #eee"><strong>${s.module||s.titre||'Séance '+s.id}</strong><br><small>${s.heure_debut||''} - ${s.heure_fin||''} | Salle: ${s.salle||'-'}</small></div>`).join('');
      }else if(seances.results){
        const list = seances.results;
        document.getElementById('seancesDuJour').innerHTML = list.length ? list.map(s=>`<div style="padding:8px;border-bottom:1px solid #eee"><strong>${s.module||s.titre||'Séance '+s.id}</strong><br><small>${s.heure_debut||''} - ${s.heure_fin||''}</small></div>`).join('') : 'Aucune séance aujourd\'hui';
      }else{
        document.getElementById('seancesDuJour').innerHTML = '<pre>'+JSON.stringify(seances, null,2).substring(0,500)+'</pre>';
      }
    }catch(e){
      document.getElementById('seancesDuJour').textContent = 'Erreur: ' + (e.data?.detail || e.status);
    }

  }catch(e){
    console.error(e);
  }
}

// Login
document.getElementById('loginForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const btn = document.getElementById('loginBtn');
  const err = document.getElementById('loginError');
  btn.disabled = true;
  btn.textContent = 'Connexion...';
  err.classList.add('hidden');
  detectApiBase();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  try{
    const data = await apiFetch('/api/auth/login/', {
      method:'POST',
      body:{username, password, device_id: deviceId, device_info: 'WebSim Chrome/122 - '+navigator.userAgent.substring(0,80)}
    });
    accessToken = data.access;
    refreshToken = data.refresh;
    localStorage.setItem('qr_access', accessToken);
    localStorage.setItem('qr_refresh', refreshToken);
    showScreen('home');
    loadDashboard();
  }catch(e){
    err.textContent = e.data?.detail || e.data?.message || JSON.stringify(e.data).substring(0,300) || 'Erreur connexion';
    err.classList.remove('hidden');
  }finally{
    btn.disabled = false;
    btn.textContent = 'Se connecter';
  }
});

document.getElementById('logoutBtn').addEventListener('click', async ()=>{
  try{ await apiFetch('/api/auth/logout/', {method:'POST'}); }catch(e){}
  accessToken=''; refreshToken='';
  localStorage.removeItem('qr_access');
  localStorage.removeItem('qr_refresh');
  if(heartbeatTimer){ clearInterval(heartbeatTimer); heartbeatTimer=null; }
  showScreen('login');
});

document.getElementById('refreshMe').addEventListener('click', ()=>loadDashboard());

// Navigation
document.querySelectorAll('[data-action]').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    const action = btn.dataset.action;
    showScreen(action);
    if(action==='history') loadHistory();
    if(action==='fiche') loadFiche();
    if(action==='config') loadConfig();
  });
});
document.querySelectorAll('[data-back]').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    if(html5QrCode){ try{ html5QrCode.stop(); }catch(e){} html5QrCode=null; document.getElementById('startScan').classList.remove('hidden'); document.getElementById('stopScan').classList.add('hidden'); }
    showScreen(btn.dataset.back);
  });
});

// Scan
document.getElementById('startScan').addEventListener('click', async ()=>{
  const readerEl = document.getElementById('reader');
  if(!window.Html5Qrcode){
    document.getElementById('scanResult').className='result error';
    document.getElementById('scanResult').textContent='Librairie QR non chargée. Utilisez saisie manuelle.';
    document.getElementById('scanResult').classList.remove('hidden');
    return;
  }
  try{
    html5QrCode = new Html5Qrcode("reader");
    await html5QrCode.start({facingMode:"environment"}, {fps:10, qrbox:250},
      (decodedText)=>{
        document.getElementById('manualToken').value = decodedText;
        doSecureScan(decodedText);
      },
      (err)=>{}
    );
    document.getElementById('startScan').classList.add('hidden');
    document.getElementById('stopScan').classList.remove('hidden');
  }catch(e){
    document.getElementById('scanResult').className='result error';
    document.getElementById('scanResult').textContent='Erreur caméra: '+e;
    document.getElementById('scanResult').classList.remove('hidden');
  }
});
document.getElementById('stopScan').addEventListener('click', async ()=>{
  if(html5QrCode){
    try{ await html5QrCode.stop(); }catch(e){}
    html5QrCode=null;
  }
  document.getElementById('startScan').classList.remove('hidden');
  document.getElementById('stopScan').classList.add('hidden');
});
document.getElementById('manualScanBtn').addEventListener('click', ()=>{
  const token = document.getElementById('manualToken').value.trim();
  if(!token){ alert('Saisissez un token'); return; }
  doSecureScan(token);
});

async function doSecureScan(tokenOrUrl){
  const resultEl = document.getElementById('scanResult');
  const lastEl = document.getElementById('lastScan');
  resultEl.classList.remove('hidden');
  resultEl.className='result';
  resultEl.textContent='Envoi scan sécurisé...';
  let payload = {};
  // token peut être URL complète, extraire token param
  try{
    const url = new URL(tokenOrUrl);
    const t = url.searchParams.get('token') || url.searchParams.get('qr_token') || tokenOrUrl;
    payload.token = t;
    if(url.pathname.includes('formations')) payload.formation_token = t;
  }catch(e){
    payload.token = tokenOrUrl;
  }
  if(currentPosition){
    payload.latitude = currentPosition.coords.latitude;
    payload.longitude = currentPosition.coords.longitude;
    payload.accuracy = currentPosition.coords.accuracy;
  }
  payload.device_id = deviceId;
  try{
    const res = await apiFetch('/api/scan/secure/', {method:'POST', body: payload});
    resultEl.className='result success';
    resultEl.innerHTML = '<strong>✓ Scan réussi</strong><br><pre>'+JSON.stringify(res, null,2)+'</pre>';
    lastEl.textContent = new Date().toLocaleString() + ' - ' + JSON.stringify(res).substring(0,500);
  }catch(e){
    resultEl.className='result error';
    resultEl.innerHTML = '<strong>✗ Échec scan</strong><br>'+ (e.data?.detail || e.data?.code || JSON.stringify(e.data).substring(0,500)) + '<br>Status: '+e.status;
    lastEl.textContent = new Date().toLocaleString() + ' - ERREUR ' + e.status + ' ' + JSON.stringify(e.data).substring(0,500);
  }
}

// History
async function loadHistory(){
  const el = document.getElementById('historyContent');
  el.textContent='Chargement...';
  try{
    const data = await apiFetch('/api/me/historique/');
    el.innerHTML = '<pre>'+JSON.stringify(data, null,2)+'</pre>';
  }catch(e){
    el.innerHTML = '<div class="error">Erreur: '+(e.data?.detail||e.status)+'</div><pre>'+JSON.stringify(e.data,null,2)+'</pre>';
  }
}
async function loadFiche(){
  const el = document.getElementById('ficheContent');
  el.textContent='Chargement...';
  try{
    const data = await apiFetch('/api/me/fiche/');
    el.innerHTML = '<pre>'+JSON.stringify(data, null,2)+'</pre>';
  }catch(e){
    el.innerHTML = '<div class="error">Erreur: '+(e.data?.detail||e.status)+'</div><pre>'+JSON.stringify(e.data,null,2)+'</pre>';
  }
}
async function loadConfig(){
  const el = document.getElementById('configContent');
  el.textContent='Chargement...';
  try{
    const data = await apiFetch('/api/mobile/config/');
    el.innerHTML = `
      <div class="card"><h4>Config serveur</h4><pre>${JSON.stringify(data,null,2)}</pre></div>
      <div class="card"><h4>Device local</h4>
        <div class="row"><span>Device ID</span><span class="muted" style="font-size:10px">${deviceId}</span></div>
        <div class="row"><span>User Agent</span><span class="muted" style="font-size:10px">${navigator.userAgent.substring(0,60)}</span></div>
        <div class="row"><span>API Base</span><span class="muted">${API_BASE||'/api (proxy)'}</span></div>
      </div>
    `;
  }catch(e){
    el.innerHTML = '<div class="error">Erreur: '+(e.data?.detail||e.status)+'</div><pre>'+JSON.stringify(e.data,null,2)+'</pre>';
  }
}

// Heartbeat
document.getElementById('toggleHeartbeat').addEventListener('click', ()=>{
  if(heartbeatTimer){
    clearInterval(heartbeatTimer);
    heartbeatTimer=null;
    document.getElementById('heartbeatStatus').textContent='Inactif';
    document.getElementById('heartbeatStatus').className='badge';
    document.getElementById('toggleHeartbeat').textContent='Activer heartbeat';
  }else{
    heartbeatTimer = setInterval(async ()=>{
      try{
        const payload = {device_id: deviceId};
        if(currentPosition){
          payload.latitude = currentPosition.coords.latitude;
          payload.longitude = currentPosition.coords.longitude;
          payload.accuracy = currentPosition.coords.accuracy;
        }
        const res = await apiFetch('/api/scan/secure/heartbeat/', {method:'POST', body: payload});
        document.getElementById('heartbeatStatus').textContent='Actif ✓ '+new Date().toLocaleTimeString();
        document.getElementById('heartbeatStatus').className='badge active';
      }catch(e){
        document.getElementById('heartbeatStatus').textContent='Erreur '+e.status;
      }
    }, 60000);
    document.getElementById('heartbeatStatus').textContent='Actif';
    document.getElementById('heartbeatStatus').className='badge active';
    document.getElementById('toggleHeartbeat').textContent='Désactiver heartbeat';
    // immediate
    (async ()=>{
      try{
        const payload = {device_id: deviceId};
        if(currentPosition){
          payload.latitude = currentPosition.coords.latitude;
          payload.longitude = currentPosition.coords.longitude;
        }
        await apiFetch('/api/scan/secure/heartbeat/', {method:'POST', body: payload});
        document.getElementById('heartbeatStatus').textContent='Actif ✓ '+new Date().toLocaleTimeString();
      }catch(e){}
    })();
  }
});

document.getElementById('getLocation').addEventListener('click', ()=>{
  const el = document.getElementById('locationStatus');
  el.textContent='Acquisition...';
  if(!navigator.geolocation){
    el.textContent='Géolocalisation non supportée';
    return;
  }
  navigator.geolocation.getCurrentPosition((pos)=>{
    currentPosition = pos;
    el.textContent = `${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)} (±${Math.round(pos.coords.accuracy)}m)`;
  }, (err)=>{
    el.textContent='Erreur: '+err.message;
  }, {enableHighAccuracy:true, timeout:10000});
});

init();

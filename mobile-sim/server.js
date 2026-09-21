const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = process.env.PORT || 5000;
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const ROOT = __dirname;

const mime = {
  '.html':'text/html; charset=utf-8',
  '.js':'application/javascript; charset=utf-8',
  '.css':'text/css; charset=utf-8',
  '.json':'application/json; charset=utf-8',
  '.png':'image/png',
  '.jpg':'image/jpeg',
  '.jpeg':'image/jpeg',
  '.svg':'image/svg+xml',
  '.ico':'image/x-icon',
  '.webmanifest':'application/manifest+json',
};

function serveFile(res, filePath){
  const ext = path.extname(filePath).toLowerCase();
  const type = mime[ext] || 'application/octet-stream';
  fs.readFile(filePath, (err, data)=>{
    if(err){
      res.writeHead(404, {'Content-Type':'text/plain'});
      res.end('Not found');
      return;
    }
    // CORS & preview headers
    res.writeHead(200, {
      'Content-Type': type,
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
      'Cache-Control': ext==='.html' ? 'no-store' : 'public, max-age=3600',
    });
    res.end(data);
  });
}

function proxyRequest(req, res, targetPath){
  const targetUrl = new URL(targetPath, BACKEND);
  // Preserve query
  const incomingUrl = new URL(req.url, `http://${req.headers.host}`);
  targetUrl.search = incomingUrl.search;

  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port,
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: {
      ...req.headers,
      host: targetUrl.host,
      'X-Forwarded-Host': req.headers.host || '',
      'X-Forwarded-Proto': req.headers['x-forwarded-proto'] || (req.headers.host && req.headers.host.includes('e2b.app') ? 'https' : 'http'),
      'X-Forwarded-For': req.socket.remoteAddress || '',
    }
  };
  // Remove hop-by-hop
  delete options.headers['connection'];
  
  const proxyReq = http.request(options, (proxyRes)=>{
    // Forward status and headers, but add CORS
    const headers = {...proxyRes.headers};
    headers['Access-Control-Allow-Origin'] = req.headers.origin || '*';
    headers['Access-Control-Allow-Credentials'] = 'true';
    headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS';
    headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-CSRFToken';
    // Fix cookie samesite for preview if needed - let backend handle
    res.writeHead(proxyRes.statusCode, headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err)=>{
    console.error('Proxy error', targetPath, err.message);
    res.writeHead(502, {'Content-Type':'application/json', 'Access-Control-Allow-Origin':'*'});
    res.end(JSON.stringify({detail:'Backend unavailable', error: err.message, target: BACKEND+targetPath}));
  });

  if(req.method !== 'GET' && req.method !== 'HEAD'){
    req.pipe(proxyReq);
  } else {
    proxyReq.end();
  }
}

const server = http.createServer((req, res)=>{
  // CORS preflight
  if(req.method === 'OPTIONS'){
    res.writeHead(204, {
      'Access-Control-Allow-Origin': req.headers.origin || '*',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-CSRFToken',
      'Access-Control-Max-Age': '86400',
    });
    res.end();
    return;
  }

  const urlPath = req.url.split('?')[0];

  // Proxy API, admin, static, media to Django
  if(urlPath.startsWith('/api/') || urlPath.startsWith('/admin/') || urlPath.startsWith('/static/') || urlPath.startsWith('/media/')){
    proxyRequest(req, res, req.url);
    return;
  }

  // Serve static files
  let filePath = path.join(ROOT, urlPath === '/' ? 'index.html' : urlPath);
  // Security: prevent directory traversal
  if(!filePath.startsWith(ROOT)){
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.stat(filePath, (err, stat)=>{
    if(err || !stat.isFile()){
      // SPA fallback: serve index.html for unknown routes
      serveFile(res, path.join(ROOT, 'index.html'));
    } else {
      serveFile(res, filePath);
    }
  });
});

server.listen(PORT, '0.0.0.0', ()=>{
  console.log(`QR Badge Mobile Sim serving on http://0.0.0.0:${PORT}`);
  console.log(`Proxying /api, /admin, /static, /media -> ${BACKEND}`);
});

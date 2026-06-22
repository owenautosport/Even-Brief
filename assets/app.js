(function(){
  // Full weather-page radar — interactive + animated through recent frames
  function initForecastRadar(){
    if(typeof L==='undefined') return;
    var el=document.getElementById('fcRadar'); if(!el || el._built) return; el._built=true;
    var dark=document.documentElement.getAttribute('data-theme')!=='light';
    var map=L.map(el,{zoomControl:true,attributionControl:true,scrollWheelZoom:false}).setView([51.235,-0.574],7);
    var base=dark?'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png':'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
    L.tileLayer(base,{subdomains:'abcd',maxZoom:19,attribution:'© OSM, © CARTO'}).addTo(map);
    fetch('https://api.rainviewer.com/public/weather-maps.json').then(function(r){return r.json();}).then(function(d){
      var frames=(((d.radar&&d.radar.past)||[]).concat((d.radar&&d.radar.nowcast)||[]));
      if(!frames.length) return;
      var layers=frames.map(function(f){ return L.tileLayer(d.host+f.path+'/256/{z}/{x}/{y}/4/1_1.png',{opacity:0,maxZoom:19}); });
      layers.forEach(function(l){ l.addTo(map); });
      var idx=frames.length-1; layers[idx].setOpacity(.7);
      setInterval(function(){ layers[idx].setOpacity(0); idx=(idx+1)%layers.length; layers[idx].setOpacity(.7); }, 700);
    }).catch(function(){});
    setTimeout(function(){ map.invalidateSize(); },250);
    window.addEventListener('resize', function(){ map.invalidateSize(); });
  }

  var navlinks = document.querySelectorAll('.mlink');
  var panels = document.querySelectorAll('.panel');
  var topbarTitle = document.getElementById('topbarTitle');
  // Keep sidebar tiles beside the article only up to the article's height; any
  // tiles that would overflow past the article's bottom move into .below (full
  // width) so a short article never sits next to a tall, half-empty rail.
  function reflow(panel){
    if(!panel) return;
    var grid = panel.querySelector('.grid'); if(!grid) return;
    var article = grid.querySelector('.article'), side = grid.querySelector('.side');
    if(!article || !side) return;
    var below = grid.querySelector('.below');
    if(!below){ below = document.createElement('div'); below.className = 'below'; grid.appendChild(below); }
    while(below.firstChild){ side.appendChild(below.firstChild); }   // reset to rail
    grid.classList.remove('fullwide');
    if(window.matchMedia('(max-width:820px)').matches){ return; }    // single column on mobile
    var cap = article.offsetHeight;
    var tiles = Array.prototype.slice.call(side.children);
    var used = 0, overflowing = false;
    for(var i=0;i<tiles.length;i++){
      var t = tiles[i], h = t.offsetHeight;
      if(!overflowing && (used + h) <= cap){ used += h + 18; }
      else { overflowing = true; below.appendChild(t); }
    }
    if(side.children.length === 0){ grid.classList.add('fullwide'); }
  }
  // Market hours board — live open/closed status + countdown to open/close (computed in each market's timezone)
  (function(){
    var grid=document.getElementById('mhGrid'); if(!grid) return;
    var MK=[
      {city:'New York',name:'NYSE · Nasdaq',tz:'America/New_York',o:570,c:960},
      {city:'London',name:'LSE',tz:'Europe/London',o:480,c:990},
      {city:'Frankfurt',name:'Xetra',tz:'Europe/Berlin',o:540,c:1050},
      {city:'Tokyo',name:'Tokyo SE',tz:'Asia/Tokyo',o:540,c:930},
      {city:'Hong Kong',name:'HKEX',tz:'Asia/Hong_Kong',o:570,c:960},
      {city:'Shanghai',name:'Shanghai SE',tz:'Asia/Shanghai',o:570,c:900},
      {city:'Sydney',name:'ASX',tz:'Australia/Sydney',o:600,c:960}
    ];
    var WD={Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6};
    function nowIn(tz){
      var parts=new Intl.DateTimeFormat('en-US',{timeZone:tz,weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZoneName:'short'}).formatToParts(new Date());
      var o={}; parts.forEach(function(p){o[p.type]=p.value;});
      var h=parseInt(o.hour,10)%24;
      return {wd:WD[o.weekday], min:h*60+parseInt(o.minute,10)+parseInt(o.second,10)/60, zone:o.timeZoneName};
    }
    function calc(m){
      var t=nowIn(m.tz), cur=t.min, wd=t.wd, trading=(wd>=1&&wd<=5);
      if(trading && cur>=m.o && cur<m.c) return {open:true, mins:m.c-cur, zone:t.zone};
      for(var off=0;off<=7;off++){ var dwd=(wd+off)%7; if(dwd>=1&&dwd<=5){ if(off===0){ if(cur<m.o) return {open:false,mins:m.o-cur,zone:t.zone}; } else return {open:false,mins:off*1440+m.o-cur,zone:t.zone}; } }
      return {open:false,mins:0,zone:t.zone};
    }
    function hhmm(x){ var h=Math.floor(x/60),m=x%60; return (h<10?'0'+h:h)+':'+(m<10?'0'+m:m); }
    function dur(mins){ mins=Math.max(0,Math.round(mins)); var d=Math.floor(mins/1440),h=Math.floor((mins%1440)/60),m=mins%60; if(d>0) return d+'d '+h+'h'; if(h>0) return h+'h '+m+'m'; return m+'m'; }
    function render(){
      grid.innerHTML=MK.map(function(m){ var r=calc(m); var st=r.open?'open':'closed';
        return '<div class="mh-card"><div class="mh-top"><span class="mh-city">'+m.city+'</span><span class="mh-pill '+st+'">'+(r.open?'Open':'Closed')+'</span></div>'
          +'<div class="mh-ex">'+m.name+'</div>'
          +'<div class="mh-hrs">'+hhmm(m.o)+'–'+hhmm(m.c)+' '+r.zone+'</div>'
          +'<div class="mh-cd '+st+'">'+(r.open?'Closes in '+dur(r.mins):'Opens in '+dur(r.mins))+'</div></div>';
      }).join('');
    }
    render(); setInterval(render,1000);
  })();

  // Live stocks (TradingView) — built on first open so widgets size correctly while visible
  var stocksReady=false;
  function tvTheme(){ return (document.documentElement.getAttribute('data-theme')==='light')?'light':'dark'; }
  function tvMake(sel, src, cfg){
    var host=document.querySelector(sel); if(!host) return;
    cfg.theme=tvTheme(); cfg.colorTheme=tvTheme();
    host.innerHTML='<div class="tradingview-widget-container__widget"></div>';
    var s=document.createElement('script'); s.type='text/javascript'; s.async=true; s.src=src;
    s.text=JSON.stringify(cfg); host.appendChild(s);
  }
  function initStocks(){
    if(stocksReady) return; stocksReady=true;
    tvMake('#tvTape','https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js',{symbols:[{proName:'FOREXCOM:SPXUSD',title:'S&P 500'},{proName:'NYSE:JPM',title:'JPMorgan'},{proName:'NYSE:BAC',title:'Bank of America'},{proName:'NYSE:XOM',title:'Exxon'},{proName:'NYSE:WMT',title:'Walmart'},{proName:'NYSE:KO',title:'Coca-Cola'},{proName:'NYSE:NKE',title:'Nike'},{proName:'NYSE:DIS',title:'Disney'}],displayMode:'adaptive',isTransparent:true,locale:'en'});
    tvMake('#tvHot','https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js',{dataSource:'SPX500',blockSize:'market_cap_basic',blockColor:'change',grouping:'no_group',locale:'en',symbolUrl:'',hasTopBar:false,isDataSetEnabled:false,isZoomEnabled:true,hasSymbolTooltip:true,isMonoSize:false,width:'100%',height:760});
    tvMake('#tvQuotes','https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js',{width:'100%',height:600,symbolsGroups:[{name:'Most popular',symbols:[{name:'NASDAQ:AAPL',displayName:'Apple'},{name:'NASDAQ:MSFT',displayName:'Microsoft'},{name:'NASDAQ:NVDA',displayName:'NVIDIA'},{name:'NASDAQ:AMZN',displayName:'Amazon'},{name:'NASDAQ:META',displayName:'Meta'},{name:'NASDAQ:TSLA',displayName:'Tesla'},{name:'NASDAQ:GOOGL',displayName:'Alphabet'},{name:'NYSE:JPM',displayName:'JPMorgan'},{name:'NYSE:V',displayName:'Visa'},{name:'NYSE:WMT',displayName:'Walmart'},{name:'NYSE:XOM',displayName:'Exxon Mobil'},{name:'NYSE:KO',displayName:'Coca-Cola'}]}],showSymbolLogo:true,isTransparent:false,locale:'en'});
    tvMake('#tvScreener','https://s3.tradingview.com/external-embedding/embed-widget-screener.js',{width:'100%',height:900,defaultColumn:'overview',defaultScreen:'most_capitalized',market:'america',showToolbar:true,locale:'en',isTransparent:true});
  }
  // Stock detail overlay — builds the big interactive chart for the chosen symbol on open
  var sdBack=document.getElementById('stkDetailBack'), sdEl=document.getElementById('stkDetail'),
      sdTitle=document.getElementById('sdTitle'), sdChart=document.getElementById('sdChart');
  function openDetail(sym, label){
    sym=String(sym||'').trim().toUpperCase(); if(!sym||!sdEl) return;
    if(sdTitle) sdTitle.textContent=label||sym;
    if(sdBack){ sdBack.hidden=false; }
    sdEl.hidden=false;
    requestAnimationFrame(function(){ if(sdBack) sdBack.classList.add('show'); sdEl.classList.add('show');
      tvMake('#sdChart','https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js',{autosize:true,symbol:sym,interval:'D',timezone:'Europe/London',style:'1',locale:'en',hide_side_toolbar:false,allow_symbol_change:true,support_host:'https://www.tradingview.com'});
    });
  }
  function closeDetail(){
    if(!sdEl) return; sdEl.classList.remove('show'); if(sdBack) sdBack.classList.remove('show');
    setTimeout(function(){ sdEl.hidden=true; if(sdBack) sdBack.hidden=true; if(sdChart) sdChart.innerHTML='<div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div></div>'; }, 220);
  }
  (function(){
    var x=document.getElementById('sdClose');
    if(x) x.addEventListener('click', closeDetail);
    if(sdBack) sdBack.addEventListener('click', closeDetail);
    document.addEventListener('keydown', function(e){ if(e.key==='Escape' && sdEl && !sdEl.hidden) closeDetail(); });
  })();
  // Stock search with ticker/company autocomplete
  (function(){
    var inp=document.getElementById('stkSym'), sug=document.getElementById('stkSug'), form=document.getElementById('stkSearch');
    if(!inp||!sug||!form) return;
    var DATA=[
{s:"AAPL",n:"Apple Inc.",e:"NASDAQ"},{s:"MSFT",n:"Microsoft Corp.",e:"NASDAQ"},{s:"NVDA",n:"NVIDIA Corp.",e:"NASDAQ"},{s:"AMZN",n:"Amazon.com Inc.",e:"NASDAQ"},{s:"GOOGL",n:"Alphabet Inc. (Class A)",e:"NASDAQ"},{s:"GOOG",n:"Alphabet Inc. (Class C)",e:"NASDAQ"},{s:"META",n:"Meta Platforms Inc.",e:"NASDAQ"},{s:"TSLA",n:"Tesla Inc.",e:"NASDAQ"},{s:"AVGO",n:"Broadcom Inc.",e:"NASDAQ"},{s:"ADBE",n:"Adobe Inc.",e:"NASDAQ"},{s:"NFLX",n:"Netflix Inc.",e:"NASDAQ"},{s:"INTC",n:"Intel Corp.",e:"NASDAQ"},{s:"AMD",n:"Advanced Micro Devices",e:"NASDAQ"},{s:"CSCO",n:"Cisco Systems",e:"NASDAQ"},{s:"QCOM",n:"Qualcomm Inc.",e:"NASDAQ"},{s:"TXN",n:"Texas Instruments",e:"NASDAQ"},{s:"AMAT",n:"Applied Materials",e:"NASDAQ"},{s:"MU",n:"Micron Technology",e:"NASDAQ"},{s:"INTU",n:"Intuit Inc.",e:"NASDAQ"},{s:"AMGN",n:"Amgen Inc.",e:"NASDAQ"},{s:"GILD",n:"Gilead Sciences",e:"NASDAQ"},{s:"BKNG",n:"Booking Holdings",e:"NASDAQ"},{s:"SBUX",n:"Starbucks Corp.",e:"NASDAQ"},{s:"MDLZ",n:"Mondelez International",e:"NASDAQ"},{s:"PEP",n:"PepsiCo Inc.",e:"NASDAQ"},{s:"COST",n:"Costco Wholesale",e:"NASDAQ"},{s:"CMCSA",n:"Comcast Corp.",e:"NASDAQ"},{s:"ADP",n:"Automatic Data Processing",e:"NASDAQ"},{s:"REGN",n:"Regeneron Pharmaceuticals",e:"NASDAQ"},{s:"VRTX",n:"Vertex Pharmaceuticals",e:"NASDAQ"},{s:"LRCX",n:"Lam Research",e:"NASDAQ"},{s:"KLAC",n:"KLA Corp.",e:"NASDAQ"},{s:"SNPS",n:"Synopsys Inc.",e:"NASDAQ"},{s:"CDNS",n:"Cadence Design Systems",e:"NASDAQ"},{s:"MRVL",n:"Marvell Technology",e:"NASDAQ"},{s:"PANW",n:"Palo Alto Networks",e:"NASDAQ"},{s:"CRWD",n:"CrowdStrike Holdings",e:"NASDAQ"},{s:"PLTR",n:"Palantir Technologies",e:"NASDAQ"},{s:"COIN",n:"Coinbase Global",e:"NASDAQ"},{s:"MRNA",n:"Moderna Inc.",e:"NASDAQ"},{s:"PYPL",n:"PayPal Holdings",e:"NASDAQ"},{s:"ABNB",n:"Airbnb Inc.",e:"NASDAQ"},{s:"HON",n:"Honeywell International",e:"NASDAQ"},{s:"KHC",n:"Kraft Heinz Co.",e:"NASDAQ"},{s:"AAL",n:"American Airlines Group",e:"NASDAQ"},{s:"UAL",n:"United Airlines Holdings",e:"NASDAQ"},{s:"QQQ",n:"Invesco QQQ Trust",e:"NASDAQ"},
{s:"JPM",n:"JPMorgan Chase & Co.",e:"NYSE"},{s:"BAC",n:"Bank of America",e:"NYSE"},{s:"WFC",n:"Wells Fargo & Co.",e:"NYSE"},{s:"C",n:"Citigroup Inc.",e:"NYSE"},{s:"GS",n:"Goldman Sachs Group",e:"NYSE"},{s:"MS",n:"Morgan Stanley",e:"NYSE"},{s:"V",n:"Visa Inc.",e:"NYSE"},{s:"MA",n:"Mastercard Inc.",e:"NYSE"},{s:"BRK.B",n:"Berkshire Hathaway (B)",e:"NYSE"},{s:"XOM",n:"Exxon Mobil Corp.",e:"NYSE"},{s:"CVX",n:"Chevron Corp.",e:"NYSE"},{s:"WMT",n:"Walmart Inc.",e:"NYSE"},{s:"KO",n:"Coca-Cola Co.",e:"NYSE"},{s:"PG",n:"Procter & Gamble",e:"NYSE"},{s:"JNJ",n:"Johnson & Johnson",e:"NYSE"},{s:"UNH",n:"UnitedHealth Group",e:"NYSE"},{s:"HD",n:"Home Depot",e:"NYSE"},{s:"MCD",n:"McDonald's Corp.",e:"NYSE"},{s:"DIS",n:"Walt Disney Co.",e:"NYSE"},{s:"NKE",n:"Nike Inc.",e:"NYSE"},{s:"PFE",n:"Pfizer Inc.",e:"NYSE"},{s:"MRK",n:"Merck & Co.",e:"NYSE"},{s:"ABBV",n:"AbbVie Inc.",e:"NYSE"},{s:"LLY",n:"Eli Lilly & Co.",e:"NYSE"},{s:"TMO",n:"Thermo Fisher Scientific",e:"NYSE"},{s:"ABT",n:"Abbott Laboratories",e:"NYSE"},{s:"ORCL",n:"Oracle Corp.",e:"NYSE"},{s:"CRM",n:"Salesforce Inc.",e:"NYSE"},{s:"IBM",n:"International Business Machines",e:"NYSE"},{s:"GE",n:"GE Aerospace",e:"NYSE"},{s:"BA",n:"Boeing Co.",e:"NYSE"},{s:"CAT",n:"Caterpillar Inc.",e:"NYSE"},{s:"MMM",n:"3M Co.",e:"NYSE"},{s:"RTX",n:"RTX Corp.",e:"NYSE"},{s:"LMT",n:"Lockheed Martin",e:"NYSE"},{s:"T",n:"AT&T Inc.",e:"NYSE"},{s:"VZ",n:"Verizon Communications",e:"NYSE"},{s:"F",n:"Ford Motor Co.",e:"NYSE"},{s:"GM",n:"General Motors",e:"NYSE"},{s:"UPS",n:"United Parcel Service",e:"NYSE"},{s:"FDX",n:"FedEx Corp.",e:"NYSE"},{s:"LOW",n:"Lowe's Companies",e:"NYSE"},{s:"TGT",n:"Target Corp.",e:"NYSE"},{s:"AXP",n:"American Express",e:"NYSE"},{s:"BLK",n:"BlackRock Inc.",e:"NYSE"},{s:"SCHW",n:"Charles Schwab",e:"NYSE"},{s:"SPGI",n:"S&P Global Inc.",e:"NYSE"},{s:"NOW",n:"ServiceNow Inc.",e:"NYSE"},{s:"UBER",n:"Uber Technologies",e:"NYSE"},{s:"SNAP",n:"Snap Inc.",e:"NYSE"},{s:"PINS",n:"Pinterest Inc.",e:"NYSE"},{s:"SHOP",n:"Shopify Inc.",e:"NYSE"},{s:"SQ",n:"Block Inc.",e:"NYSE"},{s:"CVS",n:"CVS Health Corp.",e:"NYSE"},{s:"COP",n:"ConocoPhillips",e:"NYSE"},{s:"SLB",n:"Schlumberger",e:"NYSE"},{s:"OXY",n:"Occidental Petroleum",e:"NYSE"},{s:"NEE",n:"NextEra Energy",e:"NYSE"},{s:"DUK",n:"Duke Energy",e:"NYSE"},{s:"SO",n:"Southern Co.",e:"NYSE"},{s:"CL",n:"Colgate-Palmolive",e:"NYSE"},{s:"MO",n:"Altria Group",e:"NYSE"},{s:"PM",n:"Philip Morris International",e:"NYSE"},{s:"DE",n:"Deere & Co.",e:"NYSE"},{s:"DAL",n:"Delta Air Lines",e:"NYSE"},{s:"WBA",n:"Walgreens Boots Alliance",e:"NASDAQ"},{s:"PLD",n:"Prologis Inc.",e:"NYSE"},{s:"AMT",n:"American Tower",e:"NYSE"},
{s:"SPY",n:"SPDR S&P 500 ETF",e:"NYSE"},{s:"DIA",n:"SPDR Dow Jones ETF",e:"NYSE"},{s:"IWM",n:"iShares Russell 2000 ETF",e:"NYSE"},{s:"VTI",n:"Vanguard Total Stock Market",e:"NYSE"},{s:"VOO",n:"Vanguard S&P 500 ETF",e:"NYSE"}
    ];
    var matches=[], hi=-1;
    function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
    function close(){ sug.hidden=true; sug.innerHTML=''; hi=-1; inp.setAttribute('aria-expanded','false'); }
    function pick(it){ if(!it) return; inp.value=it.s; close(); openDetail(it.s, it.s+' · '+it.n); }
    var grid=document.getElementById('stkGrid');
    function buildGrid(filter){
      if(!grid) return;
      filter=(filter||'').trim().toLowerCase();
      var items = filter ? DATA.filter(function(d){ return d.s.toLowerCase().indexOf(filter)>-1 || d.n.toLowerCase().indexOf(filter)>-1; }) : DATA;
      grid.innerHTML = items.length ? items.map(function(d){ return '<button class="stk-card" data-s="'+esc(d.s)+'" data-n="'+esc(d.n)+'"><span class="c-tk">'+esc(d.s)+'</span><span class="c-nm">'+esc(d.n)+'</span><span class="c-ex">'+esc(d.e)+'</span></button>'; }).join('') : '<div class="stk-empty">No matches in the popular list — type a full ticker and press View.</div>';
    }
    if(grid){ grid.addEventListener('click', function(e){ var c=e.target.closest('.stk-card'); if(!c) return; openDetail(c.getAttribute('data-s'), c.getAttribute('data-s')+' · '+c.getAttribute('data-n')); }); buildGrid(''); }
    function search(q){
      q=q.trim().toLowerCase(); if(!q) return [];
      var pre=[], sub=[];
      for(var i=0;i<DATA.length;i++){ var d=DATA[i], s=d.s.toLowerCase(), n=d.n.toLowerCase();
        if(s.indexOf(q)===0 || n.indexOf(q)===0) pre.push(d);
        else if(s.indexOf(q)>-1 || n.indexOf(q)>-1) sub.push(d);
      }
      return pre.concat(sub).slice(0,8);
    }
    function render(){
      if(!matches.length){ close(); return; }
      sug.innerHTML=matches.map(function(d,i){ return '<div class="stk-sug-item'+(i===hi?' active':'')+'" data-i="'+i+'"><span class="ss-tk">'+esc(d.s)+'</span><span class="ss-nm">'+esc(d.n)+'</span><span class="ss-ex">'+esc(d.e)+'</span></div>'; }).join('');
      sug.hidden=false; inp.setAttribute('aria-expanded','true');
    }
    inp.addEventListener('input', function(){ matches=search(inp.value); hi=-1; render(); buildGrid(inp.value); });
    inp.addEventListener('keydown', function(e){
      if(sug.hidden){ return; }
      if(e.key==='ArrowDown'){ e.preventDefault(); hi=Math.min(hi+1, matches.length-1); render(); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); hi=Math.max(hi-1, 0); render(); }
      else if(e.key==='Enter'){ if(hi>=0){ e.preventDefault(); pick(matches[hi]); } }
      else if(e.key==='Escape'){ close(); }
    });
    sug.addEventListener('mousedown', function(e){ var it=e.target.closest('.stk-sug-item'); if(!it) return; e.preventDefault(); pick(matches[+it.getAttribute('data-i')]); });
    inp.addEventListener('blur', function(){ setTimeout(close, 150); });
    form.addEventListener('submit', function(e){ e.preventDefault(); if(hi>=0 && matches[hi]){ pick(matches[hi]); return; } var v=inp.value.trim(); if(!v) return; close(); openDetail(v, v.toUpperCase()); });
  })();

  // Weather page: today's hourly charts (inline SVG) + selectable 7-day detail
  (function(){
    var __wx=(function(){try{return JSON.parse(document.getElementById('wxData').textContent)||{};}catch(e){return {};}})();
    var temp=(__wx.temp||[]);
    var precip=(__wx.precip||[]);
    function lineChart(data){
      var W=720,H=220,pl=30,pr=12,pt=18,pb=26,n=data.length;
      var mn=Math.min.apply(null,data),mx=Math.max.apply(null,data),lo=Math.floor(mn-1),hi=Math.ceil(mx+1);
      function X(i){return pl+(W-pl-pr)*i/(n-1);} function Y(v){return pt+(H-pt-pb)*(1-(v-lo)/((hi-lo)||1));}
      var pts=data.map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1);});
      var line='M'+pts.join(' L'), area=line+' L'+X(n-1).toFixed(1)+','+(H-pb)+' L'+X(0).toFixed(1)+','+(H-pb)+' Z';
      var yl='';[lo,Math.round((lo+hi)/2),hi].forEach(function(v){yl+='<line x1="'+pl+'" y1="'+Y(v).toFixed(1)+'" x2="'+(W-pr)+'" y2="'+Y(v).toFixed(1)+'" style="stroke:var(--line);stroke-width:1"></line><text x="2" y="'+(Y(v)+4).toFixed(1)+'" style="fill:var(--ink-mute);font-size:11px">'+v+'°</text>';});
      var xl='';for(var i=0;i<n;i++){xl+='<text x="'+X(i).toFixed(1)+'" y="'+(H-8)+'" text-anchor="middle" style="fill:var(--ink-mute);font-size:9px">'+(i<10?'0'+i:i)+'</text>';}
      var pi=data.indexOf(mx),dot='<circle cx="'+X(pi).toFixed(1)+'" cy="'+Y(mx).toFixed(1)+'" r="3.5" style="fill:var(--gold)"></circle><text x="'+X(pi).toFixed(1)+'" y="'+(Y(mx)-8).toFixed(1)+'" text-anchor="middle" style="fill:var(--ink-strong);font-size:11px;font-weight:700">'+mx+'°</text>';
      return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="display:block;height:auto">'+yl+'<path d="'+area+'" style="fill:var(--gold);opacity:.12"></path><path d="'+line+'" style="fill:none;stroke:var(--gold);stroke-width:2.5;stroke-linejoin:round"></path>'+xl+dot+'</svg>';
    }
    function barChart(data){
      var W=720,H=220,pl=30,pr=12,pt=16,pb=26,n=data.length;
      var mx=Math.max(20,Math.max.apply(null,data)); mx=Math.ceil(mx/10)*10;
      var step=(W-pl-pr)/n, bw=step*0.62;
      function Yb(v){return pt+(H-pt-pb)*(1-v/mx);}
      var bars='';for(var i=0;i<n;i++){var x=pl+step*i+(step-bw)/2,y=Yb(data[i]);bars+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+(H-pb-y).toFixed(1)+'" rx="1.5" style="fill:var(--blue);opacity:.85"></rect>';}
      var yl='';[0,mx/2,mx].forEach(function(v){yl+='<line x1="'+pl+'" y1="'+Yb(v).toFixed(1)+'" x2="'+(W-pr)+'" y2="'+Yb(v).toFixed(1)+'" style="stroke:var(--line);stroke-width:1"></line><text x="2" y="'+(Yb(v)+4).toFixed(1)+'" style="fill:var(--ink-mute);font-size:11px">'+v+'</text>';});
      var xl='';for(var i=0;i<n;i++){xl+='<text x="'+(pl+step*i+step/2).toFixed(1)+'" y="'+(H-8)+'" text-anchor="middle" style="fill:var(--ink-mute);font-size:9px">'+(i<10?'0'+i:i)+'</text>';}
      return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="display:block;height:auto">'+yl+bars+xl+'</svg>';
    }
    function miniTemp(data){
      var W=280,H=92,pl=6,pr=8,pt=18,pb=12,n=data.length;
      var mn=Math.min.apply(null,data),mx=Math.max.apply(null,data),lo=mn-1,hi=mx+1;
      function X(i){return pl+(W-pl-pr)*i/(n-1);} function Y(v){return pt+(H-pt-pb)*(1-(v-lo)/((hi-lo)||1));}
      var pts=data.map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1);});
      var line='M'+pts.join(' L'), area=line+' L'+X(n-1).toFixed(1)+','+(H-pb)+' L'+X(0).toFixed(1)+','+(H-pb)+' Z';
      var pi=data.indexOf(mx);
      var peak='<circle cx="'+X(pi).toFixed(1)+'" cy="'+Y(mx).toFixed(1)+'" r="3" style="fill:var(--gold)"></circle><text x="'+X(pi).toFixed(1)+'" y="'+(Y(mx)-6).toFixed(1)+'" text-anchor="middle" style="fill:var(--ink-strong);font-size:11px;font-weight:800">'+mx+'°</text>';
      var lows='<text x="'+X(0).toFixed(1)+'" y="'+(H-2)+'" style="fill:var(--ink-mute);font-size:9px">00:00</text><text x="'+X(n-1).toFixed(1)+'" y="'+(H-2)+'" text-anchor="end" style="fill:var(--ink-mute);font-size:9px">23:00</text>';
      return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="display:block;height:auto"><path d="'+area+'" style="fill:var(--gold);opacity:.14"></path><path d="'+line+'" style="fill:none;stroke:var(--gold);stroke-width:2.5;stroke-linejoin:round"></path>'+peak+lows+'</svg>';
    }
    var tEl=document.getElementById('wxTemp'), pEl=document.getElementById('wxPrecip'), mEl=document.getElementById('wxTempMini');
    if(tEl) tEl.innerHTML=lineChart(temp);
    if(pEl) pEl.innerHTML=barChart(precip);
    if(mEl) mEl.innerHTML=miniTemp(temp);

    var DAYS=(__wx.days||[]);
    var sel=0, daysEl=document.getElementById('fcDays'), detEl=document.getElementById('fcDetail');
    function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
    function stat(l,v){return '<div class="fcd-stat"><div class="l">'+l+'</div><div class="v">'+esc(v)+'</div></div>';}
    function renderDays(){ if(!daysEl) return; daysEl.innerHTML=DAYS.map(function(D,i){return '<button class="fc-day'+(D.warn?' warn':'')+(i===sel?' sel':'')+'" data-i="'+i+'"><div class="d">'+esc(D.d)+'</div><div class="ic">'+D.ic+'</div><div class="hi">'+D.hi+'°</div><div class="lo">'+D.lo+'°</div><div class="pr">'+esc(D.tag)+'</div></button>';}).join(''); }
    function renderDetail(){ if(!detEl) return; var D=DAYS[sel]; detEl.innerHTML='<div class="fcd-head">'+esc(D.d+' · '+D.cond)+'</div><div class="fcd-grid">'+stat('High / Low',D.hi+'° / '+D.lo+'°')+stat('Feels like',D.feels+'°')+stat('Precip',D.pc+'% · '+D.mm+' mm')+stat('Wind',D.wind+' mph')+stat('Gusts',D.gust+' mph')+stat('Humidity',D.hum+'%')+stat('UV index',String(D.uv))+stat('Sunrise',D.sr)+stat('Sunset',D.ss)+'</div><div class="fcd-sum">'+esc(D.sum)+'</div>'; }
    if(daysEl){ daysEl.addEventListener('click',function(e){var b=e.target.closest('.fc-day');if(!b)return;sel=+b.getAttribute('data-i');renderDays();renderDetail();}); renderDays(); renderDetail(); }
  })();

  function show(id){
    if(id==='stocks') initStocks();
    if(id==='forecast') initForecastRadar();
    panels.forEach(function(p){ p.classList.toggle('active', p.id===id); });
    navlinks.forEach(function(t){ t.classList.toggle('active', t.dataset.target===id); });
    document.querySelectorAll('.tbtab').forEach(function(t){ t.classList.toggle('active', t.dataset.target===id); });
    var cur = document.querySelector('.mlink[data-target="'+id+'"]');
    if(cur && topbarTitle){ topbarTitle.textContent = cur.textContent.replace(/^[★❔]\s*/,'').trim(); }
    reflow(document.getElementById(id));
    window.scrollTo({top:0, behavior:'instant' in window ? 'instant' : 'auto'});
    if(document.documentElement.classList.contains('focus')){ __focusPaint(); __focusArrows(); }
  }
  navlinks.forEach(function(t){ t.addEventListener('click', function(){ show(t.dataset.target); closeDrawer(); }); });
  document.querySelectorAll('.tbtab').forEach(function(t){ t.addEventListener('click', function(){ show(t.dataset.target); }); });
  document.querySelectorAll('.ov-card, .ov-hero').forEach(function(c){
    if(c.dataset.target){ c.style.cursor='pointer'; c.addEventListener('click', function(){ show(c.dataset.target); }); }
  });

  // Burger drawer + collapsible groups
  var drawer=document.getElementById('drawer'), backdrop=document.getElementById('drawerBackdrop'),
      burger=document.getElementById('burger'), dclose=document.getElementById('drawerClose');
  function openDrawer(){ if(!drawer) return; drawer.classList.add('open'); drawer.setAttribute('aria-hidden','false');
    if(backdrop){ backdrop.hidden=false; requestAnimationFrame(function(){ backdrop.classList.add('show'); }); }
    if(burger) burger.setAttribute('aria-expanded','true'); }
  function closeDrawer(){ if(!drawer) return; drawer.classList.remove('open'); drawer.setAttribute('aria-hidden','true');
    if(backdrop){ backdrop.classList.remove('show'); setTimeout(function(){ backdrop.hidden=true; },260); }
    if(burger) burger.setAttribute('aria-expanded','false'); }
  if(burger) burger.addEventListener('click', openDrawer);
  if(dclose) dclose.addEventListener('click', closeDrawer);
  if(backdrop) backdrop.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape' && drawer && drawer.classList.contains('open')) closeDrawer(); });
  document.querySelectorAll('.mgroup-head').forEach(function(h){
    h.addEventListener('click', function(){ var g=h.closest('.mgroup'); if(!g) return;
      var c=g.classList.toggle('collapsed'); h.setAttribute('aria-expanded', c?'false':'true'); });
  });

  // Archive & search (reads embedded JSON; today's items open their panel, older ones open a summary modal)
  (function(){
    var dataEl=document.getElementById('archiveData'); if(!dataEl) return;
    var ITEMS=[]; try{ ITEMS=JSON.parse(dataEl.textContent)||[]; }catch(e){ ITEMS=[]; }
    var input=document.getElementById('archSearch'), listEl=document.getElementById('archList'),
        countEl=document.getElementById('archCount'), fwrap=document.getElementById('archFilters'),
        mback=document.getElementById('amBack'), modal=document.getElementById('amModal');
    if(!listEl) return;
    var BC={politics:'b-politics',conflict:'b-conflict',business:'b-business',markets:'b-markets',health:'b-health',science:'b-science',technology:'b-tech',climate:'b-climate',sport:'b-sport'};
    var activeCat='All';
    function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
    function hl(t,q){ t=String(t); if(!q) return esc(t); var i=t.toLowerCase().indexOf(q); if(i<0) return esc(t); return esc(t.slice(0,i))+'<mark>'+esc(t.slice(i,i+q.length))+'</mark>'+esc(t.slice(i+q.length)); }
    function bc(cat){ return BC[String(cat||'').toLowerCase()]||'b-markets'; }
    function catKey(cat){ return 'cat-'+String(cat||'markets').toLowerCase(); }
    var EMO={politics:'🏛',conflict:'⚔',business:'📈',markets:'💹',health:'🧬',science:'🔬',technology:'💻',climate:'🌡',sport:'🏆'};
    function emo(cat){ return EMO[String(cat||'').toLowerCase()]||'📰'; }
    function imgFor(it){
      var t=((it.title||'')+' '+(it.summary||'')).toLowerCase();
      if(/iran|hormuz/.test(t)) return 'Strait_of_Hormuz_(MODIS_2020-12-04).jpg';
      if(/ebola/.test(t)) return 'Ebola_virus_virion.jpg';
      if(/lebanon/.test(t)) return 'Lebanon-CIA_WFB_Map.png';
      if(/ukraine|kyiv|moscow refinery|lavra/.test(t)) return 'Ukraine-CIA_WFB_Map.png';
      if(/san andreas|california fault/.test(t)) return 'San_Andreas_Fault_Aerial_View.gif';
      if(/burnham|makerfield|starmer/.test(t)) return 'United_Kingdom-CIA_WFB_Map.png';
      if(String(it.cat||'').toLowerCase()==='markets' || /\bfed\b|warsh/.test(t)) return 'Marriner_S._Eccles_Federal_Reserve_Board_Building.jpg';
      return null;
    }
    function render(){
      var raw=(input&&input.value||'').trim(), q=raw.toLowerCase();
      var res=ITEMS.filter(function(it){
        if(activeCat!=='All' && String(it.cat||'').toLowerCase()!==activeCat.toLowerCase()) return false;
        if(!q) return true;
        return ((it.title||'')+' '+(it.summary||'')+' '+(it.cat||'')+' '+(it.date||'')+' '+(it.edition||'')).toLowerCase().indexOf(q)>=0;
      });
      if(countEl) countEl.textContent=res.length+' article'+(res.length!==1?'s':'')+(raw?(' matching "'+raw+'"'):'')+(activeCat!=='All'?(' · '+activeCat):'');
      if(!res.length){ listEl.innerHTML='<div class="arch-empty">No articles match — try another term or category.</div>'; return; }
      listEl.innerHTML=res.map(function(it){
        var im=imgFor(it);
        var thumb='<div class="arch-thumb '+catKey(it.cat)+'"><span class="ov-emoji">'+emo(it.cat)+'</span>'+(im?'<img src="https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURI(im)+'?width=220" alt="" loading="lazy" onerror="this.style.display=\'none\'">':'')+'</div>';
        return '<button class="arch-item" data-i="'+ITEMS.indexOf(it)+'">'+thumb+'<div class="arch-body"><div class="arch-mrow"><span class="arch-date">'+esc(it.date)+'</span><span class="badge '+bc(it.cat)+'">'+esc(it.cat)+'</span></div><h4>'+hl(it.title,q)+'</h4><p>'+hl(it.summary,q)+'</p></div></button>';
      }).join('');
    }
    function openModal(it){
      if(!modal) return;
      modal.querySelector('.am-meta').textContent=(it.date||'')+'  ·  '+(it.cat||'');
      modal.querySelector('h3').textContent=it.title||'';
      modal.querySelector('.am-body').textContent=it.summary||'';
      modal.querySelector('.am-note').textContent='From the '+(it.edition||it.date||'')+' edition. Archived stories show their summary here; today’s stories open in full.';
      if(mback) mback.classList.add('show'); modal.classList.add('show');
    }
    function closeModal(){ if(modal) modal.classList.remove('show'); if(mback) mback.classList.remove('show'); }
    listEl.addEventListener('click', function(e){
      var b=e.target.closest('.arch-item'); if(!b) return;
      var it=ITEMS[+b.getAttribute('data-i')]; if(!it) return;
      if(it.panel && document.getElementById(it.panel)){ show(it.panel); if(typeof closeDrawer==='function') closeDrawer(); }
      else { openModal(it); }
    });
    if(input) input.addEventListener('input', render);
    if(fwrap) fwrap.addEventListener('click', function(e){ var c=e.target.closest('.afchip'); if(!c) return; activeCat=c.getAttribute('data-cat'); fwrap.querySelectorAll('.afchip').forEach(function(x){ x.classList.toggle('active', x===c); }); render(); });
    if(mback) mback.addEventListener('click', closeModal);
    if(modal){ var x=modal.querySelector('.am-close'); if(x) x.addEventListener('click', closeModal); }
    document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });
    render();
  })();

  // Interactive timelines: expand on tap; auto-compute the gap + spacing between dated events
  function __tlGap(days){
    if(days<=0) return 'same day';
    if(days===1) return '1 day later';
    if(days<14) return days+' days later';
    if(days<56){ var w=Math.round(days/7); return w+' week'+(w>1?'s':'')+' later'; }
    var m=Math.round(days/30.4); return m+' month'+(m>1?'s':'')+' later';
  }
  document.querySelectorAll('.timeline .tl-list').forEach(function(list){
    var evs=Array.prototype.slice.call(list.querySelectorAll('.tl-ev'));
    evs.forEach(function(ev){
      var row=ev.querySelector('.tl-row');
      if(row) row.addEventListener('click', function(){ ev.classList.toggle('open'); });
    });
    for(var i=1;i<evs.length;i++){
      var d0=new Date(evs[i-1].getAttribute('data-date')+'T00:00:00');
      var d1=new Date(evs[i].getAttribute('data-date')+'T00:00:00');
      var days=Math.round((d1-d0)/86400000);
      if(isNaN(days)) continue;
      var g=document.createElement('div'); g.className='tl-gap'; g.textContent='↓ '+__tlGap(days);
      g.style.minHeight=Math.max(20, Math.min(74, 16+days*1.0))+'px';
      list.insertBefore(g, evs[i]);
    }
  });
  window.addEventListener('resize', function(){ reflow(document.querySelector('.panel.active')); });

  // Key Facts -> jump to the related article passage (auto-matched by keywords/numbers)
  var __KFSTOP={with:1,that:1,this:1,from:1,have:1,been:1,will:1,into:1,over:1,than:1,then:1,they:1,their:1,them:1,were:1,what:1,when:1,which:1,while:1,also:1,more:1,most:1,some:1,such:1,only:1,after:1,before:1,about:1,would:1,could:1,since:1,still:1,each:1,both:1,says:1,said:1};
  function __kfTokens(t){
    t=t.toLowerCase();
    var nums=t.match(/\d[\d.,:%–\/-]*/g)||[];
    var words=(t.match(/[a-z]{4,}/g)||[]).filter(function(w){return !__KFSTOP[w];});
    return {nums:nums,words:words};
  }
  function __kfFlash(el){ el.classList.add('flash'); setTimeout(function(){ el.classList.remove('flash'); },1600); }
  function __kfBest(panel, li){
    var arts=panel.querySelectorAll('.article > p'); var tk=__kfTokens(li.textContent);
    var best=null,bestScore=0;
    arts.forEach(function(p){
      var pt=p.textContent.toLowerCase(), sc=0;
      tk.nums.forEach(function(n){ if(n.length>=2 && pt.indexOf(n)>-1) sc+=3; });
      tk.words.forEach(function(w){ if(pt.indexOf(w)>-1) sc+=1; });
      if(sc>bestScore){ bestScore=sc; best=p; }
    });
    return bestScore>0?best:null;
  }
  panels.forEach(function(panel){
    panel.querySelectorAll('.keyfacts li').forEach(function(li){
      li.style.cursor='pointer'; li.title='Jump to this in the article';
      li.addEventListener('click', function(){
        var p=__kfBest(panel, li);
        if(p){ p.scrollIntoView({behavior:'smooth', block:'center'}); __kfFlash(p); }
      });
    });
  });

  // Focus / reading mode: scroll "spotlight" — only the paragraph near screen-centre is visible
  var __focusBtn=null, __raf=null, __fnav=null;
  var __FCENTER=0.46; // fraction of viewport height the spotlight sits at
  function __focusPaint(){
    if(!document.documentElement.classList.contains('focus')) return;
    var panel=document.querySelector('.panel.active'); if(!panel) return;
    var els=panel.querySelectorAll('.article > p, .article > .pullquote, .article > .framing');
    if(panel.classList.contains('ffull')){ els.forEach(function(el){ el.style.opacity='1'; el.style.transform='none'; }); return; }
    var vh=window.innerHeight||800, center=vh*0.46, fade=vh*0.40;
    els.forEach(function(el){
      var r=el.getBoundingClientRect(); var c=r.top+r.height/2; var d=Math.abs(c-center);
      var o=1-Math.min(d/fade,1); o=o*o*(3-2*o);
      el.style.opacity=o.toFixed(3);
      var ty=(c>=center?1:-1)*(1-o)*16;
      el.style.transform='translateY('+ty.toFixed(1)+'px)';
    });
  }
  function __focusScroll(){ if(__raf) return; __raf=requestAnimationFrame(function(){ __raf=null; __focusPaint(); __focusArrows(); }); }
  function __focusClear(){ document.querySelectorAll('.article > p, .article > .pullquote, .article > .framing').forEach(function(el){ el.style.opacity=''; el.style.transform=''; }); document.querySelectorAll('.panel.ffull').forEach(function(p){ p.classList.remove('ffull'); }); }
  // Section navigation: the steps you can jump between, the current one, and the jump itself.
  function __focusSteps(){
    var panel=document.querySelector('.panel.active'); if(!panel) return [];
    return Array.prototype.slice.call(panel.querySelectorAll('.article > p, .article > .pullquote, .article > .framing, .article > .timeline'))
      .filter(function(el){ return el.offsetParent!==null; });
  }
  function __focusIndex(steps){
    var center=(window.innerHeight||800)*__FCENTER, best=0, bestd=Infinity;
    steps.forEach(function(el,i){ var r=el.getBoundingClientRect(); var d=Math.abs((r.top+r.height/2)-center); if(d<bestd){ bestd=d; best=i; } });
    return best;
  }
  function __focusGo(dir){
    if(!document.documentElement.classList.contains('focus')) return;
    var steps=__focusSteps(); if(!steps.length) return;
    var i=Math.max(0, Math.min(steps.length-1, __focusIndex(steps)+dir));
    var r=steps[i].getBoundingClientRect();
    var top=window.pageYOffset + r.top + r.height/2 - (window.innerHeight||800)*__FCENTER;
    window.scrollTo({top:Math.max(0,Math.round(top)), behavior:'smooth'});
  }
  function __focusArrows(){
    if(!__fnav) return;
    var steps=__focusSteps(), i=steps.length?__focusIndex(steps):0;
    __fnav.querySelector('.fnav-up').disabled=(i<=0);
    __fnav.querySelector('.fnav-down').disabled=(i>=steps.length-1);
  }
  function setFocus(on){
    document.documentElement.classList.toggle('focus', on);
    if(__focusBtn){ __focusBtn.classList.toggle('active', on); __focusBtn.innerHTML = on ? '◉ Focus on' : '◎ Focus'; }
    document.querySelectorAll('[data-focus-toggle]').forEach(function(b){
      b.classList.toggle('active', on); b.setAttribute('aria-pressed', on?'true':'false');
      b.innerHTML = on ? '◉ Focus mode on' : '◎ Focus mode';
    });
    try{ localStorage.setItem('briefing-focus', on?'1':'0'); }catch(e){}
    if(on){ window.addEventListener('scroll', __focusScroll, {passive:true}); window.addEventListener('resize', __focusScroll); __focusPaint(); __focusArrows(); }
    else { window.removeEventListener('scroll', __focusScroll); window.removeEventListener('resize', __focusScroll); __focusClear(); }
  }
  (function(){
    __focusBtn=document.getElementById('focusToggle');
    if(__focusBtn){ __focusBtn.addEventListener('click', function(){ setFocus(!document.documentElement.classList.contains('focus')); }); }
    // per-article focus toggles (one at the top of every story)
    document.querySelectorAll('[data-focus-toggle]').forEach(function(b){
      b.addEventListener('click', function(){ setFocus(!document.documentElement.classList.contains('focus')); });
    });
    // left-edge section navigator (shown only in focus mode, via CSS)
    __fnav=document.createElement('div'); __fnav.className='fnav'; __fnav.setAttribute('aria-label','Section navigation');
    __fnav.innerHTML='<button type="button" class="fnav-up" aria-label="Previous section" title="Previous section">↑</button><button type="button" class="fnav-down" aria-label="Next section" title="Next section">↓</button>';
    __fnav.querySelector('.fnav-up').addEventListener('click', function(){ __focusGo(-1); });
    __fnav.querySelector('.fnav-down').addEventListener('click', function(){ __focusGo(1); });
    document.body.appendChild(__fnav);
    document.querySelectorAll('.panel .article').forEach(function(art){
      var b=document.createElement('button'); b.type='button'; b.className='fullbtn'; b.innerHTML='Show full article ▾';
      b.addEventListener('click', function(){ var pn=art.closest('.panel'); if(pn) pn.classList.add('ffull'); art.querySelectorAll(':scope > p, :scope > .pullquote, :scope > .framing').forEach(function(el){ el.style.opacity='1'; el.style.transform='none'; }); });
      art.appendChild(b);
    });
    setFocus(false); // focus mode always starts off
  })();

  function __setNavH(){ var n=document.querySelector('.topbar'); if(n) document.documentElement.style.setProperty('--navh', n.offsetHeight+'px'); }
  __setNavH(); window.addEventListener('resize', __setNavH);

  // Theme switcher: dark / light
  var themer = document.getElementById('themer');
  function setTheme(t){
    document.documentElement.setAttribute('data-theme', t);
    if(themer){ themer.querySelectorAll('button').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-theme-set') === t); }); }
    try{ localStorage.setItem('briefing-theme', t); }catch(e){}
    reflow(document.querySelector('.panel.active'));
  }
  if(themer){
    themer.addEventListener('click', function(e){
      var b = e.target.closest('button'); if(!b) return;
      setTheme(b.getAttribute('data-theme-set'));
    });
  }
  var saved = 'dark';
  try{ var s = localStorage.getItem('briefing-theme'); if(s === 'light' || s === 'dark'){ saved = s; } }catch(e){}
  setTheme(saved);

  // Settings popover (cog to the right of the weather)
  (function(){
    var cog=document.getElementById('settingsCog'), pop=document.getElementById('settingsPop');
    if(!cog||!pop) return;
    function open(o){ pop.hidden=!o; cog.classList.toggle('open', o); cog.setAttribute('aria-expanded', o?'true':'false'); }
    cog.addEventListener('click', function(e){ e.stopPropagation(); open(pop.hidden); });
    pop.addEventListener('click', function(e){ e.stopPropagation(); });
    document.addEventListener('click', function(){ if(!pop.hidden) open(false); });
    document.addEventListener('keydown', function(e){ if(e.key==='Escape' && !pop.hidden) open(false); });
  })();
})();

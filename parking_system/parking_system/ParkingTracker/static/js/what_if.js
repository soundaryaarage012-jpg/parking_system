(function(){
  const slots = window.INIT_SIM_SLOTS || [];
  const simTwin = document.getElementById('simTwin');
  const ctx = document.getElementById('simTimeline').getContext('2d');
  let chart = null;

  function renderSimMap(simulated_slots){
    simTwin.innerHTML = '';
    simulated_slots.forEach(s=>{
      const el = document.createElement('div');
      el.className = 'sim-slot ' + (s.status || 'available');
      el.innerHTML = `<div class="slot-number">${s.slot_number}</div><div class="slot-meta">${s.block_name}</div><div class="sim-overlay">${s.status||'available'}</div>`;
      simTwin.appendChild(el);
    });
  }

  function renderMetrics(metrics){
    document.getElementById('sim_congestion').innerText = metrics.expected_congestion;
    document.getElementById('sim_available').innerText = metrics.available_slots;
    document.getElementById('sim_util').innerText = metrics.utilization_percent;
  }

  function renderTimeline(timeline){
    const labels = timeline.map(t=>t.minute + 'm');
    const data = timeline.map(t=>t.occupied);
    if(chart) chart.destroy();
    chart = new Chart(ctx, {type:'line',data:{labels:labels,datasets:[{label:'Occupied',data:data,borderColor:'#ff7b7b',backgroundColor:'rgba(255,123,123,0.12)',fill:true}]},options:{responsive:true,animation:{duration:800}}});
  }

  async function runScenario(scenario, params){
    const res = await fetch('/api/what-if/simulate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario,params})});
    const payload = await res.json();
    if(payload.error){ alert('Simulation error: '+payload.error); return; }
    renderMetrics(payload.metrics);
    renderTimeline(payload.timeline);
    renderSimMap(payload.simulated_slots);
  }

  // hook preset buttons
  document.querySelectorAll('.list-group-item-action').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const scenario = btn.getAttribute('data-scenario');
      const params = JSON.parse(btn.getAttribute('data-params') || '{}');
      runScenario(scenario, params);
    });
  });

  document.getElementById('runCustom').addEventListener('click', ()=>{
    const extra = parseInt(document.getElementById('custom_extra').value||'0');
    const ev = document.getElementById('custom_ev').value === 'true';
    runScenario('custom', {extra_arrivals:extra, ev_surge:ev});
  });

  // initial render with baseline
  renderSimMap(slots);
})();

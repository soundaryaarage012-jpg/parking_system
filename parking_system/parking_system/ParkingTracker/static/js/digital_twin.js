(function(){
  const container = document.getElementById('digitalTwin');
  if(!container) return;
  const SLOT_W = 120, SLOT_H = 70, GAP_X = 18, GAP_Y = 18;
  let slots = window.INIT_SLOTS || [];
  const socket = (window.io)? io() : null;
  let visionMode = false;
  let predictionMode = false;

  function groupBy(array, key){
    return array.reduce((acc,item)=>{(acc[item[key]]||(acc[item[key]]=[])).push(item);return acc},{})
  }

  function render(){
    container.innerHTML = '';
    const floors = groupBy(slots, 'floor');
    const floorNames = Object.keys(floors).sort();
    const width = container.clientWidth;
    const floorHeight = Math.floor(container.clientHeight / Math.max(1,floorNames.length));

    floorNames.forEach((floorName, fidx)=>{
      const blockGroups = groupBy(floors[floorName], 'block_name');
      const blocks = Object.keys(blockGroups).sort();
      const startY = fidx * floorHeight + 30;

      // Floor title
      const title = document.createElement('div');
      title.className = 'digital-floor-title';
      title.style.top = (startY - 26) + 'px';
      title.innerText = floorName;
      container.appendChild(title);

      blocks.forEach((blockName, bidx)=>{
        const blockSlots = blockGroups[blockName];
        const cols = Math.max(3, Math.floor(width / (SLOT_W + GAP_X)));
        blockSlots.forEach((slot, idx)=>{
          const row = Math.floor(idx/cols);
          const col = idx % cols;
          const x = 18 + col * (SLOT_W + GAP_X);
          const y = startY + bidx*120 + row * (SLOT_H + GAP_Y);

          const el = document.createElement('div');
          el.className = 'dt-slot ' + (slot.status || 'available');
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          el.setAttribute('data-slot-id', slot.id);
          el.innerHTML = `<div class="slot-number">${slot.slot_number}</div><div class="slot-meta">${slot.block_name}</div>`;

          // QR small overlay
          const qr = document.createElement('img');
          qr.className = 'dt-qr';
          if(slot.qr_path){ qr.src = slot.qr_path; qr.style.width='34px'; qr.style.height='34px'; }
          el.appendChild(qr);

          // Car element
          const car = document.createElement('div');
          car.className = 'dt-car';
          car.style.left = (x + SLOT_W/2 - 23) + 'px';
          car.style.top = (y + SLOT_H/2 - 13) + 'px';
          car.style.opacity = slot.status === 'occupied' ? '1' : '0';
          car.setAttribute('data-car-for', slot.id);
          container.appendChild(car);
          container.appendChild(el);

          // hover and click
          el.addEventListener('mouseenter', ()=>{
            el.classList.add('hover');
            showInspector(slot);
          });
          el.addEventListener('mouseleave', ()=>{
            el.classList.remove('hover');
          });
          el.addEventListener('click', ()=>{
            focusSlot(slot.id);
            showInspector(slot);
          });

          if (visionMode && slot.status === 'occupied') {
            const visionMarker = document.createElement('div');
            visionMarker.className = 'vision-marker';
            el.appendChild(visionMarker);
          }
        });
      });
    });

    if (predictionMode) {
      renderPredictionOverlay();
    }
  }

  function renderPredictionOverlay(){
    const overlay = document.createElement('div');
    overlay.className = 'prediction-overlay';
    overlay.innerHTML = '<span>Next 15 min forecast</span><strong>Zone C filling in ~12 min</strong>';
    container.appendChild(overlay);
  }

  function updateSlots(newSlots){
    const map = {};
    slots.forEach(s=>map[s.id]=s);
    newSlots.forEach(ns=>{map[ns.id]=ns});
    slots = Object.values(map);

    newSlots.forEach(ns=>{
      const el = container.querySelector(`.dt-slot[data-slot-id='${ns.id}']`);
      const car = container.querySelector(`.dt-car[data-car-for='${ns.id}']`);
      if(el){
        el.classList.remove('available','occupied','reserved');
        el.classList.add(ns.status || 'available');
        if (visionMode && ns.status === 'occupied') {
          if (!el.querySelector('.vision-marker')) {
            const visionMarker = document.createElement('div');
            visionMarker.className = 'vision-marker';
            el.appendChild(visionMarker);
          }
        } else {
          el.querySelector('.vision-marker')?.remove();
        }
        const qr = el.querySelector('.dt-qr');
        if(qr && ns.qr_path) qr.src = ns.qr_path;
      }
      if(car){
        if(ns.status === 'occupied'){
          if(car.style.opacity === '0' || car.style.opacity === ''){
            car.style.opacity = '0';
            car.style.transform = `translateX(-200px)`;
            requestAnimationFrame(()=>{
              car.style.transition = 'transform 1200ms cubic-bezier(.2,.8,.2,1),opacity 600ms';
              const rect = el.getBoundingClientRect();
              const parentRect = container.getBoundingClientRect();
              const targetX = rect.left - parentRect.left + (rect.width/2 - car.offsetWidth/2);
              const targetY = rect.top - parentRect.top + (rect.height/2 - car.offsetHeight/2);
              car.style.transform = `translate(${targetX}px, ${targetY}px)`;
              car.style.opacity = '1';
            });
          }
        } else {
          if(car.style.opacity === '1'){
            car.style.transition = 'transform 900ms ease-in,opacity 600ms';
            car.style.transform = `translateX(${container.clientWidth + 120}px)`;
            car.style.opacity = '0';
            setTimeout(()=>{}, 1000);
          }
        }
      }
    });
  }

  function showInspector(slot){
    const inspector = document.getElementById('slotInspector');
    if(!inspector) return;
    inspector.style.display = 'block';
    document.getElementById('inspector-slot').innerText = slot.slot_number;
    document.getElementById('inspector-status').innerText = 'Status: ' + (slot.status||'available');
    document.getElementById('inspector-vehicle').innerText = slot.occupied_by? ('Vehicle: ' + (slot.occupied_by)) : '';
    // reservations
    const res = window.LIVE_RESERVATIONS && window.LIVE_RESERVATIONS.find(r=>r.slot_id === slot.id);
    const resEl = document.getElementById('inspector-reservation');
    if(res){
      const expiry = new Date(res.expiry_time);
      const now = new Date();
      const mins = Math.max(0, Math.round((expiry - now)/60000));
      resEl.innerText = 'Reservation: ' + res.slot_number + ' • ' + mins + 'm remaining';
    } else {
      resEl.innerText = '';
    }
    const timeEl = document.getElementById('inspector-time');
    // find active history
    const hist = window.LIVE_RECENT && window.LIVE_RECENT.find(h=>h.slot_id === slot.id && !h.exit_time);
    if(hist){
      timeEl.innerText = 'Arrived: ' + new Date(hist.entry_time).toLocaleTimeString();
    } else {
      timeEl.innerText = '';
    }
    const qrBox = document.getElementById('inspector-qr');
    qrBox.innerHTML = '';
    if(slot.qr_path){
      const img = document.createElement('img');
      img.src = slot.qr_path;
      img.style.maxWidth = '100%';
      img.style.maxHeight = '100%';
      qrBox.appendChild(img);
    }
  }

  function focusSlot(id){
    const el = container.querySelector(`.dt-slot[data-slot-id='${id}']`);
    if(!el) return;
    el.scrollIntoView({behavior:'smooth', block:'center', inline:'center'});
    el.classList.add('focus');
    setTimeout(()=>el.classList.remove('focus'),1200);
  }

  // wire controls
  const focusAllBtn = document.getElementById('focusAll');
  const focusAvailableBtn = document.getElementById('focusAvailable');
  const focusOccupiedBtn = document.getElementById('focusOccupied');
  const focusReservedBtn = document.getElementById('focusReserved');
  const visionToggleBtn = document.getElementById('visionModeToggle');
  const predictionToggleBtn = document.getElementById('predictionToggle');

  focusAllBtn?.addEventListener('click', ()=>{container.scrollTo({top:0,left:0,behavior:'smooth'}); container.querySelectorAll('.dt-slot').forEach(el=>{el.style.opacity='1';});});
  focusAvailableBtn?.addEventListener('click', ()=>{filterSlots('available');});
  focusOccupiedBtn?.addEventListener('click', ()=>{filterSlots('occupied');});
  focusReservedBtn?.addEventListener('click', ()=>{filterSlots('reserved');});

  visionToggleBtn?.addEventListener('click', ()=>{
    visionMode = !visionMode;
    visionToggleBtn.classList.toggle('active', visionMode);
    render();
  });

  predictionToggleBtn?.addEventListener('click', ()=>{
    predictionMode = !predictionMode;
    predictionToggleBtn.classList.toggle('active', predictionMode);
    render();
  });

  function filterSlots(status){
    container.querySelectorAll('.dt-slot').forEach(el=>{
      const isMatch = el.classList.contains(status);
      el.style.opacity = isMatch ? '1' : '0.15';
    });
  }

  // socket listeners
  if(socket){
    socket.on('connect', ()=>{
      console.log('Connected to socket');
    });
    socket.on('parking_update', (data)=>{
      if(data && data.slots) updateSlots(data.slots);
      if(data && data.reservations) window.LIVE_RESERVATIONS = data.reservations;
    });
    socket.on('parking_state', (data)=>{
      if(data && data.slots) updateSlots(data.slots);
      if(data && data.recent_movements) window.LIVE_RECENT = data.recent_movements;
      if(data && data.reservations) window.LIVE_RESERVATIONS = data.reservations;
    });
  }

  // initial render
  render();

  // resize handler
  window.addEventListener('resize', ()=>{render();});

})();
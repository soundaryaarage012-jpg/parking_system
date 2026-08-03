(function(){
  const payload = window.REPLAY_PAYLOAD || {};
  const map = document.getElementById('replayMap');
  const progress = document.getElementById('replayProgress');
  const eventLog = document.getElementById('eventLog');
  const playBtn = document.getElementById('playBtn');
  const pauseBtn = document.getElementById('pauseBtn');
  const ffBtn = document.getElementById('ffBtn');
  const slowBtn = document.getElementById('slowBtn');

  let index=0;
  let speed=1;
  let playing=false;
  let timer=null;
  const events = payload.events || [];
  const slots = payload.slots || [];

  function createMap(){
    map.innerHTML = '';
    slots.forEach((slot,i)=>{
      const el=document.createElement('div');
      el.id='slot-'+slot.id;
      el.className='replay-slot '+(slot.status||'available');
      const row=Math.floor(i/4);
      const col=i%4;
      el.style.left=(col*120+16)+'px';
      el.style.top=(row*90+16)+'px';
      el.innerHTML=`<strong>${slot.slot_number}</strong><span>${slot.block_name}</span>`;
      map.appendChild(el);
    });
  }

  function renderEventList(){
    eventLog.innerHTML='';
    events.forEach((event,i)=>{
      const item=document.createElement('button');
      item.type='button';
      item.className='list-group-item list-group-item-action';
      item.innerText=`${event.time} • ${event.description}`;
      item.addEventListener('click', ()=>{ index=i; updateReplay(); });
      eventLog.appendChild(item);
    });
  }

  function updateReplay(){
    if(index<0) index=0;
    if(index>=events.length) index=events.length-1;
    const event=events[index];
    if(!event) return;
    const state = {};
    for(let i=0;i<=index;i++){
      const e=events[i];
      if(e.type==='entry') state[e.slot_id]='occupied';
      if(e.type==='exit') state[e.slot_id]='available';
      if(e.type==='reservation') state[e.slot_id]='reserved';
    }
    slots.forEach(slot=>{
      const el=document.getElementById('slot-'+slot.id);
      if(!el) return;
      const status=state[slot.id]||slot.status||'available';
      el.className='replay-slot '+status;
      if(status==='occupied') el.style.transform='scale(1.05)'; else el.style.transform='scale(1)';
    });
    progress.style.width=((index+1)/events.length*100)+'%';
    Array.from(eventLog.children).forEach((item,i)=>{
      item.classList.toggle('active', i===index);
    });
  }

  function schedule(){
    if(!playing) return;
    timer = setTimeout(()=>{
      index += speed;
      if(index >= events.length){ index = events.length-1; playing=false; return; }
      updateReplay();
      schedule();
    }, 800 / Math.abs(speed));
  }

  playBtn.addEventListener('click', ()=>{ if(!playing){ playing=true; schedule(); }});
  pauseBtn.addEventListener('click', ()=>{ playing=false; clearTimeout(timer); });
  ffBtn.addEventListener('click', ()=>{ speed = Math.min(4, speed+1); });
  slowBtn.addEventListener('click', ()=>{ speed = Math.max(1, speed-1); });

  createMap();
  renderEventList();
  updateReplay();
})();
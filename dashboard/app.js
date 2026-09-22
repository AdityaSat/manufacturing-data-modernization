import {evaluateBusiness} from './business.js';
const $=id=>document.getElementById(id), pct=x=>(x*100).toFixed(1)+'%', money=x=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(x), short=x=>money(x/1000)+'k';
const card=(label,value,note)=>`<div class="kpi"><span class="label">${label}</span><strong>${value}</strong><small>${note}</small></div>`;
let data,page=0;
const pageSize=15;
function activate(view){
  if(!['overview','model','business','rollout'].includes(view))view='overview';
  document.querySelectorAll('.view').forEach(s=>s.hidden=s.id!==view);
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
}
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>{location.hash=b.dataset.view;activate(b.dataset.view);}));
window.addEventListener('hashchange',()=>activate(location.hash.slice(1)));activate(location.hash.slice(1)||'overview');
function filtered(){return data.records.filter(r=>($('quality').value==='all'||r.product_type===$('quality').value)&&(!$('alerts-only').checked||r.model_alert)&&(! $('search-id').value || String(r.observation_id).includes($('search-id').value.trim())));}
function health(){
  const rows=filtered(), alerts=rows.filter(r=>r.model_alert), actual=rows.filter(r=>r.machine_failure);
  $('health-kpis').innerHTML=card('Observations in view',rows.length.toLocaleString(),'Held-out source records')+card('Flagged for review',alerts.length.toLocaleString(),'Fixed validation threshold')+card('Labeled failures',actual.length.toLocaleString(),'Synthetic ground truth')+card('Alert precision',alerts.length?pct(alerts.filter(r=>r.machine_failure).length/alerts.length):'n/a','Actual failures among alerts');
  $('priority-list').innerHTML=['L','M','H'].map(t=>`<div class="priority"><span>Quality type ${t}</span><strong>${alerts.filter(r=>r.product_type===t).length}</strong></div>`).join('');
  scatter(rows);
  const pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages-1);
  $('register').innerHTML=rows.slice(page*pageSize,(page+1)*pageSize).map(r=>`<tr><td>#${r.observation_id}</td><td>${r.product_type}</td><td>${r.rotational_speed_rpm.toLocaleString()}</td><td>${r.torque_nm.toFixed(1)}</td><td>${r.tool_wear_min}</td><td class="score">${r.model_score.toFixed(3)}</td><td><span class="pill ${r.model_alert?'alert':''}">${r.model_alert?'Inspect':'Below threshold'}</span></td><td>${r.machine_failure?'Failure':'No failure'}</td></tr>`).join('')||'<tr><td colspan="8" class="empty">No matching observations. Adjust the filters.</td></tr>';
  $('register-count').textContent=rows.length.toLocaleString()+' matching rows';$('page-label').textContent=`Page ${page+1} of ${pages}`;$('prev').disabled=page===0;$('next').disabled=page===pages-1;
}
function scatter(rows){
  const w=700,h=310,left=58,top=14,right=18,bottom=44,x=v=>left+(v-1100)/1900*(w-left-right),y=v=>h-bottom-v/85*(h-top-bottom);
  let s=`<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
  for(let n=0;n<=80;n+=20)s+=`<line x1="${left}" x2="${w-right}" y1="${y(n)}" y2="${y(n)}" stroke="#e7ece3"/><text x="${left-12}" y="${y(n)+4}" text-anchor="end" fill="#73836c" font-size="10">${n}</text>`;
  for(let n=1200;n<=3000;n+=300)s+=`<text x="${x(n)}" y="${h-23}" text-anchor="middle" fill="#73836c" font-size="10">${n}</text>`;
  for(const r of [...rows].sort((a,b)=>a.model_alert-b.model_alert))s+=`<circle cx="${x(r.rotational_speed_rpm)}" cy="${y(r.torque_nm)}" r="${r.model_alert?4:2.3}" fill="${r.model_alert?'#d97c35':'#315d50'}" opacity="${r.model_alert?.85:.27}"><title>Observation ${r.observation_id}: ${r.rotational_speed_rpm} rpm, ${r.torque_nm} Nm, score ${r.model_score.toFixed(3)}</title></circle>`;
  s+=`<text x="${w/2}" y="${h-2}" text-anchor="middle" fill="#64775d" font-size="11">Rotational speed (rpm)</text><text x="12" y="${h/2}" transform="rotate(-90 12 ${h/2})" text-anchor="middle" fill="#64775d" font-size="11">Torque (Nm)</text></svg>`;$('scatter').innerHTML=s;
}
function model(){const m=data.metrics,t=m.test.model;
  $('model-kpis').innerHTML=card('Holdout precision',pct(t.precision),'Validation-selected threshold')+card('Holdout recall',pct(t.recall),`${t.tp} of ${t.failures} failures detected`)+card('Average precision',t.average_precision.toFixed(3),'Full holdout score ranking')+card('False alarms',t.fp,`${t.rows.toLocaleString()} holdout observations`);
  $('model-comparison').innerHTML=[['Basic monitoring',m.test.monitoring],['Random forest',t]].map(([name,x])=>`<tr><td>${name}</td><td>${pct(x.precision)}</td><td>${pct(x.recall)}</td><td>${x.fp}</td><td>${x.fn}</td><td>${x.tp+x.fp}</td></tr>`).join('');
  $('split-list').innerHTML=Object.entries(m.split).map(([name,x])=>`<div class="split"><span>${name[0].toUpperCase()+name.slice(1)}<br><small>UDI ${x.udi_min}–${x.udi_max}</small></span><span>${x.rows.toLocaleString()} rows<br><small>${x.failures} failures</small></span></div>`).join('');
  $('quality-note').textContent=`Preserve original labels. Data checks found ${m.quality.label_mode_disagreements} rows where failure flags and the main target disagree. The report records them explicitly.`;
  $('threshold').value=m.threshold;explore();
}
function explore(){const threshold=+$('threshold').value;let tp=0,fp=0,fn=0;for(const r of data.records){const alert=r.model_score>=threshold;if(alert&&r.machine_failure)tp++;else if(alert)fp++;else if(r.machine_failure)fn++;}
  $('threshold-value').textContent=threshold.toFixed(2);$('threshold-warning').textContent=Math.abs(threshold-data.metrics.threshold)<.00001?'Original threshold selected on validation data.':'Exploratory test-set analysis. Changing this control does not replace the original reported result.';
  $('threshold-results').innerHTML=[['Precision',tp+fp?pct(tp/(tp+fp)):'n/a'],['Recall',pct(tp/(tp+fn))],['False alarms',fp],['Missed failures',fn]].map(([a,b])=>`<div>${a}<strong>${b}</strong></div>`).join('');
}
function business(){const a=structuredClone(data.assumptions);a.options.predictive.downtime_reduction=+$('reduction').value/100;a.loss_per_machine_hour=+$('loss').value;a.unplanned_downtime_rate=+$('downtime').value/100;
  const b=evaluateBusiness(a),m=b.options.monitoring,p=b.options.predictive;
  $('reduction-value').textContent=pct(a.options.predictive.downtime_reduction);$('loss-value').textContent=money(a.loss_per_machine_hour);$('downtime-value').textContent=pct(a.unplanned_downtime_rate);
  $('business-kpis').innerHTML=card('Predictive NPV',short(p.npv),'36 months, pre-tax')+card('NPV above monitoring',short(b.incremental_npv),'Incremental investment value')+card('Predictive payback',p.payback_months===null?'>36 mo':p.payback_months.toFixed(1)+' mo','Includes rollout ramp')+card('Reduction needed',pct(b.incremental_break_even_reduction),'Predictive NPV = monitoring NPV');
  const metrics=[['Implementation','implementation',money],['Annual operating cost','annual_opex',money],['Steady annual gross savings','annual_gross_savings',money],['Steady annual net benefit','steady_annual_net',money],['36-month NPV','npv',money],['36-month net cash','net_cash',money],['Payback','payback_months',x=>x===null?'Not within 36 months':x.toFixed(1)+' months']];
  $('business-comparison').innerHTML=metrics.map(([label,key,f])=>`<tr><td>${label}</td><td>${f(m[key])}</td><td>${f(p[key])}</td></tr>`).join('');
  $('business-decision').textContent=(p.npv>0&&b.incremental_npv>0?'Predictive maintenance has the higher modeled NPV. Validate its incremental savings before scaling.':m.npv>0?'Basic monitoring is the stronger investment under these assumptions.':'Neither option has a positive modeled NPV under these assumptions.')+` Annual downtime loss assumption: ${money(b.annual_downtime_cost)}.`;
  cashChart(m.cash_flows,p.cash_flows);
}
function cashChart(m,p){const w=720,h=315,l=68,r=20,t=18,bot=40;let min=Math.floor(Math.min(...m.map(x=>x.cumulative),...p.map(x=>x.cumulative))/50000)*50000,max=Math.ceil(Math.max(0,...m.map(x=>x.cumulative),...p.map(x=>x.cumulative))/50000)*50000;if(max===min)max=min+50000;const x=n=>l+n/36*(w-l-r),y=v=>h-bot-(v-min)/(max-min)*(h-t-bot);let s=`<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
  for(let i=0;i<=4;i++){const v=min+(max-min)*i/4;s+=`<line x1="${l}" x2="${w-r}" y1="${y(v)}" y2="${y(v)}" stroke="#e3e9df"/><text x="${l-10}" y="${y(v)+4}" text-anchor="end" font-size="10" fill="#64775d">${short(v)}</text>`;}
  s+=`<line x1="${l}" x2="${w-r}" y1="${y(0)}" y2="${y(0)}" stroke="#a8bba1" stroke-dasharray="4 4"/>`;
  for(const [rows,color] of [[m,'#315d50'],[p,'#d97c35']])s+=`<polyline points="${rows.map(d=>x(d.month)+','+y(d.cumulative)).join(' ')}" fill="none" stroke="${color}" stroke-width="3"/>`;
  for(let n=0;n<=36;n+=6)s+=`<text x="${x(n)}" y="${h-20}" text-anchor="middle" font-size="10" fill="#64775d">${n}</text>`;s+=`<text x="${w/2}" y="${h-1}" text-anchor="middle" font-size="11" fill="#64775d">Months after investment</text></svg>`;$('cash-chart').innerHTML=s;
}
async function init(){try{const embedded=$('project-data');if(embedded){data=JSON.parse(embedded.textContent);}else{const response=await fetch('data.json');if(!response.ok)throw new Error('Data file unavailable');data=await response.json();}health();model();business();}catch(error){$('load-error').hidden=false;$('load-error').textContent='Could not load project data. Start the dashboard with: python run.py dashboard. '+error.message;}}
['quality','alerts-only','search-id'].forEach(id=>$(id).addEventListener('input',()=>{page=0;health();}));$('prev').addEventListener('click',()=>{page--;health();});$('next').addEventListener('click',()=>{page++;health();});$('threshold').addEventListener('input',explore);$('reset-threshold').addEventListener('click',()=>{$('threshold').value=data.metrics.threshold;explore();});['reduction','loss','downtime'].forEach(id=>$(id).addEventListener('input',business));$('reset-business').addEventListener('click',()=>{$('reduction').value=25;$('loss').value=200;$('downtime').value=5;business();});
$('export').addEventListener('click',()=>{const cols=['observation_id','product_type','rotational_speed_rpm','torque_nm','tool_wear_min','model_score','model_alert','machine_failure'];const text=[cols.join(','),...filtered().map(r=>cols.map(c=>r[c]).join(','))].join('\n');const url=URL.createObjectURL(new Blob([text],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='filtered_holdout_observations.csv';a.click();URL.revokeObjectURL(url);});init();

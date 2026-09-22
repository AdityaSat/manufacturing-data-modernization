// Same monthly cash-flow mechanics as src/manufacturing/business.py.
// This module has no browser dependencies, so Node can verify it against Python.
export function evaluateBusiness(a) {
  const pool = a.assets * a.scheduled_hours_per_asset_year * a.unplanned_downtime_rate * a.loss_per_machine_hour;
  let pvBenefits = 0, pvOperating = 0;
  const schedule = Array.from({length:a.horizon_months+1}, (_,month) => {
    const realization = month <= a.pilot_months ? 0 : month <= a.pilot_months+a.partial_ramp_months ? a.partial_ramp_realization : 1;
    const discount = (1+a.discount_rate_annual)**(-month/12);
    if(month) {pvBenefits += realization*discount/12; pvOperating += discount/12;}
    return {month,realization,discount};
  });
  const options = {};
  for(const [key,o] of Object.entries(a.options)) {
    const capex=Object.values(o.implementation).reduce((s,x)=>s+x,0), opex=Object.values(o.annual_operating).reduce((s,x)=>s+x,0);
    const gross=pool*o.downtime_reduction;
    let cumulative=-capex, npv=0, payback=capex===0?0:null;
    const flows=schedule.map(s=>{
      const net=s.month ? gross/12*s.realization-opex/12 : -capex;
      const previous=cumulative;
      cumulative=s.month?cumulative+net:net;
      if(s.month && payback===null && previous<0 && cumulative>=0 && net>0)payback=s.month-1-previous/net;
      npv+=net*s.discount;
      return {month:s.month,cumulative};
    });
    options[key]={implementation:capex,annual_opex:opex,annual_gross_savings:gross,steady_annual_net:gross-opex,npv,payback_months:payback,net_cash:cumulative,cash_flows:flows};
  }
  const b=options.monitoring,p=options.predictive;
  return {options,annual_downtime_cost:pool,incremental_npv:p.npv-b.npv,incremental_break_even_reduction:pool*pvBenefits ? a.options.monitoring.downtime_reduction+(p.implementation-b.implementation+(p.annual_opex-b.annual_opex)*pvOperating)/(pool*pvBenefits):null};
}

import fs from 'node:fs';
const decode = s => s.replace(/&amp;/g,'&').replace(/&nbsp;/g,' ').replace(/&#39;|&rsquo;/g,"'").replace(/&quot;/g,'"').replace(/&ndash;/g,'–').replace(/&mdash;/g,'—');
const R = [
['red-light-therapy','red light therapy sauna','Red Light Therapy Saunas | 24 Verified, None List nm'],
['thermasol','thermasol steam shower','ThermaSol Steam Showers | 12 Systems, $8,360–$13,985'],
['outdoor-saunas','outdoor sauna','Outdoor Saunas | 33 Builds, $4,940–$26,890, 2–6 Person'],
['infrared-saunas','infrared sauna','Infrared Saunas | 91 Models, 55 Run on Standard 120V'],
['golden-designs','golden designs sauna','Golden Designs Saunas | 32 Indoor, Outdoor & Hybrid'],
['hot-tubs','hot tub','Hot Tubs | 7 Units, 4 Run Hot or Cold | InHouse Wellness'],
['sauna-life','saunalife','SaunaLife | 16 Outdoor Saunas, Plunges & Hot Tubs'],
['barrel-saunas','barrel sauna','Barrel Saunas | 17 Builds From $4,999 | InHouse Wellness'],
['massage-chairs','massage chair','Massage Chairs | 8 Models, $4,000–$10,599, L-Track'],
['scandia','scandia sauna','Scandia Saunas | 9 USA-Built Cabins & Kits, 4–8 Person'],
['dreampod','dreampod','Dreampod | 5 Float Tanks & 4 Cold Plunges From $760'],
['low-emf','low emf sauna','Low EMF Saunas | 5–10 mG, 21 Models From $1,999'],
['medical-sauna','medical sauna','Medical Sauna | 13 Cabins, $5,799–$28,649, 2–6 Person'],
['ice-tubs','ice bath tub','Ice Bath Tubs | 6 Icetubs, Chiller Built In, Thermowood'],
['mr-steam','mr steam generator','Mr Steam Generators | 5 Packages, $3,500–$13,800'],
['dynamic-cold-therapy','dynamic cold therapy','Dynamic Cold Therapy | 5 Plunges & Chillers From $899'],
['sauna','traditional sauna','Traditional Saunas | 57 Wood-Fired & Electric to 195°F'],
['helios-massage-chair','helios massage chair','Helios Massage Chairs | HM5500 & 4D HM8000, $4,000–$5,000'],
['steam-saunas','steam sauna','Steam Saunas | 15 Traditional Cabins Reaching 195°F'],
['cold-plunge','cold plunge tub','Cold Plunge Tubs | 18 From $760, 7 With a Chiller'],
['sauna-heaters','sauna heater','Sauna Heaters | 95 Electric & Wood, 4.5kW to 40kW'],
['ripavi','ripavi sauna','Ripavi Saunas | 2 Finnish Builds, $36,900 & $49,900'],
['near-zero-emf','near zero emf sauna','Near Zero EMF Saunas | 2–3 mG Measured, 23 Models'],
['far-infrared','far infrared sauna','Far Infrared Saunas | 71 Models, Every Max Is 140°F'],
['narvi','narvi sauna stove','Narvi Sauna Stoves | 7 Finnish Wood-Burning & Electric'],
['delta','delta steam generator','Delta Steam Generators | 7 Components, $2,470–$12,009'],
['designer-sauna-heaters','designer sauna heater','Designer Sauna Heaters | 4.5kW, 6kW & 8kW With Rocks'],
['sauna-accessories','sauna accessories','Sauna Accessories | 30 Items, $65–$1,742, Inc. Controls'],
['red-light-therapy-panel-skin-pain-recovery','red light therapy panel','Red Light Therapy Panels | 660nm & 850nm Published'],
['sauna-maintenance-product','sauna maintenance','Sauna Maintenance | Scandia Wood Oil & Salt Panels'],
['leisurecraft-cold-plunge','dundalk leisurecraft cold plunge','Dundalk LeisureCraft Cold Plunge | Cedar, No Chiller'],
['float-tank-upgrades','float tank accessories','Float Tank Accessories | Dreampod Anti-Vibration Mat'],
['cabin-sauna','cabin sauna','Cabin Saunas | 3 Builds, $6,953–$7,999, 2–5 Person'],
['service-upgrades','sauna delivery and installation','Sauna Delivery & Installation | $600 and $1,800 Flat'],
['chromotherapy','chromotherapy sauna','Chromotherapy Saunas | 43 Models, 40 Have LED Lighting'],
['indoor-sauna','indoor sauna','Indoor Saunas | 3 Built-In Units, $11,999–$22,800'],
['chimneys','sauna chimney','Sauna Chimney Kits | 7 Dundalk, $708–$1,518, Roof or Wall'],
['roof-option','sauna roof','Sauna Roofs | 4 Dundalk Options, Metal or Shingle'],
['mande-spa','mande spa sauna','Mande Spa Saunas | 3 Thermowood Outdoor, 2–6 Person'],
['health-smart','healthsmart red light therapy panel','HealthSmart Red Light Therapy Panel | 660nm/850nm'],
['cold-plunge-accessories','cold plunge cover','Cold Plunge Cover | SaunaLife S2 Insulated, $590'],
['kohler','kohler sauna','Kohler Saunas | 2 Built-In Units, $17,867–$22,800'],
];
console.log('handle                                        len  kw  title');
let bad=0;
for (const [h,kw,t] of R) {
  const d=decode(t); const okLen=d.length<=60; const okKw=d.toLowerCase().includes(kw.toLowerCase());
  if(!okLen||!okKw) bad++;
  console.log(`${h.slice(0,44).padEnd(45)}${String(d.length).padStart(3)}  ${okKw?'ok':'!!'}  ${d}${!okLen?'  <-- OVER 60':''}${!okKw?'  <-- KW':''}`);
}
console.log(bad?`\n${bad} FAILED`:`\nAll ${R.length} pass: under 60 decoded, primary keyword verbatim.`);
const withBrand=R.filter(([,,t])=>/InHouse Wellness/.test(t)).length;
console.log(`brand suffix: ${withBrand} of ${R.length} (a default, not a requirement)`);
fs.writeFileSync('/tmp/titles42.json',JSON.stringify(R.map(([h,kw,t])=>({handle:h,keyword:kw,title:t})),null,2));

#!/usr/bin/env python3
"""Assemble the plan-set page: style + drawings + content -> one HTML file."""
import os
import sys

import figures as F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'barrel-rocket-mass-heater.html')

d = F.derived()
DV = {  # labels printed on the drawings (8-inch system, as drawn)
    'A': '7.5 in', 'B': '16 in', 'C': '7.5 in', 'D': '12.5 in', 'E': '7.5 in',
    'F': f"{d['riser_h']:g} in", 'G': '2 in', 'H': f"{d['annulus']:g} in", 'J': f"{d['ins_t']:g} in",
    'L': '8 in', 'N': '84 in', 'P': '36 in', 'Q': '18 in', 'R': f"{d['cover']:g} in",
}

css = open(os.path.join(HERE, 'style.css')).read()

REC = '<span class="lbl rec">Record</span>'
INF = '<span class="lbl inf">Inferred</span>'
NIR = '<span class="lbl nir">Not in record</span>'
C3 = '<span class="lbl c3">Class 3</span>'


def sheet(no, title, scale, svg, caption, notes=None, legend=True):
    lg = ''
    if legend:
        lg = ('<div class="legend">'
              '<span><i class="l-brick"></i>firebrick</span>'
              '<span><i class="l-ins"></i>insulation</span>'
              '<span><i class="l-conc"></i>concrete</span>'
              '<span><i class="l-sand"></i>sand + pebble fill</span>'
              '<span><i class="l-fire"></i>hot gas</span>'
              '<span><i class="l-warm"></i>warm gas</span>'
              '<span><i class="l-cool"></i>cool air / exhaust</span></div>')
    nt = ''
    if notes:
        nt = '<ol class="notes">' + ''.join(f'<li>{n}</li>' for n in notes) + '</ol>'
    return f'''
<figure class="sheet" id="sheet-{no.lower()}">
  <div class="sheet-head"><span class="no">{no}</span><span class="ttl">{title}</span><span class="scale">{scale}</span></div>
  <div class="dscroll">{svg}</div>
  {lg}
  {nt}
</figure>
<figcaption>{caption}</figcaption>'''


def check(cid, title, label, body):
    return f'''
<li class="check" data-id="{cid}">
  <input type="checkbox" id="{cid}" aria-describedby="{cid}-why">
  <label for="{cid}">{title} {label}</label>
  <div class="why" id="{cid}-why">{body}</div>
</li>'''


checks = ''.join([
    check('c1', 'Washington&rsquo;s install rule', C3, f'''
<p>{REC} Ecology: &ldquo;It is illegal to install an uncertified wood stove in Washington&hellip; a homeowner cannot apply to certify their wood stove.&rdquo; PSCAA says the same, and its 2012 rule change added &ldquo;a prohibition on installing unapproved devices.&rdquo; ORCAA lists &ldquo;installation&hellip; of an uncertified solid fuel burning device by a private citizen&rdquo; as a violation. No Washington rule mentions rocket mass heaters. The site-built masonry-heater route (WAC 51-51-1002) needs an Ecology-approved type with tight-fitting doors and outside combustion air; this design has an open feed tube.</p>
<p>{INF} This heater is an uncertified device with no path to certification, so installing it in a building conflicts with those rules. Rests on the four sources above and the absence of any rocket-heater rule.</p>
<p>{NIR} Which county the outbuilding is in. Seattle / King County is PSCAA, (206) 716-1195. Tahuya / Mason County is ORCAA, orcaa.org. That agency is the check.</p>'''),
    check('c2', 'Permit, occupancy, insurance', C3, f'''
<p>{REC} The residential code expects solid-fuel room heaters to be tested to UL 1482 and installed per their listing (IRC M1410.1), so a site-built heater needs the building official&rsquo;s approval. PSCAA: installing an uncertified stove &ldquo;can void insurance policy coverage in some instances.&rdquo; One county building department (Coconino, AZ) reviewed rocket mass heaters and declined to approve them, citing escaping gases.</p>
<p>{NIR} Whether sleeping in this outbuilding needs a permit or dwelling approval (not verified this session). Check with the county building department and your insurer.</p>'''),
    check('c3', 'The floor can carry it', C3, f'''
<p>{INF} The bench alone weighs about 2,800&ndash;3,000 lb: roughly 29 ft&sup3; of sand and pebbles at 95&ndash;103 lb/ft&sup3;. That is about 140 lb on every square foot it covers, before the core and drum. It goes on a slab on grade, not a framed floor.</p>
<p>{NIR} What is under the spot you picked.</p>'''),
    check('c4', 'CO and smoke alarms before the first fire', C3, f'''
<p>{REC} The feed tube is open to the room, so if the draft reverses, smoke and CO come in. Builders report CO trouble mostly as the fire is dying down.</p>
<p>Put a CO alarm and a smoke alarm in the room you sleep in and test them before any fire. The code sections that likely require them (RCW 19.27.530, IRC R315) were named in research but not read this session.</p>'''),
    check('c5', 'What the drum held', C3, f'''
<p>{REC} OSHA 1910.252(a)(3)(i): no cutting or welding on used drums &ldquo;until they have been cleaned so thoroughly as to make absolutely certain that there are no flammable materials present.&rdquo; NIOSH case reports include a sealed drum with leftover diesel that exploded under a cut-off saw.</p>
<p>{NIR} What your drum held, and whether it is galvanized or lined. Don&rsquo;t cut it until you know, it&rsquo;s clean, and it&rsquo;s open to air.</p>'''),
    check('c6', 'What the pipe is', C3, f'''
<p>{REC} The system stays one size from feed tube to chimney cap. Galvanized coatings are rated for 392&deg;F continuous; zinc melts at 787&deg;F (419.5&deg;C), and riser-top readings peak around 1,400&deg;F. Zinc oxide fume causes metal fume fever.</p>
<p>{NIR} Your pipe&rsquo;s outside diameter and whether it is galvanized. These sheets are drawn for 8-inch.</p>'''),
    check('c7', 'Clearances in the room', C3, f'''
<p>{REC} NFPA 211 values for unlisted stoves, as reported by secondary sources (the primary table was not viewed): 36 in from the drum to combustibles; 12 in at the sides and rear, 18 in above, with 24-gauge sheet metal on a 1-in ventilated air space; 18 in for single-wall pipe; non-combustible floor 18 in out on all sides. Sheet S-3 draws these lines.</p>'''),
    check('c8', 'The roof cut', C3, f'''
<p>{REC} Single-wall pipe must not pass through a wall, ceiling or roof; use a listed insulated chimney with a listed support or firestop. The top goes at least 3 ft above the roof where it passes through and 2 ft higher than anything within 10 ft.</p>
<p>{INF} If the building is old, the roofing or siding you cut through is a sampling question under your own survey rules.</p>'''),
])

materials = f'''
<div class="tscroll"><table>
<thead><tr><th>What you have</th><th>Where it goes</th><th>Keep it out of</th><th>Why</th></tr></thead>
<tbody>
<tr><td class="key">55-gal steel drum</td><td>The bell over the riser: radiator and cooktop</td><td class="no">Don&rsquo;t use a galvanized drum</td><td>The usual bell for an 8-inch core. The top runs 600&ndash;700&deg;F at high fire, above zinc&rsquo;s 392&deg;F rating. {REC}</td></tr>
<tr><td class="key">Steel pipe</td><td>Bench duct and the pipe from the bench up to the ceiling, if it is 8 in</td><td class="no">Anything under 8 in; the core; through the ceiling or roof</td><td>One size all the way. Single-wall pipe can&rsquo;t pass through the building; that part is listed chimney. {REC}</td></tr>
<tr><td class="key">Galvanized pipe, if any</td><td>Only the far half of the bench duct</td><td class="no">Core, riser, manifold, the first run out of the manifold</td><td>Rated 392&deg;F continuous. The gas temperature entering the bench wasn&rsquo;t found, so the first run is black steel. {INF}</td></tr>
<tr><td class="key">Sand</td><td>Bench fill; clay-sand mortar and seals (2&ndash;3 sand : 1 clay); concrete</td><td>&mdash;</td><td>Dry sand is about 100 lb/ft&sup3; and holds 0.19 BTU per lb per &deg;F. {REC}</td></tr>
<tr><td class="key">Portland cement</td><td>Slab (1 cement : 2 sand : 3 gravel, about 3,000 psi); bench shell; bench cap past the first 2 ft</td><td class="no">Feed tube, tunnel, riser, manifold, first 2 ft of bench</td><td>Portland concrete is typically limited to about 212&deg;F service; its binder breaks down at 750&ndash;1,100&deg;F; wet concrete can spall explosively. {REC} The 2-ft line is {INF}</td></tr>
<tr><td class="key">Pebbles / gravel</td><td>Gravel base, slab aggregate, bench fill</td><td class="no">Anywhere near flame; keep them 2&ndash;3 ft away</td><td>River rock holds water and can crack violently when heated. {REC}</td></tr>
<tr><td class="key">&ldquo;Packing pebbles&rdquo; if perlite or vermiculite</td><td>Riser insulation and the layer under the core: 1 part clay slip to 6&ndash;9 parts</td><td>&mdash;</td><td>The clay keeps it in place; loose perlite slumps. {REC}</td></tr>
<tr><td class="key">&hellip;if foam packing peanuts</td><td>Nothing</td><td class="no">The whole heater</td><td>Plastic foam burns and smokes. {INF} What yours are: {NIR}</td></tr>
</tbody></table></div>'''

shopping = f'''
<ul class="plain">
<li><b>Firebrick</b>, standard hard 9 &times; 4.5 &times; 2.5 in: about 40 for the floor, tunnel, roof and feed tube, and about 50 more for a firebrick riser shaft; add 10% for cuts. {INF} Counted from these sheets; no authoritative count was found.</li>
<li><b>Clay</b>: bagged fireclay or dug clay subsoil, for slip, mortar, seals and the perlite mix.</li>
<li><b>Perlite</b> (garden center), if your pebbles aren&rsquo;t perlite. Or ceramic fiber blanket, which is an IARC 2B possible carcinogen and forms cristobalite after firing; handle it like the work you already do.</li>
<li><b>Riser sleeve</b>: 18 in OD, plain sheet steel, not galvanized.</li>
<li><b>Fittings</b>: 8-in black stovepipe for the first run, one 8-in tee with a cap for the chimney base, a plate or cap for the manifold cleanout, sheet-metal screws, high-temperature sealant.</li>
<li><b>Listed chimney parts</b>: ceiling or roof support, insulated chimney sections to height, flashing, storm collar, cap with spark screen.</li>
<li><b>Safety</b>: CO alarm, smoke alarm, ABC extinguisher, lidded metal ash can, P100 respirator for perlite, cement and fiber dust.</li>
<li><b>Optional</b>: a &frac14;-in steel disc to lay inside the drum lid. The lid is a wear part (reported life over two years) and the disc extends it; measure gap G to the disc. An infrared thermometer to read the exhaust (140&ndash;200&deg;F is the target).</li>
</ul>'''


def row(k, what, v8, v6, basis):
    return (f'<tr><td class="key"><span class="k">{k}</span>{what}</td>'
            f'<td class="v on">{v8}</td><td class="v">{v6}</td><td>{basis}</td></tr>')


sizes = '<div class="tscroll"><table><thead><tr><th>Key / part</th><th>8-inch (drawn)</th>' \
        '<th>6-inch (reference)</th><th>Rule and basis</th></tr></thead><tbody>' + ''.join([
            row('A', 'Feed tube, inside', '7.5 &times; 7.5 in', '5.5 &times; 5.5 in',
                f'Square openings never smaller than the pipe (8-in pipe = 50.3 in&sup2;; 7.5-in square = 56.3 in&sup2;). {REC}'),
            row('B', 'Feed tube height, tunnel floor to top', '16 in', '15 in', REC),
            row('C', 'Burn tunnel, inside height', '7.5 in', '5.5 in',
                f'Same square as A; not dimensioned on S-2. {REC}'),
            row('D', 'Tunnel roof, feed shaft to riser shaft', '12.5 in', 'about 12 in',
                f'8-in: 12.5 in maximum {REC}. The drum sets the minimum: at 12.5 in it clears the feed tube by '
                f'{d["feed_clear"]:g} in {INF}. 6-in: the drum&rsquo;s radius forces about 12 in {INF}. Whether a 6-inch '
                f'burns clean with a roof that long: {NIR}; the Wisners&rsquo; 21-in tunnel sat under a different bell.'),
            row('E', 'Riser, inside', '7.5 &times; 7.5 in', '5.5 &times; 5.5 in', f'Same area as A. {REC}'),
            row('F', 'Riser height, tunnel floor to top', f'{d["riser_h"]:g} in', '47 in',
                f'8-in: 40 in minimum {REC}; the drawn height is set by the drum {INF}. 6-in: the Wisners&rsquo; as-built '
                f'{REC}; under a 55-gal drum that means raising the drum about 6 in on a masonry ring {INF}.'),
            row('G', 'Gap, riser top to drum lid', '2 in', '1.5 in',
                f'About a quarter of the pipe diameter. Under 1 in chokes it; over 3 in reportedly reverses the flow. {REC} '
                f'One source gives 1.5 in for 8-in.'),
            row('H', 'Side gap, sleeve to drum wall', f'{d["annulus"]:g} in', 'about 3.25 in',
                f'The ring&rsquo;s area must be at least the riser&rsquo;s {REC}. Drawn ring: 143 in&sup2;, 2.5&times; {INF}.'),
            row('J', 'Riser insulation at the faces', f'{d["ins_t"]:g} in', '2.75 in',
                f'At least 2 in of perlite-clay {REC}, mixed 1 slip : 6&ndash;9 perlite.'),
            row('K', 'Manifold flow area', 'about 160 in&sup2; (12 &times; 14 in)', 'about 90 in&sup2;',
                f'At least 1.5&times; the pipe area where the flow turns; about 3&times; as a rule of thumb. {REC}'),
            row('L', 'Duct and chimney diameter', '8 in', '6 in', f'Same size all the way, never smaller. {REC}'),
            row('M', 'Duct allowance', '50 ft, less 5 ft per 90&deg; bend', '35 ft, less 5 ft per 90&deg; bend',
                f'{REC} One source gives about 45 ft for 6-in. This bench uses about 7.5 ft and one bend, '
                f'so about 12.5 ft of the allowance {INF}.'),
            row('N', 'Bench length', '84 in', '84 in', f'{INF} Sized for one sleeper.'),
            row('P', 'Bench width', '36 in', '36 in', INF),
            row('Q', 'Bench height', '18 in', '18 in', INF),
            row('R', 'Mass over the duct', f'{d["cover"]:g} in', '9 in',
                f'{INF} 4 in of fill plus a 3-in cap.'),
            row('&mdash;', 'Drum', '55-gal', '55-gal',
                f'Open-head drum: 22.5 in inside diameter, 33.5 in inside height; about 23 &times; 34.5 in outside. {REC}'),
        ]) + '</tbody></table></div>'

build_steps = f'''
<ol class="steps">
<li><b>Settle the checks.</b><p>Checks 1 and 3 decide whether and where this gets built. Nothing below matters until they are answered.</p></li>
<li><b>Measure and sort what you have.</b><p>Pipe outside diameter; galvanized or black; what the drum held; what the &ldquo;packing pebbles&rdquo; are.</p></li>
<li><b>Make the drum safe, then cut it.</b><p>Clean and vent it first. Cut off the end with the bung holes; the plain end becomes the lid. Burn the paint off outdoors, upwind, until it is bare steel.</p></li>
<li><b>Pour the slab.</b><p>Dig out, lay 4 in of compacted gravel, pour 4 in of 1:2:3 concrete, reaching 18 in past the core on every side and under the whole bench. Let it cure before loading it.</p></li>
<li><b>Lay the insulating layer.</b><p>2 in of perlite-clay under the core footprint. Let it dry.</p></li>
<li><b>Dry-fit the core.</b><p>Floor, tunnel walls, roof and feed tube without mortar. Check A through E against the table and check that the drum clears the feed tube by {d["feed_clear"]:g} in. Then set the bricks in thin clay slip or fireclay mortar.</p></li>
<li><b>Build the riser.</b><p>Shaft to F ({d["riser_h"]:g} in above the tunnel floor), the 18-in sleeve around it, insulation packed between, and a cap over the top edge of the insulation.</p></li>
<li><b>Test the open core.</b><p>With the drum off, burn paper and small sticks: the flame should lay over and run into the riser. If it won&rsquo;t, fix it now while everything is reachable. {INF}</p></li>
<li><b>Build the manifold and set the drum.</b><p>Firebrick and clay, floor below the duct inlet, cleanout 1 on the side. Measure G, set the drum, seal the rim with clay-sand.</p></li>
<li><b>Run the duct and the chimney.</b><p>Black steel for the first run, every joint screwed and sealed, the capped tee at the chimney base, listed support and insulated chimney through the roof, spark-screen cap, 3 ft / 2 ft / 10 ft.</p></li>
<li><b>Smoke-test before burying anything.</b><p>Run a fire and check every joint and seal. Fix leaks while they are still exposed. {INF}</p></li>
<li><b>Build the bench.</b><p>Shell walls, clay slip painted on the duct, fill in tamped layers, clay-sand cap near the manifold, concrete cap beyond.</p></li>
<li><b>Dry it out.</b><p>Small, short fires until the masonry is dry. Wet masonry heated fast can crack or spall.</p></li>
<li><b>Alarms up, extinguisher by the door.</b><p>Then the first full burn.</p></li>
</ol>'''

run_steps = f'''
<ol class="steps">
<li><b>Before lighting.</b><p>Test the CO alarm. Nothing inside the clearance lines, nothing on the drum. Check the agency&rsquo;s burn-ban status.</p></li>
<li><b>Prime a cold system.</b><p>Light a twist of newspaper in the chimney-base tee, cap it, then light the feed tube.</p></li>
<li><b>Light.</b><p>Paper and kindling standing in the feed tube. Add split dry wood standing on end once it draws hard.</p></li>
<li><b>Feed.</b><p>Keep the tube loaded but not packed. Cut sticks to about the tube&rsquo;s height; overlong sticks are a reported cause of smoke coming back out.</p></li>
<li><b>Fuel.</b><p>Dry, seasoned wood, with paper to start. Washington bans burning garbage, treated or painted wood, plastics, rubber and similar (WAC 173-433-120).</p></li>
<li><b>Watch the chimney.</b><p>Visible smoke after start-up means a poor burn. The state limit is 20% opacity for 6 minutes in any hour; start-up gets 20 minutes in any 4 hours.</p></li>
<li><b>Finish while awake.</b><p>Stop feeding and let it burn down to ash. Builders report CO trouble mostly as the fire dies down, so be up for that part.</p></li>
<li><b>Close the feed.</b><p>Once no coals glow, set a lid on the feed tube so the chimney doesn&rsquo;t pull the bench&rsquo;s heat out overnight. {INF}</p></li>
<li><b>Ash.</b><p>Shovel it out of the tunnel cold, into a lidded metal can, outside.</p></li>
</ol>'''

fixes = '''
<div class="tscroll"><table>
<thead><tr><th>What you see</th><th>Likely cause</th><th>Fix</th></tr></thead><tbody>
<tr><td>Smoke rolls out the feed tube on a cold start</td><td>Cold chimney and bench</td><td>Prime at the tee with newspaper, then relight</td></tr>
<tr><td>Smoke comes back out during a burn</td><td>Sticks too long; tube packed full; wet wood; ash choking the tunnel or manifold</td><td>Shorter sticks, fewer at a time, dry wood, clean out</td></tr>
<tr><td>Fire creeps up the wood in the feed tube</td><td>Reported by builders; no settled cause found</td><td>Shorter sticks, push them down, check the draft; stay with it</td></tr>
<tr><td>Weak, lazy flame</td><td>Ash in the tunnel; air leaking at cleanout caps or the drum seal; wet wood</td><td>Clean out, reseal, drier wood</td></tr>
<tr><td>Drum lid thin, warped or glowing</td><td>Normal wear (reported life over two years), or overfiring</td><td>&frac14;-in disc inside the lid; smaller loads</td></tr>
<tr><td>Drips or black liquid at the chimney tee</td><td>Condensation: exhaust under 140&deg;F; the condensate is acidic</td><td>Shorter duct, or a warmer chimney (inside the building, insulated)</td></tr>
<tr><td>CO alarm sounds</td><td>A leak or the draft reversing</td><td>Get out and ventilate; find the cause before the next fire</td></tr>
</tbody></table></div>'''

sources = [
    ('S1', 'permies.com/t/75071 &mdash; basic 8-in dimensions: 7.5-in square openings, 16-in feed, tunnel roof &le;12.5 in, riser 40 in+.', 'https://permies.com/t/75071/Basic-dimensions-rocket-mass-heater'),
    ('S2', 'One Community Global, Wisner &ldquo;Annex&rdquo; 6-in plans: 5.5-in feed, 15-in feed height, 21-in tunnel, 47-in riser; flame path 1,200&ndash;2,800&deg;F; drum 200&ndash;800&deg;F; masonry 60&ndash;90&deg;F; about 800 sq ft on under half a cord a year; 25 ft of duct with seven bends = 55 ft of drag.', 'https://onecommunityglobal.org/wp-content/uploads/2014/05/Rocket-Mass-Heater-Plans-Annex6.pdf'),
    ('S3', 'permies.com/t/98267 &mdash; riser-top gap: 1.5 in (6-in), 2 in (8-in); 0.8 in too small; over 3 in reversed flow.', 'https://permies.com/t/98267/relationship-riser-top-barrel'),
    ('S4', 'permies.com/t/7778 &mdash; 8-in pairs with a 55-gal drum; top gap 2&ndash;3 in, side gaps 1.5&ndash;2 in.', 'https://permies.com/t/7778/Rocket-Stove-Dimensions'),
    ('S5', 'permies.com/t/75218 &mdash; gap area at least the riser area; one builder uses 1.5 in on 8-in; Wisner guide on 2 in perlite / 4 in vermiculite.', 'https://permies.com/t/75218/Barrel-heat-riser-gap-CSA'),
    ('S6', 'permies.com/t/74402 &mdash; manifold: 150% of pipe area where the flow turns, 2&ndash;4&times; where it drops; 3&times; rule of thumb; bottlenecks cause smoke-back.', 'https://permies.com/t/74402/Rocket-Mass-Heater-MANIFOLD'),
    ('S7', 'permies.com/t/44716 &mdash; 8-in duct: about 50 ft minus 5 ft per 90&deg; bend.', 'https://permies.com/t/44716/RMH-ducting-length'),
    ('S8', 'permies.com/t/97315 &mdash; 6-in duct: about 35 ft minus 5 ft per bend; warm vertical chimney adds allowance.', 'https://permies.com/t/97315/Horizontal-duct-chimney-length-inch'),
    ('S9', 'greenlifehomestead.com &mdash; 6-in core with a 55-gal drum; 55-gal top 600&ndash;700&deg;F at high fire.', 'https://greenlifehomestead.com/6-rocket-heater-core/'),
    ('S10', 'permies.com/t/134595 &mdash; perlite-clay: 1 slip to 6&ndash;9 perlite (Evans/Jackson).', 'https://permies.com/t/134595/Perlite-Clay-mix-ratios'),
    ('S11', 'permies.com/t/29673 &mdash; steel riser liners last one or two seasons; unbound perlite collapses.', 'https://permies.com/t/29673/Heat-Riser-Insulation'),
    ('S12', 'NTP Report on Carcinogens / ScienceDirect &mdash; ceramic fiber hazards (IARC 2B; cristobalite after firing).', 'https://www.ncbi.nlm.nih.gov/books/NBK590815/'),
    ('S13', 'US patent 10358387 background &mdash; Portland concrete typically limited to about 100&deg;C service.', 'https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10358387'),
    ('S14', 'PMC7731264 &mdash; calcium hydroxide breaks down at about 400&ndash;600&deg;C.', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7731264/'),
    ('S15', 'Promat &mdash; explosive spalling from moisture and heating rate.', 'https://www.promat.com/en/tunnels/your-project/expert-area/159998/the-effect-of-fire-concrete-spalling/'),
    ('S16', 'IFLScience / HelloGravel &mdash; river rock can crack violently or explode; keep 2&ndash;3 ft from flame.', 'https://www.iflscience.com/why-you-should-never-use-river-rocks-in-a-campfire-69167'),
    ('S17', 'American Galvanizers Association &mdash; 392&deg;F continuous; peeling above 480&deg;F; 660&deg;F short-term.', 'https://galvanizeit.org/knowledgebase/article/performance-and-inspection-of-hdg-exposed-to-extreme-temperatures'),
    ('S18', 'nuclear-power.com &mdash; zinc melts at 419.5&deg;C, boils at 907&deg;C.', 'https://www.nuclear-power.com/zinc-melting-point-boiling-point/'),
    ('S19', 'NIOSH Pocket Guide &mdash; zinc oxide fume limits; metal fume fever.', 'https://www.cdc.gov/niosh/npg/npgd0675.html'),
    ('S20', 'OSHA 29 CFR 1910.252(a)(3)(i) &mdash; hot work on used drums.', 'https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.252'),
    ('S21', 'NIOSH / CDC Stacks case report &mdash; drum with leftover diesel exploded under a cut-off saw.', 'https://stacks.cdc.gov/view/cdc/228911'),
    ('S22', 'permies.com/t/204360 &mdash; burning paint off a 55-gal drum.', 'https://permies.com/t/204360/Burning-paint-gallon-drum'),
    ('S23', 'permies.com/t/60298 &mdash; exhaust 100&ndash;200&deg;F versus 350&ndash;500&deg;F for a woodstove; warm chimney inside, exit near the peak.', 'https://permies.com/t/60298/insulate-chimney-show-Rocket-Mass'),
    ('S24', 'permies.com/t/161237 &mdash; condensation stops above 140&deg;F; 180&ndash;200&deg;F ideal.', 'https://permies.com/t/161237/exhaust-temp'),
    ('S25', 'permies.com/t/74197 &mdash; priming with newspaper in the chimney-base cleanout.', 'https://permies.com/t/74197/Starting-draw'),
    ('S26', 'permies.com/t/148338 &mdash; condensate volume; it is acidic.', 'https://permies.com/t/148338/Dealing-condensation'),
    ('S27', 'permies.com/t/100951 &mdash; CO problems typically around the time the fire dies down.', 'https://permies.com/t/100951/Carbon-Monoxide'),
    ('S28', 'permies.com/t/19562 &mdash; smoke-back from sticks longer than the feed tube.', 'https://permies.com/t/19562/Fire-coming-feed-tube-rocket'),
    ('S29', 'permies.com/t/106984 &mdash; drum top is a wear part (&gt;2 years); &frac14;-in sacrificial plate.', 'https://permies.com/t/106984/Replacing-barrel'),
    ('S30', 'greenhomebuilding.com &mdash; cob: 2&ndash;3 sand to 1 clay by volume.', 'https://www.greenhomebuilding.com/QandA/cob/mixing.htm'),
    ('S31', 'Lackan Cottage &mdash; no straw next to the pipework.', 'https://lackancottage.co.uk/project/rocket-mass-heater/'),
    ('S32', 'Appropedia CCAT &mdash; clay slip on the pipe for contact.', 'https://www.appropedia.org/CCAT_rocket_mass_cobb_bench_heater'),
    ('S33', 'permies.com/t/34708 &mdash; 8-in bench tops 100&ndash;120&deg;F hot end, 80&ndash;90&deg;F far end, 130&ndash;140&deg;F after a full day.', 'https://permies.com/t/34708/cob-bench-temperatures'),
    ('S34', 'permies.com/t/20840 &mdash; an 8-in moves about twice the gas of a 6-in.', 'https://permies.com/t/20840/rocket-mass-heater'),
    ('S35', 'permies.com/t/266511 and t/21119 &mdash; 8-in output estimates: about 100,000 BTU/h vs about 14 kW (conflict).', 'https://permies.com/t/266511/BTU-hour-tube'),
    ('S36', 'Handprint Press &mdash; no proper contemporary emissions testing of rocket mass heaters.', 'https://www.handprintpress.com/tech/recent-research-on-rocket-mass-heaters-and-bell-design/'),
    ('S37', 'InspectApedia &mdash; chimney height: 3 ft above the roof, 2 ft above anything within 10 ft.', 'https://inspectapedia.com/chimneys/Chimney_Height_Codes_Specifications.php'),
    ('S38', 'Repackify &mdash; 55-gal open-head drum: 22.5 in ID, 33.5 in inside height; about 23 &times; 34.5 in outside.', 'https://www.repackify.com/blog/55-gallon-drum-dimensions'),
    ('S39', 'Concrete mix guides &mdash; 1:2:3 by volume, about 3,000 psi at 28 days.', 'https://www.probuildercalc.com/blog/how-to-read-a-concrete-mix-ratio-1-2-3-explained'),
    ('S40', 'Dry sand density about 101.8 lb/ft&sup3; (range 87&ndash;118); sand with gravel 103 lb/ft&sup3;; quartz sand 830 J/kg&middot;K (0.19 BTU/lb&middot;&deg;F).', 'https://www.engineeringtoolbox.com/specific-heat-solids-d_154.html'),
    ('L1', 'Ecology wood stove page &mdash; illegal to install an uncertified wood stove; homeowners cannot certify.', 'https://ecology.wa.gov/air-climate/air-quality/smoke-fire/wood-stove-info'),
    ('L2', 'PSCAA Legal Overview &mdash; illegal to install an uncertified stove or insert in WA; can void insurance.', 'https://pscleanair.gov/170/Legal-Overview'),
    ('L3', 'PSCAA Regulation I, Article 13 &mdash; 2012 amendment added a prohibition on installing unapproved devices (section number not confirmed).', 'https://pscleanair.gov/DocumentCenter/View/5319'),
    ('L4', 'ORCAA Regulations, Rule 8.1 &mdash; installation of an uncertified device by a private citizen is a violation; burn bans.', 'https://www.orcaa.org/wp-content/uploads/ORCAA-Regulations.pdf'),
    ('L5', 'RCW 70A.15.3510 / .3520 &mdash; device definitions; used devices must be certified to be installed.', 'https://app.leg.wa.gov/RCW/default.aspx?cite=70A.15.3520'),
    ('L6', 'WAC 173-433-100, -110, -120, -150 &mdash; certification standard, 20% opacity, prohibited fuels, Stage 2 rule.', 'https://app.leg.wa.gov/WAC/default.aspx?cite=173-433'),
    ('L7', 'WAC 51-51-1002 (IRC R1002 as amended) &mdash; masonry heaters: Ecology-approved type, ASTM E1602 / UL 1482 / EN 15250, ducted outside air, tight doors.', 'https://app.leg.wa.gov/WAC/default.aspx?cite=51-51-1002'),
    ('L8', 'RCW 70A.15.3580, WAC 173-433-030 &mdash; burn-ban stages; adequate source of heat = 70&deg;F at 3 ft above the floor in all normally inhabited areas.', 'https://app.leg.wa.gov/RCW/default.aspx?cite=70A.15.3580'),
    ('L9', 'PSCAA burn bans and &ldquo;No Other Adequate Source of Heat&rdquo; exemption; approvals ran until August 31, 2026.', 'https://pscleanair.gov/171/No-Other-Adequate-Source-of-Heat'),
    ('L10', 'PSCAA Tacoma-Pierce Smoke Reduction Zone &mdash; uncertified stoves illegal to operate since 10/1/2015.', 'https://pscleanair.gov/547/Tacoma-Pierce-Stove-Rule'),
    ('L11', 'IRC M1410.1 &mdash; solid-fuel room heaters tested to UL 1482 and installed per listing.', 'https://up.codes/s/vented-room-heaters'),
    ('L12', 'ICC &mdash; 2021 IRC Appendix AS is strawbale; no rocket-heater appendix found.', 'https://codes.iccsafe.org/content/IRC2021P2/appendix-as-strawbale-construction'),
    ('L13', 'Maine State Fire Marshal / InspectApedia &mdash; NFPA 211 unlisted-stove clearances (36 in, 18 in pipe, 18 in floor).', 'https://www1.maine.gov/dacf/mfs/projects/woodheatmaine/downloads/woodstove_installation.pdf'),
    ('L14', 'Eagle Point Mutual &mdash; clearance reduction with 24-gauge sheet metal on 1-in air space: 36 &rarr; 12 in sides and rear, 18 in above; pipe 18 &rarr; 6 in.', 'https://www.eaglepointmutual.com/important_tips/solid_fuel_heating.pdf'),
    ('L15', 'NFPA 211 pass-through summary &mdash; single-wall pipe must not penetrate walls, ceilings or roofs.', 'https://www.rockfordchimneysupply.com/blogs/chimney-pipe-and-stove-pipe/nfpa-211-combustible-wall-pass-thru-explained'),
    ('L16', 'Coconino County, AZ &mdash; building department panel declined to approve rocket mass heaters.', 'https://www.coconino.az.gov/2538/Permitting-Of-Specific-Alternative-Metho'),
]
src_html = ''.join(
    f'<li><b>{k}</b> <span>{t}</span><br><a href="{u}" target="_blank" rel="noopener">{u.split("//")[1][:70]}</a></li>'
    for k, t, u in sources)

numbers = f'''
<div class="tscroll"><table>
<thead><tr><th>Question</th><th>Answer</th><th>Basis</th></tr></thead><tbody>
<tr><td>Heat while it burns</td><td class="v">48,000&ndash;100,000 BTU/h (8-in)</td><td>{REC} Forum estimates that disagree: about 14 kW, versus 10&ndash;12 lb of wood in a 45-minute burn at about 100,000 BTU/h. A 6-inch moves about half the gas of an 8-inch.</td></tr>
<tr><td>What one did in service</td><td class="v">~800 sq ft, &lt; &frac12; cord/yr</td><td>{REC} The Wisners&rsquo; 6-inch, as its only heat, as reported.</td></tr>
<tr><td>Bench weight</td><td class="v">2,800&ndash;3,000 lb</td><td>{INF} 29 ft&sup3; of fill (36 &times; 84 &times; 18 in less the duct) at 95&ndash;103 lb/ft&sup3;. About 140 lb per ft&sup2; of footprint.</td></tr>
<tr><td>Heat the bench holds</td><td class="v">~5,500 BTU per 10&deg;F</td><td>{INF} 2,900 lb &times; 0.19 BTU/lb&middot;&deg;F &times; 10&deg;F. Roughly an hour of a 1,500-W heater (5,118 BTU/h). The missing factor is how far the whole bench&rsquo;s temperature rises, which nobody has measured for this build.</td></tr>
<tr><td>How warm the room stays overnight</td><td class="v">&mdash;</td><td>{NIR} Depends on floor area, insulation and air leaks. The bench surface itself: 100&ndash;120&deg;F at the hot end, 80&ndash;90&deg;F at the far end on 8-inch builds.</td></tr>
<tr><td>Efficiency</td><td class="v">not tested</td><td>{REC} No proper emissions testing of rocket mass heaters exists. The widely repeated 61.8% figure comes from a masonry-heater study.</td></tr>
</tbody></table></div>'''

JS = r'''
(function () {
  var KEY = 'rmh-checks-v1';
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { state = {}; }
  document.querySelectorAll('.check').forEach(function (li) {
    var id = li.getAttribute('data-id');
    var box = li.querySelector('input');
    if (state[id]) { box.checked = true; li.classList.add('done'); }
    box.addEventListener('change', function () {
      li.classList.toggle('done', box.checked);
      state[id] = box.checked;
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    });
  });
})();
'''

html = f'''<title>Barrel Rocket Mass Heater</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
{css}
</style>
<div class="wrap">

<header class="titleblock">
  <div class="tb-main">
    <span class="eyebrow">Plan set &middot; Rev A &middot; 27 Sep 2026 &middot; for Ryan</span>
    <h1>Barrel Rocket Mass Heater</h1>
    <p class="lede">An 8-inch J-tube rocket heater under your 55-gallon drum, venting through a sand-and-pebble sleeping bench. The drum throws heat while the fire burns; the bench gives it back through the night, so the fire can be out before you sleep.</p>
  </div>
  <div class="tb-cells">
    <div class="tb-cell"><span class="eyebrow">System</span><b>8-inch J-tube</b><span class="sub">55-gal drum bell, drawn to scale</span></div>
    <div class="tb-cell"><span class="eyebrow">Burn pattern</span><b>Evening burn, out by bedtime</b><span class="sub">The bench carries the night</span></div>
    <div class="tb-cell"><span class="eyebrow">Bench</span><b>36 &times; 84 &times; 18 in</b><span class="sub">About 1.5 tons; needs a slab</span></div>
    <div class="tb-cell"><span class="eyebrow">Status</span><b style="color:var(--warn)">Check 1 open</b><span class="sub">Washington install rule: read first</span></div>
  </div>
</header>

<nav class="toc" aria-label="Sections">
  <a href="#how">How it works</a><a href="#checks">Checks</a><a href="#materials">Materials</a><a href="#sizes">Sizes</a><a href="#sheets">Sheets</a><a href="#build">Build</a><a href="#run">Run it</a><a href="#fixes">Fixes</a><a href="#numbers">Numbers</a><a href="#sources">Sources</a>
</nav>

<section id="how">
  <div class="sec-head"><span class="eyebrow">Principle</span><h2>How the heat moves</h2></div>
  {sheet('S-1', 'Gas path through core, drum, bench and chimney', 'Long section &middot; to scale, chimney shortened &middot; 8-inch', F.fig_flow(),
         'Room air is pulled down the feed tube, burns sideways through the tunnel and finishes burning in the insulated riser. The hot gas hits the drum lid, turns down, and heats the drum wall, which radiates into the room. What is left runs through the bench duct, where the sand and pebbles take most of the rest. It leaves at 100&ndash;200&deg;F; a woodstove&rsquo;s exhaust leaves at 350&ndash;500&deg;F. That gap is heat kept in the building.')}
</section>

<section id="checks">
  <div class="sec-head"><span class="eyebrow">Before you build</span><h2>Checks that decide whether and where</h2></div>
  <p class="prose">These are legal and life-safety calls, so they are yours. Each one shows what the record says and what is still open. Tick them off as you settle them; the ticks are saved in this browser only.</p>
  <ol class="checks">{checks}</ol>
  <div class="callout care">
    <h3>If check 1 comes back no</h3>
    <p>The lawful version is a certified wood stove, new or used-and-certified, on a hearth poured from your sand, cement and pebbles, with a masonry bench or wall beside it, outside the stove&rsquo;s listed clearances, to soak up and hold heat. The drum and loose pipe don&rsquo;t go in that version, and the chimney is listed parts either way. {INF}</p>
  </div>
</section>

<section id="materials">
  <div class="sec-head"><span class="eyebrow">Inventory</span><h2>Your materials, and where each one goes</h2></div>
  {materials}
  <h3>What the plan needs that isn&rsquo;t on your list</h3>
  {shopping}
</section>

<section id="sizes">
  <div class="sec-head"><span class="eyebrow">Dimension schedule</span><h2>Sizes</h2></div>
  <p class="prose">Letters match the drawings. The 8-inch column is what the sheets show. The 6-inch column is reference only: the drum&rsquo;s size changes the 6-inch tunnel and riser, so redraw before building at 6-inch. Most of these numbers come from experienced builders (the Wisners and Evans &amp; Jackson, as quoted on the permies.com forum), not from tested standards; that is the state of the field.</p>
  {sizes}
</section>

<section id="sheets">
  <div class="sec-head"><span class="eyebrow">Drawings</span><h2>Sheets</h2></div>
  <p class="prose">Drawn to scale from one set of numbers. Build to the numbers in the schedule, not by measuring the screen. On a phone, scroll each sheet sideways or pinch to zoom.</p>
  {sheet('S-2', 'Core section', 'Section on centerline &middot; to scale &middot; 8-inch', F.fig_core(DV),
         'The J-tube core under the drum. Wood stands in the feed tube and burns at the bottom; the flame is pulled sideways through the tunnel and up the insulated riser. The drum rim sits on the tunnel roof and the manifold wall, sealed with clay-sand.',
         notes=[
             'Mortar: thin clay slip or fireclay mortar. No Portland cement anywhere on this sheet except the slab.',
             'Riser insulation: perlite and clay slip, 1 : 6&ndash;9, packed between the brick shaft and the sleeve; or ceramic fiber blanket, with a respirator. A bare steel liner lasts one or two seasons, and loose perlite slumps.',
             'Measure G before setting the drum: riser top to the underside of the lid, or of the &frac14;-in disc if you add one.',
             'The drum must lift off for inspection, so seal its rim with clay-sand, not cement.',
             'The manifold floor sits below the duct inlet, so ash settles there instead of in the duct. Clean it through cleanout 1.',
         ])}
  {sheet('S-3', 'Plan and clearances', 'Plan &middot; to scale &middot; 8-inch', F.fig_plan(DV),
         'Footprint of the heater and bench with the clearance lines. Combustible walls, furniture and bedding stay outside the red dashed lines, or behind a ventilated shield inside the dotted one.',
         notes=[
             'Clearance lines are NFPA 211 values for unlisted stoves, from secondary sources. Confirm with the building official; this is check 7.',
             'Shield: 24-gauge sheet metal on non-combustible spacers with 1 in of air behind it, open at the top and bottom.',
             'The slab runs 18 in past the core on every side and under the whole bench.',
             f'The feed tube draws its air from the room. In a tight building, give the room a fresh-air inlet near the heater. {INF}',
         ])}
  {sheet('S-4', 'Bench section', 'Cross-section &middot; to scale &middot; 8-inch', F.fig_bench(DV),
         'The sleeping bench is a masonry box of dry sand and pebbles around the duct. Dry fill lets the pipe move as it heats and can be dug out to repair it.',
         notes=[
             'Lay the duct on a 3-in sand bed and paint it with clay slip so the fill beds tight against it.',
             'Fill with dry sand and pebbles in layers, tamping each one.',
             f'Within 2 ft of the manifold, cap with clay-sand (2&ndash;3 sand : 1 clay, no straw near the pipe) instead of concrete. {INF}',
             'Beyond that, a 3-in cap of 1:2:3 concrete with wire mesh, over a thin layer of sand so the cap can move.',
         ])}
  {sheet('S-5', 'Chimney and roof', 'Schematic &middot; not to scale', F.fig_chimney(),
         'Where the exhaust leaves the bench it turns up through a capped tee, runs up inside the building to a listed support, and passes through the roof in listed insulated chimney.',
         notes=[
             'The tee at the bottom is the cleanout, the priming port and the drip cap. The condensate is acidic.',
             'Keep the chimney inside the building as long as possible and exit near the peak. A warm chimney draws; a cold one can stall, and wall exits let wind push the system backwards.',
             'Once running, the exhaust should read 140&ndash;200&deg;F at the base. Below 140&deg;F it condenses.',
         ], legend=False)}
</section>

<section id="build">
  <div class="sec-head"><span class="eyebrow">Sequence</span><h2>Build it in this order</h2></div>
  {build_steps}
</section>

<section id="run">
  <div class="sec-head"><span class="eyebrow">Operation</span><h2>Run it</h2></div>
  <div class="callout stop">
    <h3>The sleeping rule</h3>
    <p>Never sleep with a fire in it. Burn in the evening while you are up: the drum heats the room while it burns, and the bench gives heat back overnight. Builders report bench tops of 100&ndash;120&deg;F at the hot end and 80&ndash;90&deg;F at the far end on 8-inch systems, and 130&ndash;140&deg;F after a full day of burning.</p>
  </div>
  {run_steps}
  <div class="callout care">
    <h3>Burn bans</h3>
    <p>In a Stage 1 ban, PSCAA and ORCAA don&rsquo;t allow uncertified devices unless the device is your only adequate source of heat and you hold an approved exemption (PSCAA) or have notified the agency (ORCAA). In Stage 2, no wood burning at all, with the same exception. PSCAA&rsquo;s last exemption approvals ran until August 31, 2026. &ldquo;Adequate source of heat&rdquo; means holding 70&deg;F at 3 ft above the floor in all normally inhabited areas. {REC}</p>
  </div>
</section>

<section id="fixes">
  <div class="sec-head"><span class="eyebrow">Troubleshooting</span><h2>Fixes</h2></div>
  {fixes}
</section>

<section id="numbers">
  <div class="sec-head"><span class="eyebrow">Performance</span><h2>What the numbers say</h2></div>
  {numbers}
</section>

<section id="sources">
  <div class="sec-head"><span class="eyebrow">Evidence trail</span><h2>Source record</h2></div>
  <p class="prose">This session&rsquo;s network blocked direct page loads, so every source was read through search-engine excerpts tied to these links; quoted wording is close paraphrase. Open the link before relying on any Class 3 item. Items research named but did not read: RCW 19.27.530 and IRC R315 (CO alarms), IRC R314 (smoke alarms), IRC R1003.9 (chimney height text), WAC 51-51-0105 (permit exemptions).</p>
  <details class="src"><summary>Show all {len(sources)} sources</summary><ol>{src_html}</ol></details>
</section>

<footer>
  <p>Prepared 27 Sep 2026 for Ryan. Class 3 items are Ryan&rsquo;s to decide; this sheet is the evidence for those decisions, not the decision.</p>
  <p>Labels: <span class="lbl rec">Record</span> a retrieved source says it. <span class="lbl inf">Inferred</span> worked out from recorded factors. <span class="lbl nir">Not in record</span> nothing retrieved supports it yet.</p>
</footer>
</div>
<script>{JS}</script>
'''

with open(OUT, 'w') as fh:
    fh.write(html)
print('wrote', OUT, len(html), 'bytes')

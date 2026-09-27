"""The plan-set drawings. Geometry is the 8-inch system, drawn to scale.

All positions are inches. Section views: x runs from the front face of the
feed tube toward the bench; y runs up from the top of the slab.
"""
from svglib import Sheet

# ----------------------------------------------------------------------------
# Core geometry (8-inch system).  Change here and every view follows.
# ----------------------------------------------------------------------------
G = dict(
    wall=2.5,        # firebrick on edge (wall thickness)
    floor=2.5,       # firebrick laid flat (floor / roof thickness)
    ins_under=2.0,   # insulating layer under the core
    slab=4.0, grav=4.0,
    feed=7.5,        # feed tube inside, square            (A)
    feed_h=16.0,     # feed tube height above tunnel floor  (B)
    tun_h=7.5,       # burn tunnel inside height            (C)
    roof=12.5,       # tunnel roof between shafts           (D)
    riser=7.5,       # riser inside, square                 (E)
    gap=2.0,         # riser top to drum lid                (G)
    sleeve=18.0,     # riser insulation sleeve OD
    drum_od=23.0, drum_id=22.5, drum_h=34.5,
    duct=8.0,        # duct OD                              (L)
    duct_bot=3.0,    # duct bottom above slab (sand bed)
    bench_h=18.0, bench_w=36.0, bench_len=84.0,  # (Q, P, N)
    cap=3.0,
    man_w=19.0,      # manifold box outside width (plan)
)


def core_x():
    g = G
    x = {}
    x['f0'] = 0.0
    x['f1'] = g['wall']
    x['f2'] = x['f1'] + g['feed']
    x['f3'] = x['f2'] + g['wall']
    x['r1'] = x['f2'] + g['roof']
    x['r2'] = x['r1'] + g['riser']
    x['rc'] = (x['r1'] + x['r2']) / 2
    x['rw1'] = x['r1'] - g['wall']
    x['rw2'] = x['r2'] + g['wall']
    x['s1'] = x['rc'] - g['sleeve'] / 2
    x['s2'] = x['rc'] + g['sleeve'] / 2
    x['d1'] = x['rc'] - g['drum_od'] / 2
    x['d2'] = x['rc'] + g['drum_od'] / 2
    x['di1'] = x['rc'] - g['drum_id'] / 2
    x['di2'] = x['rc'] + g['drum_id'] / 2
    x['m2'] = x['d2'] + 3.0
    x['m3'] = x['m2'] + g['wall']
    return x


def core_y():
    g = G
    y = {}
    y['ins'] = g['ins_under']
    y['fl'] = y['ins'] + g['floor']
    y['tt'] = y['fl'] + g['tun_h']
    y['rt'] = y['tt'] + g['floor']
    y['dt'] = y['rt'] + g['drum_h']
    y['riser_top'] = y['dt'] - 0.1 - g['gap']
    y['ft'] = y['fl'] + g['feed_h']
    return y


def derived():
    x, y = core_x(), core_y()
    g = G
    return {
        'riser_h': round(y['riser_top'] - y['fl'], 1),
        'annulus': round((g['drum_id'] - g['sleeve']) / 2, 2),
        'ins_t': round((g['sleeve'] - g['riser'] - 2 * g['wall']) / 2, 2),
        'feed_clear': round(x['d1'] - x['f3'], 2),
        'cover': g['bench_h'] - g['duct_bot'] - g['duct'],
        'bench_end': x['m3'] + g['bench_len'],
        'x': x, 'y': y,
    }


def roof_top(xx, y0, slope, x0=-25.0, t=5.0):
    return y0 - (xx - x0) * slope + t


# ----------------------------------------------------------------------------
# Sheet 1 - the whole gas path, long section (to scale, 3 px/in)
# ----------------------------------------------------------------------------
def fig_flow():
    x, y = core_x(), core_y()
    g = G
    s = Sheet('f1', 920, 600, 4.0, ox=150, oy=548,
              label='Long section of the whole heater showing the gas path: room air enters the feed tube, '
                    'burns in the tunnel, rises through the insulated riser, turns down inside the drum, '
                    'passes through the bench duct where the mass takes its heat, and leaves cool up the chimney.')
    bench_end = x['m3'] + g['bench_len']
    tx1, tx2 = bench_end + 1, bench_end + 1 + g['duct']
    tcx = (tx1 + tx2) / 2
    # The chimney is broken between brk1 and brk2 so the heater can be drawn
    # large; everything above the break is shifted down by the omitted length.
    brk1, brk2 = 56.0, 62.0
    y0, sl = 76.0, 0.05
    rline = lambda xx: y0 - (xx - tcx) * sl           # underside of roof
    rtop = lambda xx: rline(xx) + 4                   # top surface of roof
    top = max(rtop(tcx) + 36, rtop(tcx - 120) + 24) + 1
    db, dt = g['duct_bot'], g['duct_bot'] + g['duct']

    s.rect(-25, -4, 185, 0, 'conc')
    s.line(-25, -8, 185, -8, 'edge-lt')
    s.poly([(-25, rline(-25)), (185, rline(185)), (185, rtop(185)), (-25, rtop(-25))], 'edge', 'far')
    s.text(185, rtop(185), 'roof', cls='t-sm', anchor='end', dx=-4, dy=-8)

    # core, simplified
    s.rect(x['f0'], y['ins'], x['rw2'], y['fl'], 'brick')
    s.rect(x['f0'], y['fl'], x['f1'], y['ft'], 'brick')
    s.rect(x['f2'], y['rt'], x['f3'], y['ft'], 'brick')
    s.rect(x['f2'], y['tt'], x['r1'], y['rt'], 'brick')
    s.rect(x['s1'], y['rt'], x['r1'], y['riser_top'], 'ins')
    s.rect(x['r2'], y['fl'], x['s2'], y['riser_top'], 'ins')
    s.rect(x['s2'], 0, x['m3'], y['rt'], 'brick')
    s.rect(x['s2'] + 0.5, 0.5, x['m2'], y['tt'], None, 'void')
    s.rect(x['d1'], y['rt'], x['d2'], y['dt'], None, 'drum')
    # bench + duct
    s.rect(x['m3'], 0, bench_end, g['bench_h'], 'sand')
    s.rect(x['m2'] - 1, db, bench_end, dt, None, 'duct-in')
    s.line(x['m2'] - 1, db, bench_end, db, 'steel-thin')
    s.line(x['m2'] - 1, dt, bench_end, dt, 'steel-thin')
    # tee, vertical exit (broken), caps, roof collar
    s.rect(bench_end, db, tx1, dt, None, 'duct-in')
    for a, b in ((db - 3, brk1), (brk2, top)):
        s.rect(tx1, a, tx2, b, None, 'duct-in')
        s.line(tx1, a, tx1, b, 'steel-thin')
        s.line(tx2, a, tx2, b, 'steel-thin')
    for yb in (brk1, brk2):
        s.path(f"M{s.P(tx1 - 2, yb)} L{s.P(tcx - 1, yb + 0.8)} L{s.P(tcx + 1, yb - 0.8)} L{s.P(tx2 + 2, yb)}", 'brk')
    s.rect(tx1 - 0.8, db - 4.2, tx2 + 0.8, db - 3, None, 'cap')
    s.rect(tx1 - 3, top + 3, tx2 + 3, top + 4.2, None, 'cap')
    s.rect(tx1 - 2.2, rline(tcx) - 5, tx2 + 2.2, rtop(tcx) + 2, None, 'collar')

    # gas path
    s.flow([(x['f1'] + 3.75, y['ft'] + 17), (x['f1'] + 3.75, y['ft'] + 1)], 'cool')
    s.flow([(x['f1'] + 3.75, y['fl'] + 3), (x['r1'] + 2, y['fl'] + 3)], 'fire')
    s.flow([(x['rc'], y['fl'] + 5), (x['rc'], y['riser_top'] - 2)], 'fire')
    ann = (x['s2'] + x['di2']) / 2
    s.flow([(x['rc'], y['riser_top'] + 1), (ann, y['riser_top'] + 1), (ann, y['rt'] + 3)], 'warm')
    s.flow([(ann, y['rt'] - 1), (ann, (db + dt) / 2), (x['m3'] + 22, (db + dt) / 2)], 'warm')
    s.flow([(x['m3'] + 26, (db + dt) / 2), (bench_end - 3, (db + dt) / 2)], 'cool', 'fade')
    s.flow([(tcx, db + 2), (tcx, brk1 - 2)], 'cool')
    s.flow([(tcx, brk2 + 2), (tcx, top - 3)], 'cool')
    s.flow([(tcx, top + 5.5), (tcx, top + 13)], 'cool')

    # heat out: radiant from the drum, stored heat from the bench
    for k in range(3):
        yy = y['rt'] + 9 + k * 9
        s.flow([(x['d1'] - 1, yy), (x['d1'] - 5, yy)], 'fire', 'thin')
    for k in range(5):
        xx = x['m3'] + 10 + k * 16
        s.flow([(xx, g['bench_h'] + 1.2), (xx, g['bench_h'] + 6)], 'warm', 'thin')

    # labels
    s.text(x['f1'] + 1.0, y['ft'] + 13, '1  room air in', cls='t', anchor='end', dx=-4, dy=4)
    s.leader(x['r1'] - 3, y['fl'] + 3, -6, y['fl'] + 22, '2  burn tunnel', anchor='end')
    s.leader(x['rc'], y['riser_top'] - 12, x['rc'] - 7, y['dt'] + 12, '3  insulated riser', anchor='end')
    s.leader(x['d2'] - 1, y['dt'] - 2, x['d2'] + 8, y['dt'] + 12, '4  drum radiates into the room')
    s.leader(x['m2'] - 2, y['tt'] - 4, x['m2'] + 14, 36, '5  manifold')
    s.text(x['m3'] + 42, g['bench_h'] + 9, '6  bench stores heat for the night', cls='t', anchor='middle')
    s.leader(tcx, 45, tcx + 9, 45, '7  cool exhaust out')
    s.text(tx2 + 3, (brk1 + brk2) / 2, 'chimney shortened', cls='t-sm', dx=4, dy=4)
    s.leader(tx2 + 0.8, db - 3.6, tx2 + 9, db + 8, 'cleanout / priming cap', cls='t-sm')
    s.leader(tx2 + 2.2, rtop(tcx) + 1, tx2 + 9, rtop(tcx) + 8, 'listed roof pass-through', cls='t-sm')
    return s.render()


# ----------------------------------------------------------------------------
# Sheet 2 - core section (to scale, 8 px/in)
# ----------------------------------------------------------------------------
def fig_core(dv):
    x, y = core_x(), core_y()
    g = G
    s = Sheet('f2', 830, 565, 8, ox=200, oy=446,
              label='Section through the rocket core: feed tube, burn tunnel, insulated heat riser inside '
                    'the upturned 55-gallon drum, and the manifold that feeds the bench duct.')
    xr = x['m3'] + 8
    db, dt = g['duct_bot'], g['duct_bot'] + g['duct']

    s.rect(-14, -g['slab'] - g['grav'], xr, -g['slab'], 'grav', 'edge-lt')
    s.rect(-14, -g['slab'], xr, 0, 'conc')
    s.rect(-1, 0, x['rw2'], y['ins'], 'ins')

    # base masonry behind riser, manifold chamber, lid
    s.rect(x['rw2'], 0, x['s2'], y['rt'], 'brick')
    s.rect(x['s2'], 0.5, x['m2'], y['tt'], 'far', 'edge-lt')
    s.rect(x['s2'], 0, x['m3'], 0.5, 'cob', 'edge-lt')
    s.rect(x['m2'], 0.5, x['m3'], db, 'brick')
    s.rect(x['m2'], dt, x['m3'], y['tt'], 'brick')
    s.rect(x['di2'] - 0.75, y['tt'], x['m3'], y['rt'], 'brick')

    # bench stub + duct
    s.rect(x['m3'], 0, xr, g['bench_h'] - g['cap'], 'sand')
    s.rect(x['m3'], g['bench_h'] - g['cap'], xr, g['bench_h'], 'cob')
    s.rect(x['m2'] - 1.0, db, xr, dt, None, 'duct-in')
    s.line(x['m2'] - 1.0, db, xr, db, 'steel')
    s.line(x['m2'] - 1.0, dt, xr, dt, 'steel')
    s.breakline(xr, -g['slab'] - g['grav'], g['bench_h'] + 1)

    # firebrick floor and far walls of the passages
    s.rect(x['f0'], y['ins'], x['rw2'], y['fl'], 'brick')
    s.rect(x['f1'], y['fl'], x['r2'], y['tt'], 'far', 'edge-lt')
    s.rect(x['f1'], y['tt'], x['f2'], y['ft'], 'far', 'edge-lt')
    s.rect(x['r1'], y['tt'], x['r2'], y['riser_top'], 'far', 'edge-lt')
    # feed tube, roof, riser walls
    s.rect(x['f0'], y['fl'], x['f1'], y['ft'], 'brick')
    s.rect(x['f2'], y['rt'], x['f3'], y['ft'], 'brick')
    s.rect(x['f2'], y['tt'], x['r1'], y['rt'], 'brick')
    s.rect(x['rw1'], y['rt'], x['r1'], y['riser_top'], 'brick')
    s.rect(x['r2'], y['fl'], x['rw2'], y['riser_top'], 'brick')
    # riser insulation + sleeve
    s.rect(x['s1'], y['rt'], x['rw1'], y['riser_top'], 'ins')
    s.rect(x['rw2'], y['rt'], x['s2'], y['riser_top'], 'ins')
    s.line(x['s1'], y['rt'], x['s1'], y['riser_top'], 'steel-thin')
    s.line(x['s2'], y['rt'], x['s2'], y['riser_top'], 'steel-thin')

    # drum with its two rolling hoops, and clay-sand seal at the rim
    s.rect(x['d1'], y['rt'], x['d2'], y['dt'], None, 'drum')
    for hh in (y['rt'] + g['drum_h'] / 3, y['rt'] + 2 * g['drum_h'] / 3):
        s.line(x['d1'] - 0.35, hh, x['d1'], hh, 'steel')
        s.line(x['d2'], hh, x['d2'] + 0.35, hh, 'steel')
    for xx, sgn in ((x['d1'], -1), (x['d2'], 1)):
        s.poly([(xx, y['rt']), (xx + sgn * 1.6, y['rt']), (xx, y['rt'] + 1.6)], 'edge', 'cob')

    # wood standing in the feed tube, flame pulled into the tunnel
    for i, (w, top) in enumerate(((1.8, y['ft'] + 1.2), (2.2, y['ft'] + 2.4), (1.6, y['ft'] + 0.6))):
        x0 = x['f1'] + 0.7 + i * 2.35
        s.rect(x0, y['fl'] + 1.5, x0 + w, top, None, 'wood')
    s.path(f"M{s.P(x['f1'] + 0.5, y['fl'] + 0.2)} Q{s.P(x['f1'] + 4, y['fl'] + 5)} {s.P(x['f2'] + 3, y['fl'] + 3.2)} "
           f"Q{s.P(x['f2'] + 7, y['fl'] + 2)} {s.P(x['r1'] + 1, y['fl'] + 4)} "
           f"L{s.P(x['r1'] + 1, y['fl'] + 0.4)} Z", 'flame')

    # gas path
    s.flow([(x['f1'] + 3.75, y['ft'] + 8.8), (x['f1'] + 3.75, y['ft'] + 3.4)], 'cool')
    s.flow([(x['f2'] + 1, y['fl'] + 3.7), (x['r1'] + 1.5, y['fl'] + 3.7)], 'fire')
    s.flow([(x['rc'], y['fl'] + 6), (x['rc'], y['riser_top'] - 3)], 'fire')
    s.flow([(x['rc'] - 0.6, y['riser_top'] + 0.9), (x['s1'] - 1.1, y['riser_top'] + 0.9),
            (x['s1'] - 1.1, y['rt'] + 9)], 'warm')
    ann = (x['s2'] + x['di2']) / 2
    s.flow([(x['rc'] + 0.6, y['riser_top'] + 0.9), (ann, y['riser_top'] + 0.9),
            (ann, y['tt'] - 1.2), (x['m2'] - 2.0, y['tt'] - 1.2), (x['m2'] - 2.0, db + 5.2),
            (xr - 1.5, db + 4)], 'warm')

    # ---- dimensions -------------------------------------------------------
    by = -g['slab'] - g['grav'] - 3.2
    s.dim_h(x['f1'], x['f2'], by, 'A', dv['A'], ext_from=y['fl'])
    s.dim_h(x['f2'], x['r1'], by, 'D', dv['D'], ext_from=y['tt'])
    s.dim_h(x['r1'], x['r2'], by, 'E', dv['E'], ext_from=y['fl'])
    s.dim_v(y['fl'], y['ft'], -2.2, 'B', dv['B'], ext_from=x['f0'])
    s.dim_v(y['fl'], y['riser_top'], -22, 'F', dv['F'], ext_from=x['s1'], side='right')
    s.dim_v(y['riser_top'], y['dt'] - 0.1, x['d2'] + 4.5, 'G', dv['G'], ext_from=x['s2'], side='right')
    s.dim_h(x['s2'], x['di2'], 41, 'H', dv['H'], text_x=x['d2'] + 1.4)
    s.dim_h(x['rw2'], x['s2'], 37, 'J', dv['J'], text_x=x['d2'] + 1.4)
    s.dim_v(db, dt, xr - 1.0, 'L', dv['L'], side='right')

    # ---- labels -----------------------------------------------------------
    rx = x['d2'] + 9.5
    rx2 = xr + 2
    s.leader(x['d2'], 45, rx, 45, '55-gal drum, open end down')
    s.leader(x['s2'] - 0.2, 32, rx, 32, 'steel sleeve, 18 in OD')
    s.leader(x['rw2'] + 1, 28, rx, 28, 'riser insulation')
    s.leader(x['r2'] + 1.2, 24, rx, 24, 'firebrick riser shaft')
    s.leader(x['d2'] + 0.5, y['rt'] + 0.5, rx, 20, 'clay-sand seal')
    s.leader(x['m3'] + 4, g['bench_h'] - 1.5, rx2, 16, 'clay-sand cap near manifold')
    s.leader(x['m2'] - 3.2, y['tt'] - 7.0, rx2, 12.5, 'manifold + ash trap')
    s.leader(x['m3'] + 5.5, 5.5, rx2, 0.5, 'bench fill')
    s.text(-14, -g['slab'] / 2, 'concrete slab', cls='t-sm', dx=3, dy=4)
    s.text(-14, -g['slab'] - g['grav'] / 2, 'compacted gravel', cls='t-sm', dx=3, dy=4)
    s.text(x['f1'] + 3.75, y['ft'] + 10.2, 'air in', cls='t-cool', anchor='middle')
    s.text(x['f2'] + 4, y['fl'] + 6.2, 'flame', cls='t-fire', anchor='middle')
    s.leader(x['f2'] + 7, y['tt'] + 1.2, x['f2'] + 1.5, y['tt'] + 25, 'burn tunnel roof', anchor='end')
    s.leader(x['f0'] + 0.3, y['ins'] - 1.0, -2.5, y['ins'] + 0.8, 'insulating layer', anchor='end', cls='t-sm')
    return s.render()


# ----------------------------------------------------------------------------
# Sheet 3 - plan view with clearance envelope (to scale, 3 px/in)
# ----------------------------------------------------------------------------
def fig_plan(dv):
    x, _ = core_x(), core_y()
    g = G
    s = Sheet('f3', 850, 440, 3.0, ox=290, oy=228,
              label='Plan view of the heater and sleeping bench with the clearance lines that must stay free '
                    'of combustible walls and furniture.')
    bench_end = x['m3'] + g['bench_len']
    tx1, tx2 = bench_end + 1, bench_end + 1 + g['duct']
    tcx = (tx1 + tx2) / 2
    hw = g['bench_w'] / 2
    rc = x['rc']
    R = g['drum_od'] / 2
    mw = g['man_w'] / 2

    # clearance envelopes first
    s.circle(rc, 0, R + 36, 'clr')
    s.circle(rc, 0, R + 12, 'clr2')
    s.circle(tcx, 0, g['duct'] / 2 + 18, 'clr')

    # slab (18 in beyond the core, full bench footprint)
    ex = R + 18
    s.poly([(-18, -ex), (x['m3'], -ex), (x['m3'], -hw), (tx2 + 2, -hw), (tx2 + 2, hw), (x['m3'], hw),
            (x['m3'], ex), (-18, ex)], 'edge-lt', 'far')
    # core
    s.rect(x['f0'], -(g['feed'] / 2 + g['wall']), x['f3'], g['feed'] / 2 + g['wall'], 'brick')
    s.rect(x['f1'], -g['feed'] / 2, x['f2'], g['feed'] / 2, None, 'void')
    s.rect(x['f3'], -(g['feed'] / 2 + g['wall']), x['rw2'], g['feed'] / 2 + g['wall'], None, 'hidden')
    s.rect(x['s2'] - 0.5, -mw, x['m3'], mw, 'brick')
    s.rect(x['s2'], -(mw - g['wall']), x['m2'], mw - g['wall'], None, 'hidden')
    s.circle(rc, 0, R, 'drum-plan')
    s.circle(rc, 0, g['sleeve'] / 2, 'hidden')
    s.rect(x['m2'] - 6.5, -mw - 1.6, x['m2'] - 0.5, -mw, None, 'cap')       # manifold cleanout
    # bench + duct + tee
    s.rect(x['m3'], -hw, bench_end, hw, 'sand')
    s.rect(x['m3'], -g['duct'] / 2, tx1, g['duct'] / 2, None, 'hidden')
    s.circle(tcx, 0, g['duct'] / 2, 'pipe-plan')

    # dims
    s.dim_h(x['m3'], bench_end, -hw - 7, 'N', dv['N'], ext_from=-hw)
    s.dim_v(-hw, hw, bench_end + 30, 'P', dv['P'], ext_from=bench_end, side='right')
    s.dim_h(rc + R, rc + R + 36, 34, None, '36 in', above=True)
    s.dim_h(rc + R, rc + R + 12, 23, None, '12 in', above=True)

    # labels
    s.leader(-9, 0, -30, 27, 'hearth: slab, 18 in past core', anchor='end', cls='t-sm')
    s.leader(x['f1'] + 3.75, 0, -30, 10, 'feed tube', anchor='end', cls='t-sm')
    s.leader(x['m2'] - 3.5, -mw - 1.2, x['m2'] - 3.5, -41, 'cleanout 1 (manifold)', cls='t-sm')
    s.text((x['m3'] + bench_end) / 2, 6, 'sleeping bench', cls='t', anchor='middle')
    s.text((x['m3'] + bench_end) / 2, -11, 'duct runs down the middle', cls='t-sm', anchor='middle')
    s.leader(tcx, -2, tcx - 12, -31, 'cleanout 2 + chimney above', anchor='end', cls='t-sm')
    s.text(rc, R + 36 + 3.5, 'unshielded: combustibles stay outside', cls='t-sm t-warn', anchor='middle')
    s.text(rc, -(R + 12) - 9.5, 'with ventilated shield', cls='t-sm t-warn', anchor='middle')
    s.text(tcx, g['duct'] / 2 + 18 + 3.5, 'single-wall pipe: 18 in', cls='t-sm t-warn', anchor='middle')
    return s.render()


# ----------------------------------------------------------------------------
# Sheet 4 - bench cross-section (to scale, 8 px/in)
# ----------------------------------------------------------------------------
def fig_bench(dv):
    g = G
    s = Sheet('f4', 790, 372, 8, ox=300, oy=254,
              label='Cross-section through the sleeping bench: slab on gravel, masonry shell, dry sand and '
                    'pebble fill around the 8-inch duct, and a cap.')
    hw = g['bench_w'] / 2
    wall = 4.0
    db, dt = g['duct_bot'], g['duct_bot'] + g['duct']
    cy = (db + dt) / 2
    s.rect(-hw - 6, -g['slab'] - g['grav'], hw + 6, -g['slab'], 'grav', 'edge-lt')
    s.rect(-hw - 6, -g['slab'], hw + 6, 0, 'conc')
    s.rect(-hw, 0, -hw + wall, g['bench_h'] - g['cap'], 'conc')
    s.rect(hw - wall, 0, hw, g['bench_h'] - g['cap'], 'conc')
    s.rect(-hw + wall, 0, hw - wall, g['bench_h'] - g['cap'], 'sand')
    s.rect(-hw, g['bench_h'] - g['cap'], hw, g['bench_h'], 'conc')
    s.line(-hw + 1, g['bench_h'] - g['cap'] + 1.3, hw - 1, g['bench_h'] - g['cap'] + 1.3, 'mesh')
    s.circle(0, cy, g['duct'] / 2 + 0.35, 'edge-lt', 'cob')     # clay slip skin on the pipe
    s.circle(0, cy, g['duct'] / 2, 'pipe-sec')
    s.rect(-hw + 1, g['bench_h'], hw - 1, g['bench_h'] + 2.2, None, 'pad')

    s.dim_v(0, g['bench_h'], -hw - 3, 'Q', dv['Q'])
    s.dim_h(-hw, hw, -g['slab'] - g['grav'] - 3.5, 'P', dv['P'], ext_from=0)
    s.dim_v(0, db, 6.5, None, f'{db:g} in', side='right')
    s.dim_v(dt, g['bench_h'], 6.5, 'R', dv['R'], side='right')
    s.dim_h(-g['duct'] / 2, g['duct'] / 2, cy + 1.2, 'L', dv['L'], above=True)

    lx = hw + 5
    s.leader(hw - 2, g['bench_h'] + 1.1, lx, g['bench_h'] + 5, 'sleeping pad')
    s.leader(hw - 3, g['bench_h'] - 1.0, lx, g['bench_h'] - 1.0, 'cap: 1:2:3 concrete + wire mesh')
    s.leader(hw - 2, 9, lx, 9, 'shell: block, poured concrete, stone or cob')
    s.leader(g['duct'] / 2 + 3.5, 3.2, lx, 3.2, 'dry sand + pebble fill, tamped')
    s.leader(hw + 3, -g['slab'] / 2, lx + 3, -g['slab'] / 2 - 2.6, 'slab on grade')
    s.leader(-g['duct'] / 2 - 0.2, cy + 1.5, -hw - 9, cy + 9, 'duct', anchor='end')
    s.leader(-g['duct'] / 2 - 0.1, cy - 1.8, -hw - 9, cy - 4, 'clay slip skin', anchor='end', cls='t-sm')
    return s.render()


# ----------------------------------------------------------------------------
# Sheet 5 - chimney exit and roof termination (schematic, 2.2 px/in)
# ----------------------------------------------------------------------------
def fig_chimney():
    s = Sheet('f5', 800, 560, 2.2, ox=260, oy=520,
              label='Chimney exit: a capped tee at the bottom, pipe up to a listed support, a listed insulated '
                    'chimney through the roof, and a top at least 3 feet above the roof and 2 feet above '
                    'anything within 10 feet.')
    px, pr = 60.0, 4.0
    ceiling = 90.0
    rline = lambda xx: 125 - xx * 0.12
    rtop = lambda xx: rline(xx) + 4
    top = max(rtop(px) + 36, rtop(px - 120) + 24) + 1.5
    s.rect(-100, -6, 240, 0, 'conc')
    s.rect(-100, 0, px - pr - 2, 18, 'sand')
    s.breakline(-100, 0, 18)
    # tee with drip / cleanout cap, and the duct coming in from the bench
    s.rect(px - pr - 2, 3, px - pr, 11, None, 'duct-in')
    s.rect(px - pr, 1, px + pr, top, None, 'duct-in')
    s.rect(px - pr - 1, -0.3, px + pr + 1, 1.0, None, 'cap')
    s.line(px - pr, 1, px - pr, 3, 'steel-thin')
    s.line(px - pr, 11, px - pr, top, 'steel-thin')
    s.line(px + pr, 1, px + pr, top, 'steel-thin')
    # ceiling and listed support box
    s.line(-100, ceiling, 240, ceiling, 'edge')
    s.rect(px - 8, ceiling - 5, px + 8, ceiling + 2, None, 'collar')
    # listed insulated chimney from the support up
    s.rect(px - 6, ceiling + 2, px + 6, top, None, 'classA')
    # roof, flashing, storm collar
    s.poly([(-100, rline(-100)), (240, rline(240)), (240, rtop(240)), (-100, rtop(-100))], 'edge', 'far')
    s.poly([(px - 16, rtop(px - 16) + 0.4), (px + 16, rtop(px + 16) + 0.4), (px + 16, rtop(px + 16) + 1.4),
            (px - 16, rtop(px - 16) + 1.4)], 'steel-thin')
    s.rect(px - 8, rtop(px) + 5, px + 8, rtop(px) + 7, None, 'collar')
    # cap with spark screen
    s.rect(px - 6, top, px + 6, top + 5, None, 'screen')
    s.rect(px - 10, top + 5, px + 10, top + 6.6, None, 'cap')

    # the 3-2-10 rule
    s.dim_v(rtop(px), top, px + 28, None, '3 ft min', side='right', ext_from=px + 6)
    xr10 = px - 120
    s.line(xr10, rtop(xr10), xr10, top + 16, 'ext')
    s.line(px, top + 6.6, px, top + 16, 'ext')
    s.dim_h(xr10, px, top + 14, None, '10 ft', above=True)
    s.dim_v(rtop(xr10), top, xr10 - 6, None, '2 ft min', side='left')
    s.line(xr10, top, px - 6, top, 'ext')

    s.leader(px + pr + 0.5, 0.4, px + 40, 8, 'tee: cleanout, priming port, drip cap', cls='t-sm')
    s.leader(px + pr, 50, px + 40, 50, 'pipe in the room: 18 in to combustibles', cls='t-sm')
    s.leader(px + 8, ceiling - 1.5, px + 40, ceiling - 8, 'listed ceiling support / firestop', cls='t-sm')
    s.leader(px + 6, ceiling + 10, px + 40, ceiling + 5, 'listed insulated chimney', cls='t-sm')
    s.leader(px + 8, rtop(px) + 6, px + 40, rtop(px) + 4, 'storm collar + flashing', cls='t-sm')
    s.leader(px + 10, top + 6, px + 40, top + 22, 'cap with spark screen', cls='t-sm')
    s.text(-100, 9, 'bench end', cls='t-sm', dx=16, dy=4)
    s.text(-100, ceiling, 'ceiling', cls='t-sm', dx=4, dy=-6)
    s.text(240, rtop(240), 'roof', cls='t-sm', anchor='end', dx=-4, dy=-6)
    return s.render()

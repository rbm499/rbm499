"""Tiny helpers for hand-built, to-scale SVG plan sheets.

Every drawing works in inches with y pointing UP from the slab top (y=0),
and converts to pixels through a Sheet's scale and origin.
"""
import html


def esc(s):
    return html.escape(str(s), quote=True)


class Sheet:
    def __init__(self, pid, w, h, scale, ox, oy, label):
        self.pid = pid          # id prefix, unique per figure
        self.w, self.h = w, h   # viewBox size (px)
        self.s = scale          # px per inch
        self.ox, self.oy = ox, oy  # pixel position of (x=0, y=0)
        self.label = label
        self.defs = []
        self.body = []
        self._patterns()

    # ---- coordinate transforms -------------------------------------------
    def X(self, x):
        return round(self.ox + x * self.s, 2)

    def Y(self, y):
        return round(self.oy - y * self.s, 2)

    def L(self, d):
        return round(d * self.s, 2)

    # ---- defs ---------------------------------------------------------------
    def _patterns(self):
        p = self.pid
        self.defs += [
            # firebrick: tinted fill + cross hatch
            f'<pattern id="{p}-brick" width="8" height="8" patternUnits="userSpaceOnUse">'
            f'<rect width="8" height="8" class="pf-brick"/>'
            f'<path d="M0 8L8 0M-2 2L2 -2M6 10L10 6" class="pl"/></pattern>',
            # insulation: tinted fill + stipple
            f'<pattern id="{p}-ins" width="9" height="9" patternUnits="userSpaceOnUse">'
            f'<rect width="9" height="9" class="pf-ins"/>'
            f'<circle cx="2" cy="2" r=".9" class="pd"/><circle cx="6.5" cy="5.5" r=".9" class="pd"/>'
            f'<circle cx="3.5" cy="7.5" r=".6" class="pd"/></pattern>',
            # concrete: fill + aggregate specks
            f'<pattern id="{p}-conc" width="16" height="12" patternUnits="userSpaceOnUse">'
            f'<rect width="16" height="12" class="pf-conc"/>'
            f'<path d="M2 3l2.2 0 -1.1 -2z M10 8l2.6 0 -1.3 -2.3z" class="pd"/>'
            f'<circle cx="7" cy="4" r=".8" class="pd"/><circle cx="13.5" cy="2.5" r=".6" class="pd"/>'
            f'<circle cx="4.5" cy="9.5" r=".7" class="pd"/></pattern>',
            # sand / gravel fill: fill + small open circles
            f'<pattern id="{p}-sand" width="12" height="10" patternUnits="userSpaceOnUse">'
            f'<rect width="12" height="10" class="pf-sand"/>'
            f'<circle cx="3" cy="3" r="1.4" class="po"/><circle cx="9" cy="7" r="1.8" class="po"/>'
            f'<circle cx="8.5" cy="1.5" r=".7" class="pd"/><circle cx="2" cy="8" r=".7" class="pd"/></pattern>',
            # compacted gravel base: bigger stones
            f'<pattern id="{p}-grav" width="18" height="12" patternUnits="userSpaceOnUse">'
            f'<rect width="18" height="12" class="pf-grav"/>'
            f'<ellipse cx="4" cy="4" rx="3" ry="2" class="po"/><ellipse cx="13" cy="8" rx="3.5" ry="2.3" class="po"/>'
            f'<circle cx="11" cy="2" r="1" class="pd"/></pattern>',
            # cob / clay-sand
            f'<pattern id="{p}-cob" width="10" height="10" patternUnits="userSpaceOnUse">'
            f'<rect width="10" height="10" class="pf-cob"/>'
            f'<path d="M1 7q2 -2 4 0M5 3q2 -2 4 0" class="pl"/></pattern>',
            # "beyond the cut" surface (far wall of a passage)
            f'<pattern id="{p}-far" width="6" height="6" patternUnits="userSpaceOnUse">'
            f'<rect width="6" height="6" class="pf-far"/></pattern>',
        ]
        for name in ('fire', 'warm', 'cool', 'ink'):
            self.defs.append(
                f'<marker id="{p}-ah-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
                f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M0 0L10 5L0 10z" class="ah-{name}"/></marker>')

    def fill(self, kind):
        return f'url(#{self.pid}-{kind})'

    # ---- primitives (inch coordinates) ---------------------------------------
    def rect(self, x1, y1, x2, y2, kind=None, cls='edge', extra=''):
        x, y = self.X(min(x1, x2)), self.Y(max(y1, y2))
        w, h = self.L(abs(x2 - x1)), self.L(abs(y2 - y1))
        f = f' fill="{self.fill(kind)}"' if kind else ''
        self.body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{f} class="{cls}" {extra}/>')

    def line(self, x1, y1, x2, y2, cls='edge', extra=''):
        self.body.append(
            f'<line x1="{self.X(x1)}" y1="{self.Y(y1)}" x2="{self.X(x2)}" y2="{self.Y(y2)}" class="{cls}" {extra}/>')

    def poly(self, pts, cls='edge', kind=None, closed=True):
        d = ' '.join(f'{self.X(x)},{self.Y(y)}' for x, y in pts)
        f = f' fill="{self.fill(kind)}"' if kind else ''
        tag = 'polygon' if closed else 'polyline'
        self.body.append(f'<{tag} points="{d}"{f} class="{cls}"/>')

    def circle(self, cx, cy, r, cls='edge', kind=None):
        f = f' fill="{self.fill(kind)}"' if kind else ''
        self.body.append(f'<circle cx="{self.X(cx)}" cy="{self.Y(cy)}" r="{self.L(r)}"{f} class="{cls}"/>')

    def path(self, d, cls='edge', extra=''):
        """d uses inch coords wrapped like {x:y} tokens -> converted."""
        self.body.append(f'<path d="{d}" class="{cls}" {extra}/>')

    def P(self, x, y):
        return f'{self.X(x)} {self.Y(y)}'

    def flow(self, pts, temp, cls_extra=''):
        """Gas-path polyline with arrowhead, colored by temperature."""
        d = 'M' + ' L'.join(self.P(x, y) for x, y in pts)
        self.body.append(
            f'<path d="{d}" class="gas g-{temp} {cls_extra}" marker-end="url(#{self.pid}-ah-{temp})"/>')

    def text(self, x, y, s, cls='t', anchor='start', dx=0, dy=0, attrs=''):
        self.body.append(
            f'<text x="{round(self.X(x) + dx, 2)}" y="{round(self.Y(y) + dy, 2)}" class="{cls}" '
            f'text-anchor="{anchor}" {attrs}>{s}</text>')

    def raw(self, s):
        self.body.append(s)

    # ---- annotations -------------------------------------------------------------
    def leader(self, x1, y1, x2, y2, label, anchor='start', cls='t'):
        """Leader line from a point on the drawing (x1,y1) to a label at (x2,y2)."""
        self.body.append(
            f'<path d="M{self.P(x1, y1)} L{self.P(x2, y2)}" class="lead"/>'
            f'<circle cx="{self.X(x1)}" cy="{self.Y(y1)}" r="1.8" class="dot"/>')
        dx = 4 if anchor == 'start' else (-4 if anchor == 'end' else 0)
        self.text(x2, y2, label, cls=cls, anchor=anchor, dx=dx, dy=4)

    def tag(self, x, y, letter, key=None):
        """Circled dimension letter; key links to the size table."""
        cx, cy = self.X(x), self.Y(y)
        k = f' data-key="{key or letter}"'
        self.body.append(
            f'<g class="tag"{k}><circle cx="{cx}" cy="{cy}" r="8.5"/>'
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle">{letter}</text></g>')

    def dim_h(self, x1, x2, y, letter=None, value='', key=None, ext_from=None, above=True, text_x=None):
        """Horizontal dimension line at height y between x1 and x2.

        text_x: put the label at this x (anchored start, on the line) instead of
        centred - for dimensions too narrow to hold their own label.
        """
        X1, X2, Yp = self.X(x1), self.X(x2), self.Y(y)
        parts = [f'<line x1="{X1}" y1="{Yp}" x2="{X2}" y2="{Yp}" class="dim"/>',
                 f'<line x1="{X1}" y1="{Yp - 5}" x2="{X1}" y2="{Yp + 5}" class="dim"/>',
                 f'<line x1="{X2}" y1="{Yp - 5}" x2="{X2}" y2="{Yp + 5}" class="dim"/>']
        if ext_from is not None:
            for xx in (X1, X2):
                parts.append(f'<line x1="{xx}" y1="{self.Y(ext_from)}" x2="{xx}" y2="{Yp}" class="ext"/>')
        label = self._dimlabel(letter, value, key)
        if text_x is not None:
            parts.append(f'<line x1="{X2}" y1="{Yp}" x2="{self.X(text_x) - 3}" y2="{Yp}" class="ext"/>')
            parts.append(f'<text x="{self.X(text_x)}" y="{Yp + 4}" class="t-dim" text-anchor="start">{label}</text>')
            self.body.append(''.join(parts))
            return
        self.body.append(''.join(parts))
        mid = (x1 + x2) / 2
        off = -6 if above else 14
        self.body.append(
            f'<text x="{self.X(mid)}" y="{Yp + off}" class="t-dim" text-anchor="middle">{label}</text>')

    def dim_v(self, y1, y2, x, letter=None, value='', key=None, ext_from=None, side='left'):
        X, Y1, Y2 = self.X(x), self.Y(y1), self.Y(y2)
        parts = [f'<line x1="{X}" y1="{Y1}" x2="{X}" y2="{Y2}" class="dim"/>',
                 f'<line x1="{X - 5}" y1="{Y1}" x2="{X + 5}" y2="{Y1}" class="dim"/>',
                 f'<line x1="{X - 5}" y1="{Y2}" x2="{X + 5}" y2="{Y2}" class="dim"/>']
        if ext_from is not None:
            for yy in (Y1, Y2):
                parts.append(f'<line x1="{self.X(ext_from)}" y1="{yy}" x2="{X}" y2="{yy}" class="ext"/>')
        self.body.append(''.join(parts))
        mid = self.Y((y1 + y2) / 2)
        label = self._dimlabel(letter, value, key)
        if side == 'left':
            self.body.append(f'<text x="{X - 8}" y="{mid + 4}" class="t-dim" text-anchor="end">{label}</text>')
        else:
            self.body.append(f'<text x="{X + 8}" y="{mid + 4}" class="t-dim" text-anchor="start">{label}</text>')

    @staticmethod
    def _dimlabel(letter, value, key):
        if letter:
            k = key or letter
            return (f'<tspan class="t-key">{letter}</tspan> '
                    f'<tspan class="dv" data-d="{k}">{esc(value)}</tspan>')
        return esc(value)

    def breakline(self, x, y1, y2):
        """Zig-zag break line (drawing continues)."""
        X = self.X(x)
        ya, yb = self.Y(y1), self.Y(y2)
        mid = (ya + yb) / 2
        self.body.append(
            f'<path d="M{X} {ya} L{X} {mid + 8} L{X - 6} {mid + 3} L{X + 6} {mid - 3} L{X} {mid - 8} L{X} {yb}" '
            f'class="brk"/>')

    def render(self, extra_cls=''):
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(self.label)}" '
                f'class="dwg {extra_cls}" xmlns="http://www.w3.org/2000/svg">'
                f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')

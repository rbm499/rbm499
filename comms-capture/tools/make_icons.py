#!/usr/bin/env python3
"""Draw the home-screen icon (two chat bubbles) as PNGs with only the standard library."""
import pathlib, struct, zlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "server" / "commscap" / "ui"
BLUE, WHITE, SOFT = (29, 95, 168, 255), (255, 255, 255, 255), (190, 214, 240, 255)

def png(size):
    px = [[BLUE] * size for _ in range(size)]
    def rrect(x0, y0, x1, y1, r, c):
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                dx = max(x0 + r - x, 0, x - (x1 - r - 1)); dy = max(y0 + r - y, 0, y - (y1 - r - 1))
                if dx * dx + dy * dy <= r * r: px[y][x] = c
    u = size / 100.0
    rrect(14*u, 22*u, 68*u, 54*u, 9*u, SOFT)      # incoming bubble (left)
    rrect(32*u, 46*u, 86*u, 78*u, 9*u, WHITE)     # outgoing bubble (right, in front)
    for i in range(3):                              # three text lines in the front bubble
        rrect(40*u, (55 + i*7)*u, (78 - (i == 2)*18)*u, (58 + i*7)*u, 1.5*u, BLUE)
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in px)
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

for n in (192, 512):
    (OUT / f"icon-{n}.png").write_bytes(png(n))
    print("wrote", OUT / f"icon-{n}.png")

#!/usr/bin/env python3
"""Host test of runtime/nvn/output_scale.c's 1x dynamic resolution (RES_DYN1X, output_scale_dyn1_step): the scene at
the Switch's 900 lines while the GPU's time per real frame plus frame generation's fits 94% of the frame, down in 5%
steps to 720 lines (0.80) while it doesn't, at least 3 s between changes, back up when the next step's estimate fits
90% for 2 s; a gap over 250 ms (loading, menus) starts the window again. The function is cut out of the file.
Run: python3 tools/test_dyn1x.py
"""
import pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'runtime/nvn/output_scale.c').read_text()
i = SRC.index('static double g_d1 = 1.0')
mod = SRC[i:SRC.index('static double dyn1_update(', i)]

C = r'''
#include <math.h>
#include <stdio.h>
#include <stdbool.h>
#define SCENE_LINES 900.0
static int nlog;
#define LOG(...) (nlog++, printf(__VA_ARGS__))
''' + mod + r'''
static int fails;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)
static double t, busy;
// n real frames at 33.3 ms, each with gpu ms of GPU work, frame generation fg ms
static double run(int n, double gpu, double fg) {
    double s = 0;
    for (int i = 0; i < n; i++) { t += 1.0 / 30, busy += gpu * 1e6; s = output_scale_dyn1_step(t, -1, busy, fg, 1000.0 / 30); }
    return s;
}
int main(void) {
    t = 10;
    CHECK(run(300, 25.0, 3.0) == 1.0);        // the Odin in the open: 28 of 33.3 ms - 1x stays (10 s)
    CHECK(nlog == 0);
    CHECK(run(16, 28.8, 3.0) == 0.95);        // a dense place: 31.8 ms - one step down after half a second
    CHECK(run(60, 28.8, 3.0) == 0.95);        // not again within 3 s
    CHECK(run(40, 28.8, 3.0) == 0.90);        // still too slow after 3 s: the next step
    CHECK(run(400, 33.0, 3.0) == 0.80);       // far over: down to 720 lines, never below
    CHECK(run(300, 26.0, 3.0) == 0.80);       // 26 x (0.85/0.8)^2 + 3 = 32.4: no room for the next step - holds
    CHECK(run(450, 20.0, 3.0) == 1.0);        // the open again: back up, a step every ~3 s, to 1x
    int n0 = nlog;
    t += 2.0;                                  // a loading screen: a 2 s gap
    CHECK(run(10, 40.0, 3.0) == 1.0 && nlog == n0);  // (the window starts again: no decision from the gap)
    t += 1.0;                                  // (another gap: the next window without those frames)
    CHECK(run(300, 26.5, 0) == 1.0);          // frame generation off: 26.5 of 33.3 - 1x
    if (fails) return 1;
    printf("1x dynamic: holds 1x in the open, steps down in dense places to 720 lines at most, 3 s apart, back up with room, ignores gaps (%d changes)\n", nlog);
    return 0;
}
'''
cc = shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
with tempfile.TemporaryDirectory() as d:
    c = pathlib.Path(d) / 't.c'
    c.write_text(C)
    exe = pathlib.Path(d) / 't'
    flags = ['-fsanitize=address,undefined'] if sys.platform.startswith('linux') else []
    r = subprocess.run([cc, '-std=gnu11', '-Wall', '-Wno-unused-function', *flags, str(c), '-o', str(exe), '-lm'], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr); sys.exit(1)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    print(r.stdout.splitlines()[-1] if r.returncode == 0 else r.stdout, end='\n'); print(r.stderr, end='', file=sys.stderr)
    sys.exit(r.returncode)

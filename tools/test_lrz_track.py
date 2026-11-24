#!/usr/bin/env python3
"""Host test of runtime/nvn/vulkan/exec.c's LRZ prediction (Amaral.16, lz_*): Turnip's rules (tu_lrz.cc, Mesa
8e0f6be875) mirrored per depth target - a clear over the whole image makes it valid, a load keeps what the last pass left;
a depth write with ALWAYS, a first depth-tested draw whose fragment shader writes depth (none before it with a
direction), a write against the direction and a clear of part of the image make it invalid until the next whole clear;
a shader writing depth after a direction is set doesn't. The module is cut out of exec.c and built against stand-ins.
Run: python3 tools/test_lrz_track.py
"""
import pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'runtime/nvn/vulkan/exec.c').read_text()
i = SRC.index('enum { LZ_ALWAYS, LZ_FS_DEPTH')
mod = SRC[i:SRC.index('static void vk_end_pass_at(int line);', i)]

C = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef enum { VK_COMPARE_OP_NEVER, VK_COMPARE_OP_LESS, VK_COMPARE_OP_EQUAL, VK_COMPARE_OP_LESS_OR_EQUAL,
               VK_COMPARE_OP_GREATER, VK_COMPARE_OP_NOT_EQUAL, VK_COMPARE_OP_GREATER_OR_EQUAL, VK_COMPARE_OP_ALWAYS } VkCompareOp;
static char logbuf[8192]; static size_t logn;
#define LOG(...) (logn += (size_t)snprintf(logbuf + logn, sizeof logbuf - logn, __VA_ARGS__))
static uint64_t hmix(uint64_t h, const void *p, size_t n) { (void)p; return h ^ n; }
''' + mod + r'''
static int fails;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)
int main(void) {
    int depthA, depthB;
    const void *A = &depthA, *B = &depthB;
    // a load of a never-cleared image: invalid
    lz_begin(A, false, 1600, 900, 1600, 900); CHECK(!lz_valid); lz_end();
    // a whole clear: valid, and kept by the next load
    lz_begin(A, true, 1600, 900, 1600, 900); CHECK(lz_valid);
    lz_draw(true, true, VK_COMPARE_OP_LESS_OR_EQUAL, false, false, 1, 0, false); CHECK(lz_valid); lz_end();
    lz_begin(A, false, 1600, 900, 1600, 900); CHECK(lz_valid);
    // a shader writing depth after the direction is known: still valid
    lz_draw(true, true, VK_COMPARE_OP_LESS, false, false, 2, 0, false);
    lz_draw(true, false, VK_COMPARE_OP_LESS, true, false, 3, 0, false); CHECK(lz_valid);
    lz_end();
    // the next pass (a break): its first depth-tested draw writes depth in the shader - invalid, for later passes too
    lz_begin(A, false, 1600, 900, 1600, 900); CHECK(lz_valid);
    lz_draw(false, false, VK_COMPARE_OP_ALWAYS, true, false, 4, 0, false); CHECK(lz_valid);  // (no depth test: ignored)
    lz_draw(true, false, VK_COMPARE_OP_LESS, true, false, 5, 0, false); CHECK(!lz_valid); lz_end();
    lz_begin(A, false, 1600, 900, 1600, 900); CHECK(!lz_valid); lz_end();
    // another image is apart; ALWAYS with a write makes it invalid
    lz_begin(B, true, 800, 450, 800, 450); CHECK(lz_valid);
    lz_draw(true, true, VK_COMPARE_OP_ALWAYS, false, false, 6, 0, false); CHECK(!lz_valid); lz_end();
    // a clear of part of the image: valid in its pass, invalid after it
    lz_begin(A, true, 1600, 800, 1600, 900); CHECK(lz_valid); lz_end();
    lz_begin(A, false, 1600, 900, 1600, 900); CHECK(!lz_valid); lz_end();
    // a write against the direction
    lz_begin(A, true, 1600, 900, 1600, 900);
    lz_draw(true, true, VK_COMPARE_OP_LESS, false, false, 7, 0, false);
    lz_draw(true, true, VK_COMPARE_OP_GREATER, false, false, 8, 0, false); CHECK(!lz_valid); lz_end();
    // our clear by a draw is its own reason
    lz_begin(B, true, 800, 450, 800, 450);
    lz_draw(true, true, VK_COMPARE_OP_ALWAYS, false, false, 0, 0, true); CHECK(!lz_valid); lz_end();
    CHECK(lz_inv[LZ_FS_DEPTH] == 1 && lz_inv[LZ_ALWAYS] == 1 && lz_inv[LZ_DIR] == 1 && lz_inv[LZ_CLEAR_AREA] == 1 &&
          lz_inv[LZ_CLEAR_DRAW] == 1);
    lz_stats();
    CHECK(strstr(logbuf, "[lrz] 10 s: 10 passes with depth") != NULL);
    CHECK(strstr(logbuf, "fs 0000000000000005") != NULL);
    if (fails) { fputs(logbuf, stderr); return 1; }
    printf("lrz prediction: 9 cases, the 10 s line and its draws\n");
    return 0;
}
'''
cc = shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
with tempfile.TemporaryDirectory() as d:
    c = pathlib.Path(d) / 't.c'
    c.write_text(C)
    exe = pathlib.Path(d) / 't'
    flags = ['-fsanitize=address,undefined'] if sys.platform.startswith('linux') else []
    r = subprocess.run([cc, '-std=gnu11', '-Wall', '-Wno-unused-function', *flags, str(c), '-o', str(exe)], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr); sys.exit(1)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    print(r.stdout, end=''); print(r.stderr, end='', file=sys.stderr)
    sys.exit(r.returncode)

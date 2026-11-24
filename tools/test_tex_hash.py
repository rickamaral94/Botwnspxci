#!/usr/bin/env python3
"""Host test of textures.c's whole hash in four parts (Amaral.9, from TOTKDroid 99735c5), cut out of the source.

- the helpers' value equals the caller's alone (hash_big == hash_big_alone), for sizes around the split;
- a byte changed in any of the four parts (and in the tail) changes the value;
- two callers at once (one gets the helpers, the other hashes alone) both get the right value.
Run: python3 tools/test_tex_hash.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'runtime/nvn/vulkan/textures.c').read_text()


def cut(start, end):
    i = SRC.index(start)
    return SRC[i:SRC.index(end, i)]


hfull = cut('static uint64_t hash_full(', '// ---- the whole hash of a large texture')
hbig = cut('#include <semaphore.h>', '// (1024 bytes spread over the texture')

HARNESS = r'''
#define _GNU_SOURCE
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int failed;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failed = 1; } } while (0)
@HFULL@
@HBIG@
static uint8_t *buf;
static uint64_t n_other, h_other;
static void *other(void *a) { (void)a; h_other = hash_big(buf + 1, n_other); return NULL; }
int main(void) {
    enum { N = 9 << 20 };
    buf = malloc(N + 64);
    uint64_t s = 1;
    for (size_t i = 0; i < N + 64; i++) { s = s * 6364136223846793005ull + 1442695040888963407ull; buf[i] = (uint8_t)(s >> 56); }
    uint64_t sizes[] = {(2 << 20) - 1, 2 << 20, (2 << 20) + 37, 5 << 20, (8 << 20) + 63};
    for (int k = 0; k < 5; k++) {
        uint64_t n = sizes[k];
        uint64_t a = hash_big(buf, n), b = hash_big_alone(buf, n);
        if (n >= HASH_PAR_MIN) CHECK(a == b); else CHECK(a == hash_full(buf, n));
        CHECK(hash_big(buf, n) == a);  /* (again: the same) */
        if (n < HASH_PAR_MIN) continue;
        uint64_t part = (n / HASH_PARTS) & ~63ull, at[] = {0, part + 5, part * 2 + 9, part * 3 + 1, n - 1};
        for (int j = 0; j < 5; j++) {
            buf[at[j]] ^= 0x40;
            CHECK(hash_big(buf, n) != a);
            buf[at[j]] ^= 0x40;
        }
        CHECK(hash_big(buf, n) == a);
    }
    for (int r = 0; r < 200; r++) {  /* two callers at once */
        n_other = 4 << 20;
        pthread_t t;
        pthread_create(&t, NULL, other, NULL);
        uint64_t mine = hash_big(buf, 6 << 20);
        pthread_join(t, NULL);
        CHECK(mine == hash_big_alone(buf, 6 << 20));
        CHECK(h_other == hash_big_alone(buf + 1, 4 << 20));
    }
    printf("tex hash: %s\n", failed ? "FAILED" : "ok");
    return failed;
}
'''


def main():
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
    src = HARNESS.replace('@HFULL@', hfull).replace('@HBIG@', hbig)
    with tempfile.TemporaryDirectory() as d:
        c, exe = pathlib.Path(d, 'th.c'), pathlib.Path(d, 'th')
        c.write_text(src)
        flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wno-unused-function']
        r = subprocess.run([cc, *flags, '-fsanitize=thread', str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            r = subprocess.run([cc, *flags, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr)
            return 1
        p = subprocess.run([str(exe)], capture_output=True, text=True)
        sys.stdout.write(p.stdout + p.stderr[-2000:])
        return p.returncode


if __name__ == '__main__':
    sys.exit(main())

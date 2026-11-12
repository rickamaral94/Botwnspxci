#!/usr/bin/env python3
"""Host tests of three runtime/nvn/vulkan/exec.c helpers from 0.3.4-beta-amaral.2, compiled from the source itself.

- compute program cache (cs_slot / cs_grow): grows past the old 256 entries, every address found again, its program
  the same object;
- copy mode's learned ranges (gres_learn): 48 by default, a range hit again moves to the newest, the oldest evicted
  becomes a spare window; LARECOMP_GRES_LEGACY=1: the old 16, no recency;
- shader / pipeline wait (wait_built): sleeps by default, LARECOMP_PIPELINE_WAIT_SPIN=1 spins up to 200 us first.

The functions are cut out of exec.c between their neighbours' markers and built with a C compiler (cc, ASan / UBSan
where available) against small stand-ins; nothing of Vulkan runs. Run: python3 tools/test_exec_caches.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'runtime/nvn/vulkan/exec.c').read_text()


def cut(start, end):
    i = SRC.index(start)
    return SRC[i:SRC.index(end, i)]


compute = cut('static CsEntry *cs_slot(', 'static CsProg *compute_program(')
ranges = cut('typedef struct { uint64_t lo, hi; bool store, learned; } GcRange;', '#define GA_RES ') + \
    cut('#define GA_NRES ', '} GaRes;') + '} GaRes;\n'
learn = cut('#define GL_LEGACY_MAX', '// Load-only arena copies')
wait = cut('static uint64_t stat_build_wait_ns', 'static bool rt_is_persistent(')

HARNESS = r'''
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#define LOG(...) ((void)0)
#define HEAP_MAX (3ull << 30)
static uint64_t plat_now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}
static void SDL_CPUPauseInstruction(void) {}
static int failed;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failed = 1; } } while (0)

/* ---- compute program cache */
typedef struct CsProg { uint64_t code_addr; } CsProg;
typedef struct { uint64_t addr; CsProg *program; } CsEntry;
static CsEntry *g_cs_tab;
static size_t g_cs_n, g_cs_cap;
@COMPUTE@
/* compute_program's lookup and insert, without the translation */
static CsProg *cs_get(uint64_t addr) {
    if (!g_cs_cap && !cs_grow()) return NULL;
    CsEntry *entry = cs_slot(g_cs_tab, g_cs_cap, addr);
    if (entry->addr) return entry->program;
    if (g_cs_n >= g_cs_cap / 2) {
        if (!cs_grow()) return NULL;
        entry = cs_slot(g_cs_tab, g_cs_cap, addr);
    }
    CsProg *cp = calloc(1, sizeof *cp);
    cp->code_addr = addr;
    *entry = (CsEntry){addr, cp};
    g_cs_n++;
    return cp;
}
static void test_compute(void) {
    enum { N = 768 };
    static CsProg *first[N];
    for (int i = 0; i < N; i++) {  /* (spread and clustered addresses: 16 B apart, and 1 MB apart) */
        uint64_t a = i & 1 ? 0x100000000ull + (uint64_t)i * 16 : 0x200000000ull + (uint64_t)i * 0x100000;
        first[i] = cs_get(a);
        CHECK(first[i] && first[i]->code_addr == a);
    }
    CHECK(g_cs_n == N);
    CHECK(g_cs_cap >= 2 * N);  /* (grown past the old 256 and kept at most half full) */
    for (int i = 0; i < N; i++) {
        uint64_t a = i & 1 ? 0x100000000ull + (uint64_t)i * 16 : 0x200000000ull + (uint64_t)i * 0x100000;
        CHECK(cs_get(a) == first[i]);  /* (found again: the same program, not built anew) */
    }
    CHECK(g_cs_n == N);
}

/* ---- learned ranges */
@RANGES@
static GaRes ga_res[GA_NRES];
static int ga_nres;
static GaRes *gres_get(uint64_t lo, uint64_t hi, bool create) {
    if (!create || ga_nres >= GA_NRES) return NULL;
    GaRes *r = &ga_res[ga_nres++];
    memset(r, 0, sizeof *r);
    r->lo = lo, r->hi = hi, r->live = true;
    return r;
}
@LEARN@
static uint32_t at(int i) { return (uint32_t)(0x1000000u + (uint32_t)i * 0x100000u); }  /* (each its own window) */
static void test_learn(int legacy) {
    int limit = legacy ? 16 : 48;
    for (int i = 0; i < limit; i++) gres_learn(at(i));
    CHECK(gl_n == limit);
    gres_learn(at(0) + 0x100);  /* (the oldest hit again: with recency, the newest) */
    CHECK(gl_n == limit);
    gres_learn(at(limit));      /* (one more: the oldest out) */
    CHECK(gl_n == limit);
    bool has0 = false, has1 = false;
    for (int i = 0; i < gl_n; i++) {
        has0 |= gl_learned[i].lo <= at(0) && at(0) < gl_learned[i].hi;
        has1 |= gl_learned[i].lo <= at(1) && at(1) < gl_learned[i].hi;
    }
    if (legacy) CHECK(!has0 && has1);  /* (no recency: the first learned went) */
    else CHECK(has0 && !has1);         /* (recency: the second went, the first stays) */
    int spare = 0;
    for (int i = 0; i < ga_nres; i++) spare += ga_res[i].spare;
    CHECK(spare == 1);                 /* (the evicted window may be let go) */
}

/* ---- waits */
@WAIT@
static _Atomic int ready;
static void *setter(void *arg) {
    usleep((useconds_t)(uintptr_t)arg);
    ready = 1;
    return NULL;
}
static void test_wait(int spin) {
    pthread_t t;
    ready = 0;
    pthread_create(&t, NULL, setter, (void *)(uintptr_t)(spin ? 20 : 2000));
    wait_built(&ready);
    pthread_join(t, NULL);
    CHECK(ready);
    CHECK(stat_build_wait_count == 1);
    CHECK(build_wait_spin_ns() == (spin ? 200000u : 0u));
    if (!spin) CHECK(stat_build_wait_spin_count == 0);
    wait_built(&ready);  /* (already built: no wait counted) */
    CHECK(stat_build_wait_count == 1);
}

int main(int argc, char **argv) {
    const char *what = argc > 1 ? argv[1] : "";
    if (!strcmp(what, "compute")) test_compute();
    else if (!strcmp(what, "learn")) test_learn(getenv("LARECOMP_GRES_LEGACY") != NULL);
    else if (!strcmp(what, "wait")) test_wait(getenv("LARECOMP_PIPELINE_WAIT_SPIN") != NULL);
    else return 2;
    printf("%s%s: %s\n", what, getenv("LARECOMP_GRES_LEGACY") || getenv("LARECOMP_PIPELINE_WAIT_SPIN") ? " (opt-in)" : "",
           failed ? "FAILED" : "ok");
    return failed;
}
'''


def main():
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
    if not cc:
        print('no C compiler')
        return 1
    src = HARNESS.replace('@COMPUTE@', compute).replace('@RANGES@', ranges).replace('@LEARN@', learn) \
        .replace('@WAIT@', wait)
    with tempfile.TemporaryDirectory() as d:
        c, exe = pathlib.Path(d, 'exec_caches.c'), pathlib.Path(d, 'exec_caches')
        c.write_text(src)
        flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wno-unused-function']
        san = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        r = subprocess.run([cc, *flags, *san, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:  # (no sanitizer runtime: plain)
            r = subprocess.run([cc, *flags, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr)
            return 1
        runs = [('compute', {}), ('learn', {}), ('learn', {'LARECOMP_GRES_LEGACY': '1'}), ('wait', {}),
                ('wait', {'LARECOMP_PIPELINE_WAIT_SPIN': '1'})]
        bad = 0
        for what, env in runs:
            e = {k: v for k, v in os.environ.items() if k not in ('LARECOMP_GRES_LEGACY', 'LARECOMP_PIPELINE_WAIT_SPIN')}
            e.update(env)
            p = subprocess.run([str(exe), what], capture_output=True, text=True, env=e)
            sys.stdout.write(p.stdout + p.stderr)
            bad |= p.returncode != 0
        print('exec caches: ' + ('FAILED' if bad else 'all passed'))
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

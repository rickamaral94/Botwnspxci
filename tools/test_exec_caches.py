#!/usr/bin/env python3
"""Host tests of three runtime/nvn/vulkan/exec.c helpers from 0.3.4-beta-amaral.2, compiled from the source itself.

- compute program cache (cs_slot / cs_grow): grows past the old 256 entries, every address found again, its program
  the same object;
- copy mode's learned ranges (gres_learn): 48 by default, a range hit again moves to the newest, the oldest evicted
  becomes a spare window; LARECOMP_GRES_LEGACY=1: the old 16, no recency;
- shader / pipeline wait (wait_built): sleeps by default, LARECOMP_PIPELINE_WAIT_SPIN=1 spins up to 200 us first;
- G-buffer alias (view_overlaps_rt, alias_case): what counts as the draw's own target, and the case left out - a target
  at a level / layer other than 0 sampled by a view covering it (Amaral.3, the [alias] counter);
- pipeline warm-up list (warm_parse, program_key): a list of another game version, build, driver or size is dropped;
  a program's table key is the same from a draw's keys and from the keys stored in the list.

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
alias = cut('static bool view_overlaps_rt(', 'static bool is_attachment_entry(')
hashw = cut('static uint64_t hash_words(uint64_t h, const void *p, size_t n) {', 'static uint64_t hmix(uint64_t h, const void *p, size_t n) {')
pkey = cut('static uint64_t program_key(', 'static int g_prog_n;')
wheader = cut('typedef struct {\n    char magic[8];', '#define WARM_MAX')
wparse = cut('static const void *warm_parse(', 'static void warm_add(')

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

/* ---- G-buffer alias */
typedef struct { uint32_t levels, width, height; } NvnTexture;
typedef struct { uint32_t setmask, base_level, num_levels, min_layer, num_layers; } NvnTextureView;
typedef struct { NvnTexture *tex; bool has_view; NvnTextureView view; } NvnTexEntry;
static uint64_t g_cur_fs_hash;
static uint64_t renderer_present_count(void) { return 0; }
@ALIAS@
static NvnTexture tex = {5, 1024, 1024};
static NvnTexEntry whole(void) { NvnTexEntry e = {&tex, false, {0}}; return e; }
static NvnTexEntry viewed(uint32_t lv, uint32_t nlv, uint32_t ly, uint32_t nly) {
    NvnTexEntry e = {&tex, true, {3, lv, nlv, ly, nly}};
    return e;
}
static NvnTextureView rt_at(uint32_t lv, uint32_t ly) { NvnTextureView v = {3, lv, 1, ly, 1}; return v; }
static void test_alias(void) {
    NvnTextureView r0 = rt_at(0, 0), r2 = rt_at(2, 0), l3 = rt_at(0, 3);
    NvnTexEntry w = whole(), low = viewed(0, 2, 0, 1), up = viewed(1, 4, 0, 1), arr = viewed(0, 1, 0, 6), arr3 = viewed(0, 1, 0, 3);
    CHECK(view_overlaps_rt(&w, &r0, true) && view_overlaps_rt(&w, NULL, false));  /* (level 0 into level 0: its own) */
    CHECK(!view_overlaps_rt(&up, &r0, true) && !alias_case(&up, &r0, true));      /* (levels 1.. against level 0) */
    CHECK(!view_overlaps_rt(&w, &r2, true) && alias_case(&w, &r2, true));         /* (the case left out: level 2 in the chain) */
    CHECK(!alias_case(&low, &r2, true));                                          /* (levels 0-1: disjoint from 2) */
    CHECK(!view_overlaps_rt(&arr, &l3, true) && alias_case(&arr, &l3, true));     /* (layer 3 of layers 0-5) */
    CHECK(!alias_case(&arr3, &l3, true));                                         /* (layers 0-2: disjoint) */
    alias_note(&w, &r2, true);
    alias_note(&low, &r2, true);
    CHECK(stat_alias == 1);
}

/* ---- pipeline warm-up list */
#define VK_UUID_SIZE 16
#define WARM_MAX 16384
@WHEADER@
@WPARSE@
#include "maxwell/shader.h"
@HASHW@
@PKEY@
static void test_warm(void) {
    enum { ES = 48 };
    static unsigned char buf[sizeof(WarmHeader) + 3 * ES + 7];
    WarmHeader want;
    memset(&want, 0, sizeof want);
    memcpy(want.magic, "BOTWPW1", 8);
    want.entry_size = ES, want.game_version = 182, want.build = 0x1234, want.vendor = 0x5143, want.device = 0x43050a01;
    want.driver_version = 7;
    for (int i = 0; i < VK_UUID_SIZE; i++) want.cache_uuid[i] = (uint8_t)i;
    WarmHeader h = want;
    h.count = 3;
    memcpy(buf, &h, sizeof h);
    uint32_t n = 99;
    CHECK(warm_parse(buf, sizeof buf, &want, ES, &n) == buf + sizeof h && n == 3);
    CHECK(!warm_parse(buf, sizeof(WarmHeader) + 2 * ES, &want, ES, &n) && n == 0);  /* (cut short) */
    CHECK(!warm_parse(buf, sizeof buf, &want, ES + 8, &n));                          /* (another entry size) */
    WarmHeader bad[8];
    for (int i = 0; i < 8; i++) bad[i] = h;
    bad[0].magic[0] = 'X'; bad[1].game_version = 160; bad[2].build ^= 1; bad[3].vendor ^= 1; bad[4].device ^= 1;
    bad[5].driver_version ^= 1; bad[6].cache_uuid[5] ^= 1; bad[7].count = WARM_MAX + 1;
    for (int i = 0; i < 8; i++) {
        memcpy(buf, &bad[i], sizeof bad[i]);
        CHECK(!warm_parse(buf, sizeof buf, &want, ES, &n));
    }
    /* a draw's keys and the same keys read back from the list: the same table key */
    ShaderKey vk, fk;
    memset(&vk, 0, sizeof vk), memset(&fk, 0, sizeof fk);
    vk.glsl = fk.glsl = 1, vk.flip_y = fk.flip_y = 1, vk.attr_kind[3] = 2, fk.rt_kind[1] = 1, fk.vs_out_mask = 0x2f;
    unsigned char stored[2 * sizeof(ShaderKey)];
    memcpy(stored, &vk, sizeof vk), memcpy(stored + sizeof vk, &fk, sizeof fk);
    ShaderKey vk2, fk2;
    memcpy(&vk2, stored, sizeof vk2), memcpy(&fk2, stored + sizeof vk2, sizeof fk2);
    uint64_t code[2] = {0x340001000ull, 0x340002000ull}, other[2] = {0x340001000ull, 0x340003000ull};
    CHECK(program_key(code, &vk, &fk) == program_key(code, &vk2, &fk2));
    CHECK(program_key(code, &vk, &fk) != program_key(other, &vk, &fk));
    fk2.rt_kind[1] = 2;
    CHECK(program_key(code, &vk, &fk) != program_key(code, &vk, &fk2));
}

int main(int argc, char **argv) {
    const char *what = argc > 1 ? argv[1] : "";
    if (!strcmp(what, "compute")) test_compute();
    else if (!strcmp(what, "learn")) test_learn(getenv("LARECOMP_GRES_LEGACY") != NULL);
    else if (!strcmp(what, "wait")) test_wait(getenv("LARECOMP_PIPELINE_WAIT_SPIN") != NULL);
    else if (!strcmp(what, "alias")) test_alias();
    else if (!strcmp(what, "warm")) test_warm();
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
        .replace('@WAIT@', wait).replace('@ALIAS@', alias).replace('@HASHW@', hashw).replace('@PKEY@', pkey) \
        .replace('@WHEADER@', wheader).replace('@WPARSE@', wparse)
    with tempfile.TemporaryDirectory() as d:
        c, exe = pathlib.Path(d, 'exec_caches.c'), pathlib.Path(d, 'exec_caches')
        c.write_text(src)
        flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wno-unused-function', '-I', str(ROOT / 'runtime/nvn')]
        san = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        r = subprocess.run([cc, *flags, *san, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:  # (no sanitizer runtime: plain)
            r = subprocess.run([cc, *flags, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr)
            return 1
        runs = [('compute', {}), ('learn', {}), ('learn', {'LARECOMP_GRES_LEGACY': '1'}), ('wait', {}),
                ('wait', {'LARECOMP_PIPELINE_WAIT_SPIN': '1'}), ('alias', {}), ('warm', {})]
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

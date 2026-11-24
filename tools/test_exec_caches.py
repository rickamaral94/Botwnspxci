#!/usr/bin/env python3
"""Host tests of runtime/nvn/vulkan/exec.c helpers from the Amaral builds, compiled from the source itself.

- copy mode's learned ranges (gres_learn): 48 by default, a range hit again moves to the newest, the oldest evicted
  becomes a spare window; LARECOMP_GRES_LEGACY=1: the old 16, no recency;
- G-buffer alias (view_overlaps_rt, alias_case): what counts as the draw's own target, and the case left out - a target
  at a level / layer other than 0 sampled by a view covering it (Amaral.3, the [alias] counter);

- pipeline warm-up list (Amaral.8, warm_parse / warm_add): a list of another game version, key layout or size is
  dropped; a repeated entry is kept once.

(Amaral.5: the compute cache, the shader / pipeline wait and the warm-up list gave way to upstream 0.4.7's object
cache, job queue and prewarm, tested by tools/test_object_cache.c, test_shader_job_queue.c, test_pipeline_prewarm.c.)

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


ranges = cut('typedef struct { uint64_t lo, hi; bool store, learned; } GcRange;', '#define GA_RES ') + \
    cut('#define GA_NRES ', '} GaRes;') + '} GaRes;\n'
learn = cut('#define GL_LEGACY_MAX', '// Load-only arena copies')
alias = cut('static bool view_overlaps_rt(', 'static bool is_attachment_entry(')
wtypes = cut('typedef struct {\n    uint64_t vsh, fsh;', 'static bool warm_dirty;')
wfuncs = cut('static uint32_t warm_slot(', 'static int warm_read(')

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
static int failed;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failed = 1; } } while (0)

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

/* ---- pipeline warm-up list (Amaral.8: it ships in the APK, so a list of another version or layout must be dropped) */
typedef struct { uint8_t b[88]; } ShaderKey;
typedef struct { void *prog; uint8_t b[600]; } PipeKey;
static int g_game_version = 182;
@WTYPES@
@WFUNCS@
static void test_warm(void) {
    static unsigned char buf[sizeof(WarmHeader) + 3 * sizeof(WarmEntry)];
    WarmHeader want, h;
    warm_header(&want);
    CHECK(!memcmp(want.magic, "BOTWPW2", 8) && want.entry_size == sizeof(WarmEntry) && want.game_version == 182);
    h = want;
    h.count = 3;
    memcpy(buf, &h, sizeof h);
    uint32_t n = 99;
    CHECK(warm_parse(buf, sizeof buf, &want, &n) == buf + sizeof h && n == 3);
    CHECK(!warm_parse(buf, sizeof buf - 1, &want, &n) && n == 0);        /* (cut short) */
    WarmHeader bad[6];
    for (int i = 0; i < 6; i++) bad[i] = h;
    bad[0].magic[0] = 'X'; bad[1].game_version = 160; bad[2].entry_size += 8; bad[3].skey_size += 8;
    bad[4].pkey_size += 8; bad[5].count = WARM_MAX + 1;
    for (int i = 0; i < 6; i++) {
        memcpy(buf, &bad[i], sizeof bad[i]);
        CHECK(!warm_parse(buf, sizeof buf, &want, &n));
    }
    /* entries: a repeat is not added twice; two pairs with the same shaders chain under one slot */
    warm_list = calloc(WARM_MAX, sizeof *warm_list), warm_next = calloc(WARM_MAX, sizeof *warm_next);
    WarmEntry e;
    memset(&e, 0, sizeof e);
    e.vsh = 0x1111, e.fsh = 0x2222;
    warm_add(&e); warm_add(&e);
    CHECK(warm_n == 1);
    e.pk.b[0] = 1;
    warm_add(&e);
    CHECK(warm_n == 2);
    int found = 0;
    for (int i = warm_index[warm_slot(0x1111, 0x2222)] - 1; i >= 0; i = warm_next[i] - 1) found++;
    CHECK(found == 2);
}

int main(int argc, char **argv) {
    const char *what = argc > 1 ? argv[1] : "";
    if (!strcmp(what, "learn")) test_learn(getenv("LARECOMP_GRES_LEGACY") != NULL);
    else if (!strcmp(what, "alias")) test_alias();
    else if (!strcmp(what, "warm")) test_warm();
    else return 2;
    printf("%s%s: %s\n", what, getenv("LARECOMP_GRES_LEGACY") ? " (opt-in)" : "",
           failed ? "FAILED" : "ok");
    return failed;
}
'''


def main():
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
    if not cc:
        print('no C compiler')
        return 1
    src = HARNESS.replace('@RANGES@', ranges).replace('@LEARN@', learn).replace('@ALIAS@', alias).replace('@WTYPES@', wtypes).replace('@WFUNCS@', wfuncs)
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
        runs = [('learn', {}), ('learn', {'LARECOMP_GRES_LEGACY': '1'}), ('alias', {}), ('warm', {})]
        bad = 0
        for what, env in runs:
            e = {k: v for k, v in os.environ.items() if k != 'LARECOMP_GRES_LEGACY'}
            e.update(env)
            p = subprocess.run([str(exe), what], capture_output=True, text=True, env=e)
            sys.stdout.write(p.stdout + p.stderr)
            bad |= p.returncode != 0
        print('exec caches: ' + ('FAILED' if bad else 'all passed'))
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

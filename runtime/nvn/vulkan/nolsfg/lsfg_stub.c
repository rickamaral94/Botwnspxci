// Frame generation left out of this build (CMake -DBOTW_LSFG=OFF): the present's calls answer "not in this build".
// (The LSFG files, runtime/nvn/vulkan/lsfg, are GPL-3.0-or-later; this stub is MIT as the rest.)
// Amaral: the state is our own frame generation's (vulkan/framegen.c), so the overlay shows the game's and the shown
// frame rates apart while it generates.
#include "../vk.h"
#ifdef __ANDROID__
extern bool fg_overlay(float *real, float *shown, int *mult);
#endif
int vk_fg_status(const char **why) {
#ifdef __ANDROID__
    float r, sh;
    int mult;
    if (fg_overlay(&r, &sh, &mult)) { if (why) *why = ""; return 1; }
#endif
    if (why) *why = "not in this build";
    return -1;
}
int vk_fg_frame(TexBackend *game, TexBackend **gen, uint64_t *hold_ns, uint64_t vsync_ns) {
    (void)game, (void)gen, (void)vsync_ns;
    *hold_ns = 0;
    return 0;
}
const char *vk_fg_dll_path(void) { return NULL; }
void vk_fg_dll_imported(void) {}  // (ui/launcher.mm, upstream's Lossless.dll copy: nothing to reload here)

#!/usr/bin/env python3
"""Host test of exec.c's queue thread (Amaral.10), cut out of the source, against stand-ins for the driver.

- submissions and presents reach the "queue" in the order they were handed over, from a burst far longer than the FIFO;
- each job is a copy: the caller's VkSubmitInfo2 / VkPresentInfoKHR and their arrays (on its stack) are overwritten
  right after the call, and the queue still sees the values as handed over (command buffers, semaphores, the
  present's image, its time);
- vk_qt_drain returns only once every job ran and the thread is idle; vk_queue_hold keeps the thread off the queue;
- a present's out-of-date answer reaches the next vk_qt_present.
Run: python3 tools/test_queue_thread.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / 'runtime/nvn/vulkan/exec.c').read_text()
i = SRC.index('enum { QT_N = 64 };')
module = SRC[i:SRC.index('// (renderer_stats, every 10 s) the thread', i)]
VKI = next((p for p in [ROOT / 'android/deps/out/include', pathlib.Path('/usr/include')]
            if (p / 'vulkan/vulkan_core.h').exists()), None)

HARNESS = r'''
#define _GNU_SOURCE
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan_core.h>
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
#define VK_CHECK(x) do { if ((x) != VK_SUCCESS) { printf("VK_CHECK failed\n"); exit(1); } } while (0)
typedef int WdMark;
enum { WD_R_SUBMIT, WD_R_QUEUE_PRESENT };
static WdMark vk_wd_enter(int r, uint64_t a) { (void)r, (void)a; return 0; }
static void vk_wd_leave(WdMark m) { (void)m; }
static void vk_devlost_dump(void) {}
static uint64_t plat_now_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000000000ull + t.tv_nsec; }
static struct { VkDevice dev; VkQueue queue; } g_vk;
static struct { bool queue_thread; } g_settings = {true};
volatile int g_diag_ab = -1;
int g_diag_ab_what = -1;
static bool seq_fences_on = true;
static bool seq_thread_on(void) { return true; }
static int failed;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failed = 1; } } while (0)
/* the "driver": a log of what reached the queue, and whether two threads ever used it at once */
static _Atomic int in_queue, overlap;
static uint64_t seen[4096][3];
static int nseen;
static bool make_out_of_date;
static VkResult stub_submit(VkQueue q, uint32_t n, const VkSubmitInfo2 *si, VkFence f) {
    (void)q, (void)n;
    if (atomic_fetch_add(&in_queue, 1)) overlap = 1;
    seen[nseen][0] = 1, seen[nseen][1] = (uint64_t)(uintptr_t)si->pCommandBufferInfos[0].commandBuffer, seen[nseen][2] = (uint64_t)(uintptr_t)f;
    if (si->waitSemaphoreInfoCount) seen[nseen][2] ^= (uint64_t)(uintptr_t)si->pWaitSemaphoreInfos[0].semaphore << 20;
    nseen++;
    usleep(50);
    atomic_fetch_sub(&in_queue, 1);
    return VK_SUCCESS;
}
static VkResult stub_present(VkQueue q, const VkPresentInfoKHR *pi) {
    (void)q;
    if (atomic_fetch_add(&in_queue, 1)) overlap = 1;
    const VkPresentTimesInfoGOOGLE *t = pi->pNext;
    seen[nseen][0] = 2, seen[nseen][1] = pi->pImageIndices[0], seen[nseen][2] = t ? t->pTimes[0].desiredPresentTime : 0;
    nseen++;
    usleep(300);  /* (the screen's wait) */
    atomic_fetch_sub(&in_queue, 1);
    return make_out_of_date ? VK_ERROR_OUT_OF_DATE_KHR : VK_SUCCESS;
}
static PFN_vkQueueSubmit2 vkQueueSubmit2 = stub_submit;
static PFN_vkQueuePresentKHR vkQueuePresentKHR = stub_present;
@MODULE@
int main(void) {
    vk_qt_frame(false);
    CHECK(vk_qt_active());
    enum { N = 1000 };
    for (int k = 0; k < N; k++) {
        if (k % 5 == 4) {
            uint32_t img = (uint32_t)k;
            VkSemaphore sem = (VkSemaphore)(uintptr_t)(0x9000 + k);
            VkPresentTimeGOOGLE when = {.presentID = (uint32_t)k, .desiredPresentTime = 1000000ull + k};
            VkPresentTimesInfoGOOGLE times = {.sType = VK_STRUCTURE_TYPE_PRESENT_TIMES_INFO_GOOGLE, .swapchainCount = 1, .pTimes = &when};
            VkSwapchainKHR sc = (VkSwapchainKHR)(uintptr_t)0x77;
            VkPresentInfoKHR pi = {.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .pNext = &times, .waitSemaphoreCount = 1,
                                   .pWaitSemaphores = &sem, .swapchainCount = 1, .pSwapchains = &sc, .pImageIndices = &img};
            vk_qt_present(&pi);
            img = 0xdead, when.desiredPresentTime = 0, sem = 0;  /* (the caller's stack, reused at once) */
        } else {
            VkCommandBufferSubmitInfo cbs[2] = {{.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO,
                                                 .commandBuffer = (VkCommandBuffer)(uintptr_t)(0x1000 + k)}};
            VkSemaphoreSubmitInfo wt = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_SUBMIT_INFO, .semaphore = (VkSemaphore)(uintptr_t)(k & 7)};
            VkSubmitInfo2 si = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO_2, .commandBufferInfoCount = 1, .pCommandBufferInfos = cbs,
                                .waitSemaphoreInfoCount = (k & 1), .pWaitSemaphoreInfos = &wt};
            qt_submit(&si, (VkFence)(uintptr_t)(0x5000 + k), (uint64_t)k);
            cbs[0].commandBuffer = 0, wt.semaphore = 0;
        }
    }
    vk_qt_drain();
    CHECK(nseen == N);
    CHECK(!overlap);
    for (int k = 0; k < N && k < nseen; k++) {
        if (k % 5 == 4) {
            CHECK(seen[k][0] == 2 && seen[k][1] == (uint64_t)k && seen[k][2] == 1000000ull + k);
        } else {
            uint64_t want = (0x5000 + k) ^ ((k & 1) ? (uint64_t)(k & 7) << 20 : 0);
            CHECK(seen[k][0] == 1 && seen[k][1] == (uint64_t)(0x1000 + k) && seen[k][2] == want);
        }
    }
    /* a hold keeps the thread off the queue while the holder uses it */
    vk_queue_hold();
    VkCommandBufferSubmitInfo cb = {.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO, .commandBuffer = (VkCommandBuffer)(uintptr_t)1};
    VkSubmitInfo2 si = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO_2, .commandBufferInfoCount = 1, .pCommandBufferInfos = &cb};
    for (int k = 0; k < 20; k++) qt_submit(&si, 0, 0);
    stub_submit(0, 1, &si, 0);  /* (the holder's own use, as ImGui's font upload) */
    vk_queue_release();
    vk_qt_drain();
    CHECK(!overlap);
    CHECK(nseen == N + 21);
    /* an out-of-date present: the next present hears of it, once */
    make_out_of_date = true;
    uint32_t img = 1;
    VkSwapchainKHR sc = (VkSwapchainKHR)(uintptr_t)0x77;
    VkPresentInfoKHR pi = {.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .swapchainCount = 1, .pSwapchains = &sc, .pImageIndices = &img};
    CHECK(vk_qt_present(&pi) == VK_SUCCESS);
    vk_qt_drain();
    make_out_of_date = false;
    CHECK(vk_qt_present(&pi) == VK_ERROR_OUT_OF_DATE_KHR);
    vk_qt_drain();
    CHECK(vk_qt_present(&pi) == VK_SUCCESS);
    vk_qt_drain();
    /* off: drained first */
    g_settings.queue_thread = false;
    vk_qt_frame(false);
    CHECK(!vk_qt_active());
    g_settings.queue_thread = true;
    vk_qt_frame(true);  /* (frame generation on: stays off) */
    CHECK(!vk_qt_active());
    printf("queue thread: %s\n", failed ? "FAILED" : "ok");
    return failed;
}
'''


def main():
    if not VKI:
        print('no Vulkan headers (android/deps/build_deps.sh): skipped')
        return 0
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
    src = HARNESS.replace('@MODULE@', module)
    with tempfile.TemporaryDirectory() as d:
        c, exe = pathlib.Path(d, 'qt.c'), pathlib.Path(d, 'qt')
        c.write_text(src)
        flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wno-unused-function', '-I', str(VKI)]
        r = subprocess.run([cc, *flags, '-fsanitize=thread', str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            r = subprocess.run([cc, *flags, str(c), '-o', str(exe), '-lpthread'], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
            return 1
        p = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
        sys.stdout.write(p.stdout + p.stderr[-3000:])
        return p.returncode


if __name__ == '__main__':
    sys.exit(main())

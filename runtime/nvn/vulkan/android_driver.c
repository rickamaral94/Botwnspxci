// Android: which Vulkan driver the backend uses. LARECOMP_VK_DRIVER=<path of a driver library in the app's internal
// storage> (the activity sets it from the user's choice, e.g. Turnip): loaded through adrenotools, in a linker
// namespace of its own (its hooks are in nativeLibraryDir, LARECOMP_NATIVE_LIB_DIR). Otherwise, or if that fails, the
// system driver. volk then takes every Vulkan function from it (device.c: volkLoadInstance / volkLoadDevice).
#include <adrenotools/driver.h>
#include <dlfcn.h>
#include <elf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "vk.h"
#include "mbedtls/sha256.h"

// Does this driver offer a Vulkan GPU at all? (Turnip v26.0.0 R8, built for the A7xx: none on an Adreno 830 - the app
// stopped at "no Vulkan device" on every start, its settings out of reach.) 1.1 and up: below 1.3 device.c checks the
// extensions it needs instead (COMPAT_EXT).
static bool driver_has_gpu(PFN_vkGetInstanceProcAddr gipa) {
    PFN_vkCreateInstance create = (PFN_vkCreateInstance)gipa(NULL, "vkCreateInstance");
    if (!create) return false;
    VkApplicationInfo app = {.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .apiVersion = VK_API_VERSION_1_3};
    VkInstanceCreateInfo ci = {.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app};
    VkInstance inst;
    if (create(&ci, NULL, &inst) != VK_SUCCESS) return false;
    PFN_vkEnumeratePhysicalDevices enumerate = (PFN_vkEnumeratePhysicalDevices)gipa(inst, "vkEnumeratePhysicalDevices");
    PFN_vkGetPhysicalDeviceProperties props = (PFN_vkGetPhysicalDeviceProperties)gipa(inst, "vkGetPhysicalDeviceProperties");
    PFN_vkDestroyInstance destroy = (PFN_vkDestroyInstance)gipa(inst, "vkDestroyInstance");
    bool ok = false;
    uint32_t n = 0;
    if (enumerate && props && enumerate(inst, &n, NULL) == VK_SUCCESS && n) {
        VkPhysicalDevice pd[8];
        if (n > 8) n = 8;
        if (enumerate(inst, &n, pd) >= 0)
            for (uint32_t i = 0; i < n && !ok; i++) {
                VkPhysicalDeviceProperties p;
                props(pd[i], &p);
                ok = p.apiVersion >= VK_API_VERSION_1_1;
            }
    }
    if (destroy) destroy(inst, NULL);
    return ok;
}

// The chosen driver the system's stood in for (its package's name; "" none): the start screen and the driver errors
// say so - before, a Turnip build for another Adreno generation fell back silently, and the "driver too old" error
// read as if Turnip lacked the extensions
static char g_rejected[128];
const char *vk_driver_rejected(void) { return g_rejected; }

// The driver library opened, identified for the driver's evidence (docs/logs/CAMPAINHA-TURNIP.md M1): the SHA-256 of
// its file and the GNU build id of its ELF; "" for the system's driver
static char g_drv_sha[65], g_drv_bid[41];
const char *vk_driver_sha256(void) { return g_drv_sha; }
const char *vk_driver_build_id(void) { return g_drv_bid; }
static void driver_identity(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = n > 0 && n < (256l << 20) ? malloc((size_t)n) : NULL;
    bool ok = buf && fread(buf, 1, (size_t)n, f) == (size_t)n;
    fclose(f);
    if (!ok) { free(buf); return; }
    uint8_t h[32];
    if (!mbedtls_sha256(buf, (size_t)n, h, 0))
        for (int i = 0; i < 32; i++) snprintf(g_drv_sha + i * 2, 3, "%02x", h[i]);
    // (the build id: a PT_NOTE of type NT_GNU_BUILD_ID, name "GNU")
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)buf;
    if ((size_t)n >= sizeof *eh && !memcmp(eh->e_ident, ELFMAG, SELFMAG) && eh->e_ident[EI_CLASS] == ELFCLASS64 &&
        eh->e_phoff + (uint64_t)eh->e_phnum * sizeof(Elf64_Phdr) <= (uint64_t)n) {
        const Elf64_Phdr *ph = (const Elf64_Phdr *)(buf + eh->e_phoff);
        for (int i = 0; i < eh->e_phnum && !g_drv_bid[0]; i++) {
            if (ph[i].p_type != PT_NOTE || ph[i].p_offset + ph[i].p_filesz > (uint64_t)n) continue;
            const uint8_t *p = buf + ph[i].p_offset, *end = p + ph[i].p_filesz;
            while (p + sizeof(Elf64_Nhdr) <= end) {
                const Elf64_Nhdr *nh = (const Elf64_Nhdr *)p;
                const uint8_t *name = p + sizeof *nh, *desc = name + ((nh->n_namesz + 3) & ~3u);
                if (desc + nh->n_descsz > end) break;
                if (nh->n_type == NT_GNU_BUILD_ID && nh->n_namesz == 4 && !memcmp(name, "GNU", 4)) {
                    for (uint32_t k = 0; k < nh->n_descsz && k < 20; k++) snprintf(g_drv_bid + k * 2, 3, "%02x", desc[k]);
                    break;
                }
                p = desc + ((nh->n_descsz + 3) & ~3u);
            }
        }
    }
    free(buf);
    LOG("[vk] driver file %s: sha256 %s build-id %s (%ld bytes)\n", path, g_drv_sha[0] ? g_drv_sha : "?",
        g_drv_bid[0] ? g_drv_bid : "?", n);
}

void vk_android_load(void) {
    void *lib = NULL;
    const char *drv = getenv("LARECOMP_VK_DRIVER"), *hooks = getenv("LARECOMP_NATIVE_LIB_DIR");
    if (drv && *drv && hooks && *hooks) {
        const char *slash = strrchr(drv, '/');
        char dir[1024];
        if (slash && (size_t)snprintf(dir, sizeof dir, "%.*s/", (int)(slash - drv), drv) < sizeof dir)
            lib = adrenotools_open_libvulkan(RTLD_NOW | RTLD_LOCAL, ADRENOTOOLS_DRIVER_CUSTOM, NULL, hooks, dir, slash + 1,
                                             NULL, NULL);
        LOG("[vk] driver %s: %s\n", drv, lib ? "loaded through adrenotools" : "FAILED, using the system driver");
        if (lib) driver_identity(drv);
        PFN_vkGetInstanceProcAddr g = lib ? (PFN_vkGetInstanceProcAddr)dlsym(lib, "vkGetInstanceProcAddr") : NULL;
        if (lib && (!g || !driver_has_gpu(g))) {
            LOG("[vk] driver %s: no Vulkan 1.1+ GPU it supports here - using the system driver\n", drv);
            g_drv_sha[0] = g_drv_bid[0] = 0;
            lib = NULL;  // (left loaded: a driver doesn't always unload cleanly)
        }
        if (!lib) {  // (the package's name: its folder, files/drivers/<name>/<library>)
            const char *name = drv;
            if (slash) {
                const char *p = slash;
                while (p > drv && p[-1] != '/') p--;
                name = p;
            }
            snprintf(g_rejected, sizeof g_rejected, "%.*s", slash && name < slash ? (int)(slash - name) : (int)strlen(name), name);
        }
    }
    if (!lib) lib = dlopen("libvulkan.so", RTLD_NOW | RTLD_LOCAL);
    if (!lib) FATAL("no Vulkan driver: %s\n", dlerror());
    PFN_vkGetInstanceProcAddr gipa = (PFN_vkGetInstanceProcAddr)dlsym(lib, "vkGetInstanceProcAddr");
    if (!gipa) FATAL("the Vulkan driver has no vkGetInstanceProcAddr\n");
    volkInitializeCustom(gipa);
}

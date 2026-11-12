#!/usr/bin/env bash
# The host tests that need no device, no NDK and no Python extras, in one go (there is no CI): each prints its own
# result, a summary at the end, exit status 1 if any failed. Run from anywhere: tools/run_host_tests.sh
# Not here (they need more): test_lift*.py / test_simd.py (unicorn), test_shader_int32.py (glslc), and the tests that
# take the NDK's bin directory or a WebAssembly build as their argument (test_android_upload_caches.py,
# test_descriptor_plan.py, test_gpu_timing_trace.py, test_shader_cache.py, test_shader_constants.py,
# test_touch_scroll.py, test_vulkan_compat.py, test_vulkan_startup.py).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${TMPDIR:-/tmp}/botw-host-tests"
mkdir -p "$OUT"
CC="${CC:-cc}"
SAN="-fsanitize=address,undefined -fno-omit-frame-pointer"
pass=() fail=() skip=()

run() {  # name, command...
    local name="$1"; shift
    echo "== $name"
    if "$@"; then pass+=("$name"); else fail+=("$name"); fi
}

run diag bash -c "'$CC' -DDIAG_TESTING $SAN -I '$ROOT/runtime' '$ROOT/runtime/diag.c' '$ROOT/tools/diag_tests/test_diag.c' \
    -o '$OUT/test_diag' -lpthread -ldl && (cd '$OUT' && ./test_diag | tail -1)"

if command -v cmake >/dev/null && command -v c++ >/dev/null; then
    run lsfg_extract bash -c "cmake -S '$ROOT/tools/lsfg_extract_tests' -B '$OUT/lsfg' -DCMAKE_BUILD_TYPE=Debug >/dev/null && \
        cmake --build '$OUT/lsfg' -j4 >/dev/null && (cd '$OUT/lsfg' && ./lsfg_extract_tests | tail -1)"
else
    skip+=("lsfg_extract (cmake / c++)")
fi

VKINC="$(find "$ROOT/android/deps" /usr/include -path '*/vulkan/vulkan_core.h' 2>/dev/null | head -1)"
if [ -n "$VKINC" ]; then
    run buffer_copy bash -c "'$CC' -I '$ROOT/runtime/nvn' -I '$(dirname "$(dirname "$VKINC")")' '$ROOT/tools/test_buffer_copy.c' \
        -o '$OUT/test_buffer_copy' && '$OUT/test_buffer_copy' | tail -1"
else
    skip+=("buffer_copy (Vulkan headers: android/deps/build_deps.sh)")
fi

run exec_caches python3 "$ROOT/tools/test_exec_caches.py"
run gamebuild_hot bash -c "python3 '$ROOT/tools/test_gamebuild_hot.py' | tail -1"
run romfs_build bash -c "python3 '$ROOT/tools/test_romfs_build.py' | tail -1"

echo
echo "passed: ${#pass[@]} (${pass[*]:-})"
[ ${#skip[@]} -gt 0 ] && echo "skipped: ${skip[*]}"
if [ ${#fail[@]} -gt 0 ]; then echo "FAILED: ${fail[*]}"; exit 1; fi

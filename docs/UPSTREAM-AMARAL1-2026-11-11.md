# BOTW Android 0.3.4-beta-amaral.1

## Scope

- Amaral base: `1bcec01` (`codex/botw-60fps-copy-cache`).
- Upstream integrated: `mamcjr/BOTWRecompAndroid` `82534ac`, including release `v0.3.4-beta` (`3d9beeb`).
- Candidate branch: `codex/botw-upstream-034`.
- Android package: `com.botwrecomp.android`.
- Candidate version: `versionCode 39`, `versionName 0.3.4-beta-amaral.1`.

## Upstream improvements integrated

- 20/30/40/45/60 FPS modes and corrected 30 FPS frame pacing.
- Benchmark scene harness and expanded runtime diagnostics.
- Android memory-map reset, shared-file Turnip heap path and low-memory profile restricted to devices with at most 4 GB.
- BC1-to-ASTC path, pipeline retention limits for constrained devices, Mali compatibility fixes and null-call safety.
- Audio resume, motion, touch controls, UI, movie and widescreen fixes.
- Render-thread placement on the fastest available cores and configurable driver environment variables.

## Amaral features preserved

- NSP/XCI importer and its localized UI.
- LSFG Vulkan frame generation at 2x/3x/4x, including HUD mask.
- Performance diagnosis and gameplay markers.
- Experimental direct constant-buffer and same-build vertex-copy reuse toggles.
- Dynamic-resolution headroom controls.
- Automatic LRZ policy for Adreno 740/8xx and automatic Turnip shared-file heap policy.

The upstream frame pacing runs first; the frame-generation base-FPS clamp is applied afterwards. Explicit LRZ configuration remains authoritative, while automatic mode targets only the validated Adreno families.

## Merge decisions and risk controls

- Kept all required Vulkan synchronization; no visual-correctness barrier was removed.
- Combined upstream render-thread affinity with Amaral diagnostics rather than increasing worker count globally.
- Preserved the upstream `IR3_SHADER_DEBUG=nouboopt` workaround only for Adreno 840+, not the Odin 2's Adreno 740.
- Corrected the upstream host test after `mark_cold` gained separate `compile_o0` and `heavy` outputs.
- No foreign optimization from a different recompiler architecture was imported without an equivalent BOTW Android validation path.

## External recompiler review

`SavageWindRecomp-Android` and the Wii U `BotWRecomp-Android` fork were reviewed for transferable ideas. Profile-guided optimization, core placement and cache warm-up remain useful experiments, but their executable formats, runtime and graphics stacks differ from this Switch/NVN-to-Vulkan port. They are roadmap candidates, not patches suitable for blind cherry-picking.

## Validation record

- `tools/test_gamebuild_hot.py`: 13 checks passed.
- `tools/test_romfs_build.py`: 6 image and 9 setup checks passed.
- `tools/test_astc.sh 1000 1`: all block sizes, 336 synthetic images and random blocks matched ARM astcenc with zero mismatching texels. The test was updated to C++20 for current astcenc's `std::bit_cast` requirement.
- `git diff --check`: passed.
- Android ARM64 dependency build: SDL3, shaderc, FFmpeg, Capstone, Unicorn, LZ4, Python and Zig passed.
- Gradle `assembleRelease`: passed, including native C/C++, LSFG, Java/Dex, resources and `lintVital`.
- APK: ZIP integrity passed; only `lib/arm64-v8a`; package `com.botwrecomp.android`; `versionCode 39`; `versionName 0.3.4-beta-amaral.1`.
- Candidate APK SHA-256: `bb42a824d62488575a6eccb648cb6b1fc2095688b8ad50f0b8eaccbc0a1680df`.
- The legitimate release keystore was not present in the repository, workspace or Library search. Gradle therefore used its documented debug fallback. Its certificate SHA-256 (`4ba608a4814ec9465291aa371a8fbf4cc7a0e6e6442f533f59e2d7a8c24abccb`) differs from the previous APK (`930841f5756d9d8716ae5e0de03cd55a871debf5959a30865f935b16a2488223`), so this candidate cannot update that installation.

## Device validation still required

An off-device build cannot prove an FPS gain. Run A/B/A on the same Odin 2 Portal Pro, driver, save, power mode and thermal start. Compare native FPS separately from generated FPS, plus P95/P99 frametime, 1% low, shader/pipeline stutters and visual correctness in the Great Plateau/open-world route.

The candidate is accepted only if it does not regress physics, saves, the importer, first-run game build, graphical correctness or sustained frame pacing.

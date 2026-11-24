#!/usr/bin/env python3
"""Check a pipeline warm-up list (cache/pipe_warm.bin, vulkan/exec.c's WarmHeader "BOTWPW2") before it goes into the
APK as android/botwrecompandroid/app/src/main/assets/pipe_seed_v<version>.bin: its header, size, game version, and how
many pipelines and shader pairs it holds. Nothing in it is the game's: hashes of the shaders' first bytes and the
pipelines' keys.

  python3 tools/pipe_warm_info.py <pipe_warm.bin> [--install]   (--install: copies it to the assets as the seed)
"""
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HDR = struct.Struct('<8s6I')  # magic, entry_size, game_version, skey_size, pkey_size, count, pad


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    data = Path(sys.argv[1]).read_bytes()
    if len(data) < HDR.size:
        print('too short for a header')
        return 1
    magic, esz, ver, sk, pk, count, _ = HDR.unpack_from(data)
    if magic != b'BOTWPW2\0':
        print('not a pipeline warm-up list (magic %r)' % magic)
        return 1
    body = len(data) - HDR.size
    if esz == 0 or body // esz < count:
        print('cut short: %d bytes for %d entries of %d' % (body, count, esz))
        return 1
    pairs = {struct.unpack_from('<QQ', data, HDR.size + i * esz) for i in range(count)}
    print('game version %d, %d pipelines over %d shader pairs; entry %d bytes (shader key %d, pipeline key %d), %d KB'
          % (ver, count, len(pairs), esz, sk, pk, len(data) // 1024))
    if '--install' in sys.argv:
        dst = ROOT / 'android/botwrecompandroid/app/src/main/assets' / ('pipe_seed_v%d.bin' % ver)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sys.argv[1], dst)
        print('installed as', dst.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())

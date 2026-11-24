#!/usr/bin/env python3
# Summary of a Turnip GPU trace (MESA_GPU_TRACES=print, MESA_GPU_TRACEFILE=...): the render passes grouped by size,
# attachments, depth, UBWC per attachment (n / y; after "|" the depth), GMEM or sysmem (tiled), load / store / clear
# bytes per pixel and LRZ - per second of the trace: passes, GPU ms, draws; then the autotune's and LRZ's reasons.
# Usage: python3 -I tools/gputrace_summary.py gputrace-<pid>.txt   (read as a stream: the traces run to ~650 MB)
import sys, re, collections
kv = re.compile(r'(\w+)=([^,]*)')
agg = collections.defaultdict(lambda: [0, 0, 0, 0])  # n, ns, draws, max
cur = None; t_first = t_last = None; total_rp_ns = 0; reasons = collections.Counter(); lrzr = collections.Counter()
with open(sys.argv[1], 'r', errors='replace') as f:
    for line in f:
        if 'start_render_pass' in line:
            ns = int(line[:16]); d = dict(kv.findall(line.split('start_render_pass', 1)[1]))
            cur = (ns, d)
            if t_first is None: t_first = ns
        elif 'end_render_pass' in line and cur:
            ns = int(line[:16]); e = dict(kv.findall(line.split('end_render_pass', 1)[1]))
            s, d = cur; cur = None; t_last = ns
            key = (d.get('width'), d.get('height'), d.get('attachment_count'), d.get('hasDepth'), d.get('ubwc'),
                   e.get('tiledRender'), d.get('loadCPP'), d.get('storeCPP'), d.get('clearCPP'), e.get('lrz'))
            a = agg[key]; dur = max(0, ns - s)
            a[0] += 1; a[1] += dur; a[2] += int(e.get('drawCount', 0) or 0); a[3] = max(a[3], dur)
            total_rp_ns += dur
            if e.get('forceRenderModeReason'): reasons[e['forceRenderModeReason']] += 1
            if d.get('cbDisableReason'): reasons['cb:' + d['cbDisableReason']] += 1
            if e.get('lrzDisableReason'): lrzr[e['lrzDisableReason']] += 1
span = (t_last - t_first) / 1e9
print(f"span {span:.1f} s, render-pass time {total_rp_ns/1e9:.2f} s")
print(" n/s    ms/s   draws/s  avg_ms  max_ms   WxH att depth ubwc tiled loadCPP storeCPP clearCPP lrz")
for k, a in sorted(agg.items(), key=lambda kv: -kv[1][1])[:22]:
    print(f"{a[0]/span:5.1f} {a[1]/1e6/span:7.2f} {a[2]/span:8.0f} {a[1]/1e6/a[0]:7.3f} {a[3]/1e6:7.2f}   {k[0]}x{k[1]} {k[2]} {k[3]} {k[4]} {k[5]} {k[6]} {k[7]} {k[8]} {k[9]}")
print("reasons", reasons.most_common(8)); print("lrz disable", lrzr.most_common(8))

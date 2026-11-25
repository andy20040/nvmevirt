#!/usr/bin/env python3
"""Read FS-nN-rR.json and matching .kernel.log; write CSV and SVG graphs.

Uses only Python's standard library. Channel/zone statistics are sampled at
successful ZNS write arrivals. They count pending modeled NAND work,
not elapsed-time channel utilization.
"""
import argparse
import csv
import json
import re
import statistics as st
from pathlib import Path
from xml.sax.saxutils import escape

NAME = re.compile(r'(zonefs|f2fs)-n(1|2|4|8)-r(\d+)')
LOG = re.compile(
    r'\[ZNS Parallelism v2\] Pending NAND Channels:\s*(\d+)\s*/\s*(\d+), '
    r'Pending NAND Zones:\s*(\d+)\s*/\s*(\d+)\s*\(Total IOs:\s*(\d+), '
    r'Op:\s*(write|read)\)'
)


def chart(path, rows, key, title, ylabel):
    groups = {}
    for r in rows:
        if r[key] != '':
            groups.setdefault((r['fs'], r['workers']), []).append(float(r[key]))
    maximum = max((max(v) for v in groups.values()), default=1) or 1
    maximum *= 1.15
    x = lambda n: 90 + [1, 2, 4, 8].index(n) * 180
    y = lambda v: 380 - v / maximum * 290
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="470" viewBox="0 0 760 470">',
           '<rect width="760" height="470" fill="white"/>',
           f'<text x="380" y="25" text-anchor="middle" font-family="sans-serif">{escape(title)}</text>',
           f'<text x="20" y="55" font-family="sans-serif" font-size="12">{escape(ylabel)}</text>']
    for i in range(6):
        value = maximum * i / 5
        yy = y(value)
        svg += [f'<path d="M80 {yy}H650" stroke="#ddd"/>',
                f'<text x="73" y="{yy+4}" text-anchor="end" font-size="12">{value:.2f}</text>']
    for fs, color in [('zonefs', '#1675c5'), ('f2fs', '#d65f18')]:
        points = []
        for n in [1, 2, 4, 8]:
            values = groups.get((fs, n))
            if not values:
                continue
            xx, yy = x(n), y(st.mean(values))
            points.append(f'{xx},{yy}')
            svg += [f'<path d="M{xx} {y(min(values))}V{y(max(values))}" stroke="{color}"/>',
                    f'<circle cx="{xx}" cy="{yy}" r="4" fill="{color}"/>']
        svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
        svg.append(f'<text x="660" y="{80 if fs == "zonefs" else 105}" fill="{color}">{fs}</text>')
    for n in [1, 2, 4, 8]:
        svg.append(f'<text x="{x(n)}" y="405" text-anchor="middle">{n}</text>')
    svg += ['<text x="380" y="435" text-anchor="middle">Workers (points: mean; bars: min–max across runs)</text>', '</svg>']
    path.write_text('\n'.join(svg))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--workers', type=int, choices=[1, 2, 4, 8])
    p.add_argument('--repeat', type=int)
    a = p.parse_args()
    rows = []
    for path in sorted(a.directory.glob('*.json')):
        match = NAME.fullmatch(path.stem)
        if not match:
            continue
        fs, workers, repeat = match.groups()
        if a.workers is not None and int(workers) != a.workers:
            continue
        if a.repeat is not None and int(repeat) != a.repeat:
            continue
        jobs = json.loads(path.read_text())['jobs']
        if any(j.get('error', 0) for j in jobs):
            raise SystemExit(f'Failed fio run: {path}')
        # group_reporting produces one aggregate job for these generated jobs.
        if len(jobs) != 1:
            raise SystemExit(f'Expected one group-reporting aggregate: {path}')
        w = jobs[0]['write']
        if w['io_bytes'] != 32 * 1024 * 1024:
            raise SystemExit(f'Unexpected total write bytes: {path}')
        log = path.with_suffix('.kernel.log')
        if not log.exists():
            raise SystemExit(f'Missing matching kernel log: {log}')
        log_text = log.read_text(errors='replace')
        if '[ZNS Parallelism]' in log_text:
            raise SystemExit(f'Legacy records mixed into v2 log: {log}')
        samples = LOG.findall(log_text)
        if not samples:
            raise SystemExit(f'No v2 samples in {log}; rerun fio with the updated module')
        if re.search(r'WP error|I/O error|Corrupted write pointer|ioremap|invalid size|'
                     r'Need to increase array size|No free entry|tracking allocation failed',
                     log_text, re.I):
            raise SystemExit(f'Kernel log contains an I/O or model error: {log}')
        io_ids = [int(s[4]) for s in samples]
        if any(curr != prev + 1 for prev, curr in zip(io_ids, io_ids[1:])):
            raise SystemExit(f'Missing or mixed parallelism records: {log}')
        write_samples = [s for s in samples if s[5] == 'write']
        if not write_samples:
            raise SystemExit(f'No successful ZNS write samples: {log}')
        channels = [int(s[0]) for s in write_samples]
        zones = [int(s[2]) for s in write_samples]
        totals = {int(s[1]) for s in samples}
        zone_totals = {int(s[3]) for s in samples}
        if len(totals) != 1 or len(zone_totals) != 1 or 0 in totals or 0 in zone_totals:
            raise SystemExit(f'Inconsistent channel/zone counts: {log}')
        if any(c > next(iter(totals)) or z > next(iter(zone_totals))
               for c, z in zip(channels, zones)):
            raise SystemExit(f'Invalid pending count: {log}')
        row = dict(fs=fs, workers=int(workers), repeat=int(repeat),
                   mib_s=w['bw_bytes'] / 1048576,
                   latency_us=w['lat_ns']['mean'] / 1000,
                   p99_clat_us=w['clat_ns'].get('percentile', {}).get('99.000000', 0) / 1000,
                   samples=len(write_samples),
                   mean_pending_nand_channels=st.mean(channels),
                   peak_pending_nand_channels=max(channels),
                   mean_pending_nand_zones=st.mean(zones),
                   peak_pending_nand_zones=max(zones),
                   sampled_pending_channel_percent=100 * st.mean(channels) / next(iter(totals)))
        rows.append(row)
    if not rows:
        raise SystemExit('No matching fio JSON files found.')
    if a.workers is not None and a.repeat is not None and {r['fs'] for r in rows} != {'zonefs', 'f2fs'}:
        raise SystemExit('The selected run needs both ZoneFS and F2FS results.')
    for row in rows:
        baseline = [r['mib_s'] for r in rows if r['fs'] == row['fs'] and r['workers'] == 1]
        row['speedup'] = row['mib_s'] / st.mean(baseline) if baseline else ''
        row['efficiency'] = row['speedup'] / row['workers'] if baseline else ''
    with (a.directory / 'summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    chart(a.directory / 'throughput.svg', rows, 'mib_s', 'Sequential write throughput', 'MiB/s')
    chart(a.directory / 'channels.svg', rows, 'mean_pending_nand_channels',
          'Request-sampled channels with pending NAND work', 'Mean channels')
    chart(a.directory / 'zones.svg', rows, 'mean_pending_nand_zones',
          'Request-sampled zones with pending NAND work', 'Mean zones')
    print('FS       MiB/s    mean/peak channels   mean/peak zones   sampled channels')
    for row in rows:
        print(f"{row['fs']:<7} {row['mib_s']:>7.2f}   "
              f"{row['mean_pending_nand_channels']:>5.2f}/{row['peak_pending_nand_channels']:<2}"
              f"              {row['mean_pending_nand_zones']:>5.2f}/{row['peak_pending_nand_zones']:<2}"
              f"            {row['sampled_pending_channel_percent']:>5.1f}%")
    print(f'Wrote summary.csv, throughput.svg, channels.svg, zones.svg in {a.directory}')


if __name__ == '__main__':
    main()

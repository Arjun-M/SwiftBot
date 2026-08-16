import csv
import json
from pathlib import Path
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
RESULTS = BASE / 'results'
OUT = BASE / 'analysis'
OUT.mkdir(exist_ok=True)

names = {
    'swiftbot': 'SwiftBot',
    'aiogram': 'aiogram',
    'ptb': 'python-telegram-bot',
    'telebot': 'pyTelegramBotAPI',
}

rows = []
for framework, display in names.items():
    speed = json.loads((RESULTS / f'full_{framework}_10routes.json').read_text())
    memory = json.loads((RESULTS / f'memory_{framework}_normalgc.json').read_text())
    stat_key = framework if framework not in {'ptb', 'telebot'} else framework
    stats = json.loads((RESULTS / f'stats_{stat_key}.json').read_text())
    rows.append({
        'framework': framework,
        'display_name': display,
        'version': {'swiftbot': '1.6.3', 'aiogram': '3.30.0', 'ptb': '22.8', 'telebot': '4.36.1'}[framework],
        'throughput_updates_per_second': speed['median_throughput_updates_per_second'],
        'latency_us_per_update': speed['median_latency_microseconds_per_update'],
        'p95_seconds_per_repeat': speed['p95_seconds'],
        'setup_ms': speed['setup_ms'],
        'peak_rss_mib': memory['peak_sampled_rss_kib'] / 1024,
        'build_rss_delta_mib': memory['build_rss_delta_kib'] / 1024,
        'workload_rss_delta_mib': memory['workload_rss_delta_kib'] / 1024,
        'framework_package_mib': stats['package_size_kib'] / 1024,
        'site_packages_mib': stats['site_packages_size_mib'],
        'handler_correct': speed['correct'] and memory['correct'],
    })

swift = next(row for row in rows if row['framework'] == 'swiftbot')
for row in rows:
    row['throughput_vs_swiftbot'] = row['throughput_updates_per_second'] / swift['throughput_updates_per_second']
    row['peak_rss_vs_swiftbot'] = row['peak_rss_mib'] / swift['peak_rss_mib']

fields = list(rows[0].keys())
with (OUT / 'extended_summary.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
(OUT / 'extended_summary.json').write_text(json.dumps(rows, indent=2) + '\n')

# Memory chart.
plt.style.use('seaborn-v0_8-whitegrid')
ordered = sorted(rows, key=lambda row: row['peak_rss_mib'])
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [row['display_name'] for row in ordered]
values = [row['peak_rss_mib'] for row in ordered]
colors = ['#177245' if row['framework'] == 'swiftbot' else '#4776a8' for row in ordered]
bars = ax.barh(labels, values, color=colors)
ax.set_xlabel('Peak sampled resident memory (MiB)')
ax.set_title('Peak RSS during 10,000-update offline dispatch workload')
for bar, value in zip(bars, values):
    ax.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f'{value:.1f}', va='center', fontsize=9)
fig.tight_layout()
fig.savefig(OUT / 'memory_peak_rss.png', dpi=180)
plt.close(fig)

# Pool scaling chart.
pool = json.loads((RESULTS / 'pool_full.json').read_text())
fig, ax = plt.subplots(figsize=(9, 5.5))
points = pool['concurrency_scaling']
ax.plot([row['workers'] for row in points], [row['median_throughput_updates_per_second'] for row in points], marker='o', linewidth=2, color='#177245')
ax.set_xlabel('SwiftBot worker count')
ax.set_ylabel('Median completed updates/second')
ax.set_title('SwiftBot worker-pool scaling with 2 ms async handler delay')
ax.set_xticks([row['workers'] for row in points])
for row in points:
    ax.annotate(f"{row['median_throughput_updates_per_second']:.0f}", (row['workers'], row['median_throughput_updates_per_second']), textcoords='offset points', xytext=(0, 8), ha='center', fontsize=9)
fig.tight_layout()
fig.savefig(OUT / 'swiftbot_pool_scaling.png', dpi=180)
plt.close(fig)

(OUT / 'pool_summary.json').write_text(json.dumps(pool, indent=2) + '\n')

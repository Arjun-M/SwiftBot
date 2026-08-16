import json
from pathlib import Path
import csv
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

primary = []
for framework in names:
    data = json.loads((RESULTS / f'full_{framework}_10routes.json').read_text())
    stats_name = 'python-telegram-bot' if framework == 'ptb' else 'pyTelegramBotAPI' if framework == 'telebot' else framework
    stats = json.loads((RESULTS / f'stats_{"ptb" if framework == "ptb" else "telebot" if framework == "telebot" else framework}.json').read_text())
    data['display_name'] = names[framework]
    data['package_size_kib'] = stats['package_size_kib']
    data['site_packages_size_mib'] = stats['site_packages_size_mib']
    data['venv_size_mib'] = stats['venv_size_mib']
    primary.append(data)

swift = next(row for row in primary if row['framework'] == 'swiftbot')
for row in primary:
    row['throughput_vs_swiftbot'] = row['median_throughput_updates_per_second'] / swift['median_throughput_updates_per_second']
    row['latency_vs_swiftbot'] = row['median_latency_microseconds_per_update'] / swift['median_latency_microseconds_per_update']

with (OUT / 'primary_summary.csv').open('w', newline='') as f:
    fields = ['display_name', 'framework', 'median_throughput_updates_per_second', 'median_latency_microseconds_per_update', 'setup_ms', 'package_size_kib', 'site_packages_size_mib', 'venv_size_mib', 'correct', 'throughput_vs_swiftbot', 'latency_vs_swiftbot']
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: row[field] for field in fields} for row in primary)

(OUT / 'primary_summary.json').write_text(json.dumps(primary, indent=2) + '\n')

# Throughput chart.
ordered = sorted(primary, key=lambda row: row['median_throughput_updates_per_second'], reverse=True)
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [row['display_name'] for row in ordered]
values = [row['median_throughput_updates_per_second'] for row in ordered]
colors = ['#177245' if row['framework'] == 'swiftbot' else '#4776a8' for row in ordered]
bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1])
ax.set_xlabel('Median offline dispatch throughput (updates/second)')
ax.set_title('Telegram framework dispatch benchmark — 10 exact-text routes')
ax.ticklabel_format(axis='x', style='plain')
for bar, value in zip(bars, values[::-1]):
    ax.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f'{value:,.0f}', va='center', fontsize=9)
fig.tight_layout()
fig.savefig(OUT / 'throughput_10routes.png', dpi=180)
plt.close(fig)

# Routing scalability chart.
fig, ax = plt.subplots(figsize=(9, 5.5))
for framework in names:
    points = []
    for routes in [1, 10, 50]:
        row = json.loads((RESULTS / f'{framework}_{routes}routes.json').read_text())
        points.append((routes, row['median_throughput_updates_per_second']))
    points.sort()
    ax.plot([p[0] for p in points], [p[1] for p in points], marker='o', linewidth=2, label=names[framework])
ax.set_xlabel('Registered exact-text routes')
ax.set_ylabel('Median offline dispatch throughput (updates/second)')
ax.set_title('Routing scalability under increasing route count')
ax.set_xticks([1, 10, 50])
ax.legend(frameon=True)
fig.tight_layout()
fig.savefig(OUT / 'routing_scalability.png', dpi=180)
plt.close(fig)

# Scaling table.
scaling = []
for framework in names:
    for routes in [1, 10, 50]:
        row = json.loads((RESULTS / f'{framework}_{routes}routes.json').read_text())
        scaling.append({
            'framework': framework,
            'display_name': names[framework],
            'routes': routes,
            'median_throughput_updates_per_second': row['median_throughput_updates_per_second'],
            'median_latency_microseconds_per_update': row['median_latency_microseconds_per_update'],
            'correct': row['correct'],
        })
(OUT / 'scaling_summary.json').write_text(json.dumps(scaling, indent=2) + '\n')

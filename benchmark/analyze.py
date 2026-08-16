"""Analyze corrected public raw-update benchmark outputs."""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results" / "public"
OUT = BASE / "reports"
OUT.mkdir(exist_ok=True)

NAMES = {
    "swiftbot": "SwiftBot",
    "aiogram": "aiogram",
    "ptb": "python-telegram-bot",
    "telebot": "pyTelegramBotAPI",
}


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


primary = []
for framework, display_name in NAMES.items():
    data = load(f"{framework}_10routes.json")
    memory = load(f"memory_{framework}.json")
    row = {
        "framework": framework,
        "display_name": display_name,
        "median_throughput_updates_per_second": data["median_throughput_updates_per_second"],
        "median_latency_microseconds_per_update": data["median_latency_microseconds_per_update"],
        "setup_ms": data["setup_ms"],
        "peak_rss_mib": memory["peak_sampled_rss_kib"] / 1024,
        "build_rss_delta_mib": memory["build_rss_delta_kib"] / 1024,
        "workload_rss_delta_mib": memory["workload_rss_delta_kib"] / 1024,
        "correct": bool(data["correct"] and memory["correct"]),
        "api_surface": data["adapter"]["api_surface"],
        "gc_mode": data["gc_mode"],
    }
    primary.append(row)

swift = next(row for row in primary if row["framework"] == "swiftbot")
for row in primary:
    row["throughput_vs_swiftbot"] = row["median_throughput_updates_per_second"] / swift["median_throughput_updates_per_second"]
    row["latency_vs_swiftbot"] = row["median_latency_microseconds_per_update"] / swift["median_latency_microseconds_per_update"]
    row["peak_rss_vs_swiftbot"] = row["peak_rss_mib"] / swift["peak_rss_mib"]

fields = [
    "display_name", "framework", "median_throughput_updates_per_second",
    "median_latency_microseconds_per_update", "setup_ms", "peak_rss_mib",
    "build_rss_delta_mib", "workload_rss_delta_mib", "correct",
    "throughput_vs_swiftbot", "latency_vs_swiftbot", "peak_rss_vs_swiftbot",
    "api_surface", "gc_mode",
]
with (OUT / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({field: row[field] for field in fields} for row in primary)
(OUT / "summary.json").write_text(json.dumps(primary, indent=2) + "\n", encoding="utf-8")

scaling = []
for framework, display_name in NAMES.items():
    for routes in [1, 10, 50]:
        row = load(f"{framework}_{routes}routes.json")
        scaling.append({
            "framework": framework,
            "display_name": display_name,
            "routes": routes,
            "median_throughput_updates_per_second": row["median_throughput_updates_per_second"],
            "median_latency_microseconds_per_update": row["median_latency_microseconds_per_update"],
            "correct": row["correct"],
        })
(OUT / "scaling.json").write_text(json.dumps(scaling, indent=2) + "\n", encoding="utf-8")

plt.style.use("seaborn-v0_8-whitegrid")

ordered = sorted(primary, key=lambda row: row["median_throughput_updates_per_second"])
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [row["display_name"] for row in ordered]
values = [row["median_throughput_updates_per_second"] for row in ordered]
colors = ["#177245" if row["framework"] == "swiftbot" else "#4776a8" for row in ordered]
bars = ax.barh(labels, values, color=colors)
ax.set_xlabel("Median updates/second")
ax.set_title("Public raw-update dispatch — 10 exact-text routes; GC enabled")
ax.ticklabel_format(axis="x", style="plain")
for bar, value in zip(bars, values):
    ax.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:,.0f}", va="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "charts" / "fair_throughput_10routes.png", dpi=180)
plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 5.5))
for framework, display_name in NAMES.items():
    points = [row for row in scaling if row["framework"] == framework]
    points.sort(key=lambda row: row["routes"])
    ax.plot(
        [row["routes"] for row in points],
        [row["median_throughput_updates_per_second"] for row in points],
        marker="o",
        linewidth=2,
        label=display_name,
    )
ax.set_xlabel("Registered exact-text routes")
ax.set_ylabel("Median updates/second")
ax.set_title("Public raw-update route scaling; GC enabled")
ax.set_xticks([1, 10, 50])
ax.legend(frameon=True)
fig.tight_layout()
fig.savefig(OUT / "charts" / "fair_scalability.png", dpi=180)
plt.close(fig)

ordered = sorted(primary, key=lambda row: row["peak_rss_mib"])
fig, ax = plt.subplots(figsize=(9, 5.5))
labels = [row["display_name"] for row in ordered]
values = [row["peak_rss_mib"] for row in ordered]
colors = ["#177245" if row["framework"] == "swiftbot" else "#4776a8" for row in ordered]
bars = ax.barh(labels, values, color=colors)
ax.set_xlabel("Peak sampled RSS (MiB)")
ax.set_title("Public raw-update memory workload — 10,000 updates; GC enabled")
for bar, value in zip(bars, values):
    ax.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "charts" / "fair_memory_peak_rss.png", dpi=180)
plt.close(fig)

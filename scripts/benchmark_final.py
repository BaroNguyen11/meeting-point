import json
import time
import numpy as np
from backend.core.config import settings
from backend.services.graph_engine import GraphEngine


def jains_fairness(times: list[float]) -> float:
    arr = np.array(times, dtype=np.float64)
    denom = len(arr) * np.sum(arr ** 2)
    return float((np.sum(arr) ** 2) / denom) if denom > 0 else 1.0


def run_benchmark(num_trials: int = 300, seed: int = 42):
    rng = np.random.default_rng(seed)
    engine = GraphEngine(
        adj_path=settings.GRAPH_ADJ_PATH,
        meta_path=settings.GRAPH_META_PATH,
        poi_path=settings.POI_CSV_PATH,
    )

    total_directed_edges = engine.adj_matrix.nnz
    summary = {
        "graph_nodes": engine.num_nodes,
        "graph_edges": total_directed_edges,
        "total_pois": len(engine.df_pois),
        "trials_per_setting": num_trials,
        "latency_by_k": {},
        "alpha_tradeoff_k4": {},
        "rush_hour_impact_k4": {},
    }

    # 1. Đo độ trễ & tỷ lệ cắt tỉa không gian Wavefront theo số lượng người k
    print("\n1/3 Đang đo độ trễ & hiệu quả cắt tỉa Wavefront theo quy mô nhóm k...")
    for k in [2, 3, 4, 6]:
        latencies_ms = []
        pruning_ratios = []

        for _ in range(num_trials):
            sampled_nodes = rng.choice(engine.num_nodes, size=k, replace=False)
            people = [
                {"name": f"P{i+1}", "lat": float(engine.coords[n, 0]), "lng": float(engine.coords[n, 1])}
                for i, n in enumerate(sampled_nodes)
            ]

            t0 = time.perf_counter()
            engine.solve(people=people, alpha=0.5, max_minutes=35.0)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            wave = engine.compute_wavefront_edges(people=people, max_minutes=35.0)
            full_search_edges = k * total_directed_edges
            pruned_pct = max(0.0, (1.0 - wave["total_edges"] / full_search_edges) * 100.0)
            pruning_ratios.append(pruned_pct)

        summary["latency_by_k"][f"k={k}"] = {
            "mean_ms": round(float(np.mean(latencies_ms)), 2),
            "p50_ms": round(float(np.percentile(latencies_ms, 50)), 2),
            "p95_ms": round(float(np.percentile(latencies_ms, 95)), 2),
            "wavefront_pruned_pct": round(float(np.mean(pruning_ratios)), 2),
        }

    # 2. Đánh giá đánh đổi Hiệu quả vs Công bằng (alpha = 0.0, 0.5, 1.0) & Giờ cao điểm (k=4)
    print("2/3 Đang đo đánh đổi Pareto (alpha) và tác động giờ cao điểm 17:30 (k=4)...")
    groups_k4 = []
    for _ in range(num_trials):
        sampled_nodes = rng.choice(engine.num_nodes, size=4, replace=False)
        groups_k4.append([
            {"name": f"P{i+1}", "lat": float(engine.coords[n, 0]), "lng": float(engine.coords[n, 1])}
            for i, n in enumerate(sampled_nodes)
        ])

    for alpha in [0.0, 0.5, 1.0]:
        f_max_list, f_avg_list, jain_list = [], [], []
        for people in groups_k4:
            res = engine.solve(people=people, alpha=alpha, max_minutes=40.0)
            t_vals = [x["minutes"] for x in res["times_per_person"]]
            f_max_list.append(max(t_vals))
            f_avg_list.append(float(np.mean(t_vals)))
            jain_list.append(jains_fairness(t_vals))

        summary["alpha_tradeoff_k4"][f"alpha={alpha}"] = {
            "mean_f_max_min": round(float(np.mean(f_max_list)), 2),
            "mean_per_person_min": round(float(np.mean(f_avg_list)), 2),
            "jains_fairness_index": round(float(np.mean(jain_list)), 4),
        }

    zone_shifts = 0
    normal_fmax, rush_fmax = [], []
    for people in groups_k4:
        res_normal = engine.solve(people=people, alpha=0.5, depart_hour=None, max_minutes=45.0)
        res_rush = engine.solve(people=people, alpha=0.5, depart_hour=17.5, max_minutes=45.0)
        if res_normal["optimum"]["node_idx"] != res_rush["optimum"]["node_idx"]:
            zone_shifts += 1
        normal_fmax.append(res_normal["optimum"]["f_max"])
        rush_fmax.append(res_rush["optimum"]["f_max"])

    summary["rush_hour_impact_k4"] = {
        "zone_shift_rate_pct": round((zone_shifts / num_trials) * 100.0, 2),
        "normal_mean_f_max_min": round(float(np.mean(normal_fmax)), 2),
        "rush_17h30_mean_f_max_min": round(float(np.mean(rush_fmax)), 2),
    }

    with open("data/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("3/3 Hoàn tất! Đã lưu kết quả tại data/benchmark_results.json:\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_benchmark(num_trials=300)
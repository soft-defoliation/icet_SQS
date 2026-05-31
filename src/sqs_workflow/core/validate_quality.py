#!/usr/bin/env python3
"""
05_validate_sqs_quality.py
步骤5：SQS质量验证 (Plan A - 基础版)
评估核心指标：团簇向量偏差、浓度准确性、基本结构检查
参考标准：van de Walle 2013
"""
from __future__ import annotations

from typing import Optional, Any
import json
import sys
import numpy as np
from pathlib import Path
from ase import Atoms
from icet import ClusterSpace
from icet.input_output.logging_tools import set_log_config

set_log_config(level="WARNING")

from sqs_workflow.constants import QualityThresholds  # noqa: E402


from sqs_workflow.utils.quality_utils import (  # noqa: E402
    calculate_cv_deviation,
    evaluate_sqs_quality,
    estimate_achievable_deviation,
    calculate_per_order_deviation,
    count_perfect_matches,
)


class SQSQualityValidator:
    def __init__(
        self,
        sqs_file: Optional[Path] = None,
        cs_file: Optional[Path] = None,
        doping_info_file: Optional[Path] = None,
    ):
        self.output_dir = Path("output")

        self.sqs_file = sqs_file or self.output_dir / "03_sqs_structure.json"
        self.cs_file = cs_file or self.output_dir / "02_clusterspace.cs"
        self.doping_info_file = doping_info_file or self.output_dir / "02_doping_info.json"

        self.sqs: Optional[Atoms] = None
        self.sqs_icet: Optional[Atoms] = None
        self.cs: Optional[ClusterSpace] = None
        self.doping_info: Optional[dict[str, Any]] = None

    def load_data(self) -> None:
        if not self.sqs_file.exists():
            raise FileNotFoundError(f"SQS 结构文件不存在: {self.sqs_file}")
        with open(self.sqs_file, "r") as f:
            sqs_data = json.load(f)
        self.sqs = Atoms(
            positions=sqs_data["positions"],
            numbers=sqs_data["numbers"],
            cell=sqs_data["cell"],
            pbc=True,
        )
        self.sqs.wrap()

        if "icet_original" in sqs_data:
            icet_data = sqs_data["icet_original"]
            self.sqs_icet = Atoms(
                positions=icet_data["positions"],
                numbers=icet_data["numbers"],
                cell=icet_data["cell"],
                pbc=True,
            )
            self.sqs_icet.wrap()
        else:
            self.sqs_icet = None

        if not self.cs_file.exists():
            raise FileNotFoundError(f"ClusterSpace 文件不存在: {self.cs_file}")
        self.cs = ClusterSpace.read(str(self.cs_file))

        if not self.doping_info_file.exists():
            raise FileNotFoundError(f"掺杂信息文件不存在: {self.doping_info_file}")
        with open(self.doping_info_file, "r") as f:
            self.doping_info = json.load(f)

    def _get_sqs_for_cv(self) -> Atoms:
        if self.sqs_icet is not None:
            return self.sqs_icet
        return self._get_sqs()

    def _get_sqs(self) -> Atoms:
        assert self.sqs is not None, "SQS结构未加载，请先调用 load_data()"
        return self.sqs

    def _get_cs(self) -> ClusterSpace:
        assert self.cs is not None, "ClusterSpace未加载，请先调用 load_data()"
        return self.cs

    def _get_doping_info(self) -> dict[str, Any]:
        assert self.doping_info is not None, "掺杂信息未加载，请先调用 load_data()"
        return self.doping_info

    def _calculate_n_disordered(self) -> int:
        doping_info = self._get_doping_info()
        sqs = self._get_sqs()
        chemical_symbols = doping_info.get("chemical_symbols", [])
        symbols = sqs.get_chemical_symbols()

        disordered_elements = set()
        for site_symbols in chemical_symbols:
            if len(site_symbols) > 1:
                disordered_elements.update(site_symbols)

        if not disordered_elements:
            return len(sqs)

        n_disordered = 0
        for sym in symbols:
            if sym in disordered_elements:
                n_disordered += 1

        return n_disordered

    def check_cluster_vector(self) -> dict[str, Any]:
        cs = self._get_cs()
        sqs_cv = self._get_sqs_for_cv()
        sqs = self._get_sqs()
        doping_info = self._get_doping_info()
        target_conc = doping_info.get("target_concentrations", {})

        if target_conc:
            deviation = calculate_cv_deviation(
                cs, sqs_cv, target_concentrations=target_conc, use_icet_comparison=False
            )
            n_disordered = self._calculate_n_disordered()
            quality, passed, context = evaluate_sqs_quality(
                deviation, len(sqs), n_disordered, target_conc
            )
            cv_sqs = cs.get_cluster_vector(sqs_cv)

            from sqs_workflow.utils.quality_utils import calculate_target_cluster_vector

            cv_target_vals = calculate_target_cluster_vector(cs, target_conc, len(cv_sqs))
            match_stats = count_perfect_matches(cv_sqs, cv_target_vals)
            per_order = calculate_per_order_deviation(cs, sqs_cv, target_conc)

            return {
                "deviation": float(deviation),
                "quality": quality,
                "context": context,
                "pass": passed,
                "cv_sqs": (cv_sqs.tolist() if len(cv_sqs) < 100 else f"[{len(cv_sqs)} values]"),
                "cv_target": (
                    cv_target_vals.tolist()
                    if len(cv_target_vals) < 100
                    else f"[{len(cv_target_vals)} values]"
                ),
                "perfect_matches": match_stats,
                "per_order_deviation": {
                    str(o): {k: v for k, v in info.items() if k not in ("indices", "components")}
                    for o, info in per_order.items()
                },
            }

        cv_sqs = cs.get_cluster_vector(sqs_cv)
        cv_target = self._calculate_target_cluster_vector()

        if cv_target is None:
            return {
                "status": "warning",
                "message": "无法计算目标团簇向量（需要目标浓度）",
                "deviation": None,
                "pass": None,
            }

        deviation = np.sqrt(np.sum((cv_sqs - cv_target) ** 2))
        quality, passed, _ = evaluate_sqs_quality(deviation)

        return {
            "deviation": float(deviation),
            "quality": quality,
            "pass": passed,
            "cv_sqs": (cv_sqs.tolist() if len(cv_sqs) < 100 else f"[{len(cv_sqs)} values]"),
            "cv_target": (
                cv_target.tolist() if len(cv_target) < 100 else f"[{len(cv_target)} values]"
            ),
        }

    def _calculate_target_cluster_vector(self) -> Optional[np.ndarray]:
        cs = self._get_cs()
        sqs = self._get_sqs_for_cv()
        doping_info = self._get_doping_info()
        target_conc = doping_info.get("target_concentrations", {})

        if not target_conc:
            return None

        try:
            from icet.tools.structure_generation import _get_sqs_cluster_vector

            return _get_sqs_cluster_vector(cs, target_conc)
        except ImportError:
            cv_sqs = cs.get_cluster_vector(sqs)
            cv_target = np.zeros(len(cv_sqs))
            cv_target[0] = 1.0
            return cv_target
        except Exception:
            import sys

            print(
                "  警告: 目标团簇向量计算失败，跳过此检查",
                file=sys.stderr,
            )
            return None

    def check_concentration(self) -> dict[str, Any]:
        doping_info = self._get_doping_info()
        sqs = self._get_sqs()
        target_conc = doping_info.get("target_concentrations", {})
        chemical_symbols = doping_info.get("chemical_symbols", [])

        if not target_conc:
            return {"status": "warning", "message": "未设置目标浓度"}

        symbols = sqs.get_chemical_symbols()
        total_atoms = len(symbols)

        actual_global_conc: dict[str, float] = {}
        for sym in set(symbols):
            count = symbols.count(sym)
            actual_global_conc[sym] = count / total_atoms

        disordered_elements = set()
        for site_symbols in chemical_symbols:
            if len(site_symbols) > 1:
                disordered_elements.update(site_symbols)

        if not disordered_elements:
            actual_conc = actual_global_conc
            n_disordered = total_atoms
        else:
            disordered_counts: dict[str, int] = {elem: 0 for elem in disordered_elements}
            n_disordered = 0

            for sym in symbols:
                if sym in disordered_elements:
                    disordered_counts[sym] += 1
                    n_disordered += 1

            actual_conc = {}
            for elem in disordered_elements:
                if n_disordered > 0:
                    actual_conc[elem] = disordered_counts[elem] / n_disordered
                else:
                    actual_conc[elem] = 0.0

        results: dict[str, dict[str, dict[str, Any]]] = {}
        all_passed = True

        for group, targets in target_conc.items():
            group_results: dict[str, dict[str, Any]] = {}

            for elem, target in targets.items():
                actual = actual_conc.get(elem, 0.0)
                deviation = abs(actual - target)

                passed = deviation < 0.01
                if not passed:
                    all_passed = False

                group_results[elem] = {
                    "target": target,
                    "actual": actual,
                    "actual_global": actual_global_conc.get(elem, 0.0),
                    "deviation": deviation,
                    "pass": passed,
                }

            results[group] = group_results

        return {
            "target_concentrations": target_conc,
            "actual_concentrations": actual_conc,
            "actual_global_concentrations": actual_global_conc,
            "n_disordered_sites": n_disordered,
            "details": results,
            "pass": all_passed,
        }

    def check_structure(self) -> dict[str, Any]:
        sqs = self._get_sqs()

        cell = np.array(sqs.cell)
        a = np.linalg.norm(cell[0])
        b = np.linalg.norm(cell[1])
        c = np.linalg.norm(cell[2])
        volume = sqs.get_volume()

        distances = sqs.get_all_distances(mic=True)
        min_dist = np.min(distances[distances > 0.1])
        too_close = np.sum((distances > 0.1) & (distances < 1.0))
        structure_ok = int(too_close) == 0

        return {
            "lattice_parameters": {"a": float(a), "b": float(b), "c": float(c)},
            "volume": float(volume),
            "density": len(sqs) / volume if volume > 0 else 0,
            "min_bond_length": float(min_dist),
            "too_close_pairs": int(too_close),
            "pass": structure_ok,
        }

    def validate(self) -> dict[str, Any]:
        self.load_data()

        sqs = self._get_sqs()
        results: dict[str, Any] = {
            "structure_info": {"formula": sqs.get_chemical_formula(), "n_atoms": len(sqs)},
            "cluster_vector": self.check_cluster_vector(),
            "concentration": self.check_concentration(),
            "structure": self.check_structure(),
        }

        cv_pass = results["cluster_vector"].get("pass", None)
        conc_pass = results["concentration"].get("pass", False)
        struct_pass = results["structure"].get("pass", False)
        overall_pass = (cv_pass is None or cv_pass) and conc_pass and struct_pass

        results["overall"] = {
            "pass": overall_pass,
            "summary": ("SQS质量验证通过 ✓" if overall_pass else "SQS质量验证未通过 ✗"),
        }

        print("Step 4/4: 质量验证")
        print("-" * 50)
        dev = results["cluster_vector"].get("deviation")
        if dev is not None:
            print(
                f"  L2={dev:.6f} | {results['cluster_vector']['quality']} | "
                f"浓度={'✓' if conc_pass else '✗'} | "
                f"结构={'✓' if struct_pass else '✗'}"
            )
        print(f"  → {results['overall']['summary']}")
        print("  详细报告: output/QUALITY_REPORT.txt")
        print()

        return results

    def generate_report(self, output_file: Optional[Path] = None) -> dict[str, Any]:
        results = self.validate()

        if output_file is None:
            output_file = self.output_dir / "QUALITY_REPORT.txt"

        lines = []
        lines.append("=" * 70)
        lines.append("SQS质量验证报告")
        lines.append("=" * 70)
        lines.append("")

        lines.append("结构信息:")
        lines.append(f"  化学式: {results['structure_info']['formula']}")
        lines.append(f"  原子数: {results['structure_info']['n_atoms']}")
        lines.append("")

        cv = results["cluster_vector"]
        lines.append("1. 团簇向量偏差:")
        if cv.get("deviation") is not None:
            lines.append(f"   偏差值 (L2): {cv['deviation']:.6f}")
            lines.append(f"   质量评估: {cv['quality']}")
            lines.append(f"   状态: {'✓ 通过' if cv['pass'] else '✗ 未通过'}")
            lines.append("")

            if "perfect_matches" in cv:
                pm = cv["perfect_matches"]
                lines.append("   完美匹配统计 (van de Walle 2013):")
                for label, th in [("excellent", 0.001), ("good", 0.01), ("acceptable", 0.10)]:
                    s = pm[label]
                    lines.append(f"     Δ<{th}: {s['matched']}/{s['total']} " f"({s['percent']}%)")
                lines.append("")

            if "per_order_deviation" in cv:
                pod = cv["per_order_deviation"]
                lines.append("   按团簇阶次偏差分解:")
                for order_key in sorted(pod, key=int):
                    info = pod[order_key]
                    bar = _deviation_bar(info["l2_deviation"])
                    lines.append(
                        f"     {info['order_name']}: "
                        f"L2={info['l2_deviation']:.6f} "
                        f"(max={info['max_deviation']:.6f}) {bar}"
                    )
                lines.append("")

            if "cv_sqs" in cv and "cv_target" in cv:
                cv_sqs = cv["cv_sqs"]
                cv_target = cv["cv_target"]

                if isinstance(cv_sqs, list) and isinstance(cv_target, list):
                    lines.append("   团簇向量逐分量:")
                    header = f"   {'#':>3}  {'SQS':>10}  " f"{'目标':>10}  {'偏差':>10}"
                    lines.append(header)
                    lines.append("   " + "-" * len(header))

                    for i, (sqs_val, target_val) in enumerate(zip(cv_sqs, cv_target)):
                        diff = abs(sqs_val - target_val)
                        if diff < QualityThresholds.EXCELLENT:
                            mark = "✓"
                        elif diff < QualityThresholds.GOOD:
                            mark = "⚠"
                        else:
                            mark = "✗"
                        lines.append(
                            f"   {i:>3}  {sqs_val:>10.6f}  "
                            f"{target_val:>10.6f}  {diff:>10.6f} {mark}"
                        )

                    lines.append("")
                    lines.append(f"   团簇向量维度: {len(cv_sqs)}")
                    deviations = [abs(s - t) for s, t in zip(cv_sqs[1:], cv_target[1:])]
                    if deviations:
                        max_dev = max(deviations)
                        avg_dev = sum(deviations) / len(deviations)
                        lines.append(f"   最大分量偏差: {max_dev:.6f}")
                        lines.append(f"   平均分量偏差: {avg_dev:.6f}")
                else:
                    lines.append(f"   团簇向量: {cv_sqs}")

            lines.append("")

            if "n_disordered_sites" in results.get("concentration", {}):
                n_disordered = results["concentration"]["n_disordered_sites"]
                lines.append("   系统大小分析:")
                lines.append(f"   无序位点数: {n_disordered}")
                lines.append(f"   总原子数: {results['structure_info']['n_atoms']}")

                if n_disordered < 20:
                    lines.append("   ⚠ 建议: 无序位点数较少，" "建议增大超胞到至少50个无序位点")
                elif n_disordered < 50:
                    lines.append("   💡 中等系统，质量可能受有限尺寸效应影响")
                else:
                    lines.append("   ✓ 系统尺寸充足，可获得高质量SQS")

                doping_info = self._get_doping_info()
                target_conc = doping_info.get("target_concentrations", {})
                if target_conc:
                    estimation = estimate_achievable_deviation(n_disordered, target_conc)
                    if estimation["is_limited"]:
                        lines.append(
                            f"   理论最小偏差估算: " f"{estimation['estimated_min_deviation']:.6f}"
                        )

                        if "discrete_atoms" in estimation:
                            lines.append(
                                f"   离散原子数: "
                                f"少数元素={estimation['discrete_atoms']['minority']}, "
                                f"多数元素={estimation['discrete_atoms']['majority']}"
                            )

                        current_dev = cv["deviation"]
                        if current_dev <= estimation["estimated_min_deviation"] * 1.2:
                            lines.append("   ✓ 当前偏差已接近理论下限")
                            lines.append("     → 这是该系统大小的物理极限，" "无需进一步优化")
        else:
            lines.append(f"   状态: {cv.get('message', '无法评估')}")
        lines.append("")

        conc = results["concentration"]
        lines.append("2. 浓度准确性:")
        if "details" in conc:
            for group, details in conc["details"].items():
                lines.append(f"   组 {group}:")
                for elem, data in details.items():
                    status = "✓" if data["pass"] else "✗"
                    lines.append(
                        f"     {elem}: 目标={data['target']:.3f}, "
                        f"实际={data['actual']:.3f} {status}"
                    )
        lines.append(f"   总体: {'✓ 通过' if conc['pass'] else '✗ 未通过'}")
        lines.append("")

        struct = results["structure"]
        lines.append("3. 结构检查:")
        lines.append(
            f"   晶格参数: a={struct['lattice_parameters']['a']:.4f}, "
            f"b={struct['lattice_parameters']['b']:.4f}, "
            f"c={struct['lattice_parameters']['c']:.4f} Å"
        )
        lines.append(f"   晶胞体积: {struct['volume']:.2f} Å³")
        lines.append(f"   最小键长: {struct['min_bond_length']:.4f} Å")
        lines.append(f"   总体: {'✓ 通过' if struct['pass'] else '✗ 未通过'}")
        lines.append("")

        lines.append("=" * 70)
        lines.append(results["overall"]["summary"])
        lines.append("=" * 70)

        with open(output_file, "w") as f:
            f.write("\n".join(lines))

        json_file = self.output_dir / "quality_validation.json"
        with open(json_file, "w") as f:
            json.dump(results, f, indent=2)

        return results


def run():
    """执行质量验证（可导入调用，异常替代 sys.exit）"""
    validator = SQSQualityValidator()
    return validator.generate_report()


def main():
    """CLI 入口（向后兼容）"""
    try:
        results = run()
        sys.exit(0 if results["overall"]["pass"] else 1)
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def _deviation_bar(value: float, width: int = 20) -> str:
    """偏差可视化条"""
    if value < 1e-10:
        return "[" + "=" * width + "] ✓"
    filled = max(0, int(width * (1 - min(value / 0.1, 1))))
    empty = width - filled
    if value < QualityThresholds.EXCELLENT:
        icon = "✅"
    elif value < QualityThresholds.GOOD:
        icon = "✓"
    elif value < QualityThresholds.ACCEPTABLE:
        icon = "⚠"
    else:
        icon = "✗"
    return "[" + "=" * filled + " " * empty + "] " + icon


if __name__ == "__main__":
    main()

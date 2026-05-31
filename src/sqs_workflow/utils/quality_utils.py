#!/usr/bin/env python3
"""
sqs_quality_utils.py
SQS质量评估工具函数（可复用）
"""
from __future__ import annotations

from typing import Optional, Any
import numpy as np
from icet import ClusterSpace
from ase import Atoms

ICET_SQS_VECTOR_AVAILABLE = False
_get_sqs_cluster_vector_fn: Any = None
try:
    from icet.tools.structure_generation import (
        _get_sqs_cluster_vector as _get_sqs_cluster_vector_fn,
    )

    ICET_SQS_VECTOR_AVAILABLE = True
except ImportError:
    pass


def calculate_target_cluster_vector(
    cs: ClusterSpace,
    target_concentrations: Optional[dict[str, dict[str, float]]] = None,
    n_components: Optional[int] = None,
) -> np.ndarray:
    """
    计算目标团簇向量（随机合金的统计期望值）。

    对于随机合金，团簇向量的期望值基于浓度乘积：
    - 空团簇 (order 0): 1.0
    - 单点团簇 (order 1): 各点浓度的平均值
    - 对团簇 (order 2): 两点浓度的乘积
    - 高阶团簇: 多点浓度的乘积
    """
    if target_concentrations and ICET_SQS_VECTOR_AVAILABLE:
        try:
            return _get_sqs_cluster_vector_fn(cs, target_concentrations)
        except Exception as e:
            print(f"  注: icet目标CV计算回退: {e}")

    if n_components is None:
        prim = cs.primitive_structure
        cv_prim = cs.get_cluster_vector(prim)
        n_components = len(cv_prim)

    cv_target = np.zeros(n_components)
    cv_target[0] = 1.0

    if not target_concentrations:
        return cv_target

    all_concs = []
    for site_concs in target_concentrations.values():
        for elem, conc in site_concs.items():
            all_concs.append(conc)

    if len(all_concs) >= 2:
        # 使用 icet 官方方法计算目标团簇向量
        try:
            from icet.tools.structure_generation import _get_sqs_cluster_vector

            return _get_sqs_cluster_vector(cs, target_concentrations)
        except ImportError:
            pass
        except Exception:
            import sys

            print(
                "  警告: icet 目标团簇向量计算失败，回退到近似值",
                file=sys.stderr,
            )

    return cv_target


def calculate_cv_deviation(
    cs: ClusterSpace,
    sqs: Atoms,
    target_concentrations: Optional[dict[str, dict[str, float]]] = None,
    use_icet_comparison: bool = True,
) -> float:
    cv_sqs = cs.get_cluster_vector(sqs)

    cv_target = calculate_target_cluster_vector(
        cs, target_concentrations=target_concentrations, n_components=len(cv_sqs)
    )

    if use_icet_comparison:
        try:
            from icet.tools.structure_generation import compare_cluster_vectors

            deviation = compare_cluster_vectors(
                cv_1=cv_sqs, cv_2=cv_target, as_list=cs.as_list, optimality_weight=1.0
            )
        except ImportError:
            deviation = np.sqrt(np.sum((cv_sqs - cv_target) ** 2))
    else:
        deviation = np.sqrt(np.sum((cv_sqs - cv_target) ** 2))

    return deviation


def evaluate_sqs_quality(
    deviation: float,
    n_atoms: Optional[int] = None,
    n_disordered: Optional[int] = None,
    target_concentrations: Optional[dict[str, dict[str, float]]] = None,
):
    """评估 SQS 质量（使用 QualityThresholds 统一阈���）"""
    from sqs_workflow.constants import QualityThresholds

    deviation = abs(deviation)
    grade, passed, msg = QualityThresholds.evaluate(deviation)
    if n_atoms and n_atoms < 200 and deviation >= QualityThresholds.EXCELLENT:
        msg = f"有限系统限制 (仅{n_atoms}原子)"
    return grade, passed, msg


def get_orbit_order_map(cs: ClusterSpace) -> dict[int, int]:
    """将 CV 索引映射到团簇阶次（0=空团簇, 1=点, 2=对, ...）"""
    cv_order_map: dict[int, int] = {}
    # 空团簇始终在 CV[0]，阶次 0
    cv_order_map[0] = 0
    cv_idx = 1
    for orbit in cs.orbit_list:
        order = orbit.order
        n_components = len(orbit.cluster_vector_elements)
        for i in range(n_components):
            cv_order_map[cv_idx] = order
            cv_idx += 1
    return cv_order_map


def calculate_per_order_deviation(
    cs: ClusterSpace,
    sqs: Atoms,
    target_concentrations: dict[str, dict[str, float]],
) -> dict[int, dict[str, Any]]:
    """按团簇阶次分解偏差"""
    cv_sqs = cs.get_cluster_vector(sqs)
    cv_target = calculate_target_cluster_vector(cs, target_concentrations, len(cv_sqs))
    order_map = get_orbit_order_map(cs)

    by_order: dict[int, dict[str, Any]] = {}
    for idx in range(len(cv_sqs)):
        order = order_map[idx]
        if order not in by_order:
            by_order[order] = {"components": [], "indices": [], "order_name": _order_name(order)}
        diff = abs(cv_sqs[idx] - cv_target[idx])
        by_order[order]["components"].append(diff)
        by_order[order]["indices"].append(idx)

    for order, info in by_order.items():
        comps = info["components"]
        info["max_deviation"] = float(max(comps))
        info["mean_deviation"] = float(sum(comps) / len(comps))
        info["l2_deviation"] = float(np.sqrt(sum(d**2 for d in comps)))
        info["n_components"] = len(comps)

    return by_order


def count_perfect_matches(
    cv_sqs: np.ndarray,
    cv_target: np.ndarray,
    thresholds: Optional[dict[str, float]] = None,
) -> dict[str, dict[str, int]]:
    """统计各阈值下的完美匹配团簇数量（van de Walle 2013 核心思想）"""
    if thresholds is None:
        from sqs_workflow.constants import QualityThresholds

        thresholds = {
            "excellent": QualityThresholds.EXCELLENT,
            "good": QualityThresholds.GOOD,
            "acceptable": QualityThresholds.ACCEPTABLE,
        }

    results: dict[str, dict[str, int]] = {}
    diffs = np.abs(cv_sqs - cv_target)
    n_total = len(diffs)

    for label in ["excellent", "good", "acceptable"]:
        threshold = thresholds[label]
        n_matched = int(np.sum(diffs < threshold))
        results[label] = {
            "matched": n_matched,
            "total": n_total,
            "percent": round(n_matched / n_total * 100, 1) if n_total > 0 else 0.0,
        }

    return results


def _order_name(order: int) -> str:
    names = {0: "空团簇", 1: "点团簇(1体)", 2: "对团簇(2体)", 3: "三体团簇", 4: "四体团簇"}
    return names.get(order, f"{order}体团簇")


def estimate_achievable_deviation(
    n_disordered: int, target_concentrations: Optional[dict[str, dict[str, float]]] = None
) -> dict[str, Any]:
    if not target_concentrations:
        return {"estimated_min_deviation": 0.0, "is_limited": False}

    conc_dict = list(target_concentrations.values())[0]
    concentrations = list(conc_dict.values())

    if len(concentrations) != 2:
        return {"estimated_min_deviation": 0.0, "is_limited": False}

    c_min = min(concentrations)

    n_minority = round(n_disordered * c_min)
    n_majority = n_disordered - n_minority

    actual_c_min = n_minority / n_disordered
    actual_c_max = n_majority / n_disordered

    concentration_error = abs(actual_c_min - c_min)

    estimated_min_deviation = concentration_error

    if c_min < 0.2 or c_min > 0.8:
        asymmetry_factor = 1.5
        estimated_min_deviation *= asymmetry_factor

    is_limited = estimated_min_deviation > 0.001

    if n_disordered < 50:
        size_factor = 1.0 + (50 - n_disordered) / 50.0
        estimated_min_deviation *= size_factor

    return {
        "estimated_min_deviation": estimated_min_deviation,
        "is_limited": is_limited,
        "n_disordered": n_disordered,
        "actual_concentrations": {"minority": actual_c_min, "majority": actual_c_max},
        "discrete_atoms": {"minority": n_minority, "majority": n_majority},
        "concentration_error": concentration_error,
    }


def get_system_size_recommendation(
    n_atoms: int,
    n_disordered: int,
    target_concentrations: Optional[dict[str, dict[str, float]]] = None,
    current_deviation: Optional[float] = None,
):
    recommendations = []

    if target_concentrations:
        estimation = estimate_achievable_deviation(n_disordered, target_concentrations)
        min_dev = estimation["estimated_min_deviation"]

        if estimation["is_limited"]:
            recommendations.append(f"⚠ 系统限制: {n_disordered}个无序位点，估算最小可达到偏差 ~{min_dev:.3f}")

            if current_deviation is not None and current_deviation <= min_dev * 1.2:
                recommendations.append(f"✓ 当前偏差 {current_deviation:.3f} 已接近理论下限 {min_dev:.3f}")
                recommendations.append("  → 这是该系统大小的物理极限，无需进一步优化")

    if n_disordered < 20:
        recommendations.append(f"💡 建议: 无序位点数较少({n_disordered})，建议增大超胞到至少50个无序位点")
    elif n_disordered < 50:
        recommendations.append(f"💡 建议: 中等系统({n_disordered}无序位点)，质量可能受有限尺寸效应影响")
    else:
        recommendations.append(f"✓ 系统尺寸充足({n_disordered}无序位点)，可获得高质量SQS")

    if target_concentrations and current_deviation is not None:
        conc_dict = list(target_concentrations.values())[0]
        concentrations = list(conc_dict.values())

        if len(concentrations) == 2:
            c_min = min(concentrations)
            if c_min < 0.2 or c_min > 0.8:
                recommendations.append(f"⚠ 不对称浓度 ({c_min:.2f}:{1 - c_min:.2f}) 可能限制SQS质量")

    return "\n".join(recommendations) if recommendations else "系统配置良好"


def print_sqs_quality_report(
    deviation: float,
    n_atoms: Optional[int] = None,
    n_disordered: Optional[int] = None,
    target_concentrations: Optional[dict[str, dict[str, float]]] = None,
    detailed: bool = True,
) -> None:
    print("\n" + "=" * 70)
    print("SQS质量评估报告")
    print("=" * 70)

    quality, passed, context = evaluate_sqs_quality(
        deviation, n_atoms, n_disordered, target_concentrations
    )

    print(f"\n团簇向量偏差: {deviation:.6f}")
    print(f"质量评级: {quality}")
    print(f"评估: {context}")
    print(f"通过: {'是' if passed else '否'}")

    if detailed and n_disordered and target_concentrations:
        print("\n" + "-" * 70)
        print("系统大小分析:")
        print("-" * 70)

        _n_atoms = n_atoms if n_atoms is not None else 0
        recommendation = get_system_size_recommendation(
            _n_atoms, n_disordered, target_concentrations, deviation
        )
        print(recommendation)

        estimation = estimate_achievable_deviation(n_disordered, target_concentrations)
        if estimation["is_limited"]:
            print(f"\n理论最小偏差估算: {estimation['estimated_min_deviation']:.6f}")
            print(
                f"离散原子数: 少数元素={estimation['discrete_atoms']['minority']}, "
                f"多数元素={estimation['discrete_atoms']['majority']}"
            )

    print("\n" + "=" * 70)

#!/usr/bin/env python3
"""sqskit — SQS Workflow 命令行工具"""

import sys
import json
from pathlib import Path
from typing import Dict, Optional, Any

from src.core import build_clusterspace as step1
from src.core import generate_sqs_enum as step2a
from src.core import generate_sqs_mc as step2b
from src.core import validate_export as step3
from src.core import validate_quality as step4

try:
    import questionary
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.align import Align
    from rich.live import Live
    from rich.text import Text
    from rich import box
except ImportError:
    print("需要安装: pip install questionary rich")
    sys.exit(1)

console = Console()

DEFAULTS = {
    'cluster_space': {
        'cutoffs': [5.0],
        'symprec': 1e-3,
        'position_tolerance': 0.1,
    },
    'sqs': {
        'max_size': 8,
        'include_smaller_cells': False,
        'supercell_matrix': [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        'pbc': [True, True, True],
        'tolerance': 0.001,
        'random_seed': None,
        'max_iterations': 5,
        'early_stop_no_improve': 3,
        'save_progress': True,
        'T_start': 5.0,
        'T_stop': 0.001,
    },
    'output': {
        'directory': 'output',
        'formats': ['vasp', 'cif'],
        'filename_prefix': 'SQS',
        'save_intermediate': True,
    },
    'validation': {
        'check_correlation': True,
        'tolerance': 0.001,
    },
}

WELCOME = """
  ███████╗ ██████╗ ███████╗    ██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗███████╗██╗      ██████╗ ██╗    ██╗
  ██╔════╝██╔═══██╗██╔════╝    ██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔════╝██║     ██╔═══██╗██║    ██║
  ███████╗██║   ██║███████╗    ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ █████╗  ██║     ██║   ██║██║ █╗ ██║
  ╚════██║██║▄▄ ██║╚════██║    ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══╝  ██║     ██║   ██║██║███╗██║
  ███████║╚██████╔╝███████║    ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██║     ███████╗╚██████╔╝╚███╔███╔╝
  ╚══════╝ ╚══▀▀═╝ ╚══════╝     ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝

                基于 icet 的 Special Quasirandom Structure 生成工具
"""


class ModernSQSInterface:
    """sqskit 交互式界面"""

    def __init__(self):
        self.work_dir = Path.cwd()
        self._check_dop_in()

    def _check_dop_in(self):
        if not (self.work_dir / "dop.in").exists():
            self._first_time_setup()
            sys.exit(0)

    def _first_time_setup(self):
        console.print(Panel.fit(
            "[bold cyan]首次运行 — 需要生成掺杂配置模板[/bold cyan]",
            border_style="cyan"
        ))

        if (self.work_dir / "POSCAR").exists():
            use_current = questionary.confirm("发现 POSCAR，使用此文件?", default=True).ask()
            poscar_file = self.work_dir / "POSCAR" if use_current else self._ask_file_path()
        else:
            poscar_file = self._ask_file_path()

        if poscar_file:
            self._generate_template(poscar_file)

    def _ask_file_path(self) -> Optional[Path]:
        poscar_file = questionary.path("请输入结构文件路径:", validate=lambda x: Path(x).exists()).ask()
        return Path(poscar_file) if poscar_file else None

    def _generate_template(self, poscar_file: Path):
        from src.utils.template_generator import UniversalTemplateGenerator
        with console.status("[cyan]生成模板...[/cyan]"):
            try:
                generator = UniversalTemplateGenerator(poscar_file)
                generator.output_dir = self.work_dir
                if generator.load_structure():
                    generator.generate_labeled_poscar()
                    generator.generate_index_guide()
                    console.print("\n[green]✓ 模板生成成功[/green]")
                    console.print(f"  [cyan]dop.in[/cyan]   — 编辑此文件设置掺杂浓度")
                    console.print(f"  [bold]sqskit[/bold] — 完成后重新运行")
            except Exception as e:
                console.print(f"\n[red]✗ 生成失败: {e}[/red]")

    def run(self):
        console.print(Align.center(Text(WELCOME, style="bold cyan"), vertical="middle"))
        console.print()

        method = self._choose_method()
        if method == "quit":
            console.print("\n[dim]再见！[/dim]")
            return

        config = self._configure_all(method)
        if self._confirm_and_run(config):
            pass
    
    def _choose_method(self) -> str:
        """选择生成方法"""
        return questionary.select(
            "选择SQS生成方法:",
            choices=[
                questionary.Choice(
                    title="[1] 枚举法 (Enumeration) - 推荐",
                    value="enumeration",
                    description="全局最优解，结果尺寸灵活，适合中小体系"
                ),
                questionary.Choice(
                    title="[2] MC方法 (Monte Carlo)",
                    value="montecarlo",
                    description="迭代优化，结果尺寸固定，适合精确控制结构大小"
                ),
                questionary.Choice(
                    title="[q] 退出",
                    value="quit",
                    description="退出程序"
                )
            ]
        ).ask()
    
    def _configure_all(self, method: str) -> Dict:
        """配置所有参数"""
        config = {
            'method': method,
            'cluster_space': dict(DEFAULTS['cluster_space']),
            'sqs': dict(DEFAULTS['sqs']),
            'output': dict(DEFAULTS['output']),
            'validation': dict(DEFAULTS['validation']),
        }
        
        level = questionary.select(
            "配置级别:",
            choices=[
                questionary.Choice(title="快速模式 - 仅基本参数", value="quick"),
                questionary.Choice(title="标准模式 - 常用参数", value="standard"),
                questionary.Choice(title="专家模式 - 全部参数", value="expert"),
            ]
        ).ask()
        
        if level == "quick":
            config = self._configure_quick(config)
        elif level == "standard":
            config = self._configure_standard(config)
        else:
            config = self._configure_expert(config)
        
        return config
    
    def _configure_quick(self, config: Dict) -> Dict:
        """快速模式 - 仅基本参数"""
        console.print("\n[bold cyan]快速配置[/bold cyan]")
        
        config['cluster_space']['cutoffs'][0] = float(questionary.text(
            "团簇截断半径 (A):",
            default=str(config['cluster_space']['cutoffs'][0]),
            validate=lambda x: self._validate_float(x, 3.0, 15.0)
        ).ask())
        
        if config['method'] == 'enumeration':
            config['sqs']['max_size'] = int(questionary.text(
                "最大原胞倍数:",
                default=str(config['sqs']['max_size']),
                validate=lambda x: x.isdigit() and 1 <= int(x) <= 200
            ).ask())
        else:
            matrix_str = questionary.text(
                "超胞矩阵 (空格分隔3个数字):",
                default="2 2 2",
                validate=lambda x: len(x.split()) == 3 and all(self._validate_int(n, 1, 10) for n in x.split())
            ).ask()
            m = [int(x) for x in matrix_str.split()]
            config['sqs']['supercell_matrix'] = [[m[0], 0, 0], [0, m[1], 0], [0, 0, m[2]]]
        
        return config
    
    def _configure_standard(self, config: Dict) -> Dict:
        """标准模式 - 常用参数"""
        config = self._configure_quick(config)
        
        console.print("\n[bold yellow]SQS质量参数[/bold yellow]")
        config['sqs']['tolerance'] = float(questionary.text(
            "目标偏差 (tolerance):",
            default=str(config['sqs']['tolerance']),
            validate=lambda x: self._validate_float(x, 0.0001, 1.0)
        ).ask())
        
        if config['method'] == 'montecarlo':
            console.print("\n[bold yellow]MC优化参数[/bold yellow]")
            config['sqs']['max_iterations'] = int(questionary.text(
                "最大迭代次数:",
                default=str(config['sqs']['max_iterations']),
                validate=lambda x: x.isdigit() and 1 <= int(x) <= 100
            ).ask())
            
            config['sqs']['early_stop_no_improve'] = int(questionary.text(
                "无改进停止次数:",
                default=str(config['sqs']['early_stop_no_improve']),
                validate=lambda x: x.isdigit() and 1 <= int(x) <= 20
            ).ask())
            
            config['sqs']['T_start'] = float(questionary.text(
                "MC初始温度 (T_start):",
                default=str(config['sqs']['T_start']),
                validate=lambda x: self._validate_float(x, 0.01, 100.0)
            ).ask())
            
            config['sqs']['T_stop'] = float(questionary.text(
                "MC终止温度 (T_stop):",
                default=str(config['sqs']['T_stop']),
                validate=lambda x: self._validate_float(x, 0.0001, 10.0)
            ).ask())
        else:
            console.print("\n[bold yellow]枚举法参数[/bold yellow]")
            config['sqs']['include_smaller_cells'] = questionary.confirm(
                "允许返回更小的优化结构?",
                default=config['sqs']['include_smaller_cells']
            ).ask()
        
        return config
    
    def _configure_expert(self, config: Dict) -> Dict:
        """专家模式 - 全部参数"""
        config = self._configure_standard(config)
        
        if questionary.confirm("\n配置ClusterSpace高级参数?", default=False).ask():
            config = self._configure_clusterspace_expert(config)
        
        if questionary.confirm("\n配置SQS高级参数?", default=False).ask():
            if config['method'] == 'enumeration':
                config = self._configure_enum_expert(config)
            else:
                config = self._configure_mc_expert(config)
        
        if questionary.confirm("\n配置输出高级参数?", default=False).ask():
            config = self._configure_output_expert(config)
        
        if questionary.confirm("\n配置验证参数?", default=False).ask():
            config = self._configure_validation_expert(config)
        
        return config
    
    def _configure_clusterspace_expert(self, config: Dict) -> Dict:
        """ClusterSpace专家参数"""
        console.print("\n[bold yellow]ClusterSpace高级参数[/bold yellow]")
        
        cutoffs_str = questionary.text(
            "截断半径列表 (逗号分隔，可多个):",
            default=','.join(str(c) for c in config['cluster_space']['cutoffs']),
            validate=lambda x: all(self._validate_float(v.strip(), 1.0, 20.0) for v in x.split(',') if v.strip())
        ).ask()
        config['cluster_space']['cutoffs'] = [float(v.strip()) for v in cutoffs_str.split(',') if v.strip()]
        
        config['cluster_space']['symprec'] = float(questionary.text(
            "对称性容差 (symprec):",
            default=str(config['cluster_space']['symprec']),
            validate=lambda x: self._validate_float(x, 1e-6, 1.0)
        ).ask())
        
        config['cluster_space']['position_tolerance'] = float(questionary.text(
            "位置容差 (position_tolerance):",
            default=str(config['cluster_space']['position_tolerance']),
            validate=lambda x: self._validate_float(x, 0.01, 1.0)
        ).ask())
        
        return config
    
    def _configure_enum_expert(self, config: Dict) -> Dict:
        """枚举法专家参数"""
        console.print("\n[bold yellow]枚举法高级参数[/bold yellow]")
        
        config['sqs']['include_smaller_cells'] = questionary.confirm(
            "允许返回更小的优化结构?",
            default=config['sqs']['include_smaller_cells']
        ).ask()
        
        config['sqs']['random_seed'] = questionary.text(
            "随机种子 (留空为None):",
            default=str(config['sqs']['random_seed']) if config['sqs']['random_seed'] else ""
        ).ask()
        config['sqs']['random_seed'] = int(config['sqs']['random_seed']) if config['sqs']['random_seed'] else None
        
        pbc_str = questionary.text(
            "周期边界条件 (3个True/False，空格分隔):",
            default="True True True"
        ).ask()
        config['sqs']['pbc'] = [x.strip().lower() == 'true' for x in pbc_str.split()]
        
        return config
    
    def _configure_mc_expert(self, config: Dict) -> Dict:
        """MC方法专家参数"""
        console.print("\n[bold yellow]MC方法高级参数[/bold yellow]")
        
        config['sqs']['early_stop_no_improve'] = int(questionary.text(
            "连续无改进停止阈值:",
            default=str(config['sqs']['early_stop_no_improve']),
            validate=lambda x: x.isdigit() and 1 <= int(x) <= 20
        ).ask())
        
        config['sqs']['save_progress'] = questionary.confirm(
            "保存优化进度?",
            default=config['sqs']['save_progress']
        ).ask()
        
        config['sqs']['T_start'] = float(questionary.text(
            "MC初始温度 (T_start):",
            default=str(config['sqs']['T_start']),
            validate=lambda x: self._validate_float(x, 0.01, 100.0)
        ).ask())
        
        config['sqs']['T_stop'] = float(questionary.text(
            "MC终止温度 (T_stop):",
            default=str(config['sqs']['T_stop']),
            validate=lambda x: self._validate_float(x, 0.0001, 10.0)
        ).ask())
        
        config['sqs']['random_seed'] = questionary.text(
            "随机种子 (留空为None):",
            default=str(config['sqs']['random_seed']) if config['sqs']['random_seed'] else ""
        ).ask()
        config['sqs']['random_seed'] = int(config['sqs']['random_seed']) if config['sqs']['random_seed'] else None
        
        return config
    
    def _configure_output_expert(self, config: Dict) -> Dict:
        """输出专家参数"""
        console.print("\n[bold yellow]输出高级参数[/bold yellow]")
        
        config['output']['directory'] = questionary.text(
            "输出目录:",
            default=config['output']['directory']
        ).ask()
        
        config['output']['filename_prefix'] = questionary.text(
            "文件名前缀:",
            default=config['output']['filename_prefix']
        ).ask()
        
        config['output']['save_intermediate'] = questionary.confirm(
            "保存中间文件?",
            default=config['output']['save_intermediate']
        ).ask()
        
        return config
    
    def _configure_validation_expert(self, config: Dict) -> Dict:
        """验证专家参数"""
        console.print("\n[bold yellow]验证参数[/bold yellow]")
        
        config['validation']['check_correlation'] = questionary.confirm(
            "检查团簇向量相关性?",
            default=config['validation']['check_correlation']
        ).ask()
        
        config['validation']['tolerance'] = float(questionary.text(
            "验证容差:",
            default=str(config['validation']['tolerance']),
            validate=lambda x: self._validate_float(x, 0.0001, 1.0)
        ).ask())
        
        return config
    
    def _confirm_and_run(self, config: Dict) -> bool:
        table = Table(title="配置确认", box=box.ROUNDED, title_style="bold cyan")
        table.add_column("类别", style="dim cyan", width=14)
        table.add_column("参数", style="yellow")
        table.add_column("值", style="bright_white")

        method_name = "枚举法" if config['method'] == 'enumeration' else "MC 方法"
        table.add_row("方法", "生成方法", method_name)
        table.add_row("ClusterSpace", "cutoffs", str(config['cluster_space']['cutoffs']))

        if config['method'] == 'enumeration':
            table.add_row("SQS", "max_size", str(config['sqs']['max_size']))
        else:
            m = config['sqs']['supercell_matrix']
            table.add_row("SQS", "超胞", f"{m[0][0]}×{m[1][1]}×{m[2][2]}")
            table.add_row("SQS", "迭代次数", str(config['sqs']['max_iterations']))

        table.add_row("SQS", "tolerance", str(config['sqs']['tolerance']))
        table.add_row("输出", "格式", str(config['output']['formats']))

        console.print()
        console.print(table)

        if not questionary.confirm("\n开始生成?", default=True).ask():
            console.print("[dim]已取消[/dim]")
            return False

        self._run_workflow(config)
        return True

    def _run_workflow(self, config: Dict):
        with open(self.work_dir / 'config.json', 'w') as f:
            json.dump({
                'cluster_space': config['cluster_space'],
                'sqs': config['sqs'],
                'output': config['output'],
                'validation': config['validation'],
            }, f, indent=2)

        stages = [
            ("构建 ClusterSpace", lambda: step1.run()),
            ("生成 SQS", lambda: step2a.run() if config['method'] == 'enumeration' else step2b.run()),
            ("导出结果", lambda: step3.run()),
            ("质量验证", lambda: step4.run()),
        ]

        console.print()
        for i, (name, fn) in enumerate(stages, 1):
            with console.status(f"[bold cyan]{i}/4 {name}...[/bold cyan]"):
                try:
                    result = fn()
                    if isinstance(result, int) and result != 0:
                        console.print(f"[red]✗ {name} 失败[/red]")
                        return
                except RuntimeError as e:
                    console.print(f"[red]✗ {name}: {e}[/red]")
                    return
                except Exception as e:
                    console.print(f"[red]✗ {name}: {e}[/red]")
                    return

        self._print_summary()

    def _print_summary(self):
        console.print()
        table = Table(box=box.ROUNDED, title="[bold green]✓ 生成完成[/bold green]", title_style="bold green")
        table.add_column("输出文件", style="cyan", width=36)
        table.add_column("说明", style="dim white")

        table.add_row("SQS_FINAL.vasp", "[green]最终结构 (VASP POSCAR 格式)[/green]")
        table.add_row("output/QUALITY_REPORT.txt", "详细质量报告")
        table.add_row("output/SQS_*x.vasp / .cif", "SQS 多格式输出")
        table.add_row("output/quality_validation.json", "质量数据 (JSON)")

        console.print(table)
        console.print()
    
    @staticmethod
    def _validate_float(value: str, min_val: float, max_val: float) -> bool:
        try:
            v = float(value)
            return min_val <= v <= max_val
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _validate_int(value: str, min_val: int, max_val: int) -> bool:
        try:
            v = int(value)
            return min_val <= v <= max_val
        except (ValueError, TypeError):
            return False


def main():
    """主函数"""
    try:
        interface = ModernSQSInterface()
        interface.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]操作已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

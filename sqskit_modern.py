#!/usr/bin/env python3
"""SQS Workflow — 命令行入口"""

import sys

from src.cli.modern_interactive import ModernSQSInterface

def main():
    """主函数"""
    try:
        interface = ModernSQSInterface()
        interface.run()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

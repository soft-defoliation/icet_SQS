.PHONY: help install dev lint test format check release push clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## 安装项目
	pip install -e .

dev: ## 安装开发依赖
	pip install -e ".[dev]"

lint: ## flake8 检查
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

test: ## 运行测试
	pytest tests/ -v --tb=short

format: ## black 格式化
	black src/ tests/

check: ## 完整质量检查 (CI 流程)
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	pytest tests/ -v --tb=short
	black --check --diff src/ tests/

release: check ## 发布新版本 (用法: make release VER=0.3.0 MSG="release notes")
	@if [ -z "$(VER)" ]; then echo "错误: 需要指定版本号, 例如 make release VER=0.3.0"; exit 1; fi
	@sed -i 's/version = ".*"/version = "$(VER)"/' pyproject.toml
	@sed -i 's/__version__ = ".*"/__version__ = "$(VER)"/' src/sqs_workflow/__init__.py
	git add -A
	git commit -m "release: v$(VER)$(if $(MSG), - $(MSG))" || true
	git tag -a "v$(VER)" -m "v$(VER)$(if $(MSG), - $(MSG))"
	@echo "✓ 已打标签 v$(VER). 运行 'make push' 推送."

push: ## 推送代码和标签到远程
	git push origin main
	git push origin --tags

clean: ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf *.egg-info build/ dist/ output/

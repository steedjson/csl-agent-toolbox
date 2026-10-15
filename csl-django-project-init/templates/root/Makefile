IMG_NS?=MUST_SPECIFIED

IMG_TAG?=latest

SERVICE=__PROJECT_NAME__
image="docker.sugonup.com/$(IMG_NS)/$(SERVICE)_backend:$(IMG_TAG)"

# ============================================
# 开发任务
# ============================================

.PHONY: install install-dev install-hooks format lint test check verify verify-full migrate dev worker clean help

# 安装依赖
install:
	.venv/bin/python -m pip install -r requirements.txt

# 安装本地开发工具
install-dev: install
	.venv/bin/python -m pip install -r requirements-dev.txt

# 安装或刷新本地 Git hooks
install-hooks:
	.venv/bin/pre-commit install --overwrite --hook-type pre-commit
	install -m 0755 scripts/git-hooks/pre-push .git/hooks/pre-push

# 代码格式化
format:
	./scripts/local_quality_gate.sh format

# 语法检查
lint:
	./scripts/local_quality_gate.sh lint

# 运行测试
test:
	.venv/bin/pytest -q $(TEST)

# 快速只读检查（变更文件格式 + Pylint + Git diff）
check:
	./scripts/local_quality_gate.sh check

# 功能验证（格式化 + Pylint + 目标测试 + Git diff）
verify:
	./scripts/local_quality_gate.sh verify $(TEST)

# 高风险完整验证
verify-full:
	./scripts/local_quality_gate.sh full

# 数据库迁移
migrate:
	.venv/bin/python manage.py makemigrations
	.venv/bin/python manage.py migrate

# 启动开发服务器
dev:
	.venv/bin/python manage.py runserver

# 启动异步任务 worker
worker:
	.venv/bin/python manage.py qcluster

# 清理缓存和临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete

# 依赖安全扫描
security-scan:
	.venv/bin/python -m pip_audit
	.venv/bin/python -m safety scan

# 显示帮助
help:
	@echo "可用的开发命令："
	@echo "  make install       - 安装运行时依赖"
	@echo "  make install-dev   - 安装运行时依赖和本地开发工具"
	@echo "  make install-hooks - 安装或刷新 pre-commit 和 pre-push"
	@echo "  make format        - 格式化变更的 Python 文件"
	@echo "  make lint          - 检查变更的 Python 文件"
	@echo "  make test TEST=... - 运行指定测试；省略 TEST 时运行完整测试"
	@echo "  make check         - 只读检查变更文件，不运行测试"
	@echo "  make verify TEST=... - 格式化、检查并运行目标测试"
	@echo "  make verify-full   - 高风险变更的完整验证"
	@echo "  make migrate       - 数据库迁移"
	@echo "  make dev           - 启动开发服务器"
	@echo "  make worker        - 启动异步任务 worker"
	@echo "  make clean         - 清理缓存和临时文件"
	@echo "  make security-scan - 依赖安全扫描"
	@echo ""
	@echo "Docker 构建命令："
	@echo "  make compile       - 生产构建（Cython 编译）"
	@echo "  make image         - 标准构建"
	@echo "  make push          - 推送镜像"
	@echo "  make release       - compile + push"

# ============================================
# Docker 构建任务
# ============================================

all: image push
release: compile push

compile:
	@echo building $(image) with compiler...
	@docker build \
-f release.Dockerfile \
-t $(image) \
--build-arg SERVICE=$(SERVICE) .

image:
	@echo building $(image) ...
	@docker build \
-t $(image) \
--build-arg SERVICE=$(SERVICE) .

push:
	@echo pushing $(image) ...
	@docker push $(image)

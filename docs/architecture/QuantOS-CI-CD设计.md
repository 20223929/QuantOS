# QuantOS Next CI/CD设计

## 1. 目标

保证每次提交自动完成：

- 代码检查
- 单元测试
- 构建验证
- 发布检查

---

# 2. GitHub Actions

目录：

```
.github/workflows

backend-test.yml
frontend-test.yml
docker-build.yml
release.yml
```

---

# 3. Backend CI

执行：

```
pytest
ruff
mypy
```

---

# 4. Frontend CI

执行：

```
npm install
npm test
npm run build
```

---

# 5. 发布流程

```
commit
 |
CI
 |
Build
 |
Docker Image
 |
Release
```

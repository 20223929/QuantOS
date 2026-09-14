# QuantOS 发布流程

## 1. 发布版本规则

QuantOS 使用 SemVer 版本号。

- 正式版本：`vMAJOR.MINOR.PATCH`
- 预发布版本：`vMAJOR.MINOR.PATCH-IDENTIFIER`
- Tag 必须与 `frontend/package.json` 的 `version` 完全一致。

当前 MVP 验证版本：`v0.1.0-alpha`。

## 2. 发布前检查

发布 Tag 前必须确保 `develop` 已通过：

1. Backend Test
2. Frontend Test
3. QuantOS Regression
4. Docker Build

Regression 必须覆盖 Python 3.12、Python 3.13、Node 22、Alembic migration 和 Release Quality Gate。

## 3. Tag 发布链路

创建并推送发布 Tag 后，以下两个工作流必须自动执行：

- `QuantOS Release`
- `Docker Build`

Release workflow 必须校验：

- Tag 格式符合 SemVer
- GitHub Tag 与前端版本一致
- Alembic 配置存在且 `script_location` 正确
- migration versions 目录存在
- release manifest 可以生成

Docker workflow 必须校验：

- Tag 格式符合 SemVer
- GitHub Tag 与前端版本一致
- Docker image 可以成功构建
- 镜像 SHA 标识可以生成
- 发布 Tag 镜像标签可以生成

## 4. 发布产物追溯

Release manifest 至少记录：

- version
- tag
- commit
- workflow
- run_id

Release manifest 应与 GitHub Release 和 Actions artifact 关联，用于后续问题定位和审计。

## 5. 预发布版本

包含 `-` 的版本属于预发布版本，例如：

```text
v0.1.0-alpha
v0.1.0-beta
v0.1.0-rc.1
```

正式版本不包含预发布后缀，例如：

```text
v0.1.0
v1.0.0
```

Release automation 应根据版本后缀自动设置 GitHub Release 的 prerelease 属性。

## 6. 22-15 验证结果

`v0.1.0-alpha` 已完成实际 Tag 演练。

验证结果：

- Release Validation：通过
- Release Gate：通过
- Docker Build：通过
- Docker release image tag：通过

## 7. 发布失败处理

发现 Release 或 Docker 任一环节失败时，不得将失败状态标记为发布成功。应保留失败 Run、commit SHA 和 Tag 信息，修复后重新执行对应验证链路。

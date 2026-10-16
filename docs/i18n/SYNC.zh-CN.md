# 同步上游 + 维护汉化：操作手册

本 fork（`ch3n4y/wifit3`）是 [`derv82/wifit3`](https://github.com/derv82/wifit3) 的 fork。
这份手册说明：**怎么同步上游更新，同时保住汉化**。

配套文档：[`GLOSSARY.zh-CN.md`](GLOSSARY.zh-CN.md)（术语表与译/不译规则）。

---

## 1. 模型：master 是镜像，zh-cn 是汉化分支

| 分支 | 内容 | 规则 |
|---|---|---|
| `master` | 与上游 `derv82/wifit3` **完全一致**的纯镜像 | 只做快进（`--ff-only`），永不提交自己的东西 |
| `zh-cn` | 汉化（唯一的自有改动） | 长期存在；上游更新用 merge 合进来 |

**不要把汉化合进 `master`**。一旦合了，`master` 不再是镜像，GitHub 的 Sync fork 与
`git merge --ff-only upstream/master` 都会失效，之后每次上游更新都要在带 1000+ 行中文改动的树上解冲突。

汉化版二进制从 `zh-cn` 打 tag 发布（见 §5）。

## 2. 一次性设置

```powershell
cd <你的仓库路径>

# 上游远端（本机未配置 SSH，用 HTTPS + gh 凭据）
git remote add upstream https://github.com/derv82/wifit3.git
gh auth setup-git                      # 让 git 复用 gh 的 token（推送时才需要）

# 让 git 记住冲突解法，下次同类冲突自动处理
git config rerere.enabled true

# 让 gh 默认操作你自己的 fork，避免误操作上游
gh repo set-default ch3n4y/wifit3
```

拉一次上游，确认通路：

```powershell
git fetch upstream
git rev-parse upstream/master master   # 两行 sha 应相同 = 镜像状态
```

## 3. 同步上游（每次上游更新后）

```powershell
# 1) master 快进到上游
git fetch upstream
git checkout master
git merge --ff-only upstream/master
git push origin master

# 2) 把上游更新合进汉化分支
git checkout zh-cn
git merge master
```

有冲突时（只会出现在**上游也改了同一行文案**的地方）：

```powershell
git status                     # 看冲突文件
# 逐个文件处理：保留上游的新代码/新英文文案，然后按 GLOSSARY 重新翻译那几行
git add <file>
git commit                     # 完成 merge
```

原则：**永远不要**用「整文件取一边」来解冲突（`git checkout --ours/--theirs` 会一次丢掉大段汉化或上游改动）。
冲突通常只有几行，按术语表重译即可。

## 4. 翻译增量（真正的日常）

同步后，上游新增的英文文案会以英文出现。用巡检脚本找出**只有新增**的那些：

```powershell
.\.venv\Scripts\python.exe tools\i18n_audit.py
```

输出含义：

- **NEW**：代码里有、基线里没有的英文字面量，是上游新加的文案。
  逐条判断：**是用户可见文案就翻译**（按 `GLOSSARY.zh-CN.md` 的术语与规则）；
  确认不是文案（新增的 logger 行、协议名、命令行…）就收进基线：
  ```powershell
  .\.venv\Scripts\python.exe tools\i18n_audit.py --init
  ```
- **STALE**：基线里有、代码里已不存在的条目（上游删掉或改写了那行）。
  `--init` 会顺便清掉它们。

想把「忘了翻译」变成硬性失败，用 `--strict`（有 NEW 时退出码 1），可以放进自己的检查脚本里。

改完文案后照例验证，然后提交：

```powershell
.\.venv\Scripts\python.exe tools\i18n_audit.py     # NEW/STALE 应为 0
.\.venv\Scripts\python.exe -m ruff check src/ tests/
.\.venv\Scripts\python.exe -m pytest
git add -A
git commit -m "chore(i18n): 同步上游并翻译新增文案"
git push origin zh-cn
```

> 注意：仓库禁止在 `src/wifit3` 里出现 em-dash（`—`，U+2014），`tests/test_style.py` 会拦。
> 也**绝不要**运行 `ruff format`：这个仓库是手工排版的，formatter 被刻意全局禁用。

## 5. 发布汉化版二进制

复用上游的 `.github/workflows/release.yml`（按 tag 触发，构建 Windows/Linux/macOS 产物）：

```powershell
git checkout zh-cn
git tag v0.4.5           # 去掉 v 之后必须等于 src/wifit3/__init__.py 的 __version__
git push origin v0.4.5
```

工作流里有**版本一致性硬门槛**（tag 与 `__version__` 必须相同）才会发布 Release。因此：

- 若不想改 `__version__`（那行每次上游发版都会冲突），就直接用上游的版本号打 tag（如 `v0.4.5`）；
- 若想要自己的版本号（如 `v0.4.5-zh.1`），需要同步改 `src/wifit3/__init__.py` 的 `__version__`，
  并接受每次上游发版时在该行解一次冲突；
- 或者用 GitHub → Actions → **Release → Run workflow**（`workflow_dispatch`）：只产出可下载的构建产物，
  不自动发布 Release，由你手动发布。

## 6. 常见问题

**Q：为什么不走 PR、直接推 `zh-cn`？**
汉化是这条长期分支的**唯一**内容，每次同步都是增量提交；PR 在自己仓库里只是多一层流程。
如果哪天想给上游贡献非汉化的修复，再从 `master` 切一条独立分支开 PR。

**Q：上游改了同一行文案，冲突怎么解最快？**
`git config rerere.enabled true` 之后，同类冲突 Git 会记住解法并在下次自动应用。
第一次遇到时，取**上游的新英文**再按术语表重译，比尝试保留旧中文更稳。

**Q：CI 为什么没跑？**
本仓库的 `.github/workflows/*` 虽然已提交，但 Actions 从未产生过运行记录
（`repos/ch3n4y/wifit3/actions/workflows` 返回 0 个）。所以本地必须跑齐 CI 的三步：
`ruff check src/ tests/`、`pytest`、以及 `ci.yml` 里的导入冒烟（导入 UI + 全部 `import_driver()`）。

**Q：我想让界面显示英文怎么办？**
`git checkout master` 构建即可；`zh-cn` 只影响 `ui/`、`campaigns/`、`setup/` 的展示文本。

**Q：以后想把汉化改成数据驱动（零冲突）？**
把所有译法抽成 `English → 中文` 的数据表 + 生成脚本，同步时 `reset --hard upstream/master` 再重新生成。
代价是中文不能直接在代码里手改。现阶段不必做，等冲突真的变多再说。

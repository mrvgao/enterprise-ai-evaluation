# Enterprise AI evaluation connector

This is the public, centrally maintained GitHub Actions connector for Agentist
Enterprise AI Environment. It contains no platform credentials, student code,
hidden tasks or grading implementation.

## Student setup / 学生接入

1. Sign in to Agentist and bind your repository and branch.
2. Download the repository setup package. Install **only**
   `.github/workflows/hyper-lab.yml`; keep your own `agent/` directory.
3. Commit and push. The entry calls this repository's reusable workflow at `v1`.
   GitHub Actions must be enabled and permit this public reusable workflow.

学生只需安装一次平台生成的入口工作流，之后继续在本地编写并 push Agent。
评测任务、场景、语言和案例范围从平台绑定读取；更换分支后请重新下载入口。
不要复制其他同学的绑定 ID。无需填写 GitHub PAT、Daytona 或模型密钥。

The managed workflow does **not** run `scripts/lab_eval.py` from the student's
repository. That file can be retained for the existing local CLI, but must be
updated separately if used locally. Old installed workflows remain supported
during migration. Replace their entry once and disable duplicate evaluation jobs.

## Updates and reproducibility

- `v1` is a maintainer-controlled moving release tag. Compatible, tested updates
  apply to **future runs**, without editing every student repository.
- Each release also has an immutable version tag, initially `v1.0.0`. A student
  may pin that tag instead of `v1`; pinned installations do not auto-update.
- Breaking interface changes require a new major version and a migration.
- The trusted client is checked out at the **same immutable SHA** as the called
  workflow, resolved via GitHub OIDC. Updating `v1` mid-run cannot mix versions.
- Receipts include the signed workflow ref and SHA (also the client revision).
  Saved results are not rewritten. Grader, model and environment versions are
  independent of connector releases; a connector release must not change scores.
- GitHub may reuse the original workflow SHA when rerunning an individual job.
  Use a new push or new dispatch to adopt a new release.

## Security boundary

Only `contents: read` and `id-token: write` are required. Do not inherit secrets.
Student source is checked out separately and read as files, never imported or
executed on the GitHub runner. Python runs with `-I`. Symlinks and credential-like
filenames are rejected. Platform authorization still verifies the paid account,
binding, caller repository/branch/workflow, signed GitHub identity and the trusted
reusable workflow. OIDC tokens are short-lived and never printed or persisted.

## Release procedure / 发布流程

Run `python3 -I -m unittest discover -s tests`, validate the workflow, then test a
bounded student submission. Review the exact public file list before publishing.
Create an immutable patch-version tag and move `v1` only after validation. Never
move an immutable version tag. Record old/new SHAs; rollback moves `v1` back to
the last known-good SHA. Existing jobs and reports retain their recorded SHA.

Platform code must support the new CI protocol before migrating students. Keep
the previous protocol available during the announced compatibility window. A
new release that needs a new API must retain compatibility with installed entry
URLs or explicitly migrate them; Preview URLs are not permanent production APIs.

Only the workflow, client, client tests, README and license belong in this public
repository. No changes to students' repositories are made by this connector.

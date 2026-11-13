# Hengshu Credit 组织主页

本仓库维护[衡枢真信 GitHub 组织主页](https://github.com/hengshu-credit)。GitHub 在组织的 Overview 页展示 `profile/README.md`。

## 主页横幅

`profile/assets/banner.svg` 是横幅源文件，画布为 1600 × 520。配色、渐变字标和项目卡片参考 [hscredit 品牌色卡](https://github.com/hengshu-credit/hscredit/blob/main/docs/assets/brand/hscredit-color-card.png)。右侧内嵌 [hscredit loading SVG](https://github.com/hengshu-credit/hscredit/blob/8876a5c7b517bda9bc98026c84153754fa95a0ad/docs/assets/brand/hscredit-loading.svg)，保留原图的 9.2 秒循环动画。

横幅沿用官网的[业务定位](https://hengshucredit.com/)与[服务介绍](https://hengshucredit.com/solutions/)。四张项目卡片与主页中的项目顺序一致，分别展示 hscredit、天枢决策引擎、瑶光营销系统和观星监控平台。

编辑 SVG 后，生成用于减少动态效果的静态 PNG，以及 WebP 和 GIF 动画备用图。在装有微软雅黑或思源黑体的环境中运行：

```powershell
python -m pip install -r tools/requirements-banner.txt
python -m playwright install chromium
python tools/render_banner.py
```

`--preview` 只生成静态 PNG。`--output-dir` 可指定预览目录，`--browser` 可指定已安装的 Chrome 或 Chromium 可执行文件。

## 联系方式

- `profile/assets/wechat.svg` 是个人微信 itlubber 的二维码，取自[官网联系页](https://hengshucredit.com/contact/)。
- `profile/assets/wechat-official-account.svg` 是「衡枢风控实验室」（`hscreditlab`）的二维码，与 [hscredit 公开 README 使用的资源](https://github.com/hengshu-credit/hscredit/blob/main/docs/assets/readme/wechat-official-account.svg)一致。更新时应保留四周留白，并核对解码结果。

## 发布

更新 `profile/README.md` 或图片后，提交并推送到 `main` 分支。变更原路径下的图片时，同步更新主页图片 URL 的版本参数。

本地目录 `hengshu-credit` 对应远程仓库 `hengshu-credit/.github`。精选仓库由组织 Owner 在主页的 **Customize pins** 中设置。

# Hengshu Credit 组织主页

本仓库用于维护 [衡枢真信 GitHub 组织主页](https://github.com/hengshu-credit)。

## 文件说明

- `profile/README.md`：展示在组织 Overview 页面的公开介绍。
- `profile/assets/banner.gif`：基于 HSCredit 原始 Logo 的 3D 动态横幅，96 帧、6 秒循环。
- `profile/assets/banner-static.png`：静态横幅，供启用减少动态效果的访客使用。
- `profile/assets/hscredit-logo.svg`：官网原始矢量 Logo，作为立体几何和配色的来源。
- `profile/assets/wechat.svg`：微信二维码。
- `profile/assets/wechat-official-account.svg`：微信公众号二维码。

联系方式与 HSCredit 公开 README 保持一致。二维码取自官网联系页使用的
`https://hengshucredit.com/images/itlubber.svg` 和
`https://hengshucredit.com/images/itlubber_art.svg`，保存在本仓库中，并添加白色背景以适配 GitHub 深色主题。
更新二维码时应保留完整码点与周围留白，并核对扫描结果。

## 更新方式

编辑 `profile/README.md` 或横幅后，提交并推送到 `main` 分支。
GitHub 会从组织的公开 `.github` 仓库读取 `profile/README.md`。

本地目录名为 `hengshu-credit`，对应远程仓库 `hengshu-credit/.github`。

精选仓库需由组织 Owner 在主页的 **Customize pins** 中设置。
建议优先展示 HSCredit、天枢决策引擎、瑶光营销平台和衡枢电商平台。

## 重新生成动态横幅

原始 Logo 来源：`https://hengshucredit.com/images/hengshucredit_animated.svg`。
渲染器沿用原始矢量路径和渐变，通过轮廓挤出、边缘高光与轻微摆动呈现立体效果。
生成文件为 GIF，GitHub 无需执行脚本即可展示动画；README 同时提供减少动态效果的静态版本。

在具备 OpenGL 3.3 驱动、Cairo 运行库和 Windows Segoe UI / 微软雅黑字体的环境中运行：

```powershell
python -m pip install -r tools/requirements-banner.txt
python tools/render_banner.py --preview
python tools/render_banner.py
```

`--preview` 仅更新静态预览；正式生成会同时更新 GIF 和静态横幅。

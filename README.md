# Hengshu Credit 组织主页

本仓库用于维护 [衡枢真信 GitHub 组织主页](https://github.com/hengshu-credit)。

## 文件说明

- `profile/README.md`：展示在组织 Overview 页面的公开介绍。
- `profile/assets/banner.webp`：无损全彩 3D 动态横幅，9.2 秒循环；按 25 帧/秒渲染，编码时合并相同的停留帧。
- `profile/assets/banner.gif`：兼容不支持 WebP 的浏览器的动画版本。
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
渲染器沿用原始矢量路径和渐变，按 **S 与 H 的字母结构**制作组合动画：先绘制完整 S，再构建 H 的两条斜竖笔画，最后由 CREDIT 字母组成完整 Logo。S 的中段作为共享的横向连接，交会处保留原图留白。短暂停留后，绕竖轴旋转一整圈，速度由慢到快再到慢。
原始 SVG 将 S 与 H 的上半笔画合并在同一路径中；渲染器仅在组合阶段分层，校验分层合并后与原始轮廓完全一致。组合结束后使用未经拆分的原始几何旋转。
旋转采用五次平滑插值，起止角速度为零。左侧文字在整个动画中保持静止。
横幅以大字号中文展示官网已有定位，并列出 HSCredit、天枢决策引擎和瑶光营销平台的既有介绍。
优先展示无损 WebP，保留渐变与字体细节；以 GIF 兼容其他浏览器。GitHub 无需执行脚本即可展示动画；README 同时提供减少动态效果的静态版本。

在具备 OpenGL 3.3 驱动、Cairo 运行库和 Windows Segoe UI / 微软雅黑字体的环境中运行：

```powershell
python -m pip install -r tools/requirements-banner.txt
python tools/render_banner.py --preview
python tools/render_banner.py
```

`--preview` 仅更新静态预览；正式生成会同时更新 WebP、GIF 和静态横幅。
静态预览取自组合完成后的 2.52 秒，避免首帧空白；可通过 `--output-dir` 将预览输出到独立目录。

动画分镜：0–1.1 秒 S 成形，1.25–2.05 秒 H 成形，1.65–2.32 秒 CREDIT 成形；2.8–7.2 秒完整旋转，7.2–8.4 秒停留，8.4–8.9 秒淡出，随后短暂停顿再循环。

## 横幅文案来源

文案核对日期：2026-10-24。以下短语均取自官网或对应项目介绍，横幅仅调整换行和排版。

| 展示内容 | 原始来源 |
| --- | --- |
| 专注金融风控技术与服务 | [官网首页](https://hengshucredit.com/) |
| 风控能力输出、模型评分服务、分析工具开源 | [官网核心业务](https://hengshucredit.com/solutions/)的三个栏目名称 |
| HSCredit：全流程量化工具箱 | [HSCredit README](https://github.com/hengshu-credit/hscredit)：面向信贷风控的全流程量化工具箱 |
| 天枢决策引擎：可视化风控决策平台 | [天枢仓库简介](https://github.com/hengshu-credit/tianshu-decision-engine) |
| 瑶光营销平台：用户营销与客户触达 | [瑶光 README](https://github.com/hengshu-credit/yaoguang-marketing)的项目定位 |

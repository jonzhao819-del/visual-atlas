# 视觉风格参考档案 · Visual Style Atlas

504 种图像风格、技法与视觉语言的个人参考库。每条都有：**中英双语名称、预览大图、来由与识别要点、可直接复制的 LetzAI 英文提示词**。

**在线地址：<https://jonzhao819-del.github.io/visual-atlas/>**

数据与图片整理自 [Atlas of Visual Effects](https://atlas.letz.ai)（LetzAI）。仅作个人学习与创作参考，图片与文字版权归原作者与 LetzAI 所有，请勿商用转载。

---

## 怎么用

- 直接打开上面的网址，手机、电脑、任何设备都行，不用装 App、不用登录。
- 搜索框支持中文名、英文名、年代、关键词，比如「蓝晒」「蒸汽波」「Canny」。
- 筛选用「历史技法 / 数字管线 / 收藏」，可以叠加年代、章节、排序。
- 点任意卡片看大图、完整提示词、识别 / 原理 / 怎么试 / 例子、术语和出处。
- 详情里点「复制提示词」直接粘进 AI 工具；按 `←` `→` 翻上一条 / 下一条，`Esc` 关闭。
- 卡片右上角的心形是收藏，存在浏览器本地。
- 首页顶部「随便看一条」随机抽一条找灵感。

## 本地打开

双击 `index.html` 即可，完全离线，不需要联网，不需要装任何东西。

整个 `visual-atlas` 文件夹拷到另一台电脑也能直接用。不要只拷 `index.html`——数据在 `assets/data.js`，图片在 `images/`。

## 手机上打开

直接用上面的 GitHub Pages 网址，Safari / Chrome 打开即可。

如果只想在家里用、不想走公网：双击 `启动服务.command`，手机连同一个 Wi-Fi，打开终端里打印的 `http://192.168.x.x:8777`。

---

## 更新网站

改完内容（或告诉我加东西）之后，任选一种：

双击 **`发布到GitHub.command`**：生成缩略图、重编数据、通过 GitHub API 发布，Pages 约 1 分钟后更新。

这台机器访问 `github.com:443` 经常超时，所以不走 `git push`，改用 GitHub API（`api.github.com` 可正常访问）。命令行等价于：

```bash
python3 scripts/make_thumbs.py
python3 scripts/build_data.py
python3 scripts/publish_github.py "更新说明"
```

GitHub 仓库：<https://github.com/jonzhao819-del/visual-atlas>

Pages 设置：仓库 **Settings → Pages** → Source 为 `main` 分支的 `/ (root)`。根目录的 `.nojekyll` 会让 Pages 按原样发布，不做 Jekyll 处理。

---

## 加新风格

把风格名（中英文）、图片、提示词、简介告诉我，我来加。也可以自己写一个 `entry.json`：

```json
{
  "title": "Neon Film Still",
  "titleZh": "霓虹剧照",
  "image": "/Users/你的用户名/Downloads/neon.jpg",
  "prompt": "Apply a neon-lit night film still ...",
  "kind": "custom",
  "decade": "2020s",
  "dating": "2020s 霓虹夜景参考",
  "caption": "一张夜景剧照，青绿色与品红光源对打。",
  "credit": "图片来源 / 授权",
  "tags": ["霓虹", "夜景", "电影感"],
  "body": {
    "识别": "整体是什么样",
    "原理": "它为什么成立",
    "怎么试": "可以怎么调"
  }
}
```

然后：

```bash
python3 scripts/add_style.py entry.json
python3 scripts/build_data.py
# 再双击 发布到GitHub.command
```

图片会自动缩放到 1100px 宽并转成 webp，存进 `images/`。卡片上会标「自建」，筛选栏会多出一个「自建」分类。

---

## 更新原站的新风格

```bash
python3 scripts/fetch_atlas.py
```

重新抓取 atlas.letz.ai 的全部条目和预览图，覆盖 `data/atlas.json` 与 `images/`，自动重编 `assets/data.js`。`data/custom.json` 里自己加的内容不会丢。

只重编、不抓图：

```bash
python3 scripts/build_data.py
```

---

## 文件结构

```
visual-atlas/
├── index.html              页面骨架
├── assets/
│   ├── styles.css          全部样式
│   ├── app.js              搜索 / 筛选 / 详情 / 收藏 / 复制
│   └── data.js             编译好的 504 条数据（自动生成，别手改）
├── images/                 504 张预览图（webp）
│   └── thumbs/             卡片用的小图（640px）
├── data/
│   ├── atlas.json          抓取下来的原始数据
│   ├── titles-zh.json      504 条中文标题（可手改）
│   └── custom.json         你自己加的条目
├── scripts/
│   ├── fetch_atlas.py      抓取原站
│   ├── make_thumbs.py      生成卡片缩略图
│   ├── build_data.py       编译 data.js
│   ├── add_style.py        加一条新风格
│   └── publish_github.py   通过 GitHub API 发布
├── screenshots/            效果截图
├── .nojekyll               GitHub Pages 跳过 Jekyll
├── robots.txt              不让搜索引擎收录
├── 发布到GitHub.command     双击提交并推送
├── 打开网站.command         双击本地打开
└── 启动服务.command         手机同一 Wi-Fi 访问（备用）
```

---

## 说明

- 纯静态：没有框架、没有构建步骤、没有外部字体请求，断网也能用。
- 图片懒加载；网格用 640px 小图（`images/thumbs/`），详情才加载原图，首屏快很多。
- `file://`、`http://` 本地服务、GitHub Pages 三种方式都测过。
- 提示词为原站英文原文，未做翻译，避免二次转写改变效果。
- 中文标题在 `data/titles-zh.json` 里，按 slug 对应；改完跑 `python3 scripts/build_data.py`。
- 页面加了 `noindex` 和 `robots.txt`：搜索引擎不收录，但拿到链接的人可以打开；仓库本身是公开的。

## 备份

GitHub 仓库是主副本，本地 `visual-atlas` 文件夹是工作副本。建议每隔一段时间把本地文件夹再拷一份到移动硬盘。

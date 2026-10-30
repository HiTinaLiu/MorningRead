# 英语晨读 MorningRead

面向小学低年级的英语美文晨读桌面工具：按篇浏览目录、改句子与配图、选配音角色、预览后导出竖屏视频，并生成对应的 A4 讲义。

## 功能

- **按篇生成视频**：一篇一个视频；开场页为主图，之后每句一页
- **英文朗读 / 中文只显示**：edge-tts 配音；开场白只朗读，不出现在画面上
- **主图可改**：大标题、二级标题可编辑；多套幼稚风格主题（太阳早餐、青草地、泡泡海等）
- **生成前可改**：句子增删改、换配图、试听与整篇预览；改动写入草稿，不覆盖 `data/catalog.json`
- **配图**：优先 Twemoji，再网上搜 Lottie JSON、Pixabay、Openverse
- **A4 讲义**：与当前草稿同内容的 PDF，含配图、中英文和「写一写」线
- **导出位置**：视频与讲义默认在 `Downloads/MorningRead/videos/`

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 桌面 | Electron + Vite + React |
| 接口 | FastAPI（`127.0.0.1:8776`） |
| 配音 | edge-tts |
| 视频 | Remotion 1080×1920 / 30fps |
| 讲义 | Pillow + resvg-py |

## 目录

```
MorningRead/
├── data/catalog.json          # 晨读目录与句子（源数据）
├── apps/desktop/              # Electron 界面
├── apps/video/                # Remotion 合成与渲染
└── services/api/              # FastAPI：目录、草稿、配图、TTS、视频、讲义
```

## 环境要求

- Node.js 18+
- Python 3.10+（推荐 3.12）
- Windows 上已装常见中文字体（如微软雅黑）便于讲义排版

## 安装

```powershell
# API
cd services/api
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 视频模块
cd ..\..\apps\video
npm install

# 桌面端
cd ..\desktop
npm install
```

可选：在设置页填入 Pixabay API Key，配图搜索结果更稳。

## 运行

在 `apps/desktop` 下：

```powershell
npm run dev
```

会启动 Vite（`6183`）、Electron，并拉起本机 FastAPI。改了 Python 代码后需重新运行 `npm run dev` 才会加载。

单独调试视频画面：

```powershell
cd apps/video
npm run studio
```

## 使用要点

1. 首页打开一篇晨读
2. 改主图标题、二级标题、主题皮肤；改开场白与句子；换图或试听
3. **预览**确认画面与配音
4. **生成视频**导出 mp4（含 srt）
5. **生成 A4 讲义**导出 PDF

草稿自动保存。「恢复原文」会丢掉该篇草稿。

## 数据位置

| 内容 | 位置 |
| --- | --- |
| 源目录 | `data/catalog.json` |
| 草稿 / TTS / 配图缓存 | 桌面端：Electron `userData`；单独跑 API：`services/api/.data` |
| 视频与讲义 | `Downloads/MorningRead/videos/<篇目 id>/` |

可用环境变量覆盖：

- `MORNINGREAD_ROOT`：仓库根目录
- `MORNINGREAD_DATA_DIR`：缓存与草稿目录
- `MORNINGREAD_OUTPUT_DIR`：视频与讲义输出目录
- `MORNINGREAD_PORT`：API 端口（默认 `8776`）
- `PIXABAY_API_KEY`：Pixabay 密钥

## 说明

- 视频按句分页：英文朗读，中文只显示在画面上
- 英文默认较慢语速（约 `-20%`），句后留跟读时间
- 配图不会改写目录源文件；用户选定的图存在草稿里

# Edge TTS Web 项目

一个可直接运行的文本转语音项目：
用户在 Web 页面输入文本，设置语速、音量、语调、音源后，后端调用 `edge-tts` 生成 MP3 并可在线试听/下载。

## 功能

- Web 前端文本输入
- 可调整语速（`rate`）
- 可调整音量（`volume`）
- 可调整语调（`pitch`）
- 可选择音源（voice）
- 生成 MP3 文件并下载

## 目录结构

```text
text_to_tts_script/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  └─ tts_service.py
├─ static/
│  ├─ css/
│  │  └─ styles.css
│  └─ js/
│     └─ app.js
├─ templates/
│  └─ index.html
├─ outputs/
│  └─ .gitkeep
├─ vendor/
│  └─ edge_tts/        # 本地内置 edge-tts（兜底）
├─ .gitignore
├─ requirements.txt
├─ start.bat
└─ README.md
```

## 环境要求

- Python 3.10 - 3.14（建议 64 位）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 一键启动（Windows）

双击项目根目录下的 `start.bat`，或命令行执行：

```bat
start.bat
```

脚本会自动：
1. 创建 `.venv` 虚拟环境（如果可用）
2. 检测依赖是否齐全，不齐全时执行 `python -m pip install -r requirements.txt`
3. 安装时优先使用二进制 wheel（避免 `aiohttp` 本地编译失败）
4. 启动服务 `http://127.0.0.1:8000`

## 手动启动

```bash
python app/main.py
```

## 使用说明

1. 打开浏览器访问 `http://127.0.0.1:8000`
2. 输入文本
3. 选择音源并调整语速/音量/语调
4. 点击“生成 MP3”
5. 在线试听或下载生成文件

## 输出文件

- 生成的 MP3 位于 `outputs/` 目录
- 文件名自动带时间戳，避免覆盖

## 说明

- 项目优先使用环境中安装的 `edge-tts`
- 若环境中未安装，代码会自动从 `vendor/edge_tts` 使用内置版本

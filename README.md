# Anna's Archive URL Scraper

自动抓取 [Anna's Archive Wikipedia](https://en.wikipedia.org/wiki/Anna%27s_Archive) 页面上的网址信息，并保存到 JSON 和 Markdown 文件中。

## 功能

- 自动抓取 Wikipedia 页面右侧信息框中的 URL
- 每天自动更新（通过 GitHub Actions）
- 支持手动触发
- 仅在有变化时提交更新

## 文件说明

| 文件 | 说明 |
|------|------|
| `scraper.py` | 抓取脚本 |
| `urls.json` | JSON 格式的 URL 数据 |
| `urls.md` | Markdown 格式的 URL 列表 |
| `.github/workflows/scraper.yml` | GitHub Actions 工作流配置 |
| `requirements.txt` | Python 依赖 |

## 本地运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行脚本

```bash
python scraper.py
```

运行后会生成 `urls.json` 和 `urls.md` 文件。

## GitHub Actions 自动运行

- **定时运行**: 每天 UTC 00:00 自动运行
- **手动触发**: 可以在 Actions 页面手动运行

### 设置步骤

1. Fork 此仓库
2. 确保 GitHub Actions 有写入权限：
   - 进入 Settings → Actions → General
   - 找到 "Workflow permissions"
   - 选择 "Read and write permissions"
   - 点击 Save

## 输出格式

### JSON 格式 (urls.json)

```json
{
  "last_updated": "2025-01-01T00:00:00",
  "source": "https://en.wikipedia.org/wiki/Anna%27s_Archive",
  "urls": [
    {
      "url": "https://annas-archive.li/",
      "display_text": "annas-archive.li"
    }
  ]
}
```

### Markdown 格式 (urls.md)

查看 [urls.md](urls.md) 获取最新 URL 列表。

## 许可证

MIT License

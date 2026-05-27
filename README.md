# 基于情感分析的餐厅智能推荐系统

用户输入自然语言需求（如"想吃辣的安静餐厅"），系统通过 NLP 解析意图，结合 BERT 情感分析结果，从 Elasticsearch 中检索最匹配的餐厅推荐给用户。

## 系统架构

```
用户输入 → Flask API → 自然语言解析(jieba) → ES查询构建 → Elasticsearch检索 → 结果排序 → 返回推荐
                                                                    ↑
                              Scrapy爬虫 → BERT情感分析 → 数据聚合导入ES
```

## 五大模块

| 模块 | 目录 | 技术栈 | 说明 |
|------|------|--------|------|
| 爬虫模块 | `crawler/` | Scrapy | 采集大众点评餐厅和评论数据 |
| 情感分析模块 | `sentiment/` | PyTorch + BERT | 菜品级别正/负面情感判断 |
| 数据存储与索引 | `storage/` | Elasticsearch | 结构化存储+高效检索 |
| 自然语言查询 | `query/` | jieba 分词 | 解析口味、氛围、价格等意图 |
| 推荐展示 | `app.py` | Flask | REST API 返回推荐列表 |

## 环境要求

- Python 3.9+
- Elasticsearch 8.x（需安装 IK 中文分词插件）
- CUDA（可选，加速 BERT 推理）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 配置 Elasticsearch 地址等
```

### 3. 启动 Elasticsearch

```bash
# 确保 ES 已启动并安装了 IK 分词插件
# 下载：https://github.com/medcl/elasticsearch-analysis-ik
```

### 4. 初始化数据并启动服务

```bash
# 使用示例数据快速启动（推荐首次体验）
python run.py --all

# 或分步执行：
python run.py --init      # 仅初始化数据到ES
python run.py             # 仅启动Flask服务
```

### 5. 完整流程（从爬虫开始）

```bash
# Step 1: 运行爬虫采集数据
python run_crawler.py

# Step 2: 运行情感分析
python run_sentiment.py

# Step 3: 导入ES并启动服务
python run.py --all
```

## API 使用

### 智能推荐

```bash
POST /api/recommend
Content-Type: application/json

{
    "query": "想吃辣的安静餐厅，人均100左右"
}
```

**响应示例：**

```json
{
    "parsed": {
        "flavors": ["辣"],
        "atmospheres": ["安静"],
        "price_range": [80, 120],
        "categories": [],
        "dishes": [],
        "keywords": ["想", "吃", "辣", "的", "安静", "餐厅"]
    },
    "results": [
        {
            "id": "xxx",
            "name": "川味观",
            "address": "北京市朝阳区三里屯路12号",
            "avg_price": 98,
            "overall_score": 4.5,
            "flavor_tags": ["辣"],
            "atmosphere_tags": ["安静"],
            "sentiment": {"overall": 0.86, "taste": 0.83, "environment": 0.83},
            "top_dishes": [
                {"name": "水煮鱼", "positive_rate": 0.96, "mentions": 1}
            ],
            "match_score": 12.5
        }
    ],
    "total": 1
}
```

### 查询示例

| 输入 | 解析结果 |
|------|----------|
| "想吃辣的安静餐厅" | 口味=辣，氛围=安静 |
| "便宜的火锅，适合聚会" | 价格<80，类别=火锅，氛围=热闹 |
| "约会用的日料，环境好的" | 类别=日料，氛围=浪漫 |
| "带孩子吃饭，人均50-100" | 氛围=家庭，价格=50-100 |

### 其他接口

```bash
GET /api/restaurant/<id>    # 餐厅详情
GET /api/health             # 健康检查
```

## 项目结构

```
.
├── app.py                  # Flask 应用入口
├── config.py               # 统一配置
├── run.py                  # 一键启动脚本
├── run_crawler.py          # 爬虫启动脚本
├── run_sentiment.py        # 情感分析脚本
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── crawler/                # 爬虫模块
│   ├── spiders/
│   │   └── dianping_spider.py
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   └── settings.py
├── sentiment/              # 情感分析模块
│   ├── analyzer.py         # BERT 分析器
│   └── process.py          # 批量处理脚本
├── storage/                # 存储模块
│   ├── es_storage.py       # ES 操作封装
│   └── importer.py         # 数据聚合与导入
├── query/                  # 查询模块
│   ├── parser.py           # 自然语言解析
│   └── builder.py          # ES 查询构建
└── data/                   # 数据目录
    ├── restaurants.jsonl    # 餐厅数据
    └── reviews_analyzed.jsonl  # 分析后的评论
```

## 技术说明

### 情感分析
- 使用 `bert-base-chinese` 预训练模型
- 支持整体情感 + 菜品级别情感 + 多维度（口味/环境/服务/价格）情感
- 批量分析提升效率

### 自然语言解析
- jieba 分词提取关键词
- 规则匹配识别口味、氛围、价格、菜系
- 正则提取价格区间

### 推荐排序
- ES BM25 文本相关性
- 情感分数加权
- 多维度综合评分

## 注意事项

1. 大众点评有较强的反爬机制，生产环境建议使用代理池和验证码服务
2. BERT 模型首次加载需下载约 400MB，建议提前下载
3. ES 需安装 IK 分词插件才能支持中文分词索引
4. 示例数据已包含情感分析结果，可跳过 Step 1-2 直接体验

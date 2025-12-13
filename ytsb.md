下面给出一个“10 分钟速览 + 可运行代码”的入门包，帮你把「传统做法」和「大模型做法」都跑通。所有脚本可直接复制到 Jupyter/VSCode 里执行，依赖仅 `scikit-learn`、`transformers`、`torch`、`openai`(可选)。

--------------------------------------------------
1 意图识别是什么？
一句话定义：把用户自然语言输入映射到“预定义业务意图”的多分类任务，是 NLU 的入口。  
示例：  
输入：“帮我订一张明天去上海的票”  
输出：intent = book_flight  
系统随后触发订机票流程并抽取 {date: “明天”, dest: “上海”} 等槽位。

--------------------------------------------------
2 传统方案：TF-IDF + 线性模型
特点：无需 GPU、毫秒级、可解释性强，适合冷启动或数据 <1w 条的小场景。

```python
# 传统机器学习意图识别（scikit-learn 版）
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# 1）造一份玩具数据
data = {
    "text": [
        "明天北京天气怎么样", "查天气", "播放周杰伦的歌", "我想听音乐",
        "帮我订一张机票", "预订航班", "关机", "退出"
    ],
    "intent": [
        "query_weather", "query_weather", "play_music", "play_music",
        "book_flight", "book_flight", "power_off", "power_off"
    ]
}
df = pd.DataFrame(data)

# 2）训练 / 测试拆分
X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["intent"], test_size=0.25, random_state=42, stratify=df["intent"])

# 3）一条 Pipeline 解决向量化 + 分类
clf = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
    ("lr", LogisticRegression(max_iter=500))
])
clf.fit(X_train, y_train)

# 4）评估
print(classification_report(y_test, clf.predict(X_test)))
print("混淆矩阵:\n", confusion_matrix(y_test, clf.predict(X_test)))

# 5）在线预测
print(clf.predict(["给我来首歌"]))   # -> ['play_music']
```

--------------------------------------------------
3 深度学习方案：BERT 微调
特点：精度高、能捕捉口语化变体；需要 GPU 或至少 4 GB 显存，数据量建议 >1 k/类。

```python
# BERT 意图分类（transformers 版）
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
import torch, evaluate, numpy as np

# 1）同样用上面的 df
label2id = {l: i for i, l in enumerate(df["intent"].unique())}
id2label = {i: l for l, i in label2id.items()}
df["label"] = df["intent"].map(label2id)

# 2）转 HuggingFace Dataset
ds = Dataset.from_pandas(df)

tok = BertTokenizer.from_pretrained("bert-base-chinese")
def encode(e):
    return tok(e["text"], truncation=True, padding="max_length", max_length=32)
ds = ds.map(encode, batched=True).train_test_split(test_size=0.2, seed=42)

# 3）模型
model = BertForSequenceClassification.from_pretrained(
    "bert-base-chinese",
    num_labels=len(label2id),
    id2label=id2label, label2id=label2id
)

# 4）训练参数（快速演示，epoch=3）
args = TrainingArguments(
    output_dir="ckpt", per_device_train_batch_size=8,
    num_train_epochs=3, logging_steps=10, evaluation_strategy="epoch"
)

metric = evaluate.load("accuracy")
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return metric.compute(predictions=preds, references=labels)

trainer = Trainer(model=model, args=args,
                  train_dataset=ds["train"],
                  eval_dataset=ds["test"],
                  compute_metrics=compute_metrics)
trainer.train()

# 5）推理
text = "明天需要雨伞吗"
inputs = tok(text, return_tensors="pt")
logits = model(**inputs).logits
print(id2label[logits.argmax(-1).item()])   # -> query_weather
```

--------------------------------------------------
4 大模型零 / 少样本方案（LLM Prompt）
特点：无需训练，只需写 Prompt + 调 API；适合意图多变、无标注或要求快速上线的场景。  
下面给出 OpenAI 版，可等量替换成 Qwen / Kimi / Baichuan 本地接口。

```python
# pip install openai
import openai, os
openai.api_key = os.getenv("OPENAI_API_KEY")

INTENT_DESC = """
query_weather: 用户想查天气
play_music: 用户想播放/听歌
book_flight: 用户想订机票
power_off: 用户想关机或退出
"""

def llm_intent(text):
    prompt = f"""
根据描述，把用户句子分到以下意图之一：
{INTENT_DESC}
用户句子：{text}
只输出意图编号，不要解释。
"""
    rsp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return rsp.choices[0].message.content.strip()

print(llm_intent("帮我查一下后天深圳的天气"))  # -> query_weather
```

进阶玩法  
1) 多意图：让 LLM 输出 JSON，支持 “intent_list”: ["query_weather", "play_music"]  
2) 槽位一起抽：在 Prompt 里加 “同时提取结构化参数，输出 {intent:…, slots:…}”  
3) 对话级上下文：把历史拼接后一起喂给模型，或采用 LangChain/LangGraph 的 Memory 模块。

--------------------------------------------------
5 如何选型？
1. 冷启动 / 规则明显 → 正则/关键词  
2. 数据 1 k~10 k、延迟敏感 → TF-IDF+SVM/LR  
3. 数据 >10 k、精度优先 → BERT 微调  
4. 意图常变、无标注人力 → LLM zero/few-shot  
5. 综合：用 LLM 做“兜底+自动标注”，把高置信结果回流给轻量模型，形成迭代闭环 。

--------------------------------------------------
6 更多实战资料
- 完整传统机器学习代码片段与指标解读   
- DevOps 工单场景：BERT + 槽位抽取 + 自动流程编排   
- 中文 BERT 意图识别端到端项目（含混淆矩阵可视化）  
- 多关键词/主题词提取与检索增强（RAG）结合意图识别   

把上面 3 份脚本依次跑通，你就拥有了“传统机器学习 + 深度微调 + 大模型 Prompt” 三套武器，可按数据、算力、时效自由切换。祝上手顺利!
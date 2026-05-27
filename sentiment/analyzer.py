import torch
from transformers import BertTokenizer, BertForSequenceClassification
from config import Config


class SentimentAnalyzer:
    """基于BERT的中文情感分析器

    对餐厅评论进行细粒度情感分析：
    - 整体评论情感 (正面/负面/中性)
    - 菜品级别情感 (提取评论中对具体菜品的评价)
    - 氛围/环境/服务等维度情感
    """

    LABELS = ["negative", "neutral", "positive"]

    ASPECT_KEYWORDS = {
        "taste": ["好吃", "难吃", "味道", "口味", "鲜", "香", "辣", "甜", "咸", "淡",
                  "油腻", "清淡", "正宗", "地道", "入味"],
        "environment": ["环境", "装修", "氛围", "安静", "吵", "干净", "卫生", "舒适",
                       "温馨", "浪漫", "情调", "格调", "优雅"],
        "service": ["服务", "态度", "热情", "冷淡", "上菜", "等位", "速度", "耐心"],
        "price": ["价格", "性价比", "便宜", "贵", "实惠", "划算", "值"],
    }

    def __init__(self, model_name=None):
        self.model_name = model_name or Config.BERT_MODEL
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()

    def _load_model(self):
        self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
        self.model = BertForSequenceClassification.from_pretrained(
            self.model_name, num_labels=3
        )
        self.model.to(self.device)
        self.model.eval()

    def analyze(self, text):
        """对单条文本做情感分析

        Returns:
            dict: {
                "label": "positive" | "neutral" | "negative",
                "score": float (0-1),
                "aspects": { "taste": score, "environment": score, ... }
            }
        """
        overall = self._predict(text)
        aspects = self._analyze_aspects(text)

        return {
            "label": overall["label"],
            "score": overall["score"],
            "aspects": aspects,
        }

    def analyze_dish(self, review_text, dish_name):
        """分析评论中对某道菜的情感

        从评论中提取包含该菜品名的句子，分析情感倾向。
        """
        import re
        sentences = re.split(r"[。！？；\n]", review_text)
        dish_sentences = [s for s in sentences if dish_name in s and s.strip()]

        if not dish_sentences:
            return {"label": "neutral", "score": 0.5, "mentioned": False}

        combined = "。".join(dish_sentences)
        result = self._predict(combined)
        result["mentioned"] = True
        return result

    def batch_analyze(self, texts, batch_size=16):
        """批量情感分析"""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = self._predict_batch(batch)
            results.extend(batch_results)
        return results

    def _predict(self, text):
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            predicted = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][predicted].item()

        return {
            "label": self.LABELS[predicted],
            "score": confidence,
        }

    def _predict_batch(self, texts):
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            predicted = torch.argmax(probs, dim=-1)

        results = []
        for i in range(len(texts)):
            label_idx = predicted[i].item()
            results.append({
                "label": self.LABELS[label_idx],
                "score": probs[i][label_idx].item(),
            })
        return results

    def _analyze_aspects(self, text):
        """分析评论的多维度情感"""
        import re
        sentences = re.split(r"[。！？；,，\n]", text)
        aspect_scores = {}

        for aspect, keywords in self.ASPECT_KEYWORDS.items():
            relevant = [s for s in sentences if any(kw in s for kw in keywords) and s.strip()]
            if relevant:
                combined = "。".join(relevant)
                result = self._predict(combined)
                score = result["score"] if result["label"] == "positive" else -result["score"]
                aspect_scores[aspect] = round(score, 3)

        return aspect_scores

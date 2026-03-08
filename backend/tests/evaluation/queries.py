"""40 test queries across 7 categories for evaluation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalQuery:
    """A single evaluation query with gold standard."""

    id: str
    category: str
    question: str
    expected_entities: list[str] = field(default_factory=list)
    expected_relationships: list[str] = field(default_factory=list)
    min_hops: int = 1
    gold_answer_keywords: list[str] = field(default_factory=list)
    difficulty: str = "medium"


# ── Factual Lookup (6 queries) ───────────────────────────────────

FACTUAL_QUERIES = [
    EvalQuery(
        id="factual_001",
        category="FACTUAL_LOOKUP",
        question="What is YOLO?",
        expected_entities=["YOLO"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["object detection", "real-time", "bounding box"],
        difficulty="easy",
    ),
    EvalQuery(
        id="factual_002",
        category="FACTUAL_LOOKUP",
        question="Describe the ResNet architecture.",
        expected_entities=["ResNet"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["residual", "skip connection", "deep"],
        difficulty="easy",
    ),
    EvalQuery(
        id="factual_003",
        category="FACTUAL_LOOKUP",
        question="What is the Transformer architecture?",
        expected_entities=["Transformer"],
        expected_relationships=["USES"],
        gold_answer_keywords=["attention", "self-attention", "encoder", "decoder"],
        difficulty="easy",
    ),
    EvalQuery(
        id="factual_004",
        category="FACTUAL_LOOKUP",
        question="What is batch normalization?",
        expected_entities=["Batch Normalization"],
        expected_relationships=["USES"],
        gold_answer_keywords=["normalize", "training", "layer"],
        difficulty="easy",
    ),
    EvalQuery(
        id="factual_005",
        category="FACTUAL_LOOKUP",
        question="What is the CIFAR-10 dataset?",
        expected_entities=["CIFAR-10"],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["image", "classification", "10 classes"],
        difficulty="easy",
    ),
    EvalQuery(
        id="factual_006",
        category="FACTUAL_LOOKUP",
        question="What is dropout regularization?",
        expected_entities=["Dropout"],
        expected_relationships=["USES"],
        gold_answer_keywords=["regularization", "overfitting", "randomly"],
        difficulty="easy",
    ),
]

# ── Comparison (6 queries) ───────────────────────────────────────

COMPARISON_QUERIES = [
    EvalQuery(
        id="comparison_001",
        category="COMPARISON",
        question="Compare BERT and GPT-2 architectures.",
        expected_entities=["BERT", "GPT-2"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["bidirectional", "autoregressive", "transformer"],
        difficulty="medium",
    ),
    EvalQuery(
        id="comparison_002",
        category="COMPARISON",
        question="What are the differences between Adam and SGD optimizers?",
        expected_entities=["Adam", "SGD"],
        expected_relationships=["USES"],
        gold_answer_keywords=["momentum", "learning rate", "adaptive"],
        difficulty="medium",
    ),
    EvalQuery(
        id="comparison_003",
        category="COMPARISON",
        question="Compare CNN and RNN for sequence modeling.",
        expected_entities=["CNN", "RNN"],
        expected_relationships=["USES"],
        gold_answer_keywords=["convolutional", "recurrent", "sequence"],
        difficulty="medium",
    ),
    EvalQuery(
        id="comparison_004",
        category="COMPARISON",
        question="How do GAN and VAE differ for image generation?",
        expected_entities=["GAN", "VAE"],
        expected_relationships=["USES"],
        gold_answer_keywords=["generative", "adversarial", "variational"],
        difficulty="medium",
    ),
    EvalQuery(
        id="comparison_005",
        category="COMPARISON",
        question="Compare ImageNet and COCO datasets.",
        expected_entities=["ImageNet", "COCO"],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["classification", "detection", "segmentation"],
        difficulty="medium",
    ),
    EvalQuery(
        id="comparison_006",
        category="COMPARISON",
        question="What are the differences between ViT and ResNet?",
        expected_entities=["ViT", "ResNet"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["vision transformer", "residual", "patches"],
        difficulty="medium",
    ),
]

# ── Temporal (6 queries) ─────────────────────────────────────────

TEMPORAL_QUERIES = [
    EvalQuery(
        id="temporal_001",
        category="TEMPORAL",
        question="What was the state of the art for ImageNet in 2022?",
        expected_entities=["ImageNet"],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["accuracy", "top-1"],
        difficulty="medium",
    ),
    EvalQuery(
        id="temporal_002",
        category="TEMPORAL",
        question="How has the use of transformers evolved since 2017?",
        expected_entities=["Transformer"],
        expected_relationships=["USES"],
        gold_answer_keywords=["attention", "NLP", "vision"],
        difficulty="hard",
    ),
    EvalQuery(
        id="temporal_003",
        category="TEMPORAL",
        question="What methods dominated object detection before 2020?",
        expected_entities=["Object Detection"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["YOLO", "Faster R-CNN", "SSD"],
        difficulty="hard",
    ),
    EvalQuery(
        id="temporal_004",
        category="TEMPORAL",
        question="When was BERT first introduced and on what tasks?",
        expected_entities=["BERT"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["2018", "NLP", "pre-training"],
        difficulty="medium",
    ),
    EvalQuery(
        id="temporal_005",
        category="TEMPORAL",
        question="What are the most recent methods for text classification?",
        expected_entities=["Text Classification"],
        expected_relationships=["USES"],
        gold_answer_keywords=["transformer", "pre-trained"],
        difficulty="medium",
    ),
    EvalQuery(
        id="temporal_006",
        category="TEMPORAL",
        question="How has LoRA usage changed over time?",
        expected_entities=["LoRA"],
        expected_relationships=["USES"],
        gold_answer_keywords=["fine-tuning", "parameter-efficient", "adaptation"],
        difficulty="hard",
    ),
]

# ── Network (5 queries) ──────────────────────────────────────────

NETWORK_QUERIES = [
    EvalQuery(
        id="network_001",
        category="NETWORK",
        question="Who are the most influential authors in NLP?",
        expected_entities=[],
        expected_relationships=["AUTHORED"],
        gold_answer_keywords=["author", "papers"],
        difficulty="hard",
        min_hops=2,
    ),
    EvalQuery(
        id="network_002",
        category="NETWORK",
        question="Which authors bridge NLP and computer vision research?",
        expected_entities=[],
        expected_relationships=["AUTHORED", "USES"],
        gold_answer_keywords=["author", "cross-domain"],
        difficulty="hard",
        min_hops=3,
    ),
    EvalQuery(
        id="network_003",
        category="NETWORK",
        question="What research groups frequently collaborate on transformer papers?",
        expected_entities=["Transformer"],
        expected_relationships=["AUTHORED"],
        gold_answer_keywords=["collaboration", "co-author"],
        difficulty="hard",
        min_hops=2,
    ),
    EvalQuery(
        id="network_004",
        category="NETWORK",
        question="Which methods share the most common authors?",
        expected_entities=[],
        expected_relationships=["AUTHORED", "USES"],
        gold_answer_keywords=["method", "author"],
        difficulty="hard",
        min_hops=3,
    ),
    EvalQuery(
        id="network_005",
        category="NETWORK",
        question="Find co-authors who work on both GANs and diffusion models.",
        expected_entities=["GAN", "Diffusion"],
        expected_relationships=["AUTHORED", "USES"],
        gold_answer_keywords=["author", "generative"],
        difficulty="hard",
        min_hops=3,
    ),
]

# ── Exploratory (7 queries) ──────────────────────────────────────

EXPLORATORY_QUERIES = [
    EvalQuery(
        id="exploratory_001",
        category="EXPLORATORY",
        question="What methods are commonly used for object detection?",
        expected_entities=["Object Detection"],
        expected_relationships=["USES"],
        gold_answer_keywords=["YOLO", "R-CNN", "detection"],
        difficulty="easy",
    ),
    EvalQuery(
        id="exploratory_002",
        category="EXPLORATORY",
        question="What datasets are available for text classification?",
        expected_entities=["Text Classification"],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["dataset", "classification"],
        difficulty="easy",
    ),
    EvalQuery(
        id="exploratory_003",
        category="EXPLORATORY",
        question="What are the main approaches to image segmentation?",
        expected_entities=["Image Segmentation"],
        expected_relationships=["USES"],
        gold_answer_keywords=["segmentation", "pixel", "mask"],
        difficulty="medium",
    ),
    EvalQuery(
        id="exploratory_004",
        category="EXPLORATORY",
        question="What tasks can transformers be applied to?",
        expected_entities=["Transformer"],
        expected_relationships=["USES"],
        gold_answer_keywords=["NLP", "vision", "task"],
        difficulty="medium",
    ),
    EvalQuery(
        id="exploratory_005",
        category="EXPLORATORY",
        question="What are popular benchmarks for language models?",
        expected_entities=[],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["benchmark", "dataset"],
        difficulty="medium",
    ),
    EvalQuery(
        id="exploratory_006",
        category="EXPLORATORY",
        question="What self-supervised learning methods exist?",
        expected_entities=["Self-Supervised Learning"],
        expected_relationships=["USES"],
        gold_answer_keywords=["contrastive", "pre-training", "self-supervised"],
        difficulty="medium",
    ),
    EvalQuery(
        id="exploratory_007",
        category="EXPLORATORY",
        question="What are the main data augmentation techniques?",
        expected_entities=["Data Augmentation"],
        expected_relationships=["USES"],
        gold_answer_keywords=["augmentation", "training", "transform"],
        difficulty="medium",
    ),
]

# ── Aggregation (5 queries) ──────────────────────────────────────

AGGREGATION_QUERIES = [
    EvalQuery(
        id="aggregation_001",
        category="AGGREGATION",
        question="How many papers use transformers?",
        expected_entities=["Transformer"],
        expected_relationships=["USES"],
        gold_answer_keywords=["papers", "count", "transformer"],
        difficulty="medium",
    ),
    EvalQuery(
        id="aggregation_002",
        category="AGGREGATION",
        question="What are the most commonly used methods across all tasks?",
        expected_entities=[],
        expected_relationships=["USES"],
        gold_answer_keywords=["method", "popular", "common"],
        difficulty="medium",
    ),
    EvalQuery(
        id="aggregation_003",
        category="AGGREGATION",
        question="Which datasets have the most benchmark results?",
        expected_entities=[],
        expected_relationships=["EVALUATED_ON"],
        gold_answer_keywords=["dataset", "benchmark", "results"],
        difficulty="medium",
    ),
    EvalQuery(
        id="aggregation_004",
        category="AGGREGATION",
        question="How many different tasks are represented in the knowledge graph?",
        expected_entities=[],
        expected_relationships=[],
        gold_answer_keywords=["task", "count"],
        difficulty="easy",
    ),
    EvalQuery(
        id="aggregation_005",
        category="AGGREGATION",
        question="What percentage of papers use attention mechanisms?",
        expected_entities=["Attention"],
        expected_relationships=["USES"],
        gold_answer_keywords=["attention", "papers", "percentage"],
        difficulty="hard",
    ),
]

# ── Multi-hop (5 queries) ────────────────────────────────────────

MULTI_HOP_QUERIES = [
    EvalQuery(
        id="multihop_001",
        category="MULTI_HOP",
        question="What datasets are used to evaluate methods that appear in papers about ResNet?",
        expected_entities=["ResNet"],
        expected_relationships=["USES", "EVALUATED_ON"],
        gold_answer_keywords=["dataset", "ResNet"],
        difficulty="hard",
        min_hops=3,
    ),
    EvalQuery(
        id="multihop_002",
        category="MULTI_HOP",
        question="What tasks are addressed by methods that use attention mechanisms?",
        expected_entities=["Attention"],
        expected_relationships=["USES"],
        gold_answer_keywords=["task", "attention"],
        difficulty="hard",
        min_hops=2,
    ),
    EvalQuery(
        id="multihop_003",
        category="MULTI_HOP",
        question="Which papers use both convolutional and recurrent methods?",
        expected_entities=["CNN", "RNN"],
        expected_relationships=["USES"],
        gold_answer_keywords=["paper", "convolutional", "recurrent"],
        difficulty="hard",
        min_hops=2,
    ),
    EvalQuery(
        id="multihop_004",
        category="MULTI_HOP",
        question="What methods are evaluated on the same datasets as BERT?",
        expected_entities=["BERT"],
        expected_relationships=["EVALUATED_ON", "USES"],
        gold_answer_keywords=["method", "BERT", "dataset"],
        difficulty="hard",
        min_hops=3,
    ),
    EvalQuery(
        id="multihop_005",
        category="MULTI_HOP",
        question="Which tasks connect the research areas of NLP and computer vision?",
        expected_entities=["NLP", "Computer Vision"],
        expected_relationships=["USES"],
        gold_answer_keywords=["task", "cross-modal", "multimodal"],
        difficulty="hard",
        min_hops=3,
    ),
]


def get_all_queries() -> list[EvalQuery]:
    """Return all 40 evaluation queries."""
    return (
        FACTUAL_QUERIES
        + COMPARISON_QUERIES
        + TEMPORAL_QUERIES
        + NETWORK_QUERIES
        + EXPLORATORY_QUERIES
        + AGGREGATION_QUERIES
        + MULTI_HOP_QUERIES
    )


def get_queries_by_category(category: str) -> list[EvalQuery]:
    """Return queries for a specific category."""
    return [q for q in get_all_queries() if q.category == category]


CATEGORIES = [
    "FACTUAL_LOOKUP",
    "COMPARISON",
    "TEMPORAL",
    "NETWORK",
    "EXPLORATORY",
    "AGGREGATION",
    "MULTI_HOP",
]

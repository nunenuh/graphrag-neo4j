"""Unit tests for library/analytics/trends.py."""

import json

from graphrag_service.library.analytics.trends import (
    build_entity_year_counts,
    compute_diffusion_paths,
    compute_trend_scores,
)


class TestComputeTrendScores:
    def test_growth(self):
        counts = {"method_a": {"2023": 5, "2024": 15}}
        result = compute_trend_scores(counts)
        assert result["method_a"] == 3.0  # 15/5

    def test_decline(self):
        counts = {"method_a": {"2023": 10, "2024": 5}}
        result = compute_trend_scores(counts)
        assert result["method_a"] == 0.5  # 5/10

    def test_stable(self):
        counts = {"method_a": {"2023": 10, "2024": 10}}
        result = compute_trend_scores(counts)
        assert result["method_a"] == 1.0

    def test_no_previous_year(self):
        counts = {"method_a": {"2024": 10}}
        result = compute_trend_scores(counts)
        assert result["method_a"] == 10.0  # 10/max(0,1) = 10

    def test_no_recent_year(self):
        counts = {"method_a": {"2023": 10}}
        result = compute_trend_scores(counts)
        assert result["method_a"] == 0.0  # 0/10

    def test_custom_years(self):
        counts = {"m": {"2021": 5, "2022": 10}}
        result = compute_trend_scores(counts, recent_year="2022", previous_year="2021")
        assert result["m"] == 2.0

    def test_empty(self):
        assert compute_trend_scores({}) == {}


class TestComputeDiffusionPaths:
    def test_basic(self):
        data = {
            "ResNet": [
                {"task": "Image Classification", "year": "2015", "paper_count": 5},
                {"task": "Object Detection", "year": "2016", "paper_count": 3},
            ]
        }
        result = compute_diffusion_paths(data)
        parsed = json.loads(result["ResNet"])
        assert len(parsed) == 2
        assert parsed[0]["year"] == "2015"

    def test_sorted_by_year(self):
        data = {
            "BERT": [
                {"task": "QA", "year": "2020", "paper_count": 2},
                {"task": "NER", "year": "2019", "paper_count": 5},
            ]
        }
        result = compute_diffusion_paths(data)
        parsed = json.loads(result["BERT"])
        assert parsed[0]["year"] == "2019"

    def test_empty(self):
        assert compute_diffusion_paths({}) == {}


class TestBuildEntityYearCounts:
    def test_method_counts(self):
        evaluations = [
            {
                "task": "Image Classification",
                "datasets": [
                    {
                        "dataset": "CIFAR-10",
                        "sota": {
                            "rows": [
                                {"model_name": "ResNet", "year": 2024},
                                {"model_name": "ResNet", "year": 2023},
                                {"model_name": "VGG", "year": 2023},
                            ]
                        },
                    }
                ],
            }
        ]
        result = build_entity_year_counts(evaluations, entity_type="method")
        assert result["ResNet"]["2024"] == 1
        assert result["ResNet"]["2023"] == 1
        assert result["VGG"]["2023"] == 1

    def test_task_counts(self):
        evaluations = [
            {
                "task": "Image Classification",
                "datasets": [
                    {"dataset": "CIFAR-10", "sota": {"rows": [{"model_name": "ResNet", "year": 2024}]}},
                ],
            }
        ]
        result = build_entity_year_counts(evaluations, entity_type="task")
        assert result["Image Classification"]["2024"] == 1

    def test_empty(self):
        assert build_entity_year_counts([]) == {}

    def test_skips_missing_task(self):
        evaluations = [{"datasets": []}]
        assert build_entity_year_counts(evaluations) == {}

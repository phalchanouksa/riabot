"""
Adaptive Recommendation System with Smart Question Selection

This module implements an advanced adaptive testing approach that:
1. Asks the most informative questions first
2. Dynamically adjusts based on student responses
3. Stops early when confident
4. Provides explainable recommendations
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .recommender import MajorRecommender
class AdaptiveRecommender:
    """
    Advanced adaptive recommendation system that minimizes questions
    while maximizing prediction accuracy.
    """
    
    # Configuration
    MAX_QUESTIONS = 256  # Maximum questions (full survey)
    MIN_QUESTIONS_BEFORE_STOP = 24  # Build a reliable profile before early stopping
    HARD_STOP_QUESTIONS = 48  # Avoid dragging the survey on too long
    CONFIDENCE_THRESHOLD = 0.85  # Stop if confidence exceeds this
    HIGH_CONFIDENCE_THRESHOLD = 0.92
    VERY_HIGH_CONFIDENCE_THRESHOLD = 0.97
    UNCERTAINTY_THRESHOLD = 0.15  # Stop if uncertainty below this (after some questions)
    LOW_UNCERTAINTY_THRESHOLD = 0.12
    DEFAULT_INTEREST_VALUE = 2.5
    DEFAULT_SKILL_VALUE = 1.5
    
    # Question importance weights (will be computed from model)
    # Higher weight = more important question
    QUESTION_IMPORTANCE = None
    
    @classmethod
    def initialize_importance_weights(cls):
        """
        Initialize question importance based on feature analysis.
        In production, this should be computed from the trained model.
        For now, we'll use heuristics.
        """
        if cls.QUESTION_IMPORTANCE is not None:
            return
        
        # Initialize all questions with base weight
        weights = np.ones(256) * 0.5
        
        # Boost importance of skill questions (ch2) over interest questions (ch1)
        # ch1: indices 0-95 (16 categories × 6 questions)
        # ch2: indices 96-255 (16 categories × 10 questions)
        weights[96:] *= 1.5  # Skills are more predictive
        
        # Boost specific high-impact questions for each major
        # These are typically the first few questions in each category
        for category_idx in range(16):
            # First 2 interest questions per category (most defining)
            ch1_start = category_idx * 6
            weights[ch1_start:ch1_start + 2] *= 1.8
            
            # First 3 skill questions per category (most practical)
            ch2_start = 96 + (category_idx * 10)
            weights[ch2_start:ch2_start + 3] *= 2.0
        
        cls.QUESTION_IMPORTANCE = weights
    
    @classmethod
    def get_question_priority(
        cls,
        answered_indices: List[int],
        current_probabilities: Optional[np.ndarray] = None,
        answers: Optional[Dict[int, int]] = None,
        allowed_categories: Optional[List[int]] = None,
    ) -> List[int]:
        """
        Get prioritized list of questions to ask next.
        
        Args:
            answered_indices: List of question indices already answered
            current_probabilities: Current prediction probabilities for each major
            
        Returns:
            List of question indices, sorted by priority (highest first)
        """
        cls.initialize_importance_weights()
        
        allowed_question_indices = cls._get_allowed_question_indices(allowed_categories)

        # Get unanswered questions
        all_indices = set(allowed_question_indices)
        answered_set = set(answered_indices)
        unanswered = list(all_indices - answered_set)

        if not unanswered:
            return []
        
        # Base priority from importance weights
        priorities = cls.QUESTION_IMPORTANCE[unanswered].copy()
        
        # If we have current probabilities, boost questions for the most likely majors.
        if current_probabilities is not None:
            top_3_classes = np.argsort(current_probabilities)[-3:][::-1]

            for class_idx in top_3_classes:
                major_id = MajorRecommender.get_original_major_id(int(class_idx))
                if major_id not in cls._normalize_allowed_categories(allowed_categories):
                    continue

                ch1_start = major_id * 6
                ch1_end = ch1_start + 6
                ch1_mask = (np.array(unanswered) >= ch1_start) & (np.array(unanswered) < ch1_end)
                priorities[ch1_mask] *= 1.5

                ch2_start = 96 + (major_id * 10)
                ch2_end = ch2_start + 10
                ch2_mask = (np.array(unanswered) >= ch2_start) & (np.array(unanswered) < ch2_end)
                priorities[ch2_mask] *= 2.0

        # Keep broad category coverage early so the survey does not lock in too soon.
        focus_categories = set(cls._get_focus_categories(allowed_categories))
        interest_covered, skill_covered = cls._get_dimension_coverage(answered_indices)
        fully_covered = interest_covered & skill_covered
        answer_signals = cls._get_category_answer_signals(answers or {})
        top_signal_categories = [
            category for category, score in sorted(
                answer_signals.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if score >= 0.65
        ][:4]
        if not top_signal_categories and answer_signals:
            top_signal_categories = [
                category for category, _ in sorted(
                    answer_signals.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:3]
            ]

        for pos, question_idx in enumerate(unanswered):
            is_interest = question_idx < 96
            category = question_idx // 6 if is_interest else (question_idx - 96) // 10

            if category in focus_categories:
                priorities[pos] *= 1.2

            if category not in fully_covered:
                if is_interest and category not in interest_covered:
                    priorities[pos] *= 2.6
                elif not is_interest and category not in skill_covered:
                    priorities[pos] *= 2.2
                elif category not in interest_covered or category not in skill_covered:
                    priorities[pos] *= 1.3

            if category in top_signal_categories:
                priorities[pos] *= 1.7
                if not is_interest and category in interest_covered and category not in skill_covered:
                    priorities[pos] *= 1.4
        
        # Sort by priority (descending)
        sorted_indices = [unanswered[i] for i in np.argsort(priorities)[::-1]]
        
        return sorted_indices
    
    @classmethod
    def predict_with_partial_data(
        cls,
        answers: Dict[int, int],
        allowed_categories: Optional[List[int]] = None,
    ) -> Dict:
        """
        Make prediction with partial survey data.
        
        Args:
            answers: Dict mapping question index to answer value
            
        Returns:
            Dict with prediction results and metadata
        """
        allowed_question_indices = cls._get_allowed_question_indices(allowed_categories)
        answers = {
            int(idx): int(value)
            for idx, value in answers.items()
            if int(idx) in allowed_question_indices
        }

        # Fill unanswered values with neutral defaults so "not asked yet"
        # does not behave like a strong dislike or zero ability.
        features = np.concatenate([
            np.full(96, cls.DEFAULT_INTEREST_VALUE, dtype=np.float32),
            np.full(160, cls.DEFAULT_SKILL_VALUE, dtype=np.float32),
        ])
        for idx, value in answers.items():
            if 0 <= idx < 256:
                features[idx] = value
        
        # Get prediction with probabilities
        model = MajorRecommender.get_model()
        if model is None:
            return {
                'error': 'Model not loaded',
                'should_continue': False
            }
        
        try:
            # Reshape for model
            features_2d = features.reshape(1, -1)
            
            # Get probabilities and blend them with direct answer signals so
            # the adaptive survey stays sensible even with partial evidence.
            raw_probabilities = model.predict_proba(features_2d)[0]
            probabilities = cls._blend_probabilities_with_answer_signals(
                raw_probabilities,
                answers,
            )
            
            # Get top prediction
            major_id = np.argmax(probabilities)
            confidence = probabilities[major_id]
            
            # Get top 3
            top_3_indices = np.argsort(probabilities)[-3:][::-1]
            top_3 = [
                {
                    'major': MajorRecommender.get_major_name(idx),
                    'major_id': int(idx),
                    'confidence': float(probabilities[idx])
                }
                for idx in top_3_indices
            ]
            
            # Calculate uncertainty (entropy)
            # Higher entropy = more uncertain
            entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
            max_entropy = np.log(16)  # 16 majors
            uncertainty = entropy / max_entropy
            
            # XAI: Feature Importance extraction using TabNet's built-in explainability
            xai_explanations = []
            try:
                # explain_matrix gives importance for each feature for this specific prediction
                explain_matrix, _ = model.explain(features_2d)
                feature_importances = explain_matrix[0]
                
                # Get the top 5 most important features that influenced this decision
                # Only consider features the user actually answered (>0)
                valid_indices = [i for i in range(256) if features[i] > 0]
                if valid_indices:
                    # Sort valid indices by their importance
                    valid_indices.sort(key=lambda idx: feature_importances[idx], reverse=True)
                    top_features_idx = valid_indices[:5]
                    
                    for idx in top_features_idx:
                        importance = float(feature_importances[idx])
                        if importance < 1e-5: continue # Skip if basically 0 importance
                        
                        if idx < 96:
                            cat_id = idx // 6
                            feat_type = "ចំណាប់អារម្មណ៍ (Interest)"
                        else:
                            offset = idx - 96
                            cat_id = offset // 10
                            feat_type = "ជំនាញ (Skill)"
                            
                        cat_name = MajorRecommender.get_major_name(cat_id)
                        
                        from .question_mapper import get_question_info
                        q_info = get_question_info(int(idx))
                        
                        xai_explanations.append({
                            "feature_index": int(idx),
                            "type": feat_type,
                            "category": cat_name,
                            "question_text": q_info.get("text", ""),
                            "importance_score": importance,
                            "user_value": int(features[idx])
                        })
            except Exception as e:
                print(f"XAI Error: {e}")
                pass
            
            # Determine if we should continue asking questions
            questions_asked = len(answers)
            should_continue = cls._should_continue_asking(
                questions_asked,
                confidence,
                uncertainty,
                list(answers.keys()),
                allowed_categories=allowed_categories,
            )

            top_major_original = MajorRecommender.get_original_major_id(int(major_id))
            if should_continue and cls._has_signal_consensus_stop(
                answers,
                top_major_original,
                float(confidence),
            ):
                should_continue = False
            
            # Get next questions to ask if continuing
            next_questions = []
            if should_continue:
                next_questions = cls.get_question_priority(
                    list(answers.keys()), 
                    probabilities,
                    answers,
                    allowed_categories=allowed_categories,
                )[:10]  # Get top 10 next questions
            
            return {
                'major': MajorRecommender.get_major_name(major_id),
                'major_id': int(major_id),
                'confidence': float(confidence),
                'uncertainty': float(uncertainty),
                'top_3': top_3,
                'questions_asked': questions_asked,
                'should_continue': should_continue,
                'next_questions': next_questions,
                'stage': cls._get_current_stage(questions_asked, confidence),
                'probabilities': probabilities.tolist(),
                'xai_explanations': xai_explanations
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'should_continue': False
            }
    
    @classmethod
    def _should_continue_asking(cls, questions_asked: int, 
                               confidence: float, uncertainty: float,
                               answered_indices: list = None,
                               allowed_categories: Optional[List[int]] = None) -> bool:
        """
        Determine if we should continue asking questions.
        """
        # Stop if reached maximum
        if questions_asked >= cls.MAX_QUESTIONS:
            return False
            
        # Build broad evidence before trusting the model enough to stop.
        if questions_asked < cls.MIN_QUESTIONS_BEFORE_STOP:
            return True

        focus_categories = set(cls._get_focus_categories(allowed_categories))
        covered_categories = cls._get_categories_covered(answered_indices or [])
        interest_covered, skill_covered = cls._get_dimension_coverage(answered_indices or [])

        focus_category_coverage = len(covered_categories & focus_categories)
        focus_interest_coverage = len(interest_covered & focus_categories)
        focus_skill_coverage = len(skill_covered & focus_categories)

        min_category_coverage = min(len(focus_categories), 12)
        min_interest_coverage = min(len(focus_categories), 10)
        min_skill_coverage = min(len(focus_categories), 6)

        if focus_category_coverage < min_category_coverage:
            return True

        if focus_interest_coverage < min_interest_coverage:
            return True

        if focus_skill_coverage < min_skill_coverage:
            return True

        # Allow an earlier stop only when the signal is overwhelming.
        if questions_asked >= 28 and confidence >= cls.VERY_HIGH_CONFIDENCE_THRESHOLD:
            return False

        if (
            questions_asked >= 32 and
            confidence >= cls.HIGH_CONFIDENCE_THRESHOLD and
            uncertainty <= cls.LOW_UNCERTAINTY_THRESHOLD
        ):
            return False

        if questions_asked >= 40 and (
            confidence >= cls.CONFIDENCE_THRESHOLD or
            uncertainty <= cls.UNCERTAINTY_THRESHOLD
        ):
            return False

        if questions_asked >= cls.HARD_STOP_QUESTIONS:
            return False

        return True
    
    @classmethod
    def _get_categories_covered(cls, answered_indices: list) -> set:
        """
        Get set of major categories that have been asked about.
        Each major has questions in both ch1 (interests) and ch2 (skills).
        
        Returns:
            Set of category indices (0-15) that have been covered
        """
        categories = set()
        
        for idx in answered_indices:
            if idx < 96:
                # ch1 (interests): 16 categories × 6 questions
                category = idx // 6
            else:
                # ch2 (skills): 16 categories × 10 questions
                category = (idx - 96) // 10
            
            categories.add(category)
        
        return categories

    @classmethod
    def _get_dimension_coverage(cls, answered_indices: list) -> Tuple[set, set]:
        """Return covered categories for interests and skills separately."""
        interest_categories = set()
        skill_categories = set()

        for idx in answered_indices:
            if idx < 96:
                interest_categories.add(idx // 6)
            else:
                skill_categories.add((idx - 96) // 10)

        return interest_categories, skill_categories

    @classmethod
    def _get_category_answer_signals(cls, answers: Dict[int, int]) -> Dict[int, float]:
        """
        Estimate which categories the student is clearly leaning toward based on
        answered values, independent of the model's current prediction.
        """
        signals = {}
        counts = {}

        for idx, value in answers.items():
            if idx < 96:
                category = idx // 6
                normalized = max(
                    0.0,
                    (float(value) - cls.DEFAULT_INTEREST_VALUE) / (4.0 - cls.DEFAULT_INTEREST_VALUE),
                )
            else:
                category = (idx - 96) // 10
                normalized = max(
                    0.0,
                    (float(value) - cls.DEFAULT_SKILL_VALUE) / (3.0 - cls.DEFAULT_SKILL_VALUE),
                ) if value is not None else 0.0

            signals[category] = signals.get(category, 0.0) + normalized
            counts[category] = counts.get(category, 0) + 1

        return {
            category: signals[category] / counts[category]
            for category in signals
            if counts[category] > 0
        }

    @classmethod
    def _blend_probabilities_with_answer_signals(
        cls,
        model_probabilities: np.ndarray,
        answers: Dict[int, int],
    ) -> np.ndarray:
        """
        Blend model probabilities with direct questionnaire signals.
        This makes partial predictions more human-like before the model has
        seen enough of the full 256-feature profile.
        """
        if not answers:
            return model_probabilities

        answer_signals = cls._get_category_answer_signals(answers)
        if not answer_signals:
            return model_probabilities

        question_count = len(answers)
        if question_count < 16:
            model_weight = 0.15
            model_temperature = 0.25
        elif question_count < 24:
            model_weight = 0.25
            model_temperature = 0.35
        elif question_count < 32:
            model_weight = 0.45
            model_temperature = 0.50
        else:
            model_weight = 0.55
            model_temperature = 0.60

        signal_weight = 1.0 - model_weight
        softened_model = np.power(model_probabilities.astype(np.float64), model_temperature)
        softened_sum = softened_model.sum()
        if softened_sum > 0:
            softened_model /= softened_sum

        blended = softened_model.copy()
        signal_vector = np.zeros_like(blended)
        coverage_bonus = np.zeros_like(blended)
        interest_covered, skill_covered = cls._get_dimension_coverage(list(answers.keys()))

        for class_idx in range(len(blended)):
            original_major_id = MajorRecommender.get_original_major_id(int(class_idx))
            signal_vector[class_idx] = answer_signals.get(original_major_id, 0.0)
            if (
                original_major_id in interest_covered and
                original_major_id in skill_covered
            ):
                coverage_bonus[class_idx] = 0.05

        signal_sum = signal_vector.sum()
        if signal_sum > 0:
            signal_vector /= signal_sum

        blended = (
            blended * model_weight +
            signal_vector * signal_weight +
            coverage_bonus
        )

        blended_sum = blended.sum()
        if blended_sum <= 0:
            return model_probabilities

        return blended / blended_sum

    @classmethod
    def _get_focus_categories(cls, allowed_categories: Optional[List[int]] = None) -> List[int]:
        """
        Return the categories that are valid for the current survey scope.
        """
        allowed = cls._normalize_allowed_categories(allowed_categories)
        return cls._interleave_categories(allowed)

    @classmethod
    def _has_signal_consensus_stop(
        cls,
        answers: Dict[int, int],
        top_major_original: int,
        confidence: float,
    ) -> bool:
        """
        Stop when the partial survey has a clear, human-readable pattern:
        the leading category already has strong answer signals and both
        interests and skills have been sampled.
        """
        questions_asked = len(answers)
        if questions_asked < cls.MIN_QUESTIONS_BEFORE_STOP:
            return False

        if confidence < 0.30:
            return False

        answer_signals = cls._get_category_answer_signals(answers)
        if not answer_signals:
            return False

        top_signal_categories = [
            category for category, _ in sorted(
                answer_signals.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:2]
        ]

        if top_major_original not in top_signal_categories:
            return False

        interest_covered, skill_covered = cls._get_dimension_coverage(list(answers.keys()))
        if top_major_original not in interest_covered or top_major_original not in skill_covered:
            return False

        return True

    @staticmethod
    def _interleave_categories(categories: List[int]) -> List[int]:
        """Mix lower and higher IDs so early questions are more balanced."""
        if not categories:
            return []

        ordered = sorted(categories)
        midpoint = (len(ordered) + 1) // 2
        left = ordered[:midpoint]
        right = ordered[midpoint:]

        result = []
        for i in range(max(len(left), len(right))):
            if i < len(left):
                result.append(left[i])
            if i < len(right):
                result.append(right[i])
        return result
    
    @classmethod
    def _get_current_stage(cls, questions_asked: int, confidence: float = 0.0) -> str:
        """
        Determine current stage based on confidence level, not question count.
        More intelligent and adaptive!
        """
        if questions_asked < 8:
            return "profiling"
        if confidence >= 0.80 and questions_asked >= 16:
            return "refining"  # High confidence, just fine-tuning
        elif confidence >= 0.55 and questions_asked >= 10:
            return "narrowing"  # Medium confidence, narrowing down options
        else:
            return "profiling"  # Low confidence, still exploring
    
    @classmethod
    def get_explanation(cls, result: Dict, answers: Dict[int, int]) -> str:
        """
        Generate human-readable explanation of the recommendation.
        
        Args:
            result: Prediction result from predict_with_partial_data
            answers: Student's answers
            
        Returns:
            Explanation string
        """
        if 'error' in result:
            return "Unable to generate recommendation at this time."
        
        major = result['major']
        confidence = result['confidence']
        questions_asked = result['questions_asked']
        stage = result['stage']
        
        explanation_parts = []
        
        # Handling Uncertainty & Low Confidence
        if confidence < 0.40 and result['questions_asked'] > 15:
            explanation_parts.append(
                f"អ្នកមានចំណាប់អារម្មណ៍ និងសមត្ថភាពចម្រុះគ្នាខ្លាំងណាស់! ប៉ុន្តែជំនាញ **{major}** មានអាទិភាពខ្ពស់ជាងគេបន្តិច ({confidence*100:.0f}% confidence)។"
            )
            explanation_parts.append("ដោយសារអ្នកមានសមត្ថភាពច្រើនផ្នែកពេក ខ្ញុំសូមណែនាំឲ្យអ្នកពិចារណាលើការរៀនជំនាញពីរ (Double Major) ឬជំនាញដែលមានទំនាក់ទំនងគ្នា។")
        elif confidence >= 0.90:
            explanation_parts.append(
                f"ខ្ញុំមានទំនុកចិត្តខ្ពស់ ({confidence*100:.0f}%) ថាជំនាញ **{major}** គឺជាជម្រើសដ៏ល្អបំផុតសម្រាប់អ្នក!"
            )
        elif confidence >= 0.70:
            explanation_parts.append(
                f"ផ្អែកតាមចម្លើយរបស់អ្នក ជំនាញ **{major}** ហាក់ដូចជាជម្រើសដែលស័ក្តិសមខ្លាំង ({confidence*100:.0f}% confidence)។"
            )
        else:
            explanation_parts.append(
                f"ជំនាញ **{major}** ជាជម្រើសដែលស័ក្តិសមសម្រាប់អ្នក ({confidence*100:.0f}% confidence) "
                f"ទោះបីជាអ្នកបង្ហាញចំណាប់អារម្មណ៍លើផ្នែកផ្សេងទៀតខ្លះៗក៏ដោយ។"
            )
        
        # XAI Explanation (Why did I recommend this?)
        if 'xai_explanations' in result and result['xai_explanations']:
            explanation_parts.append("\n**ខាងក្រោមនេះជាមូលហេតុសំខាន់ៗដែលខ្ញុំណែនាំជំនាញនេះ:**")
            for xai in result['xai_explanations'][:3]:
                # Format: I recognized your strong Interest in [Category] because you answered highly to [Question]
                val_text = "ខ្ពស់" if xai['user_value'] >= 3 else "មធ្យម"
                explanation_parts.append(
                    f"- អ្នកមានការវាយតម្លៃកម្រិត{val_text} លើ: \"{xai['question_text']}\" "
                    f"({xai['type']} - ស៊ីគ្នាខ្លាំងនឹងជំនាញ {xai['category']})"
                )
        
        # Top 3 alternatives
        if len(result['top_3']) > 1:
            alternatives = ", ".join([
                f"**{item['major']}** ({item['confidence']*100:.0f}%)"
                for item in result['top_3'][1:]
            ])
            explanation_parts.append(f"\nជម្រើសផ្សេងទៀតដែលអ្នកគួរពិចារណា៖ {alternatives}")
        
        return "\n".join(explanation_parts)
    
    @classmethod
    def get_initial_questions(cls, allowed_categories: Optional[List[int]] = None) -> List[int]:
        """
        Get the initial set of questions to start the adaptive survey.
        Returns ALL 256 questions with interests FIRST, then skills.
        
        Strategy:
        1. Ask interest questions (ch1) covering all 16 categories
        2. Then ask skill questions (ch2) covering all 16 categories
        3. Within each chapter, prioritize by importance
        
        Returns:
            List of all 256 question indices, interests first
        """
        cls.initialize_importance_weights()
        
        category_order = cls._get_focus_categories(allowed_categories)
        result = []
        seen = set()

        # Phase 1: one interest question from every category for broad profiling.
        for category in category_order:
            idx = category * 6
            result.append(idx)
            seen.add(idx)

        # Phase 2: one skill question from every category to balance the signal.
        for category in category_order:
            idx = 96 + category * 10
            result.append(idx)
            seen.add(idx)

        # Phase 3: remaining questions follow adaptive priority heuristics.
        remaining = cls.get_question_priority(result, allowed_categories=allowed_categories)
        for idx in remaining:
            if idx not in seen:
                result.append(idx)
                seen.add(idx)
        
        expected_count = len(cls._get_allowed_question_indices(allowed_categories))
        assert len(result) == expected_count, f"Expected {expected_count} questions, got {len(result)}"
        assert len(set(result)) == expected_count, f"Expected {expected_count} unique questions, got {len(set(result))}"
        
        return result

    @classmethod
    def _normalize_allowed_categories(
        cls,
        allowed_categories: Optional[List[int]] = None,
    ) -> List[int]:
        """Return the valid category IDs for the current survey scope."""
        if allowed_categories is not None:
            normalized = sorted({int(idx) for idx in allowed_categories if 0 <= int(idx) < 16})
            if normalized:
                return normalized

        enabled = [
            idx for idx in MajorRecommender.get_enabled_majors()
            if 0 <= idx < 16
        ]
        return enabled or list(range(16))

    @classmethod
    def _get_allowed_question_indices(
        cls,
        allowed_categories: Optional[List[int]] = None,
    ) -> List[int]:
        """Return all question indices for the allowed major categories only."""
        indices = []
        for category in cls._normalize_allowed_categories(allowed_categories):
            indices.extend(range(category * 6, category * 6 + 6))
            skill_start = 96 + category * 10
            indices.extend(range(skill_start, skill_start + 10))
        return indices


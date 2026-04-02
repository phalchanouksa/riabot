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
    MIN_QUESTIONS_BEFORE_STOP = 12  # Grade 12 guidance should converge earlier
    DEFAULT_TARGET_STOP_QUESTIONS = 24  # Typical adaptive finish point
    LOW_INTEREST_STOP_QUESTIONS = 20  # Flat low-interest profiles should not drag on
    HARD_STOP_QUESTIONS = 28  # Absolute cap so the survey never feels endless
    CONFIDENCE_THRESHOLD = 0.75  # Stop if confidence exceeds this
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    VERY_HIGH_CONFIDENCE_THRESHOLD = 0.92
    UNCERTAINTY_THRESHOLD = 0.15  # Stop if uncertainty below this (after some questions)
    LOW_UNCERTAINTY_THRESHOLD = 0.12
    MIN_CONFIDENCE_FOR_FINAL = 0.55
    MIN_MARGIN_FOR_FINAL = 0.08
    MIN_SIGNAL_FOR_FINAL = 0.14
    MIN_PROFILE_CLARITY_FOR_STOP = 0.56
    UNCLEAR_PROFILE_CLARITY_THRESHOLD = 0.48
    MIN_PREFERENCE_STRENGTH_FOR_FINAL = 0.20
    MIN_PREFERENCE_MARGIN_FOR_FINAL = 0.08
    DEFAULT_INTEREST_VALUE = 2.5
    DEFAULT_SKILL_VALUE = 1.5
    INTEREST_SIGNAL_WEIGHT = 0.75
    SKILL_SIGNAL_WEIGHT = 0.25
    SKILL_MODEL_INFLUENCE = 0.25
    TARGET_SKILL_RATIO = 0.25
    
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
        weights[:96] *= 1.8
        weights[96:] *= 0.55
        
        # Boost importance of skill questions (ch2) over interest questions (ch1)
        # ch1: indices 0-95 (16 categories × 6 questions)
        # ch2: indices 96-255 (16 categories × 10 questions)
        weights[96:] *= 1.0
        
        # Boost specific high-impact questions for each major
        # These are typically the first few questions in each category
        for category_idx in range(16):
            # First 2 interest questions per category (most defining)
            ch1_start = category_idx * 6
            weights[ch1_start:ch1_start + 3] *= 2.2
            
            # First 3 skill questions per category (most practical)
            ch2_start = 96 + (category_idx * 10)
            weights[ch2_start:ch2_start + 2] *= 1.1
        
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
        
        answered_indices = [int(idx) for idx in answered_indices]

        # Base priority from importance weights
        priorities = cls.QUESTION_IMPORTANCE[unanswered].copy()
        rng = np.random.default_rng()
        focus_categories = set(cls._get_focus_categories(allowed_categories))
        interest_covered, skill_covered = cls._get_dimension_coverage(answered_indices)
        interest_count, skill_count = cls._get_dimension_counts(answered_indices)
        interest_counts_by_category, skill_counts_by_category = cls._get_category_dimension_counts(answered_indices)
        fully_covered = interest_covered & skill_covered
        current_skill_ratio = skill_count / max(1, interest_count + skill_count)
        recent_categories = cls._get_recent_categories(answered_indices, limit=4)
        
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
                priorities[ch1_mask] *= 2.0

                ch2_start = 96 + (major_id * 10)
                ch2_end = ch2_start + 10
                ch2_mask = (np.array(unanswered) >= ch2_start) & (np.array(unanswered) < ch2_end)
                priorities[ch2_mask] *= 1.05

        # Keep broad category coverage early so the survey does not lock in too soon.
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
                    priorities[pos] *= 3.2
                elif not is_interest and category not in skill_covered:
                    priorities[pos] *= 1.1
                elif category not in interest_covered or category not in skill_covered:
                    priorities[pos] *= 1.15

            if category in top_signal_categories:
                priorities[pos] *= 1.4 if is_interest else 1.05
                if not is_interest and category in interest_covered and category not in skill_covered:
                    priorities[pos] *= 1.1

            if is_interest:
                priorities[pos] *= 1.4
                if interest_counts_by_category.get(category, 0) == 0:
                    priorities[pos] *= 1.5
                if category in recent_categories:
                    priorities[pos] *= 0.85
            else:
                priorities[pos] *= 0.45
                if interest_count < min(len(focus_categories), 10):
                    priorities[pos] *= 0.20
                if current_skill_ratio >= cls.TARGET_SKILL_RATIO:
                    priorities[pos] *= 0.25
                if skill_counts_by_category.get(category, 0) >= 1:
                    priorities[pos] *= 0.35
                if category in recent_categories:
                    priorities[pos] *= 0.55
        
        # Add a small amount of jitter so sessions do not feel identical while
        # still respecting the learned priority structure.
        priorities = priorities * (1.0 + rng.uniform(0.0, 0.08, size=len(priorities)))

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
                if idx < 96:
                    features[idx] = float(value)
                else:
                    features[idx] = cls.DEFAULT_SKILL_VALUE + (
                        (float(value) - cls.DEFAULT_SKILL_VALUE) * cls.SKILL_MODEL_INFLUENCE
                    )
        
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
            
            preference_scores = cls._get_category_preference_scores(answers)
            top_preference_major_original, top_preference_strength, top_preference_margin = (
                cls._get_top_preference_summary(preference_scores)
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
                valid_indices = [int(i) for i in answers.keys()]
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
                            "user_value": int(answers.get(idx, features[idx]))
                        })
            except Exception as e:
                print(f"XAI Error: {e}")
                pass
            
            # Determine if we should continue asking questions
            questions_asked = len(answers)
            top_margin = float(probabilities[top_3_indices[0]] - probabilities[top_3_indices[1]]) if len(top_3_indices) > 1 else float(confidence)
            answer_signals = cls._get_category_answer_signals(answers)
            top_major_original = MajorRecommender.get_original_major_id(int(major_id))
            top_signal_strength = float(answer_signals.get(top_major_original, 0.0))
            low_interest_profile = cls._is_low_interest_profile(answers)
            profile_clarity = cls._calculate_profile_clarity(
                confidence=float(confidence),
                top_margin=top_margin,
                top_signal_strength=top_signal_strength,
                top_preference_strength=top_preference_strength,
                top_preference_margin=top_preference_margin,
                answers=answers,
                top_major_original=top_major_original,
            )
            target_stop_questions = cls._get_target_stop_questions(
                confidence=float(confidence),
                uncertainty=float(uncertainty),
                top_signal_strength=top_signal_strength,
                top_preference_strength=top_preference_strength,
                top_preference_margin=top_preference_margin,
                profile_clarity=profile_clarity,
                low_interest_profile=bool(low_interest_profile),
            )
            should_continue = cls._should_continue_asking(
                questions_asked,
                confidence,
                uncertainty,
                list(answers.keys()),
                profile_clarity=profile_clarity,
                allowed_categories=allowed_categories,
                target_stop_questions=target_stop_questions,
            )

            if should_continue and cls._has_signal_consensus_stop(
                answers,
                top_major_original,
                float(confidence),
                top_margin,
                top_signal_strength,
                top_preference_major_original,
                top_preference_strength,
                top_preference_margin,
                profile_clarity,
            ):
                should_continue = False

            is_unclear_profile = cls._is_unclear_profile(
                questions_asked=questions_asked,
                confidence=float(confidence),
                top_margin=top_margin,
                top_signal_strength=top_signal_strength,
                top_preference_strength=top_preference_strength,
                top_preference_margin=top_preference_margin,
                profile_clarity=profile_clarity,
            )

            # If the profile is still weak, keep asking until its dynamic stop target.
            if should_continue is False and is_unclear_profile and questions_asked < target_stop_questions:
                should_continue = True
            
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
                'top_margin': top_margin,
                'top_signal_strength': top_signal_strength,
                'top_preference_major_id': int(top_preference_major_original) if top_preference_major_original is not None else None,
                'top_preference_strength': float(top_preference_strength),
                'top_preference_margin': float(top_preference_margin),
                'profile_clarity': profile_clarity,
                'target_stop_questions': int(target_stop_questions),
                'low_interest_profile': bool(low_interest_profile),
                'preference_scores': {
                    int(category): float(score)
                    for category, score in preference_scores.items()
                },
                'answer_signals': {
                    int(category): float(score)
                    for category, score in answer_signals.items()
                },
                'uncertainty': float(uncertainty),
                'top_3': top_3,
                'questions_asked': questions_asked,
                'should_continue': should_continue,
                'is_unclear_profile': bool(is_unclear_profile),
                'final_state': 'unclear' if (not should_continue and is_unclear_profile) else ('recommendation' if not should_continue else 'in_progress'),
                'next_questions': next_questions,
                'stage': cls._get_current_stage(questions_asked, confidence, profile_clarity),
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
                               profile_clarity: float = 0.0,
                               allowed_categories: Optional[List[int]] = None,
                               target_stop_questions: Optional[int] = None) -> bool:
        """
        Determine if we should continue asking questions.
        """
        # Stop if reached maximum
        if questions_asked >= cls.MAX_QUESTIONS:
            return False

        # Absolute hard stop must win over every other rule.
        if questions_asked >= cls.HARD_STOP_QUESTIONS:
            return False

        if target_stop_questions is None:
            target_stop_questions = cls.DEFAULT_TARGET_STOP_QUESTIONS
            
        # Build broad evidence before trusting the model enough to stop.
        if questions_asked < cls.MIN_QUESTIONS_BEFORE_STOP:
            return True

        focus_categories = set(cls._get_focus_categories(allowed_categories))
        covered_categories = cls._get_categories_covered(answered_indices or [])
        interest_covered, skill_covered = cls._get_dimension_coverage(answered_indices or [])

        focus_category_coverage = len(covered_categories & focus_categories)
        focus_interest_coverage = len(interest_covered & focus_categories)
        focus_skill_coverage = len(skill_covered & focus_categories)

        min_category_coverage = min(len(focus_categories), 10)
        min_interest_coverage = min(len(focus_categories), 10)
        min_skill_coverage = 0

        if focus_category_coverage < min_category_coverage:
            return True

        if focus_interest_coverage < min_interest_coverage:
            return True

        if focus_skill_coverage < min_skill_coverage:
            return True

        # Adaptive finish point: not every session should stop at the same question.
        if questions_asked >= target_stop_questions and (
            profile_clarity >= cls.UNCLEAR_PROFILE_CLARITY_THRESHOLD or
            questions_asked >= cls.HARD_STOP_QUESTIONS
        ):
            return False

        return True

    @classmethod
    def _get_target_stop_questions(
        cls,
        confidence: float,
        uncertainty: float,
        top_signal_strength: float,
        top_preference_strength: float,
        top_preference_margin: float,
        profile_clarity: float,
        low_interest_profile: bool,
    ) -> int:
        """
        Compute a variable finish target so the survey does not feel like it
        always ends at the exact same question count.
        """
        if low_interest_profile:
            return min(cls.LOW_INTEREST_STOP_QUESTIONS, cls.HARD_STOP_QUESTIONS)

        if (
            top_preference_strength >= 0.32 and
            top_preference_margin >= 0.14 and
            profile_clarity >= 0.66
        ):
            return 16

        if (
            top_preference_strength >= 0.26 and
            top_preference_margin >= 0.10 and
            profile_clarity >= 0.60
        ):
            return 18

        if (
            top_preference_strength >= cls.MIN_PREFERENCE_STRENGTH_FOR_FINAL and
            top_preference_margin >= cls.MIN_PREFERENCE_MARGIN_FOR_FINAL and
            profile_clarity >= cls.MIN_PROFILE_CLARITY_FOR_STOP
        ):
            return 20

        if (
            confidence >= cls.VERY_HIGH_CONFIDENCE_THRESHOLD and
            profile_clarity >= 0.70
        ):
            return 16

        if (
            confidence >= cls.HIGH_CONFIDENCE_THRESHOLD and
            uncertainty <= cls.LOW_UNCERTAINTY_THRESHOLD and
            profile_clarity >= 0.64
        ):
            return 18

        if (
            profile_clarity >= 0.60 and
            (confidence >= 0.72 or top_signal_strength >= 0.22 or top_preference_strength >= 0.18)
        ):
            return 20

        if (
            profile_clarity >= cls.MIN_PROFILE_CLARITY_FOR_STOP and
            (confidence >= 0.62 or top_signal_strength >= 0.16 or top_preference_strength >= 0.14)
        ):
            return 22

        if (
            profile_clarity >= 0.50 or
            confidence >= cls.MIN_CONFIDENCE_FOR_FINAL or
            top_signal_strength >= 0.12
        ):
            return cls.DEFAULT_TARGET_STOP_QUESTIONS

        return cls.HARD_STOP_QUESTIONS
    
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
    def _get_dimension_counts(cls, answered_indices: list) -> Tuple[int, int]:
        """Return how many interest and skill questions have been answered."""
        interest_count = sum(1 for idx in answered_indices if idx < 96)
        skill_count = sum(1 for idx in answered_indices if idx >= 96)
        return interest_count, skill_count

    @classmethod
    def _get_category_dimension_counts(cls, answered_indices: list) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Return answered counts per category for interests and skills."""
        interest_counts: Dict[int, int] = {}
        skill_counts: Dict[int, int] = {}

        for idx in answered_indices:
            if idx < 96:
                category = idx // 6
                interest_counts[category] = interest_counts.get(category, 0) + 1
            else:
                category = (idx - 96) // 10
                skill_counts[category] = skill_counts.get(category, 0) + 1

        return interest_counts, skill_counts

    @classmethod
    def _get_recent_categories(cls, answered_indices: list, limit: int = 3) -> List[int]:
        """Track the most recent categories so follow-ups feel less repetitive."""
        recent = []
        for idx in answered_indices[-limit:]:
            if idx < 96:
                recent.append(idx // 6)
            else:
                recent.append((idx - 96) // 10)
        return recent

    @classmethod
    def _get_category_answer_signals(cls, answers: Dict[int, int]) -> Dict[int, float]:
        """
        Estimate which categories the student is clearly leaning toward based on
        answered values, independent of the model's current prediction.
        """
        preferences = cls._get_category_preference_scores(answers)
        return {
            category: max(0.0, score)
            for category, score in preferences.items()
        }

    @classmethod
    def _get_category_preference_scores(cls, answers: Dict[int, int]) -> Dict[int, float]:
        """
        Build centered category preference scores in the range of roughly -1..1.
        Negative values mean dislike / low fit, positive values mean stronger fit.
        """
        interest_signals = {}
        interest_counts = {}
        skill_signals = {}
        skill_counts = {}

        for idx, value in answers.items():
            if idx < 96:
                category = idx // 6
                normalized = (float(value) - cls.DEFAULT_INTEREST_VALUE) / (4.0 - cls.DEFAULT_INTEREST_VALUE)
                interest_signals[category] = interest_signals.get(category, 0.0) + normalized
                interest_counts[category] = interest_counts.get(category, 0) + 1
            else:
                category = (idx - 96) // 10
                normalized = (
                    (float(value) - cls.DEFAULT_SKILL_VALUE) / (3.0 - cls.DEFAULT_SKILL_VALUE)
                ) if value is not None else 0.0
                skill_signals[category] = skill_signals.get(category, 0.0) + normalized
                skill_counts[category] = skill_counts.get(category, 0) + 1

        preferences = {}
        all_categories = set(interest_counts) | set(skill_counts)
        for category in all_categories:
            interest_score = (
                interest_signals.get(category, 0.0) / interest_counts[category]
                if interest_counts.get(category)
                else 0.0
            )
            skill_score = (
                skill_signals.get(category, 0.0) / skill_counts[category]
                if skill_counts.get(category)
                else 0.0
            )
            preferences[category] = (
                cls.INTEREST_SIGNAL_WEIGHT * interest_score +
                cls.SKILL_SIGNAL_WEIGHT * skill_score
            )

        return preferences

    @classmethod
    def _get_top_preference_summary(
        cls,
        preference_scores: Dict[int, float],
    ) -> Tuple[Optional[int], float, float]:
        """
        Return the strongest answer-pattern category plus its strength and lead
        over the second-best category.
        """
        if not preference_scores:
            return None, 0.0, 0.0

        ranked = sorted(
            ((int(category), float(score)) for category, score in preference_scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        top_major_original, top_strength = ranked[0]
        second_strength = ranked[1][1] if len(ranked) > 1 else 0.0
        return top_major_original, max(0.0, top_strength), max(0.0, top_strength - second_strength)

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

        preference_scores = cls._get_category_preference_scores(answers)
        if not preference_scores:
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
        preference_vector = np.zeros_like(blended, dtype=np.float64)
        coverage_bonus = np.zeros_like(blended)
        interest_covered, skill_covered = cls._get_dimension_coverage(list(answers.keys()))

        for class_idx in range(len(blended)):
            original_major_id = MajorRecommender.get_original_major_id(int(class_idx))
            preference_vector[class_idx] = preference_scores.get(original_major_id, 0.0)
            if original_major_id in interest_covered:
                coverage_bonus[class_idx] += 0.06
            if original_major_id in skill_covered:
                coverage_bonus[class_idx] += 0.02

        preference_logits = preference_vector * 3.0
        preference_logits -= np.max(preference_logits)
        preference_probs = np.exp(preference_logits)
        preference_sum = preference_probs.sum()
        if preference_sum > 0:
            preference_probs /= preference_sum
        else:
            preference_probs = softened_model.copy()

        blended = (
            blended * model_weight +
            preference_probs * signal_weight +
            coverage_bonus
        )

        blended_sum = blended.sum()
        if blended_sum <= 0:
            return model_probabilities

        return blended / blended_sum

    @classmethod
    def _is_low_interest_profile(cls, answers: Dict[int, int]) -> bool:
        """
        Detect when the student is explicitly showing low interest across
        most of the asked interest questions.
        """
        interest_values = [float(value) for idx, value in answers.items() if idx < 96]
        if len(interest_values) < 8:
            return False

        avg_interest = sum(interest_values) / len(interest_values)
        dislike_ratio = sum(1 for value in interest_values if value <= 1.0) / len(interest_values)

        return avg_interest <= 1.6 and dislike_ratio >= 0.60

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
        top_margin: float,
        top_signal_strength: float,
        top_preference_major_original: Optional[int],
        top_preference_strength: float,
        top_preference_margin: float,
        profile_clarity: float,
    ) -> bool:
        """
        Stop when the partial survey has a clear, human-readable pattern:
        the leading category already has strong answer signals and both
        interests and skills have been sampled.
        """
        questions_asked = len(answers)
        if questions_asked < cls.MIN_QUESTIONS_BEFORE_STOP:
            return False

        answer_signals = cls._get_category_answer_signals(answers)
        if not answer_signals:
            return False

        if top_margin < cls.MIN_MARGIN_FOR_FINAL and top_preference_margin < cls.MIN_PREFERENCE_MARGIN_FOR_FINAL:
            return False

        if (
            top_signal_strength < cls.MIN_SIGNAL_FOR_FINAL and
            top_preference_strength < cls.MIN_PREFERENCE_STRENGTH_FOR_FINAL
        ):
            return False

        if profile_clarity < cls.MIN_PROFILE_CLARITY_FOR_STOP:
            return False

        top_signal_categories = [
            category for category, _ in sorted(
                answer_signals.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:2]
        ]

        if top_major_original not in top_signal_categories:
            if top_preference_major_original != top_major_original:
                return False

        if (
            confidence < cls.MIN_CONFIDENCE_FOR_FINAL and
            top_preference_strength < cls.MIN_PREFERENCE_STRENGTH_FOR_FINAL
        ):
            return False

        interest_covered, skill_covered = cls._get_dimension_coverage(list(answers.keys()))
        if top_major_original not in interest_covered:
            return False

        return True

    @classmethod
    def _calculate_profile_clarity(
        cls,
        confidence: float,
        top_margin: float,
        top_signal_strength: float,
        top_preference_strength: float,
        top_preference_margin: float,
        answers: Dict[int, int],
        top_major_original: int,
    ) -> float:
        """Estimate how decisive the current profile is on a 0-1 scale."""
        normalized_margin = min(1.0, max(0.0, top_margin) / 0.25)
        normalized_signal = min(1.0, max(0.0, top_signal_strength) / 0.35)
        normalized_preference = min(1.0, max(0.0, top_preference_strength) / 0.30)
        normalized_preference_margin = min(1.0, max(0.0, top_preference_margin) / 0.14)

        interest_covered, skill_covered = cls._get_dimension_coverage(list(answers.keys()))
        coverage_score = 0.0
        if top_major_original in interest_covered:
            coverage_score += 0.8
        if top_major_original in skill_covered:
            coverage_score += 0.2

        clarity = (
            0.18 * float(confidence) +
            0.12 * normalized_margin +
            0.20 * normalized_signal +
            0.24 * normalized_preference +
            0.16 * normalized_preference_margin +
            0.10 * coverage_score
        )
        return float(max(0.0, min(1.0, clarity)))

    @classmethod
    def _is_unclear_profile(
        cls,
        questions_asked: int,
        confidence: float,
        top_margin: float,
        top_signal_strength: float,
        top_preference_strength: float,
        top_preference_margin: float,
        profile_clarity: float,
    ) -> bool:
        """
        Decide whether the current profile is still too weak to present as a
        final recommendation.
        """
        if questions_asked < cls.MIN_QUESTIONS_BEFORE_STOP:
            return False

        if profile_clarity < cls.UNCLEAR_PROFILE_CLARITY_THRESHOLD:
            return True

        if (
            confidence < cls.MIN_CONFIDENCE_FOR_FINAL and
            top_preference_strength < cls.MIN_PREFERENCE_STRENGTH_FOR_FINAL
        ):
            return True

        if (
            top_margin < cls.MIN_MARGIN_FOR_FINAL and
            top_signal_strength < cls.MIN_SIGNAL_FOR_FINAL and
            top_preference_margin < cls.MIN_PREFERENCE_MARGIN_FOR_FINAL
        ):
            return True

        return False

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

    @staticmethod
    def _shuffle_in_priority_bands(items: List[int], rng: np.random.Generator, band_size: int = 4) -> List[int]:
        """
        Add controlled randomness without destroying the overall priority order.
        Nearby items are assumed to have similar priority, so we only shuffle
        within small contiguous bands.
        """
        shuffled = []
        for start in range(0, len(items), band_size):
            band = list(items[start:start + band_size])
            rng.shuffle(band)
            shuffled.extend(band)
        return shuffled
    
    @classmethod
    def _get_current_stage(cls, questions_asked: int, confidence: float = 0.0, profile_clarity: float = 0.0) -> str:
        """
        Determine current stage from both quantity and clarity, not only the
        raw model confidence.
        """
        if questions_asked < 8:
            return "profiling"
        if questions_asked >= 16 and (profile_clarity >= 0.60 or confidence >= 0.70):
            return "refining"
        if questions_asked >= 10 and (profile_clarity >= 0.42 or confidence >= 0.35):
            return "narrowing"
        return "profiling"
    
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
        rng = np.random.default_rng()
        category_order = cls._shuffle_in_priority_bands(category_order, rng, band_size=3)
        result = []
        seen = set()

        # Phase 1: one interest question from every category for broad profiling.
        for category in category_order:
            interest_candidates = list(range(category * 6, category * 6 + 6))
            idx = int(rng.choice(interest_candidates))
            result.append(idx)
            seen.add(idx)

        # Phase 2: finish the interest chapter first, then use skills as
        # selective tie-breakers later in the queue.
        remaining = cls.get_question_priority(result, allowed_categories=allowed_categories)
        remaining_interest = [idx for idx in remaining if idx < 96]
        remaining_skill = [idx for idx in remaining if idx >= 96]
        remaining_interest = cls._shuffle_in_priority_bands(remaining_interest, rng, band_size=5)
        remaining_skill = cls._shuffle_in_priority_bands(remaining_skill, rng, band_size=4)

        for idx in remaining_interest:
            if idx not in seen:
                result.append(idx)
                seen.add(idx)

        # Phase 3: add a small skill sample per category later in the queue.
        for category in category_order:
            skill_start = 96 + category * 10
            skill_candidates = list(range(skill_start, skill_start + min(2, 10)))
            idx = int(rng.choice(skill_candidates))
            if idx not in seen:
                result.append(idx)
                seen.add(idx)

        for idx in remaining_skill:
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


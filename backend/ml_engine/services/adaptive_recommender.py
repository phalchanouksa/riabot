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
    CONFIDENCE_THRESHOLD = 0.85  # Stop if confidence exceeds this
    UNCERTAINTY_THRESHOLD = 0.15  # Stop if uncertainty below this (after some questions)
    
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
    def get_question_priority(cls, answered_indices: List[int], 
                             current_probabilities: Optional[np.ndarray] = None) -> List[int]:
        """
        Get prioritized list of questions to ask next.
        
        Args:
            answered_indices: List of question indices already answered
            current_probabilities: Current prediction probabilities for each major
            
        Returns:
            List of question indices, sorted by priority (highest first)
        """
        cls.initialize_importance_weights()
        
        # Get unanswered questions
        all_indices = set(range(256))
        answered_set = set(answered_indices)
        unanswered = list(all_indices - answered_set)
        
        # Base priority from importance weights
        priorities = cls.QUESTION_IMPORTANCE[unanswered].copy()
        
        # If we have current probabilities, boost questions for top uncertain majors
        if current_probabilities is not None:
            # Get top 3 majors
            top_3_majors = np.argsort(current_probabilities)[-3:][::-1]
            
            # Boost questions related to these majors
            for major_id in top_3_majors:
                # ch1 questions for this major
                ch1_start = major_id * 6
                ch1_end = ch1_start + 6
                ch1_mask = (np.array(unanswered) >= ch1_start) & (np.array(unanswered) < ch1_end)
                priorities[ch1_mask] *= 1.5
                
                # ch2 questions for this major
                ch2_start = 96 + (major_id * 10)
                ch2_end = ch2_start + 10
                ch2_mask = (np.array(unanswered) >= ch2_start) & (np.array(unanswered) < ch2_end)
                priorities[ch2_mask] *= 2.0
        
        # Sort by priority (descending)
        sorted_indices = [unanswered[i] for i in np.argsort(priorities)[::-1]]
        
        return sorted_indices
    
    @classmethod
    def predict_with_partial_data(cls, answers: Dict[int, int]) -> Dict:
        """
        Make prediction with partial survey data.
        
        Args:
            answers: Dict mapping question index to answer value
            
        Returns:
            Dict with prediction results and metadata
        """
        # Build feature array (unanswered questions = 0)
        features = np.zeros(256, dtype=int)
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
            
            # Get probabilities
            probabilities = model.predict_proba(features_2d)[0]
            
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
            
            # Determine if we should continue asking questions
            questions_asked = len(answers)
            should_continue = cls._should_continue_asking(
                questions_asked, confidence, uncertainty, list(answers.keys())
            )
            
            # Get next questions to ask if continuing
            next_questions = []
            if should_continue:
                next_questions = cls.get_question_priority(
                    list(answers.keys()), 
                    probabilities
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
                'probabilities': probabilities.tolist()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'should_continue': False
            }
    
    @classmethod
    def _should_continue_asking(cls, questions_asked: int, 
                               confidence: float, uncertainty: float,
                               answered_indices: list = None) -> bool:
        """
        Determine if we should continue asking questions.
        """
        # Stop if reached maximum
        if questions_asked >= cls.MAX_QUESTIONS:
            return False
            
        # We enforce a minimum of 15 questions before we trust the confidence
        if questions_asked < 15:
            return True
            
        # Stop if very confident (at least 95%)
        # Note: threshold is strict since we only asked 15+ questions
        if confidence >= 0.95:
            return False
        
        # Stop if uncertainty is very low (model is sure)
        # Require at least 20 questions to avoid stopping too early
        if uncertainty < cls.UNCERTAINTY_THRESHOLD and questions_asked >= 20:
            return False
        
        # Continue otherwise
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
    def _get_current_stage(cls, questions_asked: int, confidence: float = 0.0) -> str:
        """
        Determine current stage based on confidence level, not question count.
        More intelligent and adaptive!
        """
        # Stage based on confidence, not arbitrary question counts
        if confidence >= 0.75:
            return "refining"  # High confidence, just fine-tuning
        elif confidence >= 0.50:
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
        
        # Build explanation
        explanation_parts = []
        
        # Confidence statement
        if confidence >= 0.90:
            explanation_parts.append(
                f"I'm very confident ({confidence*100:.0f}%) that **{major}** is an excellent fit for you!"
            )
        elif confidence >= 0.80:
            explanation_parts.append(
                f"Based on your answers, **{major}** appears to be a strong match ({confidence*100:.0f}% confidence)."
            )
        else:
            explanation_parts.append(
                f"**{major}** seems like a good fit ({confidence*100:.0f}% confidence), "
                f"though I'd like to ask a few more questions to be more certain."
            )
        
        # Stage information
        stage_messages = {
            'profiling': "We're in the initial profiling stage, getting a broad sense of your interests and skills.",
            'narrowing': "I'm narrowing down the options based on your strongest areas.",
            'refining': "We're in the final refinement stage, fine-tuning the recommendation."
        }
        explanation_parts.append(stage_messages.get(stage, ""))
        
        # Top 3 alternatives
        if len(result['top_3']) > 1:
            alternatives = ", ".join([
                f"{item['major']} ({item['confidence']*100:.0f}%)"
                for item in result['top_3'][1:]
            ])
            explanation_parts.append(f"\nOther strong options: {alternatives}")
        
        return " ".join(explanation_parts)
    
    @classmethod
    def get_initial_questions(cls) -> List[int]:
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
        
        import random
        
        # Separate into chapters
        ch1_indices = list(range(0, 96))  # Interests: 96 questions
        ch2_indices = list(range(96, 256))  # Skills: 160 questions
        
        # Sort each chapter by importance
        ch1_sorted = sorted(ch1_indices, key=lambda x: cls.QUESTION_IMPORTANCE[x], reverse=True)
        ch2_sorted = sorted(ch2_indices, key=lambda x: cls.QUESTION_IMPORTANCE[x], reverse=True)
        
        # Strategy: Ask interests first (all categories), then skills (all categories)
        # This ensures natural flow: "What do you like?" → "What can you do?"
        
        result = []
        
        # Phase 1: Interest questions (ch1) - randomize top ones for variety
        if len(ch1_sorted) >= 20:
            # Randomize top 20 to avoid robotic feel
            top_interests = ch1_sorted[:20]
            random.shuffle(top_interests)
            result.extend(top_interests)
            result.extend(ch1_sorted[20:])  # Rest in priority order
        else:
            result.extend(ch1_sorted)
        
        # Phase 2: Skill questions (ch2) - randomize top ones for variety
        if len(ch2_sorted) >= 30:
            # Randomize top 30 to avoid robotic feel
            top_skills = ch2_sorted[:30]
            random.shuffle(top_skills)
            result.extend(top_skills)
            result.extend(ch2_sorted[30:])  # Rest in priority order
        else:
            result.extend(ch2_sorted)
        
        # Verify we have exactly 256
        assert len(result) == 256, f"Expected 256 questions, got {len(result)}"
        assert len(set(result)) == 256, f"Expected 256 unique questions, got {len(set(result))}"
        
        return result


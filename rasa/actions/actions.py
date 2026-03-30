"""
RiaBot Custom Actions for Rasa
===============================
These actions connect Rasa (dialogue controller) with:
1. TabNet ML Engine (major predictions) via Django API
2. Adaptive Recommender (smart question selection) via Django API
"""

import json
import logging
import os
import requests
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted, FollowupAction

logger = logging.getLogger(__name__)

# Django API base URL (set by docker-compose or defaults to localhost)
DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000/api")


# ============================================
# Helper Functions
# ============================================

def call_django_api(endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
    """Call Django ML API endpoint."""
    url = f"{DJANGO_API_URL}/ml/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Django API error {response.status_code}: {response.text}")
            return None
    except requests.ConnectionError:
        logger.error(f"Cannot connect to Django at {url}")
        return None
    except Exception as e:
        logger.error(f"Django API call failed: {e}")
        return None


def get_question_info(index: int) -> Optional[dict]:
    """Get question text and metadata from Django."""
    return call_django_api(f"question/{index}/")


def get_adaptive_prediction(answers: dict) -> Optional[dict]:
    """Get prediction with partial answers from Django."""
    return call_django_api("adaptive/predict/", method="POST", data={"answers": answers})


def get_initial_questions() -> Optional[dict]:
    """Get initial question order from Django."""
    return call_django_api("adaptive/start/")


def get_adaptive_explanation(answers: dict) -> Optional[dict]:
    """Get human-readable XAI explanation from Django."""
    return call_django_api("adaptive/explain/", method="POST", data={"answers": answers})


# ============================================
# ACTION: Start Survey
# ============================================
class ActionStartSurvey(Action):
    def name(self) -> Text:
        return "action_start_survey"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Get initial question order from adaptive recommender
        result = get_initial_questions()

        if result and "questions" in result:
            questions_queue = result["questions"]
        else:
            # Fallback: sequential order
            questions_queue = list(range(256))

        # Welcome message
        dispatcher.utter_message(response="utter_survey_welcome")

        return [
            SlotSet("survey_active", True),
            SlotSet("questions_queue", questions_queue),
            SlotSet("answers_collected", {}),
            SlotSet("questions_asked_count", 0),
            SlotSet("current_question_idx", questions_queue[0] if questions_queue else -1),
            SlotSet("survey_stage", "profiling"),
            SlotSet("prediction_confidence", 0.0),
            SlotSet("predicted_major", None),
            SlotSet("should_continue", True),
        ]


# ============================================
# ACTION: Ask Next Question
# ============================================
class ActionAskNextQuestion(Action):
    def name(self) -> Text:
        return "action_ask_next_question"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        survey_active = tracker.get_slot("survey_active")
        should_continue = tracker.get_slot("should_continue")
        questions_asked = int(tracker.get_slot("questions_asked_count") or 0)
        confidence = float(tracker.get_slot("prediction_confidence") or 0.0)



        if not survey_active or not should_continue:
            # Survey is done, show results instead
            return self._show_final_results(dispatcher, tracker)

        questions_queue = tracker.get_slot("questions_queue") or []
        questions_asked = int(tracker.get_slot("questions_asked_count") or 0)
        answers = tracker.get_slot("answers_collected") or {}

        if questions_asked >= len(questions_queue):
            return self._show_final_results(dispatcher, tracker)

        # Get the next question index
        question_idx = questions_queue[questions_asked]

        # Get question info from Django
        q_info = get_question_info(question_idx)

        if q_info and "text" in q_info:
            question_text = q_info["text"]
            
            if question_idx < 96:
                scale = "សូមវាយតម្លៃ ១-៤ (១=មិនចូលចិត្តសោះ, ៤=ចូលចិត្តខ្លាំង)"
                ui_buttons = [
                    {"title": "១", "payload": "1"},
                    {"title": "២", "payload": "2"},
                    {"title": "៣", "payload": "3"},
                    {"title": "៤", "payload": "4"}
                ]
            else:
                scale = "សូមវាយតម្លៃ ០-៣ (០=គ្មានជំនាញ, ៣=ជំនាញខ្លាំង)"
                ui_buttons = [
                    {"title": "០", "payload": "0"},
                    {"title": "១", "payload": "1"},
                    {"title": "២", "payload": "2"},
                    {"title": "៣", "payload": "3"}
                ]
                
            stage = tracker.get_slot("survey_stage") or "profiling"
            confidence = tracker.get_slot("prediction_confidence") or 0.0

            dispatcher.utter_message(
                response="utter_ask_question",
                question_num=questions_asked + 1,
                question_text=question_text,
                scale=scale,
                stage=stage.capitalize(),
                confidence=f"{confidence*100:.0f}",
                buttons=ui_buttons
            )
        else:
            # Fallback if API is down
            if question_idx < 96:
                scale = "សូមវាយតម្លៃ ១-៤ (១=មិនចូលចិត្តសោះ, ៤=ចូលចិត្តខ្លាំង)"
                ui_buttons = [
                    {"title": "១", "payload": "1"},
                    {"title": "២", "payload": "2"},
                    {"title": "៣", "payload": "3"},
                    {"title": "៤", "payload": "4"}
                ]
            else:
                scale = "សូមវាយតម្លៃ ០-៣ (០=គ្មានជំនាញ, ៣=ជំនាញខ្លាំង)"
                ui_buttons = [
                    {"title": "០", "payload": "0"},
                    {"title": "១", "payload": "1"},
                    {"title": "២", "payload": "2"},
                    {"title": "៣", "payload": "3"}
                ]

            dispatcher.utter_message(
                response="utter_ask_question_fallback",
                question_num=questions_asked + 1,
                question_idx=question_idx,
                scale=scale,
                buttons=ui_buttons
            )

        return [
            SlotSet("current_question_idx", question_idx),
        ]

# ============================================
# Mapping: ML Generic Majors -> Official University Programs
# ============================================
import time
_MAPPINGS_CACHE = {}
_LAST_FETCH = 0

_CAREER_CACHE = {}
_LAST_CAREER_FETCH = 0

def get_official_majors(generic_major_name: str) -> str:
    global _MAPPINGS_CACHE, _LAST_FETCH
    
    # Refresh cache every 60 seconds
    if time.time() - _LAST_FETCH > 60:
        res = call_django_api("mappings/")
        if res and "mappings" in res:
            _MAPPINGS_CACHE = res["mappings"]
        _LAST_FETCH = time.time()

    mapped_list = _MAPPINGS_CACHE.get(generic_major_name, [])
    if not mapped_list:
        return ""
        
    result_str = "\n   *University Programs & Career Paths:*"
    for item in mapped_list:
        name = item.get("name", "Unknown Program")
        careers = item.get("careers", [])
        
        result_str += f"\n   🔹 {name}"
        if careers:
            result_str += f" (Careers: {', '.join(careers)})"
            
    return result_str

    def _show_final_results(self, dispatcher, tracker):
        """Helper to transition to results when survey is complete."""
        answers = tracker.get_slot("answers_collected") or {}

        if not answers:
            dispatcher.utter_message(response="utter_no_answers")
            return [SlotSet("survey_active", False)]

        # Get final prediction AND explanation
        explanation_result = get_adaptive_explanation(answers)

        if explanation_result and "result" in explanation_result:
            result = explanation_result["result"]
            explanation_text = explanation_result.get("explanation", "")
            
            major = result["major"]
            confidence = result["confidence"]
            top_3 = result.get("top_3", [])

            # Add structured results
            results_summary = ""
            for i, m in enumerate(top_3):
                rank_major = m.get('major', 'Unknown')
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                
                official_list = get_official_majors(rank_major)
                
                results_summary += f"\n{medal} **{rank_major}** - {m.get('confidence', 0)*100:.0f}%{official_list}"

            dispatcher.utter_message(
                response="utter_survey_results",
                num_answers=len(answers),
                results_summary=results_summary,
                explanation=explanation_text
            )
            
            # Generate Radar Chart Data
            radar_data = []
            categories = [
                "Agriculture", "Architecture", "Arts", "Business", "Education", "Finance",
                "Government", "Health", "Hospitality", "Human Services", "IT", "Law",
                "Manufacturing", "Sales", "Science", "Transport"
            ]
            for i in range(16):
                int_sum = sum(answers.get(str(i * 6 + j), answers.get(i * 6 + j, 0)) for j in range(6))
                skill_sum = sum(answers.get(str(96 + i * 10 + j), answers.get(96 + i * 10 + j, 0)) for j in range(10))
                
                radar_data.append({
                    "category": categories[i],
                    "interest": round((int_sum / 18) * 100), # 6 questions * 3 points max
                    "skill": round((skill_sum / 30) * 100), # 10 questions * 3 points max
                })
                
            dispatcher.utter_message(custom={
                "type": "radar_chart", 
                "data": radar_data
            })


            return [
                SlotSet("survey_active", False),
                SlotSet("should_continue", False),
                SlotSet("survey_stage", "complete"),
                SlotSet("predicted_major", major),
                SlotSet("prediction_confidence", confidence),
            ]
        else:
            dispatcher.utter_message(response="utter_ml_error")
            return [SlotSet("survey_active", False)]


# ============================================
# ACTION: Process Answer
# ============================================
class ActionProcessAnswer(Action):
    def name(self) -> Text:
        return "action_process_answer"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        survey_active = tracker.get_slot("survey_active")
        if not survey_active:
            dispatcher.utter_message(response="utter_no_survey_active")
            return []

        # Extract the answer value
        answer_value = tracker.get_slot("answer_value")

        if answer_value is None:
            # Try to extract from the latest message text
            latest_message = tracker.latest_message.get("text", "").strip()
            try:
                answer_value = int(latest_message)
            except (ValueError, TypeError):
                dispatcher.utter_message(response="utter_invalid_answer_number")
                return []

        answer_value = int(answer_value)
        current_idx = int(tracker.get_slot("current_question_idx") or 0)

        # Validate the answer range
        if current_idx < 96:
            # Interest question: scale 1-4
            if not 1 <= answer_value <= 4:
                dispatcher.utter_message(response="utter_invalid_answer_interest")
                return []
        else:
            # Skill question: scale 0-3
            if not 0 <= answer_value <= 3:
                dispatcher.utter_message(response="utter_invalid_answer_skill")
                return []

        # Store the answer
        answers = tracker.get_slot("answers_collected") or {}
        answers[str(current_idx)] = answer_value

        questions_asked = int(tracker.get_slot("questions_asked_count") or 0) + 1

        # Get prediction with current answers (every 3 questions or after 16)
        should_predict = (questions_asked % 3 == 0) or (questions_asked >= 16)
        should_continue = True
        confidence = tracker.get_slot("prediction_confidence") or 0.0
        major = tracker.get_slot("predicted_major")
        stage = tracker.get_slot("survey_stage") or "profiling"
        next_questions = None

        if should_predict:
            result = get_adaptive_prediction(answers)

            if result and "major" in result:
                confidence = result["confidence"]
                major = result["major"]
                should_continue = result.get("should_continue", True)
                stage = result.get("stage", "profiling")
                next_questions = result.get("next_questions")

                # If adaptive recommender suggests new question order, update queue
                if next_questions and should_continue:
                    questions_queue = tracker.get_slot("questions_queue") or []
                    # Insert adaptive questions at the front of remaining queue
                    remaining = questions_queue[questions_asked:]
                    # Merge: adaptive first, then remaining (avoiding duplicates)
                    answered_set = set(answers.keys())
                    new_queue = questions_queue[:questions_asked]
                    added = set()
                    for q in next_questions:
                        if str(q) not in answered_set and q not in added:
                            new_queue.append(q)
                            added.add(q)
                    for q in remaining:
                        if q not in added and str(q) not in answered_set:
                            new_queue.append(q)
                            added.add(q)

                    return [
                        SlotSet("answers_collected", answers),
                        SlotSet("questions_asked_count", questions_asked),
                        SlotSet("prediction_confidence", confidence),
                        SlotSet("predicted_major", major),
                        SlotSet("should_continue", should_continue),
                        SlotSet("survey_stage", stage),
                        SlotSet("questions_queue", new_queue),
                        SlotSet("answer_value", None),
                        FollowupAction("action_ask_next_question"),
                    ]

        return [
            SlotSet("answers_collected", answers),
            SlotSet("questions_asked_count", questions_asked),
            SlotSet("prediction_confidence", confidence),
            SlotSet("predicted_major", major),
            SlotSet("should_continue", should_continue),
            SlotSet("survey_stage", stage),
            SlotSet("answer_value", None),
            FollowupAction("action_ask_next_question"),
        ]


# ============================================
# ACTION: Show Results
# ============================================
class ActionShowResults(Action):
    def name(self) -> Text:
        return "action_show_results"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        answers = tracker.get_slot("answers_collected") or {}

        if not answers:
            dispatcher.utter_message(response="utter_no_answers")
            return []

        explanation_result = get_adaptive_explanation(answers)

        if explanation_result and "result" in explanation_result:
            result = explanation_result["result"]
            explanation_text = explanation_result.get("explanation", "")
            
            major = result["major"]
            confidence = result["confidence"]
            top_3 = result.get("top_3", [])

            results_summary = ""
            for i, m in enumerate(top_3[:3]):
                rank_major = m.get('major', 'Unknown')
                medal = ["🥇", "🥈", "🥉"][i]
                official_list = get_official_majors(rank_major)
                results_summary += f"\n{medal} **{rank_major}** - {m.get('confidence', 0)*100:.0f}%{official_list}"

            dispatcher.utter_message(
                response="utter_survey_results_partial",
                major=major,
                confidence=f"{confidence*100:.0f}",
                num_answers=len(answers),
                results_summary=results_summary,
                explanation=explanation_text
            )

            return [
                SlotSet("predicted_major", major),
                SlotSet("prediction_confidence", confidence),
            ]
        else:
            dispatcher.utter_message(response="utter_ml_error")
            return []


# ============================================
# ACTION: Explain Recommendation
# ============================================
class ActionExplainRecommendation(Action):
    def name(self) -> Text:
        return "action_explain_recommendation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        answers = tracker.get_slot("answers_collected") or {}
        major = tracker.get_slot("predicted_major")

        if not major or not answers:
            dispatcher.utter_message(response="utter_no_recommendation_yet")
            return []

        result = get_adaptive_explanation(answers)

        if result and "explanation" in result:
            explanation_text = result["explanation"]
            
            # Use the exact text generated by our XAI backend
            dispatcher.utter_message(text=explanation_text)
            
            # Follow up if they have low confidence
            pred_data = result.get("result", {})
            if pred_data and pred_data.get("confidence", 1.0) < 0.60:
                dispatcher.utter_message(
                    text="Because your answers cover many different fields, I recommend talking to a human career counselor or exploring double-major options."
                )
        else:
            dispatcher.utter_message(response="utter_explain_error")

        return []


# ============================================
# ACTION: Fallback Chat (for out-of-scope / casual)
# ============================================
class ActionFallbackChat(Action):
    def name(self) -> Text:
        return "action_fallback_chat"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        survey_active = tracker.get_slot("survey_active")
        if survey_active:
            dispatcher.utter_message(response="utter_fallback_chat_active")
        else:
            dispatcher.utter_message(response="utter_fallback_chat")
        return []


# ============================================
# ACTION: Stop Survey
# ============================================
class ActionStopSurvey(Action):
    def name(self) -> Text:
        return "action_stop_survey"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        answers = tracker.get_slot("answers_collected") or {}

        if answers:
            result = get_adaptive_prediction(answers)
            if result and "major" in result:
                dispatcher.utter_message(
                    response="utter_survey_paused",
                    num_answers=len(answers),
                    major=result['major'],
                    confidence=f"{result['confidence']*100:.0f}"
                )
            else:
                dispatcher.utter_message(
                    response="utter_survey_paused_no_pred",
                    num_answers=len(answers)
                )
        else:
            dispatcher.utter_message(response="utter_survey_stopped_new")

        return [
            SlotSet("survey_active", False),
            SlotSet("should_continue", False),
        ]


# ============================================
# ACTION: Default Fallback
# ============================================
class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "").strip()

        # Check if this might be a survey answer (just a number)
        survey_active = tracker.get_slot("survey_active")
        if survey_active:
            try:
                val = int(user_message)
                if 0 <= val <= 4:
                    # This IS a survey answer that got misclassified as nlu_fallback.
                    # Set the answer_value slot and chain to process_answer + ask_next.
                    logger.info(f"Fallback intercepted survey answer: {val}")
                    return [
                        SlotSet("answer_value", val),
                        FollowupAction("action_process_answer"),
                    ]
            except (ValueError, TypeError):
                pass

        # Genuine fallback: user said something we don't understand
        dispatcher.utter_message(response="utter_fallback_rephrase")
        return [UserUtteranceReverted()]


"""
Custom actions for the simplified RiaBot flow.

Scope:
1. Start and continue the major recommendation survey
2. Show survey results from the Django backend
3. Keep fallbacks tightly bounded to university FAQ or survey start
"""

import logging
import os
from typing import Any, Dict, List, Optional, Text

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)

DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000/api")


def call_django_api(endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
    """Call the Django ML API."""
    url = f"{DJANGO_API_URL}/ml/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)

        if response.status_code == 200:
            return response.json()

        logger.error("Django API error %s: %s", response.status_code, response.text)
        return None
    except requests.ConnectionError:
        logger.error("Cannot connect to Django at %s", url)
        return None
    except Exception as exc:
        logger.error("Django API call failed: %s", exc)
        return None


def get_question_info(index: int) -> Optional[dict]:
    return call_django_api(f"question/{index}/")


def get_initial_questions() -> Optional[dict]:
    return call_django_api("adaptive/start/")


def get_adaptive_prediction(answers: dict) -> Optional[dict]:
    return call_django_api("adaptive/predict/", method="POST", data={"answers": answers})


def get_adaptive_explanation(answers: dict) -> Optional[dict]:
    return call_django_api("adaptive/explain/", method="POST", data={"answers": answers})


def get_question_scale(question_idx: int) -> tuple[str, List[Dict[str, str]]]:
    """Return the display scale and quick-reply buttons for a question."""
    if question_idx < 96:
        return (
            "សូមឆ្លើយជាលេខ 1-4 (1 = មិនចូលចិត្តសោះ, 4 = ចូលចិត្តខ្លាំង)",
            [
                {"title": "1", "payload": "1"},
                {"title": "2", "payload": "2"},
                {"title": "3", "payload": "3"},
                {"title": "4", "payload": "4"},
            ],
        )

    return (
        "សូមឆ្លើយជាលេខ 0-3 (0 = មិនទាន់មានជំនាញ, 3 = ជំនាញខ្លាំង)",
        [
            {"title": "0", "payload": "0"},
            {"title": "1", "payload": "1"},
            {"title": "2", "payload": "2"},
            {"title": "3", "payload": "3"},
        ],
    )


def build_results_summary(university_recommendations: List[dict]) -> str:
    lines = []
    for idx, rec in enumerate(university_recommendations[:3], start=1):
        rank_major = rec.get("generic_major", "Unknown")
        confidence = rec.get("confidence", 0) * 100
        lines.append(f"{idx}. **{rank_major}** - {confidence:.0f}%")
    return "\n" + "\n".join(lines) if lines else ""


class ActionStartSurvey(Action):
    def name(self) -> Text:
        return "action_start_survey"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        result = get_initial_questions()
        questions_queue = result["questions"] if result and "questions" in result else list(range(256))

        dispatcher.utter_message(response="utter_survey_welcome")

        return [
            SlotSet("survey_active", True),
            SlotSet("questions_queue", questions_queue),
            SlotSet("answers_collected", {}),
            SlotSet("questions_asked_count", 0),
            SlotSet("current_question_idx", questions_queue[0] if questions_queue else 0),
            SlotSet("survey_stage", "profiling"),
            SlotSet("prediction_confidence", 0.0),
            SlotSet("predicted_major", None),
            SlotSet("should_continue", True),
            SlotSet("last_processed_message_id", None),
        ]


class ActionAskNextQuestion(Action):
    def name(self) -> Text:
        return "action_ask_next_question"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        survey_active = tracker.get_slot("survey_active")
        should_continue = tracker.get_slot("should_continue")

        if not survey_active or not should_continue:
            return self._show_final_results(dispatcher, tracker)

        questions_queue = tracker.get_slot("questions_queue") or []
        questions_asked = int(tracker.get_slot("questions_asked_count") or 0)

        if questions_asked >= len(questions_queue):
            return self._show_final_results(dispatcher, tracker)

        question_idx = questions_queue[questions_asked]
        q_info = get_question_info(question_idx)
        scale, ui_buttons = get_question_scale(question_idx)

        if q_info and "text" in q_info:
            dispatcher.utter_message(
                response="utter_ask_question",
                question_num=questions_asked + 1,
                question_text=q_info["text"],
                scale=scale,
                stage=(tracker.get_slot("survey_stage") or "profiling").capitalize(),
                confidence=f"{float(tracker.get_slot('prediction_confidence') or 0.0) * 100:.0f}",
                buttons=ui_buttons,
            )
        else:
            dispatcher.utter_message(
                response="utter_ask_question_fallback",
                question_num=questions_asked + 1,
                question_idx=question_idx,
                scale=scale,
                buttons=ui_buttons,
            )

        return [SlotSet("current_question_idx", question_idx)]

    def _show_final_results(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
    ) -> List[Dict[Text, Any]]:
        answers = tracker.get_slot("answers_collected") or {}

        if not answers:
            dispatcher.utter_message(response="utter_no_answers")
            return [SlotSet("survey_active", False)]

        explanation_result = get_adaptive_explanation(answers)
        if not explanation_result or "result" not in explanation_result:
            dispatcher.utter_message(response="utter_ml_error")
            return [SlotSet("survey_active", False)]

        result = explanation_result["result"]
        explanation_text = explanation_result.get("explanation", "")
        major = result.get("major")
        confidence = result.get("confidence", 0.0)
        university_recommendations = result.get("university_recommendations", [])

        if not major or not university_recommendations:
            dispatcher.utter_message(response="utter_ml_error")
            return [SlotSet("survey_active", False)]

        dispatcher.utter_message(
            response="utter_survey_results",
            results_summary=build_results_summary(university_recommendations),
            explanation=explanation_text,
        )
        dispatcher.utter_message(
            custom={
                "type": "university_recommendations",
                "data": university_recommendations,
            }
        )

        return [
            SlotSet("survey_active", False),
            SlotSet("should_continue", False),
            SlotSet("survey_stage", "complete"),
            SlotSet("predicted_major", major),
            SlotSet("prediction_confidence", confidence),
        ]


class ActionProcessAnswer(Action):
    def name(self) -> Text:
        return "action_process_answer"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        if not tracker.get_slot("survey_active"):
            dispatcher.utter_message(response="utter_no_survey_active")
            return []

        latest_message = tracker.latest_message or {}
        latest_intent = (latest_message.get("intent") or {}).get("name")
        current_message_id = latest_message.get("message_id") or latest_message.get("text", "").strip()
        last_processed_message_id = tracker.get_slot("last_processed_message_id")

        # Guard against duplicate execution on the same user turn.
        if current_message_id and str(last_processed_message_id) == str(current_message_id):
            logger.info("Skipping duplicate answer processing for message_id=%s", current_message_id)
            return []

        answer_value = tracker.get_slot("answer_value")
        if answer_value is None:
            latest_text = latest_message.get("text", "").strip()
            khmer_digits = str.maketrans("០១២៣៤", "01234")
            try:
                answer_value = int(latest_text.translate(khmer_digits))
            except (ValueError, TypeError):
                dispatcher.utter_message(response="utter_invalid_answer_number")
                return []

        answer_value = int(answer_value)
        current_idx = int(tracker.get_slot("current_question_idx") or 0)

        if current_idx < 96:
            if not 1 <= answer_value <= 4:
                dispatcher.utter_message(response="utter_invalid_answer_interest")
                return []
        elif not 0 <= answer_value <= 3:
            dispatcher.utter_message(response="utter_invalid_answer_skill")
            return []

        answers = tracker.get_slot("answers_collected") or {}
        answers[str(current_idx)] = answer_value
        questions_asked = int(tracker.get_slot("questions_asked_count") or 0) + 1

        should_predict = (questions_asked % 3 == 0) or (questions_asked >= 16)
        needs_followup_question = latest_intent == "nlu_fallback"
        should_continue = True
        confidence = tracker.get_slot("prediction_confidence") or 0.0
        major = tracker.get_slot("predicted_major")
        stage = tracker.get_slot("survey_stage") or "profiling"

        if should_predict:
            result = get_adaptive_prediction(answers)
            if result and "major" in result:
                confidence = result["confidence"]
                major = result["major"]
                should_continue = result.get("should_continue", True)
                stage = result.get("stage", "profiling")
                next_questions = result.get("next_questions")

                if next_questions and should_continue and questions_asked >= 12:
                    questions_queue = tracker.get_slot("questions_queue") or []
                    remaining = questions_queue[questions_asked:]
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
                        SlotSet("last_processed_message_id", str(current_message_id)),
                    ] + ([FollowupAction("action_ask_next_question")] if needs_followup_question else [])

        return [
            SlotSet("answers_collected", answers),
            SlotSet("questions_asked_count", questions_asked),
            SlotSet("prediction_confidence", confidence),
            SlotSet("predicted_major", major),
            SlotSet("should_continue", should_continue),
            SlotSet("survey_stage", stage),
            SlotSet("answer_value", None),
            SlotSet("last_processed_message_id", str(current_message_id)),
        ] + ([FollowupAction("action_ask_next_question")] if needs_followup_question else [])


class ActionShowResults(Action):
    def name(self) -> Text:
        return "action_show_results"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        answers = tracker.get_slot("answers_collected") or {}

        if not answers:
            dispatcher.utter_message(response="utter_no_answers")
            return []

        explanation_result = get_adaptive_explanation(answers)
        if not explanation_result or "result" not in explanation_result:
            dispatcher.utter_message(response="utter_ml_error")
            return []

        result = explanation_result["result"]
        explanation_text = explanation_result.get("explanation", "")
        major = result.get("major")
        confidence = result.get("confidence", 0.0)
        university_recommendations = result.get("university_recommendations", [])

        if not major or not university_recommendations:
            dispatcher.utter_message(response="utter_ml_error")
            return []

        dispatcher.utter_message(
            response="utter_survey_results_partial",
            major=major,
            confidence=f"{confidence * 100:.0f}",
            results_summary=build_results_summary(university_recommendations),
            explanation=explanation_text,
        )
        dispatcher.utter_message(
            custom={
                "type": "university_recommendations",
                "data": university_recommendations,
            }
        )

        return [
            SlotSet("predicted_major", major),
            SlotSet("prediction_confidence", confidence),
        ]


class ActionStopSurvey(Action):
    def name(self) -> Text:
        return "action_stop_survey"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        if not tracker.get_slot("survey_active"):
            dispatcher.utter_message(response="utter_no_survey_active")
            return [
                SlotSet("questions_queue", []),
                SlotSet("answers_collected", {}),
                SlotSet("questions_asked_count", 0),
                SlotSet("current_question_idx", 0),
                SlotSet("prediction_confidence", 0.0),
                SlotSet("predicted_major", None),
                SlotSet("survey_stage", "profiling"),
                SlotSet("should_continue", True),
                SlotSet("answer_value", None),
                SlotSet("last_processed_message_id", None),
            ]

        answers = tracker.get_slot("answers_collected") or {}

        if answers:
            result = get_adaptive_prediction(answers)
            if result and "major" in result:
                dispatcher.utter_message(
                    response="utter_survey_paused",
                    major=result["major"],
                    confidence=f"{result['confidence'] * 100:.0f}",
                )
            else:
                dispatcher.utter_message(response="utter_survey_paused_no_pred")
        else:
            dispatcher.utter_message(response="utter_survey_stopped_new")

        return [
            SlotSet("survey_active", False),
            SlotSet("should_continue", False),
            SlotSet("answer_value", None),
            SlotSet("last_processed_message_id", None),
        ]


class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        user_message = tracker.latest_message.get("text", "").strip()
        normalized_message = user_message.lower()

        if tracker.get_slot("survey_active"):
            khmer_digits = str.maketrans("០១២៣៤", "01234")
            try:
                value = int(user_message.translate(khmer_digits))
                if 0 <= value <= 4:
                    logger.info("Fallback intercepted survey answer: %s", value)
                    return [
                        SlotSet("answer_value", value),
                        FollowupAction("action_process_answer"),
                    ]
            except (ValueError, TypeError):
                pass

        bot_name_hints = [
            "who are you",
            "what is your name",
            "what's your name",
            "your name",
            "bot name",
            "ឈ្មោះអ្វី",
            "ឈ្មោះអី",
            "អ្នកឈ្មោះអ្វី",
            "អ្នកជាអ្នកណា",
        ]
        if any(hint in normalized_message for hint in bot_name_hints):
            dispatcher.utter_message(response="utter_bot_name")
            return []

        major_guidance_hints = [
            "what major should i study",
            "which major should i choose",
            "which major fits me",
            "recommend a major",
            "help me choose a major",
            "គួររៀនជំនាញអ្វី",
            "គូររៀនជំនាញអ្វី",
            "គួរជ្រើសជំនាញអ្វី",
            "សមនឹងជំនាញអ្វី",
            "ណែនាំជំនាញ",
            "major ឲ្យខ្ញុំ",
            "major អ្វី",
        ]
        if any(hint in normalized_message for hint in major_guidance_hints):
            dispatcher.utter_message(response="utter_major_guidance")
            return []

        dispatcher.utter_message(response="utter_fallback_rephrase")
        return []

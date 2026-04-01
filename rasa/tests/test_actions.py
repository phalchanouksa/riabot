import os
import sys
from unittest.mock import patch

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.actions import ActionShowResults, build_results_summary


def test_build_results_summary_formats_top_three():
    recommendations = [
        {"generic_major": "IT", "confidence": 0.85},
        {"generic_major": "Business", "confidence": 0.60},
        {"generic_major": "Finance", "confidence": 0.45},
        {"generic_major": "Agriculture", "confidence": 0.40},
    ]

    result = build_results_summary(recommendations)

    assert "1. **IT** - 85%" in result
    assert "2. **Business** - 60%" in result
    assert "3. **Finance** - 45%" in result
    assert "Agriculture" not in result


@patch("actions.actions.get_adaptive_explanation")
def test_action_show_results(mock_get_explanation):
    mock_get_explanation.return_value = {
        "result": {
            "major": "IT",
            "confidence": 0.85,
            "university_recommendations": [
                {
                    "generic_major": "IT",
                    "confidence": 0.85,
                    "programs": [
                        {
                            "name": "Information Technology",
                            "careers": ["Software Developer"],
                        }
                    ],
                },
                {
                    "generic_major": "Business",
                    "confidence": 0.60,
                    "programs": [
                        {
                            "name": "Business Administration",
                            "careers": ["Business Analyst"],
                        }
                    ],
                },
                {
                    "generic_major": "Finance",
                    "confidence": 0.45,
                    "programs": [
                        {
                            "name": "Banking and Finance",
                            "careers": ["Financial Officer"],
                        }
                    ],
                },
            ],
        },
        "explanation": "Because your answers align with technology-focused study paths.",
    }

    dispatcher = CollectingDispatcher()
    tracker = Tracker(
        sender_id="test_user",
        slots={"answers_collected": {"1": 4, "2": 3, "3": 4}},
        latest_message={},
        events=[],
        paused=False,
        followup_action=None,
        active_loop=None,
        latest_action_name=None,
    )

    action = ActionShowResults()

    with patch.object(dispatcher, "utter_message") as mock_utter:
        events = action.run(dispatcher, tracker, domain={})

    assert len(events) == 2
    assert events[0] == SlotSet("predicted_major", "IT")
    assert events[1] == SlotSet("prediction_confidence", 0.85)

    assert mock_utter.call_count == 2

    first_call = mock_utter.call_args_list[0].kwargs
    assert first_call["response"] == "utter_survey_results_partial"
    assert "1. **IT** - 85%" in first_call["results_summary"]
    assert "2. **Business** - 60%" in first_call["results_summary"]
    assert "3. **Finance** - 45%" in first_call["results_summary"]

    second_call = mock_utter.call_args_list[1].kwargs
    assert second_call["custom"]["type"] == "university_recommendations"
    assert len(second_call["custom"]["data"]) == 3

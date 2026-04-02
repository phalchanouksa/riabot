import os
import json
import glob
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from .models import UniversityMajor
from .services.recommender import MajorRecommender, ALL_MAJOR_NAMES
from .services.data_processor import parse_json_to_flat_array, validate_csv_format
from .services.tabnet_trainer import start_training_thread, TRAINING_DATA_DIR, TrainingState
from .services.adaptive_recommender import AdaptiveRecommender
from .services.model_manager import ModelManager
from .services.question_mapper import get_question_info
from .services.major_config import get_major_config_for_ui, save_enabled_majors, get_enabled_majors


def _get_enabled_survey_category_ids():
    """Return original major IDs enabled for the questionnaire/model."""
    return sorted(
        int(mid) for mid in get_enabled_majors()
        if 0 <= int(mid) < 16
    )


def _get_allowed_university_category_ids():
    """Return original major IDs that are both enabled and mapped to AU programs."""
    enabled_major_ids = set(_get_enabled_survey_category_ids())
    name_to_id = {name: mid for mid, name in ALL_MAJOR_NAMES.items()}
    mapped_names = set(
        UniversityMajor.objects.values_list('ml_category', flat=True).distinct()
    )
    allowed_ids = sorted(
        mid for name, mid in name_to_id.items()
        if name in mapped_names and mid in enabled_major_ids
    )
    return allowed_ids


def _get_allowed_university_categories():
    """Only show categories that are both trained and mapped to AU programs."""
    return {
        ALL_MAJOR_NAMES[mid]
        for mid in _get_allowed_university_category_ids()
        if mid in ALL_MAJOR_NAMES
    }


def _question_category_from_index(question_idx):
    """Map a NEA question index back to its major category ID."""
    if question_idx < 96:
        return question_idx // 6
    return (question_idx - 96) // 10


def _filter_question_indices_for_survey(question_indices):
    """Keep only questions that belong to enabled trained categories."""
    allowed_ids = set(_get_enabled_survey_category_ids())
    return [
        int(question_idx)
        for question_idx in question_indices
        if _question_category_from_index(int(question_idx)) in allowed_ids
    ]


def _filter_answers_for_survey(answers):
    """Ignore stale answers from categories that should not be in the survey."""
    allowed_questions = set(_filter_question_indices_for_survey(range(256)))
    return {
        int(question_idx): int(value)
        for question_idx, value in answers.items()
        if int(question_idx) in allowed_questions
    }


def _build_university_recommendations(top_majors):
    categories = [item.get("major") for item in top_majors if item.get("major")]
    if not categories:
        return []

    programs_by_category = {}
    queryset = (
        UniversityMajor.objects
        .filter(ml_category__in=categories)
        .prefetch_related('career_paths')
        .order_by('ml_category', 'official_name')
    )

    for obj in queryset:
        programs_by_category.setdefault(obj.ml_category, []).append({
            "name": obj.official_name,
            "careers": list(obj.career_paths.values_list('job_title', flat=True)),
        })

    recommendations = []
    for item in top_majors:
        major_name = item.get("major")
        programs = programs_by_category.get(major_name, [])
        if not programs:
            continue
        recommendations.append({
            "generic_major": major_name,
            "confidence": item.get("confidence", 0.0),
            "programs": programs,
        })

    return recommendations


def _to_int_keyed_scores(scores):
    normalized = {}
    for key, value in (scores or {}).items():
        try:
            normalized[int(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_non_negative_scores(score_map):
    cleaned = {int(key): max(0.0, float(value)) for key, value in (score_map or {}).items()}
    total = sum(cleaned.values())
    if total <= 0:
        return {key: 0.0 for key in cleaned}
    return {key: value / total for key, value in cleaned.items()}


def _get_model_probability_by_original_major(result):
    probability_by_original_major = {}
    for class_idx, probability in enumerate(result.get('probabilities', []) or []):
        original_major_id = MajorRecommender.get_original_major_id(int(class_idx))
        probability_by_original_major[int(original_major_id)] = float(probability)
    return probability_by_original_major


def _build_exploratory_top_majors(result, max_items=3):
    """
    Build softer "directions to explore" from answer patterns first and model
    output second. This is more stable for limited-data deployments than using
    raw class probabilities directly.
    """
    candidate_major_ids = _get_allowed_university_category_ids()
    if not candidate_major_ids:
        return []

    preference_scores = _to_int_keyed_scores(result.get('preference_scores'))
    answer_signals = _to_int_keyed_scores(result.get('answer_signals'))
    model_probabilities = _get_model_probability_by_original_major(result)

    positive_preferences = {
        major_id: max(0.0, preference_scores.get(major_id, 0.0))
        for major_id in candidate_major_ids
    }
    normalized_preferences = _normalize_non_negative_scores(positive_preferences)

    positive_signals = {
        major_id: max(0.0, answer_signals.get(major_id, 0.0))
        for major_id in candidate_major_ids
    }
    normalized_signals = _normalize_non_negative_scores(positive_signals)

    normalized_model = _normalize_non_negative_scores({
        major_id: model_probabilities.get(major_id, 0.0)
        for major_id in candidate_major_ids
    })

    if any(value > 0 for value in normalized_preferences.values()):
        combined_scores = {
            major_id: (
                0.75 * normalized_preferences.get(major_id, 0.0) +
                0.15 * normalized_signals.get(major_id, 0.0) +
                0.10 * normalized_model.get(major_id, 0.0)
            )
            for major_id in candidate_major_ids
        }
    elif any(value > 0 for value in normalized_signals.values()):
        combined_scores = {
            major_id: (
                0.80 * normalized_signals.get(major_id, 0.0) +
                0.20 * normalized_model.get(major_id, 0.0)
            )
            for major_id in candidate_major_ids
        }
    else:
        combined_scores = normalized_model

    ranked_major_ids = sorted(
        candidate_major_ids,
        key=lambda major_id: combined_scores.get(major_id, 0.0),
        reverse=True,
    )

    top_majors = []
    for major_id in ranked_major_ids[:max_items]:
        major_name = ALL_MAJOR_NAMES.get(int(major_id))
        if not major_name:
            continue
        top_majors.append({
            'major': major_name,
            'major_id': int(major_id),
            'confidence': float(combined_scores.get(major_id, 0.0)),
        })

    return top_majors


def _filter_result_for_university(result):
    if not result or 'error' in result:
        return result

    allowed_categories = _get_allowed_university_categories()
    filtered_top_3 = [
        item for item in result.get('top_3', [])
        if item.get('major') in allowed_categories
    ]
    university_recommendations = _build_university_recommendations(filtered_top_3)

    # Keep only the categories that still have AU program mappings.
    allowed_result_categories = {
        item["generic_major"] for item in university_recommendations
    }
    filtered_top_3 = [
        item for item in filtered_top_3
        if item.get("major") in allowed_result_categories
    ][:3]

    exploratory_top_3 = _build_exploratory_top_majors(result, max_items=3)
    exploratory_university_recommendations = _build_university_recommendations(exploratory_top_3)
    allowed_exploratory_categories = {
        item["generic_major"] for item in exploratory_university_recommendations
    }
    exploratory_top_3 = [
        item for item in exploratory_top_3
        if item.get("major") in allowed_exploratory_categories
    ][:3]

    filtered_result = dict(result)
    filtered_result['top_3'] = filtered_top_3
    filtered_result['university_recommendations'] = university_recommendations[:3]
    filtered_result['soft_top_3'] = exploratory_top_3[:2] if exploratory_top_3 else filtered_top_3[:2]
    filtered_result['soft_university_recommendations'] = (
        exploratory_university_recommendations[:2]
        if exploratory_university_recommendations
        else university_recommendations[:2]
    )
    filtered_result['xai_explanations'] = [
        item for item in result.get('xai_explanations', [])
        if item.get('category') in allowed_result_categories
    ]
    filtered_result['next_questions'] = _filter_question_indices_for_survey(
        result.get('next_questions', [])
    )

    if filtered_result.get('final_state') == 'unclear':
        if filtered_result['soft_top_3']:
            top_result = filtered_result['soft_top_3'][0]
            filtered_result['top_3'] = filtered_result['soft_top_3']
            filtered_result['major'] = top_result.get('major')
            filtered_result['major_id'] = top_result.get('major_id')
            filtered_result['confidence'] = top_result.get('confidence', 0.0)
            filtered_result['university_recommendations'] = filtered_result['soft_university_recommendations']
            filtered_result['display_state'] = 'exploratory'
        else:
            filtered_result['major'] = None
            filtered_result['major_id'] = None
            filtered_result['confidence'] = 0.0
            filtered_result['university_recommendations'] = []
            filtered_result['display_state'] = 'unclear'
        return filtered_result

    if filtered_top_3:
        top_result = filtered_top_3[0]
        filtered_result['major'] = top_result.get('major')
        filtered_result['major_id'] = top_result.get('major_id')
        filtered_result['confidence'] = top_result.get('confidence', 0.0)
    else:
        filtered_result['major'] = None
        filtered_result['major_id'] = None
        filtered_result['confidence'] = 0.0
    filtered_result['display_state'] = 'final'

    return filtered_result


def _build_university_explanation(result):
    if result.get('final_state') == 'unclear':
        return (
            "លទ្ធផលបច្ចុប្បន្ននៅមិនទាន់ច្បាស់គ្រប់គ្រាន់ទេ។ "
            "ចម្លើយរបស់អ្នកមិនទាន់បង្ហាញទិសដៅច្បាស់ទៅកាន់មុខជំនាញណាមួយនៅឡើយ "
            "ដូច្នេះប្រព័ន្ធមិនទាន់សន្និដ្ឋានជាចុងក្រោយទេ។ "
            "សូមឆ្លើយបន្ថែម ឬធ្វើតេស្តម្តងទៀតដោយផ្អែកលើចំណាប់អារម្មណ៍ និងជំនាញពិតរបស់អ្នក។"
        )

    recommendations = result.get('university_recommendations', [])
    if not recommendations:
        return (
            "បច្ចុប្បន្នមិនទាន់មានមុខជំនាញដែលផ្គូផ្គងនឹងទិន្នន័យបណ្តុះបណ្តាល "
            "និងមាននៅសាកលវិទ្យាល័យអង្គរដែលអាចបង្ហាញបានទេ។"
        )

    top_result = recommendations[0]
    explanation = (
        f"ផ្អែកលើចម្លើយរបស់អ្នក ក្រុមជំនាញដែលសមស្របជាងគេគឺ "
        f"**{top_result['generic_major']}** "
        f"({top_result['confidence'] * 100:.0f}%)។ "
        "ខាងក្រោមនេះគឺជាមុខជំនាញដែលមានបង្រៀននៅសាកលវិទ្យាល័យអង្គរ "
        "និងអាជីពដែលពាក់ព័ន្ធ ដើម្បីឱ្យអ្នកពិចារណាបន្ត។"
    )

    if len(recommendations) > 1:
        alternatives = ", ".join(
            f"{item['generic_major']} ({item['confidence'] * 100:.0f}%)"
            for item in recommendations[1:3]
        )
        explanation += f" ជម្រើសបន្ថែមដែលគួរពិចារណា៖ {alternatives}។"

    return explanation

def _build_university_explanation(result):
    if result.get('final_state') == 'unclear':
        if result.get('low_interest_profile'):
            return (
                "លទ្ធផលបច្ចុប្បន្ននៅមិនទាន់អាចសន្និដ្ឋានជាចុងក្រោយបានទេ។ "
                "ចម្លើយរបស់អ្នកបង្ហាញថា អ្នកមិនសូវចាប់អារម្មណ៍លើមុខជំនាញភាគច្រើនដែលបានសួរនៅឡើយ "
                "ដូច្នេះប្រព័ន្ធមិនចង់បង្ខំផ្តល់លទ្ធផលដែលអាចមិនត្រឹមត្រូវទេ។ "
                "សូមធ្វើតេស្តម្តងទៀតដោយឆ្លើយតាមចំណាប់អារម្មណ៍ពិតរបស់អ្នក ឬស្វែងរកផ្នែកដែលអ្នកចូលចិត្តជាងគេជាមុនសិន។"
            )
        return (
            "លទ្ធផលបច្ចុប្បន្ននៅមិនទាន់ច្បាស់គ្រប់គ្រាន់ទេ។ "
            "ចម្លើយរបស់អ្នកនៅមិនទាន់បង្ហាញទិសដៅច្បាស់ទៅកាន់មុខជំនាញណាមួយនៅឡើយ "
            "ដូច្នេះប្រព័ន្ធមិនទាន់សន្និដ្ឋានជាចុងក្រោយទេ។ "
            "សូមឆ្លើយបន្ថែម ឬធ្វើតេស្តម្តងទៀតដោយផ្អែកលើចំណាប់អារម្មណ៍ពិតរបស់អ្នក។"
        )

    recommendations = result.get('university_recommendations', [])
    if not recommendations:
        return (
            "បច្ចុប្បន្នមិនទាន់មានមុខជំនាញដែលផ្គូផ្គងនឹងទិន្នន័យបណ្ដុះបណ្ដាល "
            "និងមាននៅសាកលវិទ្យាល័យអង្គរដែលអាចបង្ហាញបានទេ។"
        )

    top_result = recommendations[0]
    explanation = (
        f"ផ្អែកលើចម្លើយរបស់អ្នក ក្រុមជំនាញដែលសមស្របជាងគេគឺ "
        f"**{top_result['generic_major']}** "
        f"({top_result['confidence'] * 100:.0f}%)។ "
        "ខាងក្រោមនេះគឺជាមុខជំនាញដែលមានបង្រៀននៅសាកលវិទ្យាល័យអង្គរ "
        "និងអាជីពដែលពាក់ព័ន្ធ ដើម្បីឱ្យអ្នកពិចារណាបន្ត។"
    )

    if len(recommendations) > 1:
        alternatives = ", ".join(
            f"{item['generic_major']} ({item['confidence'] * 100:.0f}%)"
            for item in recommendations[1:3]
        )
        explanation += f" ជម្រើសបន្ថែមដែលគួរពិចារណា៖ {alternatives}។"

    return explanation


def _build_university_explanation(result):
    if result.get('final_state') == 'unclear':
        soft_recommendations = result.get('soft_university_recommendations', [])
        if soft_recommendations:
            top_result = soft_recommendations[0]
            explanation = (
                f"ផ្អែកលើចម្លើយរបស់អ្នក ទិសដៅដែលអ្នកអាចសាកស្វែងយល់មុនគេគឺ "
                f"**{top_result['generic_major']}** "
                f"({top_result['confidence'] * 100:.0f}%)។ "
                "ខាងក្រោមនេះគឺជាមុខជំនាញនៅសាកលវិទ្យាល័យអង្គរដែលអាចសមស្របសម្រាប់អ្នកឱ្យពិចារណាជាមុន។"
            )

            if len(soft_recommendations) > 1:
                alternatives = ", ".join(
                    f"{item['generic_major']} ({item['confidence'] * 100:.0f}%)"
                    for item in soft_recommendations[1:3]
                )
                explanation += f" ទិសដៅបន្ថែមដែលអាចសាកស្វែងយល់មាន៖ {alternatives}។"

            if result.get('low_interest_profile'):
                explanation += " ដោយសារចម្លើយរបស់អ្នកមានកម្រិតចាប់អារម្មណ៍ទាបលើមុខជំនាញជាច្រើន សូមយកវាជាទិសដៅសាកស្វែងយល់ មិនមែនជាការសន្និដ្ឋានចុងក្រោយទេ។"

            return explanation

        if result.get('low_interest_profile'):
            return (
                "ចម្លើយរបស់អ្នកបង្ហាញថា អ្នកមិនសូវចាប់អារម្មណ៍លើមុខជំនាញភាគច្រើនដែលបានសួរនៅឡើយ។ "
                "សូមធ្វើតេស្តម្តងទៀតដោយឆ្លើយតាមចំណាប់អារម្មណ៍ពិតរបស់អ្នក ដើម្បីឱ្យប្រព័ន្ធអាចណែនាំបានច្បាស់ជាងមុន។"
            )

        return (
            "ចម្លើយរបស់អ្នកនៅមិនទាន់បង្ហាញទិសដៅច្បាស់ទៅកាន់មុខជំនាញណាមួយនៅឡើយ។ "
            "សូមឆ្លើយបន្ថែម ឬធ្វើតេស្តម្តងទៀត ដើម្បីឱ្យប្រព័ន្ធអាចណែនាំបានច្បាស់ជាងមុន។"
        )

    recommendations = result.get('university_recommendations', [])
    if not recommendations:
        return (
            "បច្ចុប្បន្នមិនទាន់មានមុខជំនាញដែលផ្គូផ្គងនឹងទិន្នន័យបណ្ដុះបណ្ដាល "
            "និងមាននៅសាកលវិទ្យាល័យអង្គរដែលអាចបង្ហាញបានទេ។"
        )

    top_result = recommendations[0]
    explanation = (
        f"ផ្អែកលើចម្លើយរបស់អ្នក ក្រុមជំនាញដែលសមស្របជាងគេគឺ "
        f"**{top_result['generic_major']}** "
        f"({top_result['confidence'] * 100:.0f}%)។ "
        "ខាងក្រោមនេះគឺជាមុខជំនាញដែលមានបង្រៀននៅសាកលវិទ្យាល័យអង្គរ "
        "និងអាជីពដែលពាក់ព័ន្ធ ដើម្បីឱ្យអ្នកពិចារណាបន្ត។"
    )

    if len(recommendations) > 1:
        alternatives = ", ".join(
            f"{item['generic_major']} ({item['confidence'] * 100:.0f}%)"
            for item in recommendations[1:3]
        )
        explanation += f" ជម្រើសបន្ថែមដែលគួរពិចារណា៖ {alternatives}។"

    return explanation


@method_decorator(csrf_exempt, name='dispatch')
class TrainingStatusView(View):
    def get(self, request):
        state = TrainingState()
        return JsonResponse(state.to_dict())


@method_decorator(csrf_exempt, name='dispatch')
class RecommendationAPI(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            # Expecting the raw JSON structure from the frontend
            # e.g. {"ch1": [...], "ch2": [...]}
            
            features = parse_json_to_flat_array(data)
            major = MajorRecommender.recommend(features)
            
            if major:
                return JsonResponse({"major": major}, status=200)
            else:
                return JsonResponse({"error": "Model not loaded or prediction failed"}, status=503)
                
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class MLIndexView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return render(request, 'ml_engine/ml_index.html')


@method_decorator(csrf_exempt, name='dispatch')
class AdminRetrainView(View):
    # Only allow superusers to trigger retraining
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return render(request, 'ml_engine/retrain.html')

    def post(self, request):
        # CSV file is now optional - can train with only synthetic data
        if 'file' in request.FILES and request.FILES['file']:
            file = request.FILES['file']
            if not file.name.endswith('.csv'):
                return JsonResponse({"error": "File must be a CSV"}, status=400)
                
            # Validate CSV Format
            is_valid, error_msg = validate_csv_format(file)
            if not is_valid:
                 return JsonResponse({"error": error_msg}, status=400)

            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            filename = f"batch_{timestamp}.csv"
            file_path = os.path.join(TRAINING_DATA_DIR, filename)
            
            # Save file
            try:
                # Ensure directory exists
                if not os.path.exists(TRAINING_DATA_DIR):
                    os.makedirs(TRAINING_DATA_DIR)
                
                # Delete all existing CSV files for fresh upload approach
                existing_csvs = glob.glob(os.path.join(TRAINING_DATA_DIR, "*.csv"))
                for old_csv in existing_csvs:
                    try:
                        os.remove(old_csv)
                    except Exception as e:
                        print(f"Warning: Could not delete {old_csv}: {e}")
                    
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                        
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            filename = None
            
        try:
            # Get synthetic count from form data, default to 5000
            synthetic_count = int(request.POST.get('synthetic_count', 5000))
            
            # Get training hyperparameters
            max_epochs = int(request.POST.get('max_epochs', 20))
            patience = int(request.POST.get('patience', 5))
            batch_size = int(request.POST.get('batch_size', 256))
            
            # Get enabled majors from form data (comma-separated IDs)
            enabled_majors_raw = request.POST.get('enabled_majors', '')
            if enabled_majors_raw.strip():
                try:
                    enabled_majors = [int(x) for x in enabled_majors_raw.split(',') if x.strip()]
                    enabled_majors = sorted(set(m for m in enabled_majors if 0 <= m <= 15))
                except (ValueError, TypeError):
                    enabled_majors = None  # Fall back to saved config
            else:
                enabled_majors = None  # Use whatever is in saved config
            
            if enabled_majors is not None and len(enabled_majors) < 2:
                return JsonResponse({"error": "Please select at least 2 majors for training."}, status=400)
            
            # Trigger training
            result = start_training_thread(
                n_synthetic=synthetic_count,
                max_epochs=max_epochs,
                patience=patience,
                batch_size=batch_size,
                enabled_majors=enabled_majors
            )
            
            dispatch_method = result.get('dispatch', 'unknown') if result else 'skipped'
            message = f"Training started via {dispatch_method}. Model will update shortly."
            
            response_data = {
                "status": message,
                "dispatch": dispatch_method,
            }
            if result and result.get('task_id'):
                response_data["task_id"] = result["task_id"]
            if filename:
                response_data["file_saved"] = filename
            else:
                response_data["file_saved"] = "none (synthetic data only)"
                
            return JsonResponse(response_data, status=200)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AdminModelManagerView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return render(request, 'ml_engine/models.html')

@method_decorator(csrf_exempt, name='dispatch')
class TestModelView(View):
    """Public test interface for the AI model"""
    def get(self, request):
        return render(request, 'ml_engine/test_model.html')

@method_decorator(csrf_exempt, name='dispatch')
class ModelListView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        models = ModelManager.list_models()
        return JsonResponse({"models": models}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class DatasetListView(View):
    """List all training datasets"""
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        try:
            datasets = []
            if os.path.exists(TRAINING_DATA_DIR):
                for filename in os.listdir(TRAINING_DATA_DIR):
                    if filename.endswith('.csv'):
                        filepath = os.path.join(TRAINING_DATA_DIR, filename)
                        stat = os.stat(filepath)
                        
                        # Count rows in CSV
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                row_count = sum(1 for line in f) - 1  # Subtract header
                        except:
                            row_count = 0
                        
                        datasets.append({
                            'filename': filename,
                            'size': stat.st_size,
                            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'rows': row_count
                        })
            
            return JsonResponse({'datasets': datasets}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class DatasetDetailView(View):
    """Get details of a specific dataset"""
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request, filename):
        try:
            filepath = os.path.join(TRAINING_DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                return JsonResponse({'error': 'Dataset not found'}, status=404)
            
            stat = os.stat(filepath)
            
            # Read first few rows as preview
            import csv
            preview_rows = []
            headers = []
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    for i, row in enumerate(reader):
                        if i >= 10:  # First 10 rows
                            break
                        preview_rows.append(row)
            except Exception as e:
                preview_rows = []
            
            # Count total rows
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    row_count = sum(1 for line in f) - 1
            except:
                row_count = 0
            
            return JsonResponse({
                'filename': filename,
                'size': stat.st_size,
                'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'rows': row_count,
                'headers': headers,
                'preview': preview_rows
            }, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class DatasetDeleteView(View):
    """Delete a training dataset"""
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def delete(self, request, filename):
        try:
            filepath = os.path.join(TRAINING_DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                return JsonResponse({'error': 'Dataset not found'}, status=404)
            
            os.remove(filepath)
            return JsonResponse({'message': f'Dataset {filename} deleted successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ModelActionView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            model_id = data.get('model_id')
            
            if action == 'activate':
                ModelManager.activate_model(model_id)
                # Reload the recommender to use the new active model
                MajorRecommender.reload_model()
                return JsonResponse({"status": "success", "message": f"Model {model_id} activated"}, status=200)
                
            elif action == 'delete':
                ModelManager.delete_model(model_id)
                return JsonResponse({"status": "success", "message": f"Model {model_id} deleted"}, status=200)
                
            else:
                return JsonResponse({"error": "Invalid action"}, status=400)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



@method_decorator(csrf_exempt, name='dispatch')
class MajorConfigView(View):
    """GET the current major configuration (for the UI checkboxes).
       POST to save enabled majors without triggering training."""
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        majors = get_major_config_for_ui()
        return JsonResponse({"majors": majors}, status=200)

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request):
        try:
            data = json.loads(request.body)
            enabled_ids = data.get('enabled_majors', [])
            if not isinstance(enabled_ids, list):
                return JsonResponse({"error": "enabled_majors must be a list"}, status=400)
            if len(enabled_ids) < 2:
                return JsonResponse({"error": "Please select at least 2 majors."}, status=400)
            saved = save_enabled_majors(enabled_ids)
            return JsonResponse({"status": "saved", "config": saved}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AdaptiveStartView(View):
    """
    Get initial questions to start adaptive survey.
    Returns the most important questions for quick profiling.
    """
    def get(self, request):
        try:
            allowed_category_ids = _get_enabled_survey_category_ids()
            initial_questions = AdaptiveRecommender.get_initial_questions(
                allowed_categories=allowed_category_ids,
            )
            return JsonResponse({
                "questions": initial_questions,
                "count": len(initial_questions),
                "stage": "profiling",
                "message": "Start with these high-priority questions"
            }, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AdaptivePredictView(View):
    """
    Make prediction with partial survey data.
    Returns confidence, next questions, and whether to continue.
    
    POST body:
    {
        "answers": {
            "0": 4,
            "1": 3,
            "10": 5,
            ...
        }
    }
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})
            
            # Convert string keys to integers
            answers_int = _filter_answers_for_survey(answers)
            allowed_category_ids = _get_enabled_survey_category_ids()
            
            # Get prediction with adaptive logic
            result = AdaptiveRecommender.predict_with_partial_data(
                answers_int,
                allowed_categories=allowed_category_ids,
            )
            result = _filter_result_for_university(result)
            
            if 'error' in result:
                return JsonResponse(result, status=500)
            
            return JsonResponse(result, status=200)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AdaptiveExplainView(View):
    """
    Get human-readable explanation of recommendation.
    
    POST body:
    {
        "answers": {
            "0": 4,
            "1": 3,
            ...
        }
    }
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})
            
            # Convert string keys to integers
            answers_int = _filter_answers_for_survey(answers)
            allowed_category_ids = _get_enabled_survey_category_ids()
            
            # Get prediction
            result = AdaptiveRecommender.predict_with_partial_data(
                answers_int,
                allowed_categories=allowed_category_ids,
            )
            result = _filter_result_for_university(result)
            
            if 'error' in result:
                return JsonResponse(result, status=500)
            
            # Generate a university-specific explanation so the frontend only
            # talks about majors that are actually available at AU.
            explanation = _build_university_explanation(result)
            
            return JsonResponse({
                "explanation": explanation,
                "result": result
            }, status=200)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class QuestionTextView(View):
    """
    Get human-readable question text from question index.
    Supports both single question and batch requests.
    
    GET /api/ml/question/<index>/  - Single question
    POST /api/ml/questions/        - Batch questions
    
    POST body:
    {
        "indices": [10, 106, 20, 116]
    }
    """
    def get(self, request, index=None):
        try:
            from .services.question_mapper import get_question_info
            
            if index is None:
                return JsonResponse({"error": "Question index required"}, status=400)
            
            try:
                index = int(index)
            except ValueError:
                return JsonResponse({"error": "Invalid index format"}, status=400)
            
            info = get_question_info(index)
            
            if 'error' in info:
                return JsonResponse(info, status=400)
            
            return JsonResponse(info, status=200)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            indices = data.get('indices', [])
            
            if not isinstance(indices, list):
                return JsonResponse({"error": "indices must be a list"}, status=400)
            
            results = []
            for idx in indices:
                try:
                    idx_int = int(idx)
                    info = get_question_info(idx_int)
                    results.append(info)
                except (ValueError, TypeError):
                    results.append({"error": f"Invalid index: {idx}"})
            
            return JsonResponse({"questions": results}, status=200)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StopTrainingView(View):
    """POST /api/ml/stop/ — request training cancellation."""
    def post(self, request):
        state = TrainingState()
        current = state.status
        if current not in ("TRAINING", "STOPPING"):
            # Not training — just reset to clean state
            state.set_status("IDLE")
            return JsonResponse({"status": "idle", "message": "Nothing was running."})
        state.set_status("STOPPING")
        state.log("Stop requested — will halt after current epoch.")
        return JsonResponse({"status": "stopping"})

@method_decorator(csrf_exempt, name='dispatch')
class MajorMappingAPI(View):
    """GET/POST/DELETE for Custom UI"""
    def get(self, request):
        from .models import UniversityMajor
        try:
            mappings = {}
            for obj in UniversityMajor.objects.all():
                if request.GET.get('format') == 'ui':
                    mappings.setdefault(obj.ml_category, []).append({
                        "id": obj.id,
                        "name": obj.official_name
                    })
                else:
                    careers = list(obj.career_paths.values_list('job_title', flat=True))
                    mappings.setdefault(obj.ml_category, []).append({
                        "name": obj.official_name,
                        "careers": careers
                    })
            return JsonResponse({"mappings": mappings}, status=200)
        except Exception:
            return JsonResponse({"mappings": {}}, status=200)

    def post(self, request):
        from .models import UniversityMajor
        try:
            data = json.loads(request.body)
            cat = data.get('category')
            name = data.get('name')
            if cat and name:
                obj = UniversityMajor.objects.create(ml_category=cat, official_name=name)
                return JsonResponse({"id": obj.id, "category": cat, "name": name}, status=200)
            return JsonResponse({"error": "Missing fields"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request):
        from .models import UniversityMajor
        try:
            data = json.loads(request.body)
            obj_id = data.get('id')
            if obj_id:
                UniversityMajor.objects.filter(id=obj_id).delete()
                return JsonResponse({"success": True}, status=200)
            return JsonResponse({"error": "Missing id"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CareerMappingAPI(View):
    """GET/POST/DELETE for CareerPaths UI"""
    def get(self, request):
        from .models import CareerPath
        try:
            careers = {}
            for obj in CareerPath.objects.all():
                if request.GET.get('format') == 'ui':
                    careers.setdefault(obj.university_major.id, []).append({
                        "id": obj.id,
                        "title": obj.job_title
                    })
            return JsonResponse({"careers": careers}, status=200)
        except Exception:
            return JsonResponse({"careers": {}}, status=200)

    def post(self, request):
        from .models import CareerPath
        try:
            data = json.loads(request.body)
            major_id = data.get('major_id')
            title = data.get('title')
            if major_id and title:
                obj = CareerPath.objects.create(university_major_id=major_id, job_title=title)
                return JsonResponse({"id": obj.id, "major_id": major_id, "title": title}, status=200)
            return JsonResponse({"error": "Missing fields"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request):
        from .models import CareerPath
        try:
            data = json.loads(request.body)
            obj_id = data.get('id')
            if obj_id:
                CareerPath.objects.filter(id=obj_id).delete()
                return JsonResponse({"success": True}, status=200)
            return JsonResponse({"error": "Missing id"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class MajorMappingUIView(View):
    """Renders the custom HTML page for managing majors without Django Admin."""
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return render(request, 'ml_engine/major_mapping.html')

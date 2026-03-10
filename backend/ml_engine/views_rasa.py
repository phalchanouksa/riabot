import os
import subprocess
import threading
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RASA_DIR = os.path.join(BASE_DIR, 'rasa')

RASA_FILES = {
    'nlu': os.path.join(RASA_DIR, 'data', 'nlu.yml'),
    'domain': os.path.join(RASA_DIR, 'domain.yml'),
    'stories': os.path.join(RASA_DIR, 'data', 'stories.yml'),
    'rules': os.path.join(RASA_DIR, 'data', 'rules.yml'),
    'config': os.path.join(RASA_DIR, 'config.yml'),
}

class RasaTrainingState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RasaTrainingState, cls).__new__(cls)
            cls._instance.is_training = False
            cls._instance.logs = []
            cls._instance.model_path = None
        return cls._instance

training_state = RasaTrainingState()

def run_rasa_train():
    training_state.is_training = True
    training_state.logs = []
    
    try:
        # Run Rasa train (windows)
        training_state.logs.append("==== STARTED RASA TRAINING ====")
        training_state.logs.append("Validating data...")
        
        process = subprocess.Popen(
            f'cd "{RASA_DIR}" && .\\venv\\Scripts\\activate && rasa train',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                training_state.logs.append(line.strip())
            
        process.wait()
        
        if process.returncode == 0:
            training_state.logs.append("==== TRAINING COMPLETED SUCCESSFULLY ====")
            
            # Find the newest model
            models_dir = os.path.join(RASA_DIR, 'models')
            models = [os.path.join(models_dir, f) for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
            if models:
                newest_model = max(models, key=os.path.getmtime)
                training_state.logs.append(f"-> Found new model: {os.path.basename(newest_model)}")
                
                # Make HTTP PUT to Rasa API to load it
                try:
                    training_state.logs.append("-> Replacing active model in running Rasa Server via API...")
                    response = requests.put(
                        "http://localhost:5005/model",
                        json={"model_file": newest_model},
                        timeout=300
                    )
                    if response.status_code == 204:
                        training_state.logs.append("✅ SUCCESSFULLY HOT-SWAPPED RASA MODEL! 🚀")
                        training_state.logs.append("✅ Your chatbot is now using the newest data without needing a restart.")
                    else:
                        training_state.logs.append(f"❌ Failed to load model through API. Ensure `--enable-api` is used. Status: {response.status_code}")
                except Exception as e:
                    training_state.logs.append(f"❌ Could not connect to Rasa API: {str(e)}")
                    training_state.logs.append("❌ Please ensure Rasa is running with the --enable-api flag")
        else:
            training_state.logs.append(f"❌ Training failed with exit code {process.returncode}")
            
    except Exception as e:
        training_state.logs.append(f"❌ Error during training process: {str(e)}")
    finally:
        training_state.is_training = False


@method_decorator(csrf_exempt, name='dispatch')
class RasaAdminView(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return render(request, 'ml_engine/rasa_admin.html')

@method_decorator(csrf_exempt, name='dispatch')
class RasaFileAPI(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request, file_type):
        if file_type not in RASA_FILES:
            return JsonResponse({"error": "Invalid file type"}, status=400)
            
        file_path = RASA_FILES[file_type]
        if not os.path.exists(file_path):
            return JsonResponse({"error": "File not found"}, status=404)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return JsonResponse({"content": content})

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request, file_type):
        if file_type not in RASA_FILES:
            return JsonResponse({"error": "Invalid file type"}, status=400)
            
        try:
            data = json.loads(request.body)
            content = data.get('content')
            
            if content is None:
                return JsonResponse({"error": "No content provided"}, status=400)
                
            file_path = RASA_FILES[file_type]
            
            # Make a backup just in case
            backup_path = f"{file_path}.bak"
            if os.path.exists(file_path):
                import shutil
                shutil.copy2(file_path, backup_path)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return JsonResponse({"status": "success", "message": f"{file_type} saved successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RasaTrainAPI(View):
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request):
        if training_state.is_training:
            return JsonResponse({"error": "Training is already in progress"}, status=400)
            
        thread = threading.Thread(target=run_rasa_train)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({"status": "Started Rasa training in the background."})
        
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return JsonResponse({
            "is_training": training_state.is_training,
            "logs": training_state.logs  # Return logs to show training output
        })

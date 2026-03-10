import os
import json
import shutil
from datetime import datetime
from django.conf import settings

SAVED_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_models')
METADATA_FILE = os.path.join(SAVED_MODELS_DIR, 'models_metadata.json')
ACTIVE_MODEL_PATH = os.path.join(SAVED_MODELS_DIR, 'major_model.zip')

class ModelManager:
    @staticmethod
    def _load_metadata():
        if not os.path.exists(METADATA_FILE):
            return []
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _save_metadata(metadata):
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=4)

    @staticmethod
    def register_model(model_filename, metrics, config):
        """
        Registers a newly trained model in the metadata.
        """
        metadata = ModelManager._load_metadata()
        
        # Deactivate all others if this is the new active one (which it usually is after training)
        for m in metadata:
            m['is_active'] = False
            
        new_entry = {
            'id': os.path.splitext(model_filename)[0],
            'filename': model_filename,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'config': config,
            'is_active': True
        }
        
        metadata.insert(0, new_entry) # Add to top
        ModelManager._save_metadata(metadata)
        return new_entry

    @staticmethod
    def list_models():
        return ModelManager._load_metadata()

    @staticmethod
    def activate_model(model_id):
        """
        Sets a specific model as the active 'major_model.zip'.
        """
        metadata = ModelManager._load_metadata()
        target_model = None
        
        for m in metadata:
            if m['id'] == model_id:
                target_model = m
                m['is_active'] = True
            else:
                m['is_active'] = False
                
        if not target_model:
            raise ValueError(f"Model {model_id} not found")
            
        # Copy the file to major_model.zip
        source_path = os.path.join(SAVED_MODELS_DIR, target_model['filename'])
        if not os.path.exists(source_path):
             raise FileNotFoundError(f"Model file {source_path} not found")
             
        # We need to handle the .zip extension carefully as TabNet adds it automatically
        # But here we are dealing with files that already exist
        
        # If source is .zip, copy to major_model.zip
        shutil.copy2(source_path, ACTIVE_MODEL_PATH)
        
        ModelManager._save_metadata(metadata)
        return target_model

    @staticmethod
    def delete_model(model_id):
        metadata = ModelManager._load_metadata()
        
        # Check if active
        for m in metadata:
            if m['id'] == model_id and m['is_active']:
                raise ValueError("Cannot delete the active model. Activate another model first.")
                
        # Filter out
        new_metadata = [m for m in metadata if m['id'] != model_id]
        deleted_entry = next((m for m in metadata if m['id'] == model_id), None)
        
        if deleted_entry:
            file_path = os.path.join(SAVED_MODELS_DIR, deleted_entry['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
                
        ModelManager._save_metadata(new_metadata)
        return True

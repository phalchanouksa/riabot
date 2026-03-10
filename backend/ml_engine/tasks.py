from celery import shared_task
from .services.tabnet_trainer import train_hybrid_model_task


@shared_task(bind=True, name='ml_engine.train_model', ignore_result=False,
             max_retries=0, time_limit=1800, soft_time_limit=1500)
def train_model_task(self, n_synthetic=5000, max_epochs=20, patience=5, batch_size=256):
    """
    Celery task that runs ML model training in a dedicated worker process.
    
    - time_limit: hard kill after 30 minutes (safety net)
    - soft_time_limit: raises SoftTimeLimitExceeded after 25 minutes (allows graceful cleanup)
    - max_retries=0: training should not auto-retry on failure
    """
    from .services.tabnet_trainer import TrainingState
    
    try:
        train_hybrid_model_task(
            n_synthetic=n_synthetic,
            max_epochs=max_epochs,
            patience=patience,
            batch_size=batch_size
        )
        state = TrainingState()
        return {
            'status': state.status,
            'metrics': state.metrics
        }
    except Exception as e:
        state = TrainingState()
        state.log(f"Celery task error: {str(e)}")
        state.set_status("ERROR")
        raise

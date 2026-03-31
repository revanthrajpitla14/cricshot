import datetime

def log_prediction(result: dict, file_type: str, session_token: str = None, manual_user_id: int = None):
    """
    Persist a Prediction row after a successful inference. Protected against DB Outages.
    Importing SQLAlchemy app context explicitly at runtime completely breaks circular dependencies.
    """
    from app import db, Prediction, AnonymousSession
    
    try:
        pred = Prediction(
            user_id          = manual_user_id,
            session_token    = session_token if not manual_user_id else None,
            shot_name        = result.get("shot", "Unknown"),
            confidence       = result.get("confidence", 0.0),
            file_type        = file_type,
            frame_count      = result.get("frame_count"),
            frames_processed = result.get("frames_processed"),
            ip_address       = "127.0.0.1", # Hardcoded due to background thread context loss
        )
        db.session.add(pred)

        # Increment anonymous quota safely
        if not manual_user_id and session_token:
            anon = AnonymousSession.query.filter_by(session_token=session_token).first()
            if anon:
                anon.prediction_count += 1
                anon.last_used = datetime.datetime.now(datetime.timezone.utc)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e  # Let the db_flusher_loop or fallback array catch this.

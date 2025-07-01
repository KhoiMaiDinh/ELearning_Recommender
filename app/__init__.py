from flask import Flask, jsonify
from config import Config
from app.services.recommender import bp as recommender_bp
from app.database import DatabaseManager
from app.services.recommender import CourseRecommender

import threading

# def start_kafka_worker():
#     thread = threading.Thread(target=run_worker, daemon=True)
#     thread.start()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    with app.app_context():
        # Initialize shared services
        db_manager = DatabaseManager()
        recommender = CourseRecommender(db_manager)
        
        # Store in Flask app context
        app.extensions["db_manager"] = db_manager
        app.extensions["recommender"] = recommender
        
        # start_kafka_worker()

    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        app.extensions["db_manager"].dispose()

    app.register_blueprint(recommender_bp, url_prefix='/api')
    return app

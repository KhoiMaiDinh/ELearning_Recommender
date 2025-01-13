from flask import Blueprint, jsonify
from app.recommender.services import EventRecommender

bp = Blueprint('recommender', __name__)

@bp.route('/api/recommendations/<user_id>')
def get_recommendations(user_id):
    recommender = EventRecommender()
    recommendations = recommender.get_recommendations(user_id)
    return jsonify(recommendations)

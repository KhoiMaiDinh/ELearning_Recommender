from flask import Blueprint, jsonify
from app.recommender.services import EventRecommender

bp = Blueprint('recommender', __name__)

# from app.recommender import routes

@bp.route('/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id):
    recommender = EventRecommender()
    recommendations = recommender.get_recommendations(user_id)
    return jsonify(recommendations)
    # return jsonify({"user_id": user_id})


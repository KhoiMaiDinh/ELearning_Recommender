from flask import Blueprint, jsonify, current_app
from app.services.recommender.service import CourseRecommender
import pandas as pd
from datetime import datetime
from flask import request

bp = Blueprint('recommender', __name__)

# from app.recommender import routes


@bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    recommender: CourseRecommender = current_app.extensions["recommender"]
    # Get course IDs from query parameter, e.g., ?courses=1,2,3
    courses_param = request.args.get("courses", "")
    course_ids = [int(cid) for cid in courses_param.split(",") if cid.strip().isdigit()]
    k = int(request.args.get("top_k", 10))
    prediction = recommender.predict(course_ids, k)
    # Convert DataFrame to list of dicts for JSON response
    result = prediction.to_dict(orient="records") if hasattr(prediction, "to_dict") else prediction
    return jsonify(result)


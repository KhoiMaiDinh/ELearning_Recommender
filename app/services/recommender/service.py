import pandas as pd
from .tfidf import TfidfRecommender
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import joblib
from app.database import DatabaseManager
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os

model_path = "app/models/tfidf_recommender.pkl"

class CourseRecommender:
    def __init__(self, db_manager: DatabaseManager):
        self.recommender = TfidfRecommender(id_col='id', tokenization_method='scibert')
        self.cosine_sim = None
        self.df = None
        self.user_interactions = {} 
        self.db_manager = db_manager
        self.clean_col = 'cleaned_text'
        self.is_loaded = False

        # Load recommender data once at server startup
        self._initialize_recommender()
        self._setup_scheduler()

    def _initialize_recommender(self):
        """Initialize recommender data if not already loaded."""
        if os.path.exists(model_path):
            self.recommender = joblib.load(model_path)
            # Load other necessary objects (e.g., self.df, self.cosine_sim) similarly
            self.is_loaded = True
        else:
            self.reload()
            self.is_loaded = True

    def reload(self):
        """
        Reload and fit the recommender data.
        This should be called once a week by a scheduler or at server startup.
        """
        self.load_data()
        tf, vectors_tokenized = self.recommender.tokenize_text(self.df, text_col=self.clean_col)
        self.recommender.fit(tf, vectors_tokenized)
        # Save the fitted model if needed
        os.makedirs('app/models', exist_ok=True)
        joblib.dump(self.recommender, model_path)
        print("Recommender data reloaded and fitted.")
        
    def _setup_scheduler(self):
        scheduler = BackgroundScheduler()
        # Schedule reload to run every week (e.g., Sunday at midnight)
        scheduler.add_job(self.reload, 'cron', day_of_week='sun', hour=0, minute=0)
        scheduler.start()

    def load_data(self):
        # Try to load from database
        courses = None
        courses = self.get_candidate_courses()
        if not courses:
            # Load sample data from JSON file if DB is empty
            sample_path = os.path.join(os.path.dirname(__file__), '../../sample_courses.json')
            sample_path = os.path.abspath(sample_path)
            with open(sample_path, 'r', encoding='utf-8') as f:
                courses = json.load(f)
        df = pd.DataFrame(courses)
        self.df = self.preprocessing_data(df)

        # Load into DataFrame
        self.df = self.preprocessing_data(df)
        
    def preprocessing_data(self, dataframe):
        # Convert lists in 'requirements' and 'outcomes' to strings
        for col in ['requirements', 'outcomes']:
            if col in dataframe.columns:
                dataframe[col] = dataframe[col].apply(
                    lambda x: " ".join(x) if isinstance(x, list) else (x if x is not None else "")
                )
        cols_to_clean = [
            'title', 'subtitle', 'description', 'category_slug', 'level', 'instructor_email',
            'requirements', 'outcomes'
        ]
        
        df_clean = self.recommender.clean_dataframe(dataframe, cols_to_clean, self.clean_col)
        return df_clean
    
    def get_candidate_courses(self):
        session = self.db_manager.get_session()  # Get a session from the DB manager
        try:
            query = text("""
                SELECT 
                    c.id, c.title, c.subtitle, c.description, c.level, c.requirements, c.outcomes,
                    cat.slug AS category_slug,
                    u.email AS instructor_email
                FROM course c
                LEFT JOIN category cat ON c.category_id = cat.category_id
                LEFT JOIN instructor i ON c.instructor_id = i.instructor_id
                LEFT JOIN "user" u ON i.user_id = u.user_id
                WHERE c.status = :status AND c.deleted_at IS NULL
            """)

            result = session.execute(query, {'status': 'PUBLISHED'})
            courses = [dict(zip(result.keys(), row)) for row in result.fetchall()]
            return courses
        finally:
            session.close()

    def fit_data(self):
        """Fit the TF-IDF vectorizer and calculate cosine similarity"""
        self.load_data()
        tf, vectors_tokenized = self.recommender.tokenize_text(self.df, text_col=self.clean_col)
        print(vectors_tokenized)

        # Save the fitted model and cosine similarity matrix
        joblib.dump(vectors_tokenized, 'app/models/vectorizer.pkl')
        print("Model fitted and saved!")

    def recommend_course(self, user_id):
        """Recommend courses based on the user's profile (aggregated course interactions)"""
        # Get the courses the user has interacted with
        interacted_courses = self.user_interactions.get(user_id, [])
        
        if not interacted_courses:
            print(f"No interactions found for user {user_id}.")
            return []

        # Get the vector representation for all interacted courses
        user_vector = np.zeros(self.cosine_sim.shape[1])  # Initialize a vector of zeros

        for course_id in interacted_courses:
            idx = self.df[self.df['id'] == course_id].index[0]
            user_vector += self.cosine_sim[idx]  # Aggregate the vectors (can also apply a weighted sum)

        # Normalize the user profile vector (optional)
        user_vector /= len(interacted_courses)

        # Get similarity scores with all courses
        sim_scores = cosine_similarity([user_vector], self.cosine_sim)
        sim_scores = sim_scores.flatten()

        # Get the top 3 most similar courses
        recommended_indices = sim_scores.argsort()[-4:-1][::-1]  # Exclude the user’s own interactions

        recommended_courses = self.df.iloc[recommended_indices]
        return recommended_courses[['id', 'title']]

    def user_interact(self, user_id, course_id):
        """Simulate a user interacting with a course"""
        if user_id not in self.user_interactions:
            self.user_interactions[user_id] = []
        self.user_interactions[user_id].append(course_id)

    def predict(self, course_ids, k=5):
        """
        Predict top-k similar courses for a given list of course_ids using the recommender.
        """
        print(self.df)
        if self.df is None or self.recommender.tfidf_matrix is None:
            # Load and fit if not already done
            self.reload()

        # If a single course_id is provided, convert to list
        if isinstance(course_ids, (int, str)):
            course_ids = [course_ids]

        # Aggregate vectors for the given course_ids
        indices = [self.df[self.df['id'] == cid].index[0] for cid in course_ids if cid in self.df['id'].values]
        if not indices:
            return []

        # Get the mean vector for the selected courses
        course_vectors = self.recommender.tfidf_matrix[indices]
        mean_vector = course_vectors.mean(axis=0)

        # Convert mean_vector and tfidf_matrix to numpy arrays to avoid np.matrix issues
        mean_vector = np.asarray(mean_vector)
        tfidf_matrix = self.recommender.tfidf_matrix
        if hasattr(tfidf_matrix, "toarray"):
            tfidf_matrix = tfidf_matrix.toarray()

        # Compute similarity with all courses
        sim_scores = cosine_similarity(mean_vector.reshape(1, -1), tfidf_matrix).flatten()

        # Exclude the input courses from recommendations
        exclude_indices = set(indices)
        recommended_indices = [i for i in sim_scores.argsort()[::-1] if i not in exclude_indices][:k]

        recommended_courses = self.df.iloc[recommended_indices]
        return recommended_courses[['id', 'title', 'subtitle', 'description']]

from app.database import get_db_connection
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class EventRecommender:
    def __init__(self):
        self.conn = get_db_connection()
        
    def _get_user_interactions(self, user_id):
        query = """
        SELECT DISTINCT e.*,
               STRING_AGG(c.Name, ', ') as Categories
        FROM Events e
        LEFT JOIN EventCategories ec ON e.Id = ec.EventId
        LEFT JOIN Categories c ON ec.CategoryId = c.Id
        WHERE e.Id IN (
            -- Events user has tickets for
            SELECT EventId FROM Tickets WHERE UserId = ?
            UNION
            -- Events user has favorited
            SELECT EventId FROM FavouriteEvents WHERE UserId = ?
            UNION
            -- Events user has reviewed
            SELECT EventId FROM Reviews WHERE AuthorId = ?
        )
        GROUP BY e.Id, e.Name, e.Description, e.Location, e.StartTime, 
                 e.EndTime, e.Status, e.EventCycleType, e.IsPrivate
        """
        return pd.read_sql(query, self.conn, params=[user_id, user_id, user_id])
    
    def _get_candidate_events(self):
        query = """
        SELECT e.*,
               STRING_AGG(c.Name, ', ') as Categories
        FROM Events e
        LEFT JOIN EventCategories ec ON e.Id = ec.EventId
        LEFT JOIN Categories c ON ec.CategoryId = c.Id
        WHERE e.StartTime > GETDATE()
        AND e.IsDeleted = 0
        AND e.Status = 1
        GROUP BY e.Id, e.Name, e.Description, e.Location, e.StartTime, 
                 e.EndTime, e.Status, e.EventCycleType, e.IsPrivate
        """
        return pd.read_sql(query, self.conn)
    
    def _prepare_event_features(self, events_df):
        # Combine relevant text features
        events_df['features'] = events_df['Name'] + ' ' + \
                               events_df['Description'] + ' ' + \
                               events_df['Location'] + ' ' + \
                               events_df['Categories'].fillna('')
        
        # Convert text to TF-IDF features
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(events_df['features'])
        
        return tfidf_matrix
    
    def get_recommendations(self, user_id, num_recommendations=5):
        # Get user's interacted events
        user_events = self._get_user_interactions(user_id)
        if user_events.empty:
            return []
        
        # Get candidate events
        candidate_events = self._get_candidate_events()
        
        # Combine both sets for feature extraction
        all_events = pd.concat([user_events, candidate_events]).drop_duplicates(subset=['Id'])
        
        # Create feature matrix
        tfidf_matrix = self._prepare_event_features(all_events)
        
        # Calculate similarity between all events
        cosine_sim = cosine_similarity(tfidf_matrix)
        
        # Get indices of user's events and candidate events
        user_event_indices = all_events[all_events['Id'].isin(user_events['Id'])].index
        candidate_indices = all_events[all_events['Id'].isin(candidate_events['Id'])].index
        
        # Calculate average similarity to user's events for each candidate event
        similarity_scores = []
        for candidate_idx in candidate_indices:
            avg_similarity = cosine_sim[candidate_idx][user_event_indices].mean()
            similarity_scores.append((candidate_idx, avg_similarity))
        
        # Sort by similarity and get top recommendations
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        recommended_indices = [idx for idx, score in similarity_scores[:num_recommendations]]
        
        # Get recommended events details
        recommendations = all_events.iloc[recommended_indices]
        
        return recommendations[['Id', 'Name', 'Description', 'Location', 'StartTime', 'Categories']].to_dict('records')
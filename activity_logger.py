import os
import json
import logging
import time
from datetime import datetime
from threading import Lock

logger = logging.getLogger("activity_logger")

class ActivityLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.lock = Lock()  # For thread safety
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
    def get_log_file(self):
        """Get the log file name for today."""
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f"activity_{today}.log")
        
    def log_activity(self, activity_type, user, details, success=True):
        """Log an activity to the activity log file."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": activity_type,
            "user": user,
            "details": details,
            "success": success
        }
        
        try:
            with self.lock:  # Ensure thread safety
                with open(self.get_log_file(), "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
                    
            # Also log to standard logger
            if success:
                logger.info(f"[{activity_type}] {user}: {json.dumps(details)}")
            else:
                logger.warning(f"[{activity_type}] {user}: {json.dumps(details)} - FAILED")
                
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
            
    def get_activities(self, days=1, activity_type=None, user=None, limit=100):
        """Get recent activities from log files."""
        activities = []
        
        # Calculate date range
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        
        # Process each date's log file
        for date in dates:
            log_file = os.path.join(self.log_dir, f"activity_{date}.log")
            if not os.path.exists(log_file):
                continue
                
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            activity = json.loads(line.strip())
                            
                            # Apply filters
                            if activity_type and activity.get('type') != activity_type:
                                continue
                                
                            if user and activity.get('user') != user:
                                continue
                                
                            activities.append(activity)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid log entry: {line}")
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
                
        # Sort by timestamp (newest first) and limit results
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return activities[:limit]
        
    def get_statistics(self, days=1):
        """Get activity statistics for the specified time period."""
        activities = self.get_activities(days=days, limit=1000000)  # Get all activities
        
        stats = {
            "total_activities": len(activities),
            "success_rate": 0,
            "activity_types": {},
            "users": {},
            "hourly_distribution": [0] * 24
        }
        
        # Calculate statistics
        if activities:
            # Success rate
            successes = sum(1 for a in activities if a.get('success', False))
            stats["success_rate"] = successes / len(activities)
            
            # Activity types
            for activity in activities:
                activity_type = activity.get('type', 'unknown')
                if activity_type not in stats["activity_types"]:
                    stats["activity_types"][activity_type] = 0
                stats["activity_types"][activity_type] += 1
                
                # User statistics
                user = activity.get('user', 'unknown')
                if user not in stats["users"]:
                    stats["users"][user] = 0
                stats["users"][user] += 1
                
                # Hourly distribution
                try:
                    timestamp = datetime.fromisoformat(activity.get('timestamp', ''))
                    hour = timestamp.hour
                    stats["hourly_distribution"][hour] += 1
                except (ValueError, IndexError):
                    pass
                    
        return stats
import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

logger = logging.getLogger(__name__)

class TennisPipelineRunner:
    def __init__(self):
        self.base_dir = Path(__file__).parent.resolve()
        self.data_dir = self.base_dir / "data"
        self.archive_dir = self.data_dir / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions_file = self.data_dir / "today_predictions.json"
        self.results_file = self.data_dir / "today_accuracy_results.json"
        self.matches_file = self.data_dir / "today_matches.json"

    def archive_past_data(self):
        """Checks existing prediction/result files and archives them if their date is older than today."""
        today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        
        # 1. Archive predictions
        if self.predictions_file.exists():
            try:
                with open(self.predictions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                file_date = data.get("date")
                if not file_date:
                    # Fallback to file modification date
                    mtime = os.path.getmtime(self.predictions_file)
                    file_date = datetime.fromtimestamp(mtime, tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
                
                if file_date and file_date < today_str:
                    archive_path = self.archive_dir / f"predictions_{file_date}.json"
                    if not archive_path.exists():
                        with open(archive_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                        logger.info(f"📁 Tennis: Archived predictions for {file_date}")
            except Exception as e:
                logger.error(f"❌ Error archiving tennis predictions: {e}")
                
        # 2. Archive results
        if self.results_file.exists():
            try:
                with open(self.results_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                file_date = data.get("date")
                if not file_date:
                    # Fallback to file modification date
                    mtime = os.path.getmtime(self.results_file)
                    file_date = datetime.fromtimestamp(mtime, tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
                
                if file_date and file_date < today_str:
                    archive_path = self.archive_dir / f"results_{file_date}.json"
                    if not archive_path.exists():
                        with open(archive_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                        logger.info(f"📁 Tennis: Archived accuracy results for {file_date}")
            except Exception as e:
                logger.error(f"❌ Error archiving tennis results: {e}")

    def run_pipeline(self):
        """Runs the sequential tennis scraping and prediction updates."""
        logger.info("🎾 Starting Tennis Scraping & Prediction Pipeline...")
        
        # 1. Archive yesterday's files
        self.archive_past_data()
        
        # Import the service modules dynamically inside run to keep startup clean
        from app.sports.tennis.services import update_profiles, fetch_fexture
        from app.sports.tennis.models import predict
        
        # 2. Update player profiles with completed matches in the current matches file
        logger.info("🎾 Step 1/4: Updating player profiles with completed matches...")
        try:
            update_profiles.main()
        except Exception as e:
            logger.error(f"❌ Error updating tennis player profiles: {e}")
            
        # 3. Fetch today's new matches
        logger.info("🎾 Step 2/4: Fetching today's matches fixture...")
        try:
            fetch_fexture.main()
        except Exception as e:
            logger.error(f"❌ Error fetching tennis matches: {e}")
            
        # 4. Predict today's matches
        logger.info("🎾 Step 3/4: Generating today's predictions...")
        try:
            predict.predict_today_matches()
        except Exception as e:
            logger.error(f"❌ Error generating tennis predictions: {e}")
            
        # 5. Evaluate today's accuracy results
        logger.info("🎾 Step 4/4: Evaluating match accuracy results...")
        try:
            predict.evaluate_today_accuracy()
        except Exception as e:
            logger.error(f"❌ Error evaluating tennis accuracy: {e}")
            
        logger.info("🎾 Tennis Pipeline Run Completed Successfully!")

if __name__ == "__main__":
    import sys
    # Add root folder to sys.path to resolve 'app' imports correctly
    project_root = Path(__file__).parent.parent.parent.parent.resolve()
    sys.path.append(str(project_root))
    
    # Configure logger to output to stdout when run directly
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    runner = TennisPipelineRunner()
    runner.run_pipeline()

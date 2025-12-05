import os

class Settings:
    PROJECT_NAME: str = "TrickyClip"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/trickyclip")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # storage paths
    DATA_DIR: str = os.getenv("DATA_DIR", "/data")
    ORIGINALS_DIR: str = os.path.join(DATA_DIR, "originals")
    CANDIDATES_DIR: str = os.path.join(DATA_DIR, "candidates")
    FINAL_CLIPS_DIR: str = os.path.join(DATA_DIR, "final_clips")
    
    # google drive settings
    GOOGLE_DRIVE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "/app/secrets/graphic-parsec-480000-i8-0552e472ced1.json")
    GOOGLE_DRIVE_ROOT_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")  # trickyclip archive folder id
    GOOGLE_DRIVE_DUMP_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_DUMP_FOLDER_ID", "")  # dump folder where you upload raw videos
    GOOGLE_DRIVE_PROCESSED_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_PROCESSED_FOLDER_ID", "")  # processed folder for completed raw videos

settings = Settings()


"""
Dedicated entry point for Drive sync poller worker.
This runs in its own container and polls Drive every 2 minutes.
"""
import sys
import os

# Ensure we can import from app
sys.path.insert(0, '/app')

if __name__ == "__main__":
    print("=" * 60)
    print("DRIVE SYNC WORKER STARTING")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"REDIS_URL: {os.getenv('REDIS_URL', 'NOT SET')}")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
    print("=" * 60)
    
    try:
        from app.worker import drive_sync_poller
        print("✅ Successfully imported drive_sync_poller")
        print("🚀 Starting polling loop...")
        drive_sync_poller()
    except KeyboardInterrupt:
        print("\n🛑 Sync worker stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


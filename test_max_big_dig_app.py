#!/usr/bin/env python3
"""
Test script for MaxBigDigApp components
Tests individual components without GUI for headless environments
"""

import asyncio
import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from max_big_dig_app import (
    Logger, ThreadSafeQueue, SessionManager, 
    AsyncioManager, TelegramOperations, TaskManager, ProfileManager
)


async def test_logger():
    """Test logging functionality"""
    print("Testing Logger...")
    logger = Logger("TestLogger")
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print("✓ Logger test completed")


def test_thread_safe_queue():
    """Test thread-safe queue"""
    print("Testing ThreadSafeQueue...")
    queue = ThreadSafeQueue()
    
    # Test put/get
    queue.put("test_item")
    item = queue.get(timeout=1)
    assert item == "test_item", "Queue item mismatch"
    
    # Test empty
    assert queue.empty(), "Queue should be empty"
    
    print("✓ ThreadSafeQueue test completed")


async def test_session_manager():
    """Test session manager"""
    print("Testing SessionManager...")
    logger = Logger("SessionManagerTest")
    session_manager = SessionManager(logger)
    
    # Test directory creation
    assert session_manager.sessions_dir.exists(), "Sessions directory not created"
    
    # Test client management
    assert len(session_manager.active_clients) == 0, "Should start with no active clients"
    
    print("✓ SessionManager test completed")


async def test_asyncio_manager():
    """Test asyncio manager"""
    print("Testing AsyncioManager...")
    logger = Logger("AsyncioManagerTest")
    asyncio_manager = AsyncioManager(logger)
    
    # Start manager
    asyncio_manager.start()
    
    # Wait a bit for initialization
    await asyncio.sleep(0.5)
    
    # Test coroutine execution
    async def test_coro():
        return "test_result"
    
    if asyncio_manager.loop:
        future = asyncio_manager.run_coroutine_threadsafe(test_coro())
        result = future.result(timeout=5)
        assert result == "test_result", "Coroutine execution failed"
    
    # Shutdown
    asyncio_manager.shutdown()
    
    print("✓ AsyncioManager test completed")


def test_task_manager():
    """Test task manager"""
    print("Testing TaskManager...")
    logger = Logger("TaskManagerTest")
    task_manager = TaskManager(logger)
    
    # Test task addition
    def test_task():
        return "completed"
    
    task_manager.add_task("test_task", test_task)
    
    # Wait for completion
    import time
    time.sleep(1)
    
    status = task_manager.get_task_status("test_task")
    assert status in ["completed", "running"], f"Unexpected status: {status}"
    
    # Test cleanup
    task_manager.cleanup_completed_tasks()
    
    # Shutdown
    task_manager.shutdown()
    
    print("✓ TaskManager test completed")


def test_profile_manager():
    """Test profile manager"""
    print("Testing ProfileManager...")
    logger = Logger("ProfileManagerTest")
    profile_manager = ProfileManager(logger)
    
    # Test profile creation
    test_data = {"name": "Test Profile", "value": 123}
    assert profile_manager.create_profile("test_profile", test_data), "Profile creation failed"
    
    # Test profile retrieval
    retrieved = profile_manager.get_profile("test_profile")
    assert retrieved is not None, "Profile retrieval failed"
    assert retrieved["name"] == "Test Profile", "Profile data mismatch"
    
    # Test profile list
    profiles = profile_manager.list_profiles()
    assert "test_profile" in profiles, "Profile not in list"
    
    # Test profile update
    updated_data = {"name": "Updated Profile", "value": 456}
    assert profile_manager.update_profile("test_profile", updated_data), "Profile update failed"
    
    # Test profile deletion
    assert profile_manager.delete_profile("test_profile"), "Profile deletion failed"
    
    print("✓ ProfileManager test completed")


async def main():
    """Run all tests"""
    print("Running MaxBigDigApp component tests...\n")
    
    try:
        # Test individual components
        await test_logger()
        test_thread_safe_queue()
        await test_session_manager()
        await test_asyncio_manager()
        test_task_manager()
        test_profile_manager()
        
        print("\n✅ All tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run tests
    asyncio.run(main())
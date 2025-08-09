#!/usr/bin/env python3
"""
Example usage script for MaxBigDigApp API
Demonstrates how to use the application programmatically
"""

import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from max_big_dig_app import MaxBigDigAPI


async def example_session_creation():
    """Example: Create and authorize a Telegram session"""
    api = MaxBigDigAPI()
    
    # Replace with your actual credentials
    session_name = "example_session"
    api_id = 12345  # Get from https://my.telegram.org/apps
    api_hash = "your_api_hash_here"
    phone = "+1234567890"
    
    print("Creating Telegram session...")
    
    # Create session
    success = await api.create_session(session_name, api_id, api_hash, phone)
    if success:
        print(f"✓ Session {session_name} created. Check your phone for verification code.")
        
        # In real usage, you would get the code from user input
        # code = input("Enter verification code: ")
        # password = input("Enter 2FA password (if required): ") or None
        
        # auth_success = await api.authorize_session(session_name, code, password)
        # if auth_success:
        #     print("✓ Session authorized successfully")
        # else:
        #     print("✗ Session authorization failed")
    else:
        print("✗ Failed to create session")
    
    await api.shutdown()


async def example_user_parsing():
    """Example: Parse users from a chat"""
    api = MaxBigDigAPI()
    
    session_name = "example_session"
    chat_id = -1001234567890  # Replace with actual chat ID
    
    print("Parsing users from chat...")
    
    try:
        users = await api.get_participants(session_name, chat_id, limit=100)
        print(f"✓ Found {len(users)} users")
        
        for user in users[:5]:  # Show first 5 users
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            print(f"  - {name} (@{user.get('username', 'N/A')}) - ID: {user.get('id')}")
        
        if len(users) > 5:
            print(f"  ... and {len(users) - 5} more users")
            
    except Exception as e:
        print(f"✗ Error parsing users: {e}")
    
    await api.shutdown()


async def example_message_sending():
    """Example: Send messages"""
    api = MaxBigDigAPI()
    
    session_name = "example_session"
    target_user_id = 123456789  # Replace with actual user ID
    message = "Hello from MaxBigDigApp!"
    
    print("Sending message...")
    
    try:
        success = await api.send_message(session_name, target_user_id, message)
        if success:
            print("✓ Message sent successfully")
        else:
            print("✗ Failed to send message")
    except Exception as e:
        print(f"✗ Error sending message: {e}")
    
    await api.shutdown()


async def example_bulk_operations():
    """Example: Bulk invitation with error handling"""
    api = MaxBigDigAPI()
    
    session_name = "example_session"
    target_chat_id = -1001234567890
    user_ids_to_invite = [111111111, 222222222, 333333333]  # Replace with actual IDs
    
    print("Starting bulk invitation...")
    
    try:
        results = await api.invite_users(session_name, target_chat_id, user_ids_to_invite, delay=3)
        
        print(f"✓ Invitation completed:")
        print(f"  - Successful: {results['success']}")
        print(f"  - Failed: {results['failed']}")
        
        if results['errors']:
            print("  - Errors:")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"    • {error}")
                
    except Exception as e:
        print(f"✗ Error during bulk invitation: {e}")
    
    await api.shutdown()


async def example_auto_responder():
    """Example: Setup auto-responder"""
    api = MaxBigDigAPI()
    
    session_name = "example_session"
    response_text = "Thank you for your message! I'll get back to you soon."
    
    print("Setting up auto-responder...")
    
    try:
        await api.setup_auto_responder(session_name, response_text)
        print("✓ Auto-responder activated")
        
        # Auto-responder will run until stopped
        print("Auto-responder is active. Press Ctrl+C to stop...")
        
        # In real usage, you might want to run this for a specific time
        # await asyncio.sleep(3600)  # Run for 1 hour
        
        # api.stop_auto_responder()
        # print("✓ Auto-responder stopped")
        
    except KeyboardInterrupt:
        api.stop_auto_responder()
        print("\n✓ Auto-responder stopped by user")
    except Exception as e:
        print(f"✗ Error with auto-responder: {e}")
    
    await api.shutdown()


def example_profile_management():
    """Example: Profile management"""
    api = MaxBigDigAPI()
    
    print("Managing profiles...")
    
    # Create a profile
    profile_data = {
        "name": "Marketing Campaign",
        "target_audience": "Tech enthusiasts",
        "message_template": "Hi {name}, check out our new product!",
        "delay_between_messages": 5,
        "max_messages_per_day": 50
    }
    
    success = api.create_profile("marketing_profile", profile_data)
    if success:
        print("✓ Profile created")
    
    # Retrieve profile
    retrieved = api.get_profile("marketing_profile")
    if retrieved:
        print("✓ Profile retrieved:")
        print(f"  - Name: {retrieved['name']}")
        print(f"  - Target: {retrieved['target_audience']}")
    
    # Note: No async shutdown needed for profile operations


async def example_task_management():
    """Example: Task management"""
    api = MaxBigDigAPI()
    
    print("Managing background tasks...")
    
    def long_running_task():
        """Simulate a long-running task"""
        import time
        print("Task started...")
        time.sleep(5)
        print("Task completed!")
        return "Task result"
    
    # Add background task
    task_id = "example_task"
    api.add_background_task(task_id, long_running_task)
    print(f"✓ Task {task_id} added")
    
    # Check task status
    for i in range(10):
        status = api.get_task_status(task_id)
        print(f"Task status: {status}")
        
        if status in ['completed', 'failed', 'cancelled']:
            break
            
        await asyncio.sleep(1)
    
    await api.shutdown()


async def main():
    """Main example runner"""
    print("MaxBigDigApp - Example Usage")
    print("=" * 40)
    
    examples = [
        ("Session Creation", example_session_creation),
        ("Profile Management", lambda: example_profile_management()),
        ("Task Management", example_task_management),
        # Uncomment these when you have valid credentials and session
        # ("User Parsing", example_user_parsing),
        # ("Message Sending", example_message_sending),
        # ("Bulk Operations", example_bulk_operations),
        # ("Auto Responder", example_auto_responder),
    ]
    
    for name, example_func in examples:
        print(f"\n--- {name} ---")
        try:
            if asyncio.iscoroutinefunction(example_func):
                await example_func()
            else:
                example_func()
        except Exception as e:
            print(f"Error in {name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✅ All examples completed!")
    print("\nNote: Some examples require valid Telegram credentials and active sessions.")
    print("See README_MaxBigDigApp.md for detailed setup instructions.")


if __name__ == "__main__":
    print("Running MaxBigDigApp examples...")
    asyncio.run(main())
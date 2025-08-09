# MaxBigDigApp - Comprehensive Telegram Client Application

MaxBigDigApp is a full-featured Telegram client application that addresses common issues with asyncio, Telethon integration, threading, and provides a complete solution for Telegram automation tasks.

## Features Implemented

### ✅ 1. Асинхронные операции и event loop
- ✅ Proper asyncio event loop management in separate thread
- ✅ Correct coroutine handling with thread-safe execution
- ✅ Fixed tkinter + asyncio integration issues
- ✅ Thread pool executor for background tasks

### ✅ 2. Методы Telethon
- ✅ Fixed synchronous/asynchronous API calls
- ✅ Proper session management and persistence
- ✅ Correct entity handling for Telegram operations
- ✅ Event handlers for incoming messages

### ✅ 3. Сессии и аутентификация
- ✅ Improved session handling with automatic persistence
- ✅ Fixed authentication process with 2FA support
- ✅ Proper session file management
- ✅ Multiple session support

### ✅ 4. Многопоточность
- ✅ Fixed race conditions with thread locks
- ✅ Thread-safe communication between GUI and backend
- ✅ Separate asyncio event loop thread
- ✅ Safe thread pool for concurrent operations

### ✅ 5. Обработка ошибок
- ✅ Comprehensive exception handling throughout
- ✅ Detailed logging with thread-safe logger
- ✅ User-friendly error messages
- ✅ Graceful degradation and recovery

## Core Functionality

### Account Management
- Create and manage multiple Telegram sessions
- Automatic session persistence
- 2FA authentication support
- Session status monitoring

### User Parsing
- Parse users from chats and channels
- Export user data (ID, name, username, phone)
- Batch processing with rate limiting
- Filter and search capabilities

### Message Sending
- Send messages to users or groups
- Bulk messaging with delays
- Message templating support
- Rate limiting to avoid spam detection

### Phone Number Verification
- Check if phone numbers are registered on Telegram
- Bulk phone verification
- Export results for analysis

### Auto-Responder
- Automatic response to incoming messages
- Customizable response templates
- Enable/disable per session
- Logging of all interactions

### Invitation System
- Invite users to chats/channels
- Bulk invitation with delays
- Success/failure tracking
- Anti-spam protections

### Task Management
- Background task execution
- Task status monitoring
- Cancellation support
- Automatic cleanup

### Profile Management
- Save and load user profiles
- JSON-based configuration
- Import/export capabilities
- Template management

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy configuration template:
```bash
cp config_template.json config.json
```

3. Edit config.json with your API credentials from https://my.telegram.org/apps

## Usage

### GUI Mode (with tkinter)
```bash
python max_big_dig_app.py
```

### Headless/API Mode
```python
from max_big_dig_app import MaxBigDigAPI

# Initialize API
api = MaxBigDigAPI()

# Create session
await api.create_session("my_session", api_id, api_hash, "+1234567890")

# Authorize with code
await api.authorize_session("my_session", "12345", "password_if_2fa")

# Send message
await api.send_message("my_session", user_id, "Hello!")

# Parse users
users = await api.get_participants("my_session", chat_id, limit=1000)

# Cleanup
await api.shutdown()
```

### Testing
```bash
python test_max_big_dig_app.py
```

## Architecture

### Thread Safety
- All operations are thread-safe using proper locking mechanisms
- GUI updates happen on main thread only
- Background operations in separate threads
- Thread-safe queue for inter-thread communication

### Asyncio Integration
- Dedicated asyncio event loop in separate thread
- Proper coroutine execution from GUI thread
- Thread-safe future handling
- Graceful shutdown process

### Error Handling
- Comprehensive try-catch blocks
- Detailed logging with context
- User-friendly error messages
- Recovery mechanisms where possible

### Session Management
- Automatic session file creation and management
- Multiple session support
- Proper disconnect handling
- Session state tracking

## Configuration

See `config_template.json` for all available options:
- API credentials
- Rate limiting settings
- Safety limits
- Default responses
- Logging configuration

## File Structure

```
kuroed/
├── max_big_dig_app.py          # Main application
├── test_max_big_dig_app.py     # Component tests
├── config_template.json        # Configuration template
├── requirements.txt            # Dependencies
├── sessions/                   # Session files (auto-created)
├── profiles.json              # User profiles (auto-created)
└── max_big_dig_app.log        # Application logs (auto-created)
```

## Safety Features

- Rate limiting to prevent API abuse
- Maximum limits on bulk operations
- Automatic delays between operations
- Session validation before operations
- Error logging and recovery

## Logging

The application provides comprehensive logging:
- File logging to `max_big_dig_app.log`
- Console output for immediate feedback
- GUI log viewer (in GUI mode)
- Thread-safe logging across all components
- Configurable log levels

## Error Recovery

- Automatic retry for transient errors
- Session reconnection on network issues
- Graceful handling of API rate limits
- User notification for critical errors
- Detailed error context in logs

## Performance Optimizations

- Async I/O for all Telegram operations
- Thread pool for CPU-intensive tasks
- Memory-efficient user data handling
- Configurable batch sizes
- Automatic resource cleanup

## Compatibility

- Python 3.7+
- Windows, Linux, macOS
- GUI mode requires tkinter (usually included with Python)
- Headless mode works without GUI dependencies

## Troubleshooting

### Common Issues

1. **tkinter not available**: Use headless mode or install tkinter
2. **Session authorization failed**: Check API credentials and phone number
3. **Rate limit errors**: Increase delays in configuration
4. **Memory issues**: Reduce batch sizes for large operations

### Getting Help

1. Check logs in `max_big_dig_app.log`
2. Run tests with `python test_max_big_dig_app.py`
3. Verify configuration in `config.json`
4. Check Telegram API documentation

## Security Notes

- Store API credentials securely
- Use session files carefully (contain authentication data)
- Follow Telegram's Terms of Service
- Respect rate limits and user privacy
- Keep application updated

## Contributing

1. Run tests before submitting changes
2. Follow existing code style and patterns
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure thread safety for all new components
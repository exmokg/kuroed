#!/usr/bin/env python3
"""
MaxBigDigApp - Comprehensive Telegram Client Application

This application addresses the following issues:
1. Асинхронные операции и event loop
2. Методы Telethon
3. Сессии и аутентификация
4. Многопоточность
5. Обработка ошибок

Features:
- Account management
- User parsing
- Message sending
- Phone number verification
- Auto-responder
- Invitation functionality
- Task management
- Profile editing
"""

import asyncio
import logging
import threading
import queue
from typing import Optional, Dict, List, Any, Callable
import json
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import contextlib
import traceback
from pathlib import Path

# GUI imports with fallback for headless environments
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("Warning: tkinter not available. GUI functionality disabled.")

from telethon import TelegramClient, events, functions, types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, PeerChannel, PeerChat, PeerUser
import telethon.sessions


class Logger:
    """Centralized logging system with thread safety"""
    
    def __init__(self, name: str = "MaxBigDigApp"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers()
        self._lock = threading.Lock()
    
    def _setup_handlers(self):
        """Setup file and console handlers"""
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler('max_big_dig_app.log', encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def log(self, level: str, message: str, exc_info: bool = False):
        """Thread-safe logging method"""
        with self._lock:
            getattr(self.logger, level.lower())(message, exc_info=exc_info)
    
    def debug(self, message: str): self.log('DEBUG', message)
    def info(self, message: str): self.log('INFO', message)
    def warning(self, message: str): self.log('WARNING', message)
    def error(self, message: str, exc_info: bool = False): self.log('ERROR', message, exc_info)
    def critical(self, message: str, exc_info: bool = False): self.log('CRITICAL', message, exc_info)


class ThreadSafeQueue:
    """Thread-safe queue for communication between threads"""
    
    def __init__(self):
        self._queue = queue.Queue()
    
    def put(self, item: Any):
        """Put item into queue"""
        self._queue.put(item)
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """Get item from queue"""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()


class SessionManager:
    """Manages Telethon sessions with proper error handling"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.sessions_dir = Path("sessions")
        self.sessions_dir.mkdir(exist_ok=True)
        self.active_clients: Dict[str, TelegramClient] = {}
        self._lock = threading.Lock()
    
    async def create_session(self, session_name: str, api_id: int, api_hash: str, phone: str) -> Optional[TelegramClient]:
        """Create new Telegram session with proper error handling"""
        try:
            session_path = self.sessions_dir / f"{session_name}.session"
            client = TelegramClient(str(session_path), api_id, api_hash)
            
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                self.logger.info(f"Code sent to {phone}")
                return client
            else:
                self.logger.info(f"Session {session_name} already authorized")
                with self._lock:
                    self.active_clients[session_name] = client
                return client
                
        except Exception as e:
            self.logger.error(f"Failed to create session {session_name}: {e}", exc_info=True)
            return None
    
    async def authorize_session(self, client: TelegramClient, code: str, password: str = None) -> bool:
        """Authorize session with code and optional password"""
        try:
            await client.sign_in(code=code)
            self.logger.info("Successfully authorized with code")
            return True
        except SessionPasswordNeededError:
            if password:
                try:
                    await client.sign_in(password=password)
                    self.logger.info("Successfully authorized with password")
                    return True
                except Exception as e:
                    self.logger.error(f"Password authorization failed: {e}")
                    return False
            else:
                self.logger.error("Two-factor authentication required but no password provided")
                return False
        except PhoneCodeInvalidError:
            self.logger.error("Invalid phone code")
            return False
        except Exception as e:
            self.logger.error(f"Authorization failed: {e}", exc_info=True)
            return False
    
    async def get_client(self, session_name: str) -> Optional[TelegramClient]:
        """Get active client by session name"""
        with self._lock:
            return self.active_clients.get(session_name)
    
    async def disconnect_all(self):
        """Disconnect all active clients"""
        with self._lock:
            for session_name, client in self.active_clients.items():
                try:
                    await client.disconnect()
                    self.logger.info(f"Disconnected session: {session_name}")
                except Exception as e:
                    self.logger.error(f"Error disconnecting {session_name}: {e}")
            self.active_clients.clear()


class AsyncioManager:
    """Manages asyncio event loop in separate thread"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
    
    def start(self):
        """Start asyncio event loop in separate thread"""
        if self.thread and self.thread.is_alive():
            self.logger.warning("Asyncio manager already running")
            return
        
        self._shutdown_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.logger.info("Asyncio manager started")
    
    def _run_loop(self):
        """Run asyncio event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.logger.info("Asyncio event loop created")
            
            # Run until shutdown
            self.loop.run_until_complete(self._wait_for_shutdown())
        except Exception as e:
            self.logger.error(f"Error in asyncio loop: {e}", exc_info=True)
        finally:
            if self.loop:
                self.loop.close()
                self.logger.info("Asyncio event loop closed")
    
    async def _wait_for_shutdown(self):
        """Wait for shutdown signal"""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(0.1)
    
    def run_coroutine_threadsafe(self, coro):
        """Run coroutine in asyncio thread"""
        if not self.loop:
            raise RuntimeError("Asyncio loop not running")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
    
    def shutdown(self):
        """Shutdown asyncio manager"""
        self._shutdown_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Asyncio manager shutdown")


class TelegramOperations:
    """Handles all Telegram operations with proper async/await patterns"""
    
    def __init__(self, session_manager: SessionManager, logger: Logger):
        self.session_manager = session_manager
        self.logger = logger
        self.auto_responder_active = False
        self.auto_response_text = ""
    
    async def get_dialogs(self, session_name: str, limit: int = 100) -> List[Dict]:
        """Get user dialogs/chats"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            raise ValueError(f"Session {session_name} not found")
        
        try:
            dialogs = []
            async for dialog in client.iter_dialogs(limit=limit):
                dialogs.append({
                    'id': dialog.id,
                    'name': dialog.name,
                    'type': type(dialog.entity).__name__,
                    'unread_count': dialog.unread_count
                })
            return dialogs
        except Exception as e:
            self.logger.error(f"Failed to get dialogs: {e}", exc_info=True)
            return []
    
    async def send_message(self, session_name: str, entity_id: int, message: str) -> bool:
        """Send message to entity"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            self.logger.error(f"Session {session_name} not found")
            return False
        
        try:
            await client.send_message(entity_id, message)
            self.logger.info(f"Message sent to {entity_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}", exc_info=True)
            return False
    
    async def get_participants(self, session_name: str, chat_id: int, limit: int = 1000) -> List[Dict]:
        """Get chat participants"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            raise ValueError(f"Session {session_name} not found")
        
        try:
            participants = []
            async for user in client.iter_participants(chat_id, limit=limit):
                participants.append({
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'phone': user.phone,
                    'is_bot': user.bot
                })
            return participants
        except Exception as e:
            self.logger.error(f"Failed to get participants: {e}", exc_info=True)
            return []
    
    async def invite_user(self, session_name: str, chat_id: int, user_id: int) -> bool:
        """Invite user to chat"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            self.logger.error(f"Session {session_name} not found")
            return False
        
        try:
            await client(functions.channels.InviteToChannelRequest(
                channel=chat_id,
                users=[user_id]
            ))
            self.logger.info(f"User {user_id} invited to {chat_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to invite user: {e}", exc_info=True)
            return False
    
    async def check_phone_number(self, session_name: str, phone: str) -> Optional[Dict]:
        """Check if phone number is registered on Telegram"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            self.logger.error(f"Session {session_name} not found")
            return None
        
        try:
            result = await client(functions.contacts.ResolveUsernameRequest(phone))
            if result.users:
                user = result.users[0]
                return {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'phone': user.phone
                }
        except Exception as e:
            self.logger.debug(f"Phone {phone} not found or error: {e}")
        
        return None
    
    async def setup_auto_responder(self, session_name: str, response_text: str):
        """Setup auto-responder for incoming messages"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            self.logger.error(f"Session {session_name} not found")
            return
        
        self.auto_responder_active = True
        self.auto_response_text = response_text
        
        @client.on(events.NewMessage(incoming=True))
        async def auto_respond(event):
            if self.auto_responder_active and not event.is_private:
                return
            
            try:
                await event.respond(self.auto_response_text)
                self.logger.info(f"Auto-responded to {event.sender_id}")
            except Exception as e:
                self.logger.error(f"Auto-responder error: {e}")
        
        self.logger.info("Auto-responder activated")
    
    def stop_auto_responder(self):
        """Stop auto-responder"""
        self.auto_responder_active = False
        self.logger.info("Auto-responder deactivated")


class TaskManager:
    """Manages background tasks and operations"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.tasks: Dict[str, Dict] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        self._lock = threading.Lock()
    
    def add_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        """Add task to manager"""
        with self._lock:
            if task_id in self.tasks:
                self.logger.warning(f"Task {task_id} already exists")
                return
            
            future = self.executor.submit(task_func, *args, **kwargs)
            self.tasks[task_id] = {
                'future': future,
                'created_at': datetime.now(),
                'status': 'running'
            }
            self.logger.info(f"Task {task_id} added")
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            if task['future'].done():
                if task['future'].exception():
                    task['status'] = 'failed'
                else:
                    task['status'] = 'completed'
            
            return task['status']
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            success = task['future'].cancel()
            if success:
                task['status'] = 'cancelled'
                self.logger.info(f"Task {task_id} cancelled")
            
            return success
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """Get all tasks"""
        with self._lock:
            return self.tasks.copy()
    
    def cleanup_completed_tasks(self):
        """Remove completed/failed/cancelled tasks"""
        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if task['future'].done() or task['status'] in ['completed', 'failed', 'cancelled']:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
            
            if to_remove:
                self.logger.info(f"Cleaned up {len(to_remove)} tasks")
    
    def shutdown(self):
        """Shutdown task manager"""
        self.executor.shutdown(wait=True)
        self.logger.info("Task manager shutdown")


class ProfileManager:
    """Manages user profiles and editing"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.profiles_file = "profiles.json"
        self.profiles: Dict[str, Dict] = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, Dict]:
        """Load profiles from file"""
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}")
        return {}
    
    def _save_profiles(self):
        """Save profiles to file"""
        try:
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save profiles: {e}")
    
    def create_profile(self, name: str, data: Dict) -> bool:
        """Create new profile"""
        if name in self.profiles:
            self.logger.warning(f"Profile {name} already exists")
            return False
        
        self.profiles[name] = {
            **data,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self._save_profiles()
        self.logger.info(f"Profile {name} created")
        return True
    
    def update_profile(self, name: str, data: Dict) -> bool:
        """Update existing profile"""
        if name not in self.profiles:
            self.logger.warning(f"Profile {name} not found")
            return False
        
        self.profiles[name].update(data)
        self.profiles[name]['updated_at'] = datetime.now().isoformat()
        self._save_profiles()
        self.logger.info(f"Profile {name} updated")
        return True
    
    def delete_profile(self, name: str) -> bool:
        """Delete profile"""
        if name not in self.profiles:
            self.logger.warning(f"Profile {name} not found")
            return False
        
        del self.profiles[name]
        self._save_profiles()
        self.logger.info(f"Profile {name} deleted")
        return True
    
    def get_profile(self, name: str) -> Optional[Dict]:
        """Get profile by name"""
        return self.profiles.get(name)
    
    def list_profiles(self) -> List[str]:
        """List all profile names"""
        return list(self.profiles.keys())


class MaxBigDigGUI:
    """Main GUI class with proper threading integration"""
    
    def __init__(self):
        if not GUI_AVAILABLE:
            raise RuntimeError("GUI not available. tkinter module not found.")
            
        self.logger = Logger()
        self.asyncio_manager = AsyncioManager(self.logger)
        self.session_manager = SessionManager(self.logger)
        self.telegram_ops = TelegramOperations(self.session_manager, self.logger)
        self.task_manager = TaskManager(self.logger)
        self.profile_manager = ProfileManager(self.logger)
        
        self.root = tk.Tk()
        self.root.title("MaxBigDigApp - Telegram Client")
        self.root.geometry("1200x800")
        
        # Thread-safe communication
        self.gui_queue = ThreadSafeQueue()
        
        self._setup_gui()
        self._setup_closing_handler()
        
        # Start asyncio manager
        self.asyncio_manager.start()
        
        # Setup periodic GUI updates
        self._schedule_gui_updates()
    
    def _setup_gui(self):
        """Setup main GUI interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self._create_session_tab()
        self._create_accounts_tab()
        self._create_messages_tab()
        self._create_users_tab()
        self._create_tasks_tab()
        self._create_profiles_tab()
        self._create_logs_tab()
    
    def _create_session_tab(self):
        """Create session management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Sessions")
        
        # Session creation
        session_frame = ttk.LabelFrame(frame, text="Create Session")
        session_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(session_frame, text="Session Name:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.session_name_var = tk.StringVar()
        ttk.Entry(session_frame, textvariable=self.session_name_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(session_frame, text="API ID:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.api_id_var = tk.StringVar()
        ttk.Entry(session_frame, textvariable=self.api_id_var, width=15).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(session_frame, text="API Hash:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.api_hash_var = tk.StringVar()
        ttk.Entry(session_frame, textvariable=self.api_hash_var, width=40).grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        
        ttk.Label(session_frame, text="Phone:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.phone_var = tk.StringVar()
        ttk.Entry(session_frame, textvariable=self.phone_var, width=20).grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Button(session_frame, text="Create Session", command=self._create_session).grid(row=2, column=2, padx=5, pady=2)
        
        # Authorization
        auth_frame = ttk.LabelFrame(frame, text="Authorization")
        auth_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(auth_frame, text="Code:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.code_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.code_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(auth_frame, text="Password (if 2FA):").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.password_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.password_var, width=20, show='*').grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Button(auth_frame, text="Authorize", command=self._authorize_session).grid(row=0, column=4, padx=5, pady=2)
        
        # Active sessions
        sessions_frame = ttk.LabelFrame(frame, text="Active Sessions")
        sessions_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.sessions_tree = ttk.Treeview(sessions_frame, columns=('Status',), show='tree headings')
        self.sessions_tree.heading('#0', text='Session Name')
        self.sessions_tree.heading('Status', text='Status')
        self.sessions_tree.pack(fill='both', expand=True)
    
    def _create_accounts_tab(self):
        """Create accounts management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Accounts")
        
        # Account selection
        account_frame = ttk.LabelFrame(frame, text="Select Account")
        account_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(account_frame, text="Session:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.selected_session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(account_frame, textvariable=self.selected_session_var, width=20)
        self.session_combo.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(account_frame, text="Refresh", command=self._refresh_sessions).grid(row=0, column=2, padx=5, pady=2)
        
        # Account info
        info_frame = ttk.LabelFrame(frame, text="Account Information")
        info_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.account_info_text = scrolledtext.ScrolledText(info_frame, height=20)
        self.account_info_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def _create_messages_tab(self):
        """Create messages tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Messages")
        
        # Message sending
        send_frame = ttk.LabelFrame(frame, text="Send Message")
        send_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(send_frame, text="To (ID):").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.target_id_var = tk.StringVar()
        ttk.Entry(send_frame, textvariable=self.target_id_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(send_frame, text="Message:").grid(row=1, column=0, sticky='nw', padx=5, pady=2)
        self.message_text = tk.Text(send_frame, height=4, width=60)
        self.message_text.grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        
        ttk.Button(send_frame, text="Send", command=self._send_message).grid(row=1, column=3, padx=5, pady=2, sticky='n')
        
        # Auto-responder
        auto_frame = ttk.LabelFrame(frame, text="Auto-Responder")
        auto_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(auto_frame, text="Response Text:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.auto_response_var = tk.StringVar()
        ttk.Entry(auto_frame, textvariable=self.auto_response_var, width=50).grid(row=0, column=1, padx=5, pady=2)
        
        self.auto_responder_active_var = tk.BooleanVar()
        self.auto_responder_check = ttk.Checkbutton(auto_frame, text="Active", variable=self.auto_responder_active_var, command=self._toggle_auto_responder)
        self.auto_responder_check.grid(row=0, column=2, padx=5, pady=2)
    
    def _create_users_tab(self):
        """Create users management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Users")
        
        # User parsing
        parse_frame = ttk.LabelFrame(frame, text="Parse Users")
        parse_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(parse_frame, text="Chat ID:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.chat_id_var = tk.StringVar()
        ttk.Entry(parse_frame, textvariable=self.chat_id_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(parse_frame, text="Limit:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.parse_limit_var = tk.StringVar(value="1000")
        ttk.Entry(parse_frame, textvariable=self.parse_limit_var, width=10).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Button(parse_frame, text="Parse Users", command=self._parse_users).grid(row=0, column=4, padx=5, pady=2)
        
        # Users list
        users_frame = ttk.LabelFrame(frame, text="Users")
        users_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.users_tree = ttk.Treeview(users_frame, columns=('ID', 'Name', 'Username', 'Phone'), show='headings')
        self.users_tree.heading('ID', text='ID')
        self.users_tree.heading('Name', text='Name')
        self.users_tree.heading('Username', text='Username')
        self.users_tree.heading('Phone', text='Phone')
        
        users_scrollbar = ttk.Scrollbar(users_frame, orient='vertical', command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=users_scrollbar.set)
        
        self.users_tree.pack(side='left', fill='both', expand=True)
        users_scrollbar.pack(side='right', fill='y')
        
        # Invite controls
        invite_frame = ttk.LabelFrame(frame, text="Invite Users")
        invite_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(invite_frame, text="Target Chat ID:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.invite_chat_id_var = tk.StringVar()
        ttk.Entry(invite_frame, textvariable=self.invite_chat_id_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(invite_frame, text="Invite Selected", command=self._invite_selected_users).grid(row=0, column=2, padx=5, pady=2)
    
    def _create_tasks_tab(self):
        """Create tasks management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Tasks")
        
        # Tasks list
        tasks_frame = ttk.LabelFrame(frame, text="Active Tasks")
        tasks_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.tasks_tree = ttk.Treeview(tasks_frame, columns=('Status', 'Created'), show='tree headings')
        self.tasks_tree.heading('#0', text='Task ID')
        self.tasks_tree.heading('Status', text='Status')
        self.tasks_tree.heading('Created', text='Created At')
        self.tasks_tree.pack(fill='both', expand=True)
        
        # Task controls
        task_controls_frame = ttk.Frame(frame)
        task_controls_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(task_controls_frame, text="Refresh", command=self._refresh_tasks).pack(side='left', padx=5)
        ttk.Button(task_controls_frame, text="Cancel Selected", command=self._cancel_selected_task).pack(side='left', padx=5)
        ttk.Button(task_controls_frame, text="Cleanup Completed", command=self._cleanup_tasks).pack(side='left', padx=5)
    
    def _create_profiles_tab(self):
        """Create profiles management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Profiles")
        
        # Profile creation
        create_frame = ttk.LabelFrame(frame, text="Create/Edit Profile")
        create_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(create_frame, text="Profile Name:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.profile_name_var = tk.StringVar()
        ttk.Entry(create_frame, textvariable=self.profile_name_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(create_frame, text="Load", command=self._load_profile).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(create_frame, text="Save", command=self._save_profile).grid(row=0, column=3, padx=5, pady=2)
        ttk.Button(create_frame, text="Delete", command=self._delete_profile).grid(row=0, column=4, padx=5, pady=2)
        
        # Profile data
        data_frame = ttk.LabelFrame(frame, text="Profile Data")
        data_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.profile_data_text = scrolledtext.ScrolledText(data_frame)
        self.profile_data_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Profiles list
        list_frame = ttk.LabelFrame(frame, text="Existing Profiles")
        list_frame.pack(fill='x', padx=5, pady=5)
        
        self.profiles_listbox = tk.Listbox(list_frame, height=5)
        self.profiles_listbox.pack(fill='x', padx=5, pady=5)
        self.profiles_listbox.bind('<Double-1>', self._on_profile_double_click)
        
        self._refresh_profiles_list()
    
    def _create_logs_tab(self):
        """Create logs tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Logs")
        
        self.logs_text = scrolledtext.ScrolledText(frame)
        self.logs_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Add log handler to display logs in GUI
        log_handler = GuiLogHandler(self.logs_text)
        self.logger.logger.addHandler(log_handler)
    
    def _setup_closing_handler(self):
        """Setup proper application closing"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _schedule_gui_updates(self):
        """Schedule periodic GUI updates"""
        self._process_gui_queue()
        self.root.after(100, self._schedule_gui_updates)
    
    def _process_gui_queue(self):
        """Process GUI update queue"""
        while not self.gui_queue.empty():
            try:
                item = self.gui_queue.get(timeout=0.01)
                if item:
                    item()
            except:
                break
    
    def _run_async_task(self, coro, callback=None):
        """Run async task and optionally call callback with result"""
        def task_runner():
            try:
                future = self.asyncio_manager.run_coroutine_threadsafe(coro)
                result = future.result(timeout=30)
                if callback:
                    self.gui_queue.put(lambda: callback(result))
            except Exception as e:
                self.logger.error(f"Async task failed: {e}", exc_info=True)
                if callback:
                    self.gui_queue.put(lambda: callback(None))
        
        threading.Thread(target=task_runner, daemon=True).start()
    
    # Session management methods
    def _create_session(self):
        """Create new Telegram session"""
        session_name = self.session_name_var.get().strip()
        api_id = self.api_id_var.get().strip()
        api_hash = self.api_hash_var.get().strip()
        phone = self.phone_var.get().strip()
        
        if not all([session_name, api_id, api_hash, phone]):
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        try:
            api_id = int(api_id)
        except ValueError:
            messagebox.showerror("Error", "API ID must be a number")
            return
        
        def on_result(client):
            if client:
                messagebox.showinfo("Success", f"Session {session_name} created. Check for SMS code.")
            else:
                messagebox.showerror("Error", "Failed to create session")
        
        self._run_async_task(
            self.session_manager.create_session(session_name, api_id, api_hash, phone),
            on_result
        )
    
    def _authorize_session(self):
        """Authorize session with code"""
        session_name = self.session_name_var.get().strip()
        code = self.code_var.get().strip()
        password = self.password_var.get().strip()
        
        if not session_name or not code:
            messagebox.showerror("Error", "Please provide session name and code")
            return
        
        async def authorize():
            client = await self.session_manager.get_client(session_name)
            if not client:
                # Try to get from sessions directory
                session_path = self.session_manager.sessions_dir / f"{session_name}.session"
                if session_path.exists():
                    api_id = int(self.api_id_var.get())
                    api_hash = self.api_hash_var.get()
                    client = TelegramClient(str(session_path), api_id, api_hash)
                    await client.connect()
                else:
                    return False
            
            success = await self.session_manager.authorize_session(client, code, password or None)
            if success:
                with self.session_manager._lock:
                    self.session_manager.active_clients[session_name] = client
            return success
        
        def on_result(success):
            if success:
                messagebox.showinfo("Success", f"Session {session_name} authorized successfully")
                self._refresh_sessions()
            else:
                messagebox.showerror("Error", "Authorization failed")
        
        self._run_async_task(authorize(), on_result)
    
    def _refresh_sessions(self):
        """Refresh sessions list"""
        sessions = list(self.session_manager.active_clients.keys())
        self.session_combo['values'] = sessions
        
        # Update sessions tree
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        for session_name in sessions:
            self.sessions_tree.insert('', 'end', text=session_name, values=('Active',))
    
    # Message methods
    def _send_message(self):
        """Send message"""
        session_name = self.selected_session_var.get().strip()
        target_id = self.target_id_var.get().strip()
        message = self.message_text.get(1.0, tk.END).strip()
        
        if not all([session_name, target_id, message]):
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        try:
            target_id = int(target_id)
        except ValueError:
            messagebox.showerror("Error", "Target ID must be a number")
            return
        
        def on_result(success):
            if success:
                messagebox.showinfo("Success", "Message sent successfully")
                self.message_text.delete(1.0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to send message")
        
        self._run_async_task(
            self.telegram_ops.send_message(session_name, target_id, message),
            on_result
        )
    
    def _toggle_auto_responder(self):
        """Toggle auto-responder"""
        session_name = self.selected_session_var.get().strip()
        if not session_name:
            messagebox.showerror("Error", "Please select a session")
            self.auto_responder_active_var.set(False)
            return
        
        if self.auto_responder_active_var.get():
            response_text = self.auto_response_var.get().strip()
            if not response_text:
                messagebox.showerror("Error", "Please enter response text")
                self.auto_responder_active_var.set(False)
                return
            
            self._run_async_task(
                self.telegram_ops.setup_auto_responder(session_name, response_text)
            )
        else:
            self.telegram_ops.stop_auto_responder()
    
    # User methods
    def _parse_users(self):
        """Parse users from chat"""
        session_name = self.selected_session_var.get().strip()
        chat_id = self.chat_id_var.get().strip()
        limit = self.parse_limit_var.get().strip()
        
        if not all([session_name, chat_id]):
            messagebox.showerror("Error", "Please provide session and chat ID")
            return
        
        try:
            chat_id = int(chat_id)
            limit = int(limit) if limit else 1000
        except ValueError:
            messagebox.showerror("Error", "Chat ID and limit must be numbers")
            return
        
        def on_result(participants):
            if participants is not None:
                # Clear existing users
                for item in self.users_tree.get_children():
                    self.users_tree.delete(item)
                
                # Add new users
                for user in participants:
                    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    self.users_tree.insert('', 'end', values=(
                        user.get('id', ''),
                        name,
                        user.get('username', ''),
                        user.get('phone', '')
                    ))
                
                messagebox.showinfo("Success", f"Parsed {len(participants)} users")
            else:
                messagebox.showerror("Error", "Failed to parse users")
        
        self._run_async_task(
            self.telegram_ops.get_participants(session_name, chat_id, limit),
            on_result
        )
    
    def _invite_selected_users(self):
        """Invite selected users"""
        session_name = self.selected_session_var.get().strip()
        chat_id = self.invite_chat_id_var.get().strip()
        
        if not all([session_name, chat_id]):
            messagebox.showerror("Error", "Please provide session and target chat ID")
            return
        
        try:
            chat_id = int(chat_id)
        except ValueError:
            messagebox.showerror("Error", "Chat ID must be a number")
            return
        
        selected_items = self.users_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Please select users to invite")
            return
        
        user_ids = []
        for item in selected_items:
            values = self.users_tree.item(item, 'values')
            if values and values[0]:
                try:
                    user_ids.append(int(values[0]))
                except ValueError:
                    continue
        
        if not user_ids:
            messagebox.showerror("Error", "No valid user IDs selected")
            return
        
        def invite_task():
            success_count = 0
            for user_id in user_ids:
                try:
                    future = self.asyncio_manager.run_coroutine_threadsafe(
                        self.telegram_ops.invite_user(session_name, chat_id, user_id)
                    )
                    if future.result(timeout=10):
                        success_count += 1
                    # Add delay between invites
                    import time
                    time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Failed to invite user {user_id}: {e}")
            
            self.gui_queue.put(lambda: messagebox.showinfo("Completed", f"Invited {success_count}/{len(user_ids)} users"))
        
        self.task_manager.add_task(f"invite_{datetime.now().timestamp()}", invite_task)
        messagebox.showinfo("Started", f"Invitation task started for {len(user_ids)} users")
    
    # Task methods
    def _refresh_tasks(self):
        """Refresh tasks list"""
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        tasks = self.task_manager.get_all_tasks()
        for task_id, task_info in tasks.items():
            status = self.task_manager.get_task_status(task_id)
            created_at = task_info['created_at'].strftime('%H:%M:%S')
            self.tasks_tree.insert('', 'end', text=task_id, values=(status, created_at))
    
    def _cancel_selected_task(self):
        """Cancel selected task"""
        selected_item = self.tasks_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a task to cancel")
            return
        
        task_id = self.tasks_tree.item(selected_item[0], 'text')
        if self.task_manager.cancel_task(task_id):
            messagebox.showinfo("Success", f"Task {task_id} cancelled")
            self._refresh_tasks()
        else:
            messagebox.showerror("Error", f"Failed to cancel task {task_id}")
    
    def _cleanup_tasks(self):
        """Cleanup completed tasks"""
        self.task_manager.cleanup_completed_tasks()
        self._refresh_tasks()
        messagebox.showinfo("Success", "Completed tasks cleaned up")
    
    # Profile methods
    def _load_profile(self):
        """Load profile"""
        profile_name = self.profile_name_var.get().strip()
        if not profile_name:
            messagebox.showerror("Error", "Please enter profile name")
            return
        
        profile_data = self.profile_manager.get_profile(profile_name)
        if profile_data:
            self.profile_data_text.delete(1.0, tk.END)
            self.profile_data_text.insert(1.0, json.dumps(profile_data, indent=2, ensure_ascii=False))
            messagebox.showinfo("Success", f"Profile {profile_name} loaded")
        else:
            messagebox.showerror("Error", f"Profile {profile_name} not found")
    
    def _save_profile(self):
        """Save profile"""
        profile_name = self.profile_name_var.get().strip()
        if not profile_name:
            messagebox.showerror("Error", "Please enter profile name")
            return
        
        try:
            profile_data = json.loads(self.profile_data_text.get(1.0, tk.END))
            if self.profile_manager.create_profile(profile_name, profile_data):
                messagebox.showinfo("Success", f"Profile {profile_name} saved")
                self._refresh_profiles_list()
            else:
                # Try update
                if self.profile_manager.update_profile(profile_name, profile_data):
                    messagebox.showinfo("Success", f"Profile {profile_name} updated")
                else:
                    messagebox.showerror("Error", f"Failed to save profile {profile_name}")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON format: {e}")
    
    def _delete_profile(self):
        """Delete profile"""
        profile_name = self.profile_name_var.get().strip()
        if not profile_name:
            messagebox.showerror("Error", "Please enter profile name")
            return
        
        if messagebox.askyesno("Confirm", f"Delete profile {profile_name}?"):
            if self.profile_manager.delete_profile(profile_name):
                messagebox.showinfo("Success", f"Profile {profile_name} deleted")
                self._refresh_profiles_list()
                self.profile_data_text.delete(1.0, tk.END)
            else:
                messagebox.showerror("Error", f"Failed to delete profile {profile_name}")
    
    def _refresh_profiles_list(self):
        """Refresh profiles list"""
        self.profiles_listbox.delete(0, tk.END)
        for profile_name in self.profile_manager.list_profiles():
            self.profiles_listbox.insert(tk.END, profile_name)
    
    def _on_profile_double_click(self, event):
        """Handle profile double click"""
        selection = self.profiles_listbox.curselection()
        if selection:
            profile_name = self.profiles_listbox.get(selection[0])
            self.profile_name_var.set(profile_name)
            self._load_profile()
    
    def _on_closing(self):
        """Handle application closing"""
        try:
            # Shutdown components
            self.task_manager.shutdown()
            
            # Disconnect all sessions
            async def disconnect_all():
                await self.session_manager.disconnect_all()
            
            if self.asyncio_manager.loop:
                future = self.asyncio_manager.run_coroutine_threadsafe(disconnect_all())
                future.result(timeout=5)
            
            # Shutdown asyncio manager
            self.asyncio_manager.shutdown()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.logger.info("MaxBigDigApp started")
        self.root.mainloop()


class MaxBigDigAPI:
    """Headless API for MaxBigDigApp functionality"""
    
    def __init__(self):
        self.logger = Logger("MaxBigDigAPI")
        self.asyncio_manager = AsyncioManager(self.logger)
        self.session_manager = SessionManager(self.logger)
        self.telegram_ops = TelegramOperations(self.session_manager, self.logger)
        self.task_manager = TaskManager(self.logger)
        self.profile_manager = ProfileManager(self.logger)
        
        # Start asyncio manager
        self.asyncio_manager.start()
        self.logger.info("MaxBigDigAPI initialized")
    
    async def create_session(self, session_name: str, api_id: int, api_hash: str, phone: str) -> bool:
        """Create and setup Telegram session"""
        client = await self.session_manager.create_session(session_name, api_id, api_hash, phone)
        return client is not None
    
    async def authorize_session(self, session_name: str, code: str, password: str = None) -> bool:
        """Authorize session with verification code"""
        client = await self.session_manager.get_client(session_name)
        if not client:
            return False
        return await self.session_manager.authorize_session(client, code, password)
    
    async def send_message(self, session_name: str, entity_id: int, message: str) -> bool:
        """Send message to entity"""
        return await self.telegram_ops.send_message(session_name, entity_id, message)
    
    async def get_participants(self, session_name: str, chat_id: int, limit: int = 1000) -> List[Dict]:
        """Get chat participants"""
        return await self.telegram_ops.get_participants(session_name, chat_id, limit)
    
    async def invite_users(self, session_name: str, chat_id: int, user_ids: List[int], delay: int = 2) -> Dict:
        """Invite multiple users to chat with delay"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        for user_id in user_ids:
            try:
                success = await self.telegram_ops.invite_user(session_name, chat_id, user_id)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to invite user {user_id}")
                
                # Add delay between invites
                await asyncio.sleep(delay)
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error inviting user {user_id}: {e}")
        
        return results
    
    async def setup_auto_responder(self, session_name: str, response_text: str):
        """Setup auto-responder"""
        await self.telegram_ops.setup_auto_responder(session_name, response_text)
    
    def stop_auto_responder(self):
        """Stop auto-responder"""
        self.telegram_ops.stop_auto_responder()
    
    def create_profile(self, name: str, data: Dict) -> bool:
        """Create user profile"""
        return self.profile_manager.create_profile(name, data)
    
    def get_profile(self, name: str) -> Optional[Dict]:
        """Get user profile"""
        return self.profile_manager.get_profile(name)
    
    def list_sessions(self) -> List[str]:
        """List active sessions"""
        return list(self.session_manager.active_clients.keys())
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status"""
        return self.task_manager.get_task_status(task_id)
    
    def add_background_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        """Add background task"""
        self.task_manager.add_task(task_id, task_func, *args, **kwargs)
    
    async def shutdown(self):
        """Shutdown API and cleanup resources"""
        try:
            await self.session_manager.disconnect_all()
            self.task_manager.shutdown()
            self.asyncio_manager.shutdown()
            self.logger.info("MaxBigDigAPI shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


class GuiLogHandler(logging.Handler):
    """Custom log handler for GUI display"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    def emit(self, record):
        """Emit log record to GUI"""
        if not GUI_AVAILABLE:
            return
            
        try:
            msg = self.format(record)
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            
            # Limit log size
            lines = int(self.text_widget.index('end-1c').split('.')[0])
            if lines > 1000:
                self.text_widget.delete(1.0, '500.0')
        except:
            pass


def main():
    """Main entry point"""
    try:
        if GUI_AVAILABLE:
            app = MaxBigDigGUI()
            app.run()
        else:
            print("MaxBigDigApp - GUI not available")
            print("For headless operation, use the individual components programmatically")
            print("Example: python test_max_big_dig_app.py")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
import sqlite3
from datetime import datetime, timedelta

def create_dbx():
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS forms (
        user_id INTEGER PRIMARY KEY,
        citizenship TEXT,
        age TEXT,
        fullname TEXT,
        city TEXT,
        address TEXT,
        bad_habits TEXT,
        username TEXT,
        travel TEXT,
        license TEXT,
        phone TEXT,
        passport TEXT,
        experience TEXT,
        passport_front TEXT,
        passport_back TEXT,
        selfie TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_form(data, user_id):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO forms (
        user_id, citizenship, age, fullname, city, address, bad_habits, username, 
        travel, license, phone, passport, experience, passport_front, passport_back, selfie
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
    (
        user_id,
        data.get('citizenship', ''),
        data.get('age', ''),
        data.get('fullname', ''),
        data.get('city', ''),
        data.get('address', ''),
        data.get('bad_habits', ''),
        data.get('username', ''),
        data.get('travel', ''),
        data.get('license', ''),
        data.get('phone', ''),
        data.get('passport', ''),
        data.get('experience', ''),
        data.get('passport_front', ''),
        data.get('passport_back', 'N/A'),
        data.get('selfie', '')
    ))
    conn.commit()
    conn.close()

def get_transferred_fullnames_by_period(days):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    date_limit = datetime.now() - timedelta(days=days)
    c.execute('''SELECT fullname, created_at FROM forms 
                 WHERE status = 'передан' AND created_at >= ?''', (date_limit,))
    results = [{'fullname': row[0], 'created_at': row[1]} for row in c.fetchall()]
    conn.close()
    return results

def is_user_blacklisted(user_id):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT status FROM forms WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 'швырь'

def update_status(user_id, status):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('UPDATE forms SET status = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def get_form_by_user_id(user_id):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM forms WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    columns = [desc[0] for desc in c.description]
    conn.close()
    if result:
        return dict(zip(columns, result))
    return None

def search_by_fullname(fullname):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM forms WHERE fullname LIKE ?', (f'%{fullname}%',))
    results = c.fetchall()
    columns = [desc[0] for desc in c.description]
    conn.close()
    if results:
        return [dict(zip(columns, row)) for row in results]
    return []

def search_by_phone(phone):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM forms WHERE phone LIKE ?', (f'%{phone}%',))
    results = c.fetchall()
    columns = [desc[0] for desc in c.description]
    conn.close()
    if results:
        return [dict(zip(columns, row)) for row in results]
    return []

def get_count_by_period(days):
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    date_limit = datetime.now() - timedelta(days=days)
    c.execute('SELECT COUNT(*) FROM forms WHERE status = ? AND created_at >= ?', ('передан', date_limit))
    count = c.fetchone()[0]
    conn.close()
    return count

# ==== СТАТИСТИКА ====
def get_total_users():
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM forms')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_forms():
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM forms')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_rejected():
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM forms WHERE status='швырь'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_transferred():
    conn = sqlite3.connect('forms.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM forms WHERE status='передан'")
    count = c.fetchone()[0]
    conn.close()
    return count
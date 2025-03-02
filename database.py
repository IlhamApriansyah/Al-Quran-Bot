import sqlite3

# Inisialisasi database
def init_db():
    conn = sqlite3.connect('quran_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                 (user_id INTEGER, surah_number INTEGER, verse_number INTEGER, surah_name TEXT)''')
    conn.commit()
    conn.close()

# Tambahkan penanda
def add_bookmark(user_id, surah_number, verse_number, surah_name):
    conn = sqlite3.connect('quran_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO bookmarks (user_id, surah_number, verse_number, surah_name) VALUES (?, ?, ?, ?)",
              (user_id, surah_number, verse_number, surah_name))
    conn.commit()
    conn.close()

# Ambil daftar penanda
def get_bookmarks(user_id, keyword=None):
    conn = sqlite3.connect('quran_bot.db')
    c = conn.cursor()
    if keyword:
        c.execute("SELECT surah_number, verse_number, surah_name FROM bookmarks WHERE user_id=? AND surah_name LIKE ?",
                  (user_id, f"%{keyword}%"))
    else:
        c.execute("SELECT surah_number, verse_number, surah_name FROM bookmarks WHERE user_id=?", (user_id,))
    bookmarks = [{'surah_number': row[0], 'verse_number': row[1], 'surah_name': row[2]} for row in c.fetchall()]
    conn.close()
    return bookmarks


# Inisialisasi database saat pertama kali dijalankan
init_db()
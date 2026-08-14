import sqlite3

conn = sqlite3.connect('/var/www/html/avaliacoes.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        nota INTEGER NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()
print("✅ Banco de dados criado com sucesso!")

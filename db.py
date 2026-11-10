import asyncpg
from .config import settings

SCHEMA = '''
CREATE TABLE IF NOT EXISTS players (
 discord_id BIGINT PRIMARY KEY, username TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS registrations (
 id BIGSERIAL PRIMARY KEY, captain_id BIGINT NOT NULL, partner_id BIGINT NOT NULL,
 team_name TEXT NOT NULL, entry_fee_cents INTEGER NOT NULL CHECK(entry_fee_cents>0),
 status TEXT NOT NULL DEFAULT 'awaiting_payment', created_at TIMESTAMPTZ DEFAULT NOW(),
 CHECK(captain_id<>partner_id)
);
CREATE TABLE IF NOT EXISTS payments (
 id BIGSERIAL PRIMARY KEY, registration_id BIGINT NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0), proof_reference TEXT,
 status TEXT NOT NULL DEFAULT 'pending', reviewed_by BIGINT, review_note TEXT,
 created_at TIMESTAMPTZ DEFAULT NOW(), reviewed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS matches (
 id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, starts_at TEXT NOT NULL,
 room_info TEXT NOT NULL DEFAULT 'A definir', status TEXT NOT NULL DEFAULT 'scheduled',
 created_by BIGINT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS settings (
 key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMPTZ DEFAULT NOW()
);
'''

class Database:
    pool = None
    async def connect(self):
        url = settings.database_url.replace("postgres://", "postgresql://", 1)
        self.pool = await asyncpg.create_pool(url, min_size=1, max_size=5, command_timeout=30)
        async with self.pool.acquire() as c:
            await c.execute(SCHEMA)
            await c.execute("INSERT INTO settings(key,value) VALUES('pix_key',$1) ON CONFLICT(key) DO NOTHING", settings.pix_key)
            await c.execute("INSERT INTO settings(key,value) VALUES('pix_receiver',$1) ON CONFLICT(key) DO NOTHING", settings.pix_receiver)
    async def close(self):
        if self.pool: await self.pool.close()
    async def setting(self, key, default=""):
        async with self.pool.acquire() as c:
            row = await c.fetchrow("SELECT value FROM settings WHERE key=$1", key)
            return row["value"] if row else default
    async def set_setting(self, key, value):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO settings(key,value) VALUES($1,$2) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=NOW()", key, str(value))

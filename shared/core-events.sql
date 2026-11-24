-- Additive contract v1. No prompts, tool arguments, window titles, or credentials.
CREATE TABLE IF NOT EXISTS core_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TRIGGER IF NOT EXISTS core_events_bound AFTER INSERT ON core_events
BEGIN
  DELETE FROM core_events WHERE seq <= NEW.seq - 2000;
END;
CREATE TRIGGER IF NOT EXISTS core_chat_created AFTER INSERT ON chats
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('chat',NEW.id,'created');
END;
CREATE TRIGGER IF NOT EXISTS core_chat_changed AFTER UPDATE ON chats
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('chat',NEW.id,'updated');
END;
CREATE TRIGGER IF NOT EXISTS core_chat_deleted AFTER DELETE ON chats
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('chat',OLD.id,'deleted');
END;
CREATE TRIGGER IF NOT EXISTS core_exchange_created AFTER INSERT ON exchanges
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('conversation',NEW.chat_id,'appended');
END;
CREATE TRIGGER IF NOT EXISTS core_setting_created AFTER INSERT ON preferences
WHEN NEW.key IN ('core.voice_style','core.mode','active')
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('setting',NEW.key,'updated');
END;
CREATE TRIGGER IF NOT EXISTS core_setting_changed AFTER UPDATE ON preferences
WHEN NEW.key IN ('core.voice_style','core.mode','active') AND OLD.value IS NOT NEW.value
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('setting',NEW.key,'updated');
END;
CREATE TABLE IF NOT EXISTS core_activity (
  client_id TEXT PRIMARY KEY,
  interface TEXT NOT NULL CHECK(interface IN ('classic','pet')),
  state TEXT NOT NULL CHECK(state IN ('IDLE','LISTENING','TRANSCRIBING','THINKING','SPEAKING','ERROR')),
  updated_at REAL NOT NULL
);
CREATE TRIGGER IF NOT EXISTS core_activity_created AFTER INSERT ON core_activity
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('activity',NEW.client_id,NEW.state);
END;
CREATE TRIGGER IF NOT EXISTS core_activity_changed AFTER UPDATE ON core_activity
WHEN OLD.state != NEW.state
BEGIN
  INSERT INTO core_events(topic,entity_id,action) VALUES('activity',NEW.client_id,NEW.state);
END;
INSERT OR IGNORE INTO core_meta(key,value) VALUES('events_version','1');

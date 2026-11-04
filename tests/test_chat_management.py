import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import companion

class ChatDeletionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
  self.patches=[patch.object(companion,'DATA',root),patch.object(companion,'DB_PATH',root/'chat.sqlite3')]
  for p in self.patches:p.start()
  companion.init();self.chat=companion.create()
  with companion.db() as con:
   self.message=con.execute("INSERT INTO messages(conversation,role,content,created) VALUES(?,'user','уникальныйтрактор воспоминание',?)",(self.chat['id'],companion.now())).lastrowid
   con.execute('INSERT INTO attachments VALUES(?,?,?,?)',('a'*32,self.message,'image/png',b'picture'))
  companion.save_memory('Сохранённый отдельный факт',source=self.message)
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_delete_hides_messages_from_history_search_and_context_then_restore_recovers_them(self):
  ident=self.chat['id'];self.assertTrue(companion.search('уникальныйтрактор'))
  companion.remove_conversation(ident);companion.init()
  self.assertEqual(companion.overview()['conversations'],[]);self.assertEqual(companion.search('уникальныйтрактор'),[])
  with self.assertRaises(ValueError):companion.overview(ident)
  self.assertEqual(companion.trashed_conversations()[0]['id'],ident)
  self.assertEqual(len(companion.memories()),1)
  companion.restore_conversation(ident)
  rows=companion.overview(ident)['messages'];self.assertEqual(rows[0]['content'],'уникальныйтрактор воспоминание')
  self.assertEqual(companion.attachment(rows[0]['images'][0]['id'])[1],b'picture')
  self.assertTrue(companion.search('уникальныйтрактор'));self.assertEqual(companion.trashed_conversations(),[])
 def test_generating_conversation_is_not_removed(self):
  with companion.db() as con:con.execute("INSERT INTO messages(conversation,role,status,created) VALUES(?,'assistant','generating',?)",(self.chat['id'],companion.now()))
  with self.assertRaises(BlockingIOError):companion.remove_conversation(self.chat['id'])
  self.assertEqual(len(companion.overview()['conversations']),1)
 def test_invalid_and_missing_identifiers_do_not_change_existing_conversations(self):
  for ident in ['../chat',None,'b'*32]:
   with self.assertRaises(ValueError):companion.remove_conversation(ident)
  self.assertEqual(len(companion.overview()['conversations']),1)
 def test_original_database_schema_migrates_and_still_allows_new_chats(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'old.sqlite3';con=sqlite3.connect(path)
   con.execute('CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL)');con.commit();con.close()
   with patch.object(companion,'DATA',root),patch.object(companion,'DB_PATH',path):
    companion.init();ident=companion.create()['id'];companion.remove_conversation(ident);companion.restore_conversation(ident)
    self.assertEqual(companion.overview()['conversations'][0]['id'],ident)

if __name__=='__main__':unittest.main()

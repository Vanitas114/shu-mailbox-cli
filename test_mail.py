import unittest
from mail import list_messages, MailError, metadata

class Reply:
    status_code = 200
    def __init__(self, body): self.body = body
    def json(self): return self.body

class Session:
    def __init__(self, replies): self.replies = iter(replies); self.requests=[]
    def post(self, url, **kw): self.requests.append((url,kw)); return Reply(next(self.replies))

class MailTests(unittest.TestCase):
    def test_page_and_fields(self):
        s = Session([{'code':'S_OK','var':[{'from':['Alice <alice@example.org>'],'subject':'Hello','receivedDate':'2026-01-01'}], 'total':21}])
        rows,total = list_messages(s,'test-session',1,page=2)
        self.assertEqual(total,21)
        self.assertEqual(rows[0]['person'],'Alice <alice@example.org>')
        self.assertEqual(s.requests[0][1]['json']['start'],20)
        self.assertEqual(s.requests[0][1]['json']['summaryWindowSize'],0)
    def test_todo_uses_virtual_filter_and_excludes_trash(self):
        folders = [{'id':1},{'id':2},{'id':3},{'id':4},{'id':-5,'vp':{'filterFlags':{'deferred':True}}}]
        s = Session([{'code':'S_OK','var':folders}, {'code':'S_OK','var':[]}])
        rows,_ = list_messages(s,'test-session',-5)
        self.assertEqual(rows,[])
        self.assertTrue(s.requests[0][0].endswith('/XT/jsp/mail.jsp'))
        body=s.requests[1][1]['json']
        self.assertEqual(body['fids'],[1,2,3])
        self.assertEqual(body['filterFlags'],{'deferred':True})
    def test_errors_are_not_empty_lists(self):
        with self.assertRaises(MailError): list_messages(Session([{'code':'FA_INVALID_SESSION'}]), 'x', 1)
        with self.assertRaises(MailError): list_messages(Session([{'code':'S_OK','var':{'unrecognized':[]}}]), 'x', 1)
    def test_sent_and_draft_recipients(self):
        self.assertEqual(metadata({'to':['recipient@example.org'],'subject':'x','sentDate':'y'},3)['person'],'recipient@example.org')
        self.assertEqual(metadata({'to':['recipient@example.org'],'subject':'x','receivedDate':'y'},2)['date'],'y')

if __name__=='__main__': unittest.main()

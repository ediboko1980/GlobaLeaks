# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import token
from globaleaks.jobs import anomalies
from globaleaks.rest import errors
from globaleaks.tests import helpers


class Test_TokenCreate(helpers.TestHandlerWithPopulatedDB):
    _handler = token.TokenCreate

    def assert_default_token_values(self, token):
        self.assertEqual(token['type'], 'submission')

    @inlineCallbacks
    def test_post(self):
        yield anomalies.Anomalies().run()

        handler = self.request({'type': 'submission'})

        handler.request.client_using_tor = True

        response = yield handler.post()

        self.assert_default_token_values(response)

    def test_post_disabled_submissions(self):
        self.state.tenant_cache[1]['disable_submissions'] = True

        handler = self.request({'type': 'submission'})

        handler.request.client_using_tor = True

        self.assertRaises(errors.SubmissionDisabled, handler.post)


class Test_TokenInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = token.TokenInstance

    @inlineCallbacks
    def test_put_right_answer(self):
        self.pollute_events()
        yield anomalies.Anomalies().run()

        token = self.state.tokens.new(1, 'submission')
        token.solved = False
        token.question = '7GJ4Sl37AEnP10Zk9p7q'

        request_payload = token.serialize()
        request_payload['answer'] = 26

        handler = self.request(request_payload)

        response = yield handler.put(token.id)

        token.use()

        self.assertTrue(token.solved)

    @inlineCallbacks
    def test_put_wrong_answer(self):
        self.pollute_events()
        yield anomalies.Anomalies().run()

        token = self.state.tokens.new(1, 'submission')
        token.solved = False
        token.question = '7GJ4Sl37AEnP10Zk9p7q'

        request_payload = token.serialize()
        request_payload['answer'] = 0

        handler = self.request(request_payload)

        response = yield handler.put(token.id)

        self.assertRaises(Exception, token.use)

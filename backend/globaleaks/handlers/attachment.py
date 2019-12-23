# -*- coding: utf-8 -*-
#
# Handler dealing with submissions file uploads and subsequent submissions attachments
import base64

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.orm import transact
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now


@transact
def register_ifile_on_db(session, tid, internaltip_id, uploaded_file):
    now = datetime_now()

    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == internaltip_id, models.InternalTip.tid == tid).one()

    itip.update_date = now
    itip.wb_last_access = now

    if itip.crypto_tip_pub_key:
        for k in ['name', 'type', 'size']:
            uploaded_file[k] = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, uploaded_file[k]))

    new_file = models.InternalFile()
    new_file.name = uploaded_file['name']
    new_file.content_type = uploaded_file['type']
    new_file.size = uploaded_file['size']
    new_file.internaltip_id = internaltip_id
    new_file.filename = uploaded_file['filename']
    new_file.submission = uploaded_file['submission']
    new_file.internaltip_id = internaltip_id

    session.add(new_file)

    return serializers.serialize_ifile(session, new_file)


class SubmissionAttachment(BaseHandler):
    """
    WhistleBlower interface to upload a new file for a non-finalized submission
    """
    check_roles = 'none'
    upload_handler = True

    def post(self, token_id):
        token = self.state.tokens.get(token_id)

        self.uploaded_file['submission'] = True

        token.associate_file(self.uploaded_file)


class PostSubmissionAttachment(SubmissionAttachment):
    """
    WhistleBlower interface to upload a new file for an existing submission
    """
    check_roles = 'whistleblower'
    upload_handler = True

    def post(self):
        self.uploaded_file['submission'] = False

        return register_ifile_on_db(self.request.tid, self.current_user.user_id, self.uploaded_file)

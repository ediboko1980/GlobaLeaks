# -*- coding: utf-8
#
# Handlers dealing with user preferences
import pyotp

from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.admin.modelimgs import db_get_model_img
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.models import get_localized_values
from globaleaks.orm import transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.crypto import Base64Encoder, GCE, generateRandomKey
from globaleaks.utils.utility import datetime_to_ISO8601, datetime_now, datetime_null


def parse_pgp_options(user, request):
    """
    Used for parsing PGP key infos and fill related user configurations.
    """
    pgp_key_public = request['pgp_key_public']
    remove_key = request['pgp_key_remove']

    k = None
    if not remove_key and pgp_key_public:
        pgpctx = PGPContext(State.settings.tmp_path)

        k = pgpctx.load_key(pgp_key_public)

    if k is not None:
        user.pgp_key_public = pgp_key_public
        user.pgp_key_fingerprint = k['fingerprint']
        user.pgp_key_expiration = k['expiration']
    else:
        user.pgp_key_public = ''
        user.pgp_key_fingerprint = ''
        user.pgp_key_expiration = datetime_null()


def user_serialize_user(session, user, language):
    """
    Serialize user description

    :param user:
    :param language:
    :param session: the session on which perform queries.
    :return: a serialization of the object
    """
    picture = db_get_model_img(session, 'users', user.id)

    ret_dict = {
        'id': user.id,
        'username': user.username,
        'password': '',
        'old_password': '',
        'salt': '',
        'role': user.role,
        'state': user.state,
        'last_login': datetime_to_ISO8601(user.last_login),
        'name': user.name,
        'description': user.description,
        'public_name': user.public_name,
        'mail_address': user.mail_address,
        'change_email_address': user.change_email_address,
        'language': user.language,
        'password_change_needed': user.password_change_needed,
        'password_change_date': datetime_to_ISO8601(user.password_change_date),
        'pgp_key_fingerprint': user.pgp_key_fingerprint,
        'pgp_key_public': user.pgp_key_public,
        'pgp_key_expiration': datetime_to_ISO8601(user.pgp_key_expiration),
        'pgp_key_remove': False,
        'picture': picture,
        'can_edit_general_settings': user.can_edit_general_settings,
        'can_delete_submission': user.can_delete_submission,
        'can_postpone_expiration': user.can_postpone_expiration,
        'can_grant_permissions': user.can_grant_permissions,
        'recipient_configuration': user.recipient_configuration,
        'tid': user.tid,
        'notification': user.notification,
        'encryption': user.crypto_pub_key != b'',
        'two_factor_enable': user.two_factor_enable
    }

    return get_localized_values(ret_dict, user, user.localized_keys, language)


def db_get_user(session, tid, user_id):
    return models.db_get(session,
                         models.User,
                         models.User.id == user_id,
                         models.User.tid == tid)


@transact
def get_user(session, tid, user_id, language):
    user = db_get_user(session, tid, user_id)

    return user_serialize_user(session, user, language)


def db_user_update_user(session, tid, user_session, request):
    """
    Updates the specified user.
    This version of the function is specific for users that with comparison with
    admins can change only few things:
      - real name
      - email address
      - preferred language
      - the password (with old password check)
      - pgp key
    raises: globaleaks.errors.ResourceNotFound` if the receiver does not exist.
    """
    from globaleaks.handlers.admin.notification import db_get_notification
    from globaleaks.handlers.admin.node import db_admin_serialize_node

    user = models.db_get(session,
                         models.User,
                         models.User.id == user_session.user_id)

    user.language = request.get('language', State.tenant_cache[tid].default_language)
    user.name = request['name']
    user.public_name = request['public_name'] if request['public_name'] else request['name']

    if request['password']:
        if user.password_change_needed:
            user.password_change_needed = False
        else:
            if not GCE.check_password(user.hash_alg,
                                      request['old_password'],
                                      user.salt,
                                      user.password):
                raise errors.InvalidOldPassword

        # Regenerate the password hash only if different from the best choice on the platform
        if user.hash_alg != 'ARGON2':
            user.hash_alg = 'ARGON2'
            user.salt = GCE.generate_salt()

        password_hash = GCE.hash_password(request['password'], user.salt)

        # Check that the new password is different form the current password
        if user.password == password_hash:
            raise errors.PasswordReuseError

        user.password = password_hash
        user.password_change_date = datetime_now()

        if State.tenant_cache[tid].encryption:
            enc_key = GCE.derive_key(request['password'].encode(), user.salt)
            if not user_session.cc:
                # Th First first password change triggers the generation
                # of the user encryption private key and its backup
                user_session.cc, crypto_pub_key = GCE.generate_keypair()
                user.crypto_pub_key = Base64Encoder.encode(crypto_pub_key)
                user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(user_session.cc)

                # If the user had already enabled two factor before encryption was not enable
                # encrypt the two factor secret
                if user.two_factor_secret:
                    user.two_factor_secret = Base64Encoder.encode(GCE.asymmetric_encrypt(user.crypto_pub_key, user.two_factor_secret))

            user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(enc_key, user_session.cc))

    # If the email address changed, send a validation email
    if request['mail_address'] != user.mail_address:
        user.change_email_address = request['mail_address']
        user.change_email_date = datetime_now()
        user.change_email_token = generateRandomKey(32)

        user_desc = user_serialize_user(session, user, user.language)

        user_desc['mail_address'] = request['mail_address']

        template_vars = {
            'type': 'email_validation',
            'user': user_desc,
            'new_email_address': request['mail_address'],
            'validation_token': user.change_email_token,
            'node': db_admin_serialize_node(session, tid, user.language),
            'notification': db_get_notification(session, tid, user.language)
        }

        State.format_and_send_mail(session, tid, user_desc, template_vars)

    parse_pgp_options(user, request)

    return user


@transact
def update_user_settings(session, tid, user_session, request, language):
    user = db_user_update_user(session, tid, user_session, request)

    return user_serialize_user(session, user, language)


@inlineCallbacks
def can_edit_general_settings_or_raise(handler):
    """Determines if this user has ACL permissions to edit general settings"""
    if handler.current_user.user_role == 'admin':
        returnValue(True)
    else:
        # Get the full user so we can see what we can access
        user = yield get_user(handler.current_user.user_tid,
                              handler.current_user.user_id,
                              handler.request.language)
        if user['can_edit_general_settings'] is True:
            returnValue(True)

    raise errors.InvalidAuthentication


class UserInstance(BaseHandler):
    """
    This handler allow users to modify some of their fields:
        - language
        - password
        - notification settings
        - pgp key
    """
    check_roles = 'user'
    invalidate_cache = True

    def get(self):
        return get_user(self.current_user.user_tid,
                        self.current_user.user_id,
                        self.request.language)

    def put(self):
        request = self.validate_message(self.request.content.read(), requests.UserUserDesc)

        return update_user_settings(self.current_user.user_tid,
                                    self.current_user,
                                    request,
                                    self.request.language)


@transact
def get_recovery_key(session, user_tid, user_id, user_cc):
    user = db_get_user(session, user_tid, user_id)

    if not user.crypto_rec_key:
        return ''

    return Base64Encoder().encode(GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(user.crypto_rec_key))).replace(b'=', b'')


@transact
def enable_2fa_step1(session, user_tid, user_id, user_cc):
    user = db_get_user(session, user_tid, user_id)

    if user.two_factor_secret:
        return user.two_factor_secret

    two_factor_secret = pyotp.random_base32()

    if user.crypto_pub_key:
        user.two_factor_secret = Base64Encoder.encode(GCE.asymmetric_encrypt(user.crypto_pub_key, two_factor_secret))
    else:
        user.two_factor_secret = two_factor_secret

    return two_factor_secret


@transact
def enable_2fa_step2(session, user_tid, user_id, user_cc, token):
    user = db_get_user(session, user_tid, user_id)

    if user.crypto_pub_key:
        two_factor_secret = GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(user.two_factor_secret))
    else:
        two_factor_secret = user.two_factor_secret

    # RFC 6238: step size 30 sec; valid_window = 1; total size of the window: 1.30 sec
    if pyotp.TOTP(two_factor_secret).verify(token):
        user.two_factor_enable = True
    else:
        raise errors.InvalidTwoFactorAuthCode


@transact
def disable_2fa(session, user_tid, user_id):
    user = db_get_user(session, user_tid, user_id)

    user.two_factor_enable = False
    user.two_factor_secret = b''


class UserOperationHandler(OperationHandler):
    check_roles = 'user'

    def get_recovery_key(self, req_args, *args, **kwargs):
        return get_recovery_key(self.current_user.user_tid,
                                self.current_user.user_id,
                                self.current_user.cc)

    def enable_2fa_step1(self, req_args, *args, **kwargs):
        return enable_2fa_step1(self.current_user.user_tid,
                                self.current_user.user_id,
                                self.current_user.cc)

    def enable_2fa_step2(self, req_args, *args, **kwargs):
        return enable_2fa_step2(self.current_user.user_tid,
                                self.current_user.user_id,
                                self.current_user.cc,
                                req_args['value'])

    def disable_2fa(self, req_args, *args, **kwargs):
        return disable_2fa(self.current_user.user_tid,
                           self.current_user.user_id)

    def operation_descriptors(self):
        return {
            'get_recovery_key': (UserOperationHandler.get_recovery_key, {}),
            'enable_2fa_step1': (UserOperationHandler.enable_2fa_step1, {}),
            'enable_2fa_step2': (UserOperationHandler.enable_2fa_step2, {'value': str}),
            'disable_2fa': (UserOperationHandler.disable_2fa, {})
        }

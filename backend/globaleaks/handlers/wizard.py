# -*- coding: utf-8
#
# Handlers implementing platform wizard
from globaleaks import models
from globaleaks.db import db_refresh_memory_variables
from globaleaks.handlers.admin.context import db_create_context
from globaleaks.handlers.admin.node import db_update_enabled_languages
from globaleaks.handlers.admin.user import db_create_user
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import config, profiles
from globaleaks.orm import tw
from globaleaks.rest import requests, errors
from globaleaks.utils.utility import datetime_now
from globaleaks.utils.log import log


def db_wizard(session, tid, request, client_using_tor, language):
    language = request['node_language']

    node = config.ConfigFactory(session, tid)

    if tid != 1:
        root_tenant_node = config.ConfigFactory(session, 1)
    else:
        root_tenant_node = node

    if node.get_val('wizard_done'):
        log.err("DANGER: Wizard already initialized!", tid=tid)
        raise errors.ForbiddenOperation

    db_update_enabled_languages(session, tid, [language], language)

    node.set_val('name', request['node_name'])
    node.set_val('default_language', language)
    node.set_val('wizard_done', True)
    node.set_val('enable_developers_exception_notification', request['enable_developers_exception_notification'])

    node_l10n = config.ConfigL10NFactory(session, tid)
    node_l10n.set_val('header_title_homepage', language, request['node_name'])

    profiles.load_profile(session, tid, request['profile'])

    admin_desc = models.User().dict(language)
    admin_desc['name'] = request['admin_name']
    admin_desc['username'] = 'admin'
    admin_desc['password'] = request['admin_password']
    admin_desc['name'] = request['admin_name']
    admin_desc['mail_address'] = request['admin_mail_address']
    admin_desc['language'] = language
    admin_desc['role'] = 'admin'
    admin_desc['pgp_key_remove'] = False

    admin_user = db_create_user(session, tid, admin_desc, language)
    admin_user.password_change_needed = False
    admin_user.password_change_date = datetime_now()

    receiver_desc = models.User().dict(language)
    receiver_desc['name'] = request['receiver_name']
    receiver_desc['username'] = 'recipient'
    receiver_desc['password'] = request['receiver_password']
    receiver_desc['name'] = request['receiver_name']
    receiver_desc['mail_address'] = request['receiver_mail_address']
    receiver_desc['language'] = language
    receiver_desc['role'] = 'receiver'
    receiver_desc['pgp_key_remove'] = False

    receiver_user = db_create_user(session, tid, receiver_desc, language)

    context_desc = models.Context().dict(language)
    context_desc['status'] = 1
    context_desc['name'] = 'Default'
    context_desc['receivers'] = [receiver_user.id]

    context = db_create_context(session, tid, context_desc, language)

    # Root tenants initialization terminates here

    if tid == 1:
        db_refresh_memory_variables(session, [tid])
        return

    # Secondary tenants initialization starts here

    tenant = models.db_get(session, models.Tenant, models.Tenant.id == tid)
    tenant.label = request['node_name']

    mode = node.get_val('mode')

    if mode != 'default':
        node.set_val('hostname', tenant.subdomain + '.' + root_tenant_node.get_val('rootdomain'))

        for varname in ['reachable_via_web',
                        'enable_receipt_hint',
                        'disable_privacy_badge',
                        'simplified_login',
                        'can_delete_submission',
                        'can_postpone_expiration',
                        'anonymize_outgoing_connections',
                        'frame_ancestors',
                        'password_change_period',
                        'default_questionnaire',
                        'enable_password_reset']:
            node.set_val(varname, root_tenant_node.get_val(varname))

        context.questionnaire_id = root_tenant_node.get_val('default_questionnaire')

    # Apply the general settings to apply on all mode != default
    if mode in ['whistleblowing.it', 'eat']:
        # Enable the recipient user to configure platform general settings
        receiver_user.can_edit_general_settings = True

        # Set data retention policy to 18 months
        context.tip_timetolive = 540

        # Delete the admin user
        request['admin_password'] = ''
        session.delete(admin_user)

    # Apply the specific fixes related to whistleblowing.it projects
    if mode == 'whistleblowing.it':
        node.set_val('simplified_login', True)
        node.set_val('tor', False)

        # Enable recipients to load files to the whistleblower
        context.enable_rc_to_wb_files = True

        # Set the recipient name equal to the node name
        receiver_user.name = request['node_name']

    db_refresh_memory_variables(session, [tid])


class Wizard(BaseHandler):
    """
    Setup Wizard handler
    """
    check_roles = 'none'
    invalidate_cache = True

    def post(self):
        request = self.validate_message(self.request.content.read(),
                                        requests.WizardDesc)

        return tw(db_wizard, self.request.tid, request, self.request.client_using_tor, self.request.language)

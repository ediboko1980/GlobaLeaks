# -*- coding: utf-8
# GlobaLeaks Utility used to handle Mail, format, exception, etc
from io import BytesIO

from email import utils  # pylint: disable=no-name-in-module
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.mail.smtp import ESMTPSenderFactory
from twisted.protocols import tls

from globaleaks.utils.socks import SOCKS5ClientEndpoint
from globaleaks.utils.tls import TLSClientContextFactory
from globaleaks.utils.log import log


def MIME_mail_build(src_name, src_mail, dest_name, dest_mail, title, mail_body):
    # This example is of an email with text and html alternatives.
    multipart = MIMEMultipart('alternative')

    # We need to use Header objects here instead of just assigning the strings in
    # order to get our headers properly encoded (with QP).
    # You may want to avoid this if your headers are already ASCII, just so people
    # can read the raw message without getting a headache.
    multipart['Subject'] = Header(title.encode(), 'UTF-8').encode()
    multipart['Date'] = utils.formatdate()
    multipart['To'] = Header(dest_name.encode(), 'UTF-8').encode() + " <" + dest_mail + ">"
    multipart['From'] = Header(src_name.encode(), 'UTF-8').encode() + " <" + src_mail + ">"
    multipart['X-Mailer'] = "fnord"

    multipart.attach(MIMEText(mail_body.encode(), 'plain', 'UTF-8'))

    multipart_as_bytes = multipart.as_bytes()  # pylint: disable=no-member

    return BytesIO(multipart_as_bytes)  # pylint: disable=no-member


def sendmail(tid, smtp_host, smtp_port, security, authentication, username, password, from_name, from_address, to_address, subject, body, anonymize=True, socks_host='127.0.0.1', socks_port=9050):
    """
    Send an email using SMTPS/SMTP+TLS and maybe torify the connection.

    @param to_address: the 'To:' field of the email
    @param subject: the mail subject
    @param body: the mail body

    @return: a {Deferred} that returns a success {bool} if the message was passed
             to the server.
             :param tid:
             :param smtp_host:
             :param smtp_port:
             :param security:
             :param authentication:
             :param username:
             :param password:
             :param from_name:
             :param from_address:
             :param anonymize:
             :param socks_host:
             :param socks_port:
    """
    try:
        timeout = 30

        message = MIME_mail_build(from_name,
                                  from_address,
                                  to_address,
                                  to_address,
                                  subject,
                                  body)

        log.debug('Sending email to %s using SMTP server [%s:%d] [%s]',
                  to_address,
                  smtp_host,
                  smtp_port,
                  security,
                  tid=tid)

        context_factory = TLSClientContextFactory()

        smtp_deferred = defer.Deferred()

        factory = ESMTPSenderFactory(
            username.encode() if authentication else None,
            password.encode() if authentication else None,
            from_address,
            to_address,
            message,
            smtp_deferred,
            contextFactory=context_factory,
            requireAuthentication=authentication,
            requireTransportSecurity=(security == 'TLS'),
            retries=0,
            timeout=timeout)

        if security == "SSL":
            factory = tls.TLSMemoryBIOFactory(context_factory, True, factory)

        if anonymize:
            socksProxy = TCP4ClientEndpoint(reactor, socks_host, socks_port, timeout=timeout)
            endpoint = SOCKS5ClientEndpoint(smtp_host, smtp_port, socksProxy)
        else:
            endpoint = TCP4ClientEndpoint(reactor, smtp_host, smtp_port, timeout=timeout)

        conn_deferred = endpoint.connect(factory)

        final = defer.DeferredList([conn_deferred, smtp_deferred], fireOnOneErrback=True, consumeErrors=True)

        def failure_cb(failure):
            """
            @param failure {Failure {twisted.internet.FirstError {Failure}}}
            """
            log.err("SMTP connection failed (Exception: %s)",
                    failure.value.subFailure.value, tid=tid)
            log.debug(failure)
            return False

        def success_cb(results):
            """
            @param results {list of (success, return_val) tuples}
            """
            return True

        return final.addCallbacks(success_cb, failure_cb)

    except Exception as excep:
        # avoids raising an exception inside email logic to avoid chained errors
        log.err("Unexpected exception in sendmail: %s", str(excep), tid=tid)
        return defer.succeed(False)

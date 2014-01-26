#!/usr/bin/python


import os
import optparse
import subprocess
import contextlib


from M2Crypto import SSL, X509


def getChainFromSSL(host):
    '''Return certificate from SSL handlshake

    Parameters:
    host -- (host, port)

    '''
    def check_ignore(*args, **kw):
        return True

    ctx = SSL.Context()
    ctx.set_verify(SSL.verify_none, 10)
    with contextlib.closing(SSL.Connection(ctx)) as sock:
        # we would like to ignore any issue with certificates
        sock.set_post_connection_check_callback(check_ignore)
        sock.connect(host)
        # if we do not shutdown some sites hungs on close
        sock.shutdown(3)
        return [c.as_pem() for c in sock.get_peer_cert_chain()]


def main():
    parser = optparse.OptionParser()
    parser.add_option(
        '--host',
        dest='host',
        default='localhost',
        help='host to connect to [localhost]',
    )
    parser.add_option(
        '--port',
        dest='port',
        default='443',
        help='port to connect to [443]',
    )
    parser.add_option(
        '--keystore',
        dest='keystore',
        metavar='FILE',
        help='key store to write',
    )
    parser.add_option(
        '--storepass',
        dest='storepass',
        default='changeit',
        help='key store password [changeit]',
    )
    parser.add_option(
        '--keytool',
        dest='keytool',
        metavar='FILE',
        default='keytool',
        help='keytool path [keytool]',
    )
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error('incorrect number of arguments')
    if options.keystore is None:
        parser.error('please specify store to write into')

    tmp = "%s.tmp" % options.keystore
    if os.path.exists(tmp):
        os.unlink(tmp)
    for c in getChainFromSSL((options.host, int(options.port)))[1:]:
        cert = X509.load_cert_string(c, X509.FORMAT_PEM)
        p = subprocess.Popen(
            (
                options.keytool,
                '-import',
                '-noprompt',
                '-trustcacerts',
                '-storetype', 'JKS',
                '-keystore', tmp,
                '-storepass', options.storepass,
                '-alias', str(cert.get_subject()),
            ),
            stdin=subprocess.PIPE,
            close_fds=True,
        )
        p.communicate(input=c)
        if p.returncode != 0:
            raise RuntimeError('keytool failed')
    if os.path.exists(tmp):
        os.rename(tmp, options.keystore)

main()

# vim: expandtab tabstop=4 shiftwidth=4

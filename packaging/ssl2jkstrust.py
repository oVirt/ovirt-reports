#!/usr/bin/python


import os
import optparse
import subprocess


from M2Crypto import SSL, X509


def getChainFromSSL(host):
    '''Return certificate from SSL handlshake

    Parameters:
    host -- (host, port)

    '''
    # openssl verify callback does not
    # accept context, so we collect the chain
    # in semi-global dictionary
    #
    # a certificate may be revisit more than one time.
    #
    # format:
    #   depth: certificate
    chain = {}

    def verify(ok, store):
        chain[store.get_error_depth()] = store.get_current_cert().as_pem()
        return True

    def check_ignore(*args, **kw):
        return True

    ctx = SSL.Context()
    ctx.set_verify(
        SSL.verify_peer | SSL.verify_fail_if_no_peer_cert,
        depth=10,
        callback=verify
    )
    sock = SSL.Connection(ctx)
    # we would like to ignore any issue with certificates
    sock.set_post_connection_check_callback(check_ignore)
    sock.connect(host)
    sock.close()

    # return sorted by depth
    # first is end certificate
    return [chain[depth] for depth in sorted(chain.keys())]


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
    os.rename(tmp, options.keystore)

main()

# vim: expandtab tabstop=4 shiftwidth=4

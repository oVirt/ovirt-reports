#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""apache PKI plugin."""


import contextlib
import os
import tempfile
import urllib2


import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from M2Crypto import X509
from M2Crypto import EVP
from M2Crypto import RSA


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import util
from otopi import plugin


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons


@util.export
class Plugin(plugin.PluginBase):
    """apache pki plugin."""

    def _genReq(self):

        rsa = RSA.gen_key(
            self.environment[oreportscons.ConfigEnv.KEY_SIZE],
            65537,
        )
        rsapem = rsa.as_pem(cipher=None)
        evp = EVP.PKey()
        evp.assign_rsa(rsa)
        rsa = None  # should not be freed here
        req = X509.Request()
        req.set_pubkey(evp)
        req.sign(evp, 'sha1')
        return rsapem, req.as_pem(), req.get_pubkey().as_pem(cipher=None)

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._enabled = False
        self._need_key = False
        self._need_cert = False
        self._need_ca_cert = False
        self._csr_file = None

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.APACHE_CERTIFICATE,
            None
        )
        self.environment.setdefault(
            oreportscons.ConfigEnv.APACHE_CA_CERTIFICATE,
            None
        )
        self.environment.setdefault(
            oreportscons.ConfigEnv.PKI_APACHE_CSR_FILENAME,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        before=(
            oengcommcons.Stages.DIALOG_TITLES_E_PKI,
        ),
        after=(
            oreportscons.Stages.CORE_ENABLE,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
            oengcommcons.Stages.DIALOG_TITLES_S_PKI,
        ),
        condition=lambda self: (
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] and
            # If on same host as engine, engine setup code creates pki for us
            not self.environment[
                oreportscons.EngineCoreEnv.ENABLE
            ]
        ),
    )
    def _customization(self):
        self._enabled = True

        engine_apache_pki_found = (
            os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            ) and os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            ) and os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )
        )

        if not engine_apache_pki_found:
            self._need_cert = not os.path.exists(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT
            )
            self._need_key = not os.path.exists(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY
            )
            self._need_ca_cert = not os.path.exists(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT
            )

        if self._need_key:
            self._key, req, my_pubk = self._genReq()
            self._need_cert = True

        if (
            self._need_cert and
            self.environment[
                oreportscons.ConfigEnv.APACHE_CERTIFICATE
            ] is None
        ):
            csr_fname = self.environment[
                oreportscons.ConfigEnv.PKI_APACHE_CSR_FILENAME
            ]
            with (
                open(csr_fname, 'w') if csr_fname
                else tempfile.NamedTemporaryFile(mode='w', delete=False)
            ) as self._csr_file:
                self._csr_file.write(req)

            remote_name = '{name}-{fqdn}'.format(
                name=oreportscons.Const.PKI_REPORTS_APACHE_CERT_NAME,
                fqdn=self.environment[osetupcons.ConfigEnv.FQDN],
            )
            enroll_command = (
                " /usr/share/ovirt-engine/bin/pki-enroll-request.sh \\\n"
                "     --name={remote_name} \\\n"
                "     --subject=\""
                "$(openssl x509 -in {pkidir}/ca.pem -noout "
                "-subject | sed 's;subject= \(/C=[^/]*/O=[^/]*\)/.*;\\1;')"
                "/CN={fqdn}\""
            ).format(
                remote_name=remote_name,
                pkidir=oreportscons.FileLocations.OVIRT_ENGINE_PKIDIR,
                fqdn=self.environment[osetupcons.ConfigEnv.FQDN],
            )

            self.dialog.note(
                text=_(
                    "\nTo sign the Apache certificate on the engine server, "
                    "please:\n\n"
                    "1. Copy {tmpcsr} from here to {enginecsr} on the engine "
                    "server.\n\n"
                    "2. Run on the engine server:\n\n"
                    "{enroll_command}\n\n"
                    "3. Copy {enginecert} from the engine server to some file "
                    "here. Provide the file name below.\n\n"
                    "See {url} for more details, including using an external "
                    "certificate authority."
                ).format(
                    tmpcsr=self._csr_file.name,
                    enginecsr='{pkireqdir}/{remote_name}.req'.format(
                        pkireqdir=oreportscons.FileLocations.
                            OVIRT_ENGINE_PKIREQUESTSDIR,
                        remote_name=remote_name,
                    ),
                    enroll_command=enroll_command,
                    enginecert='{pkicertdir}/{remote_name}.cer'.format(
                        pkicertdir=oreportscons.FileLocations.
                            OVIRT_ENGINE_PKICERTSDIR,
                        remote_name=remote_name,
                    ),
                    url="http://www.ovirt.org/Features/Separate-Reports-Host",
                ),
            )

            goodcert = False
            while not goodcert:
                filename = self.dialog.queryString(
                    name='REPORTS_APACHE_CERT_FILENAME',
                    note=_(
                        '\nPlease input the location of the file where you '
                        'copied the signed certificate in step 3 above: '
                    ),
                    prompt=True,
                )
                try:
                    with open(filename) as f:
                        cert = f.read()
                    goodcert = my_pubk == X509.load_cert_string(
                        cert
                    ).get_pubkey().as_pem(cipher=None)
                    self.environment[
                        oreportscons.ConfigEnv.APACHE_CERTIFICATE
                    ] = cert
                    if not goodcert:
                        self.logger.error(
                            _(
                                'The certificate in {cert} does not match '
                                'the request in {req}. Please try again.'
                            ).format(
                                cert=filename,
                                req=self._csr_file.name,
                            )
                        )
                except:
                    self.logger.error(
                        _(
                            'Error while reading or parsing {cert}. '
                            'Please try again.'
                        ).format(
                            cert=filename,
                        )
                    )
                    self.logger.debug('Error reading cert', exc_info=True)
            self.logger.info(_('Apache certificate read successfully'))

        while (
            self._need_ca_cert and
            self.environment[
                oreportscons.ConfigEnv.APACHE_CA_CERTIFICATE
            ] is None
        ):
            remote_engine_host = self.environment[
                oreportscons.EngineConfigEnv.ENGINE_FQDN
            ]

            with contextlib.closing(
                urllib2.urlopen(
                    'http://{engine_fqdn}/ovirt-engine/services/'
                    'pki-resource?resource=ca-certificate&'
                    'format=X509-PEM'.format(
                        engine_fqdn=remote_engine_host
                    )
                )
            ) as urlObj:
                engine_ca_cert = urlObj.read()
                if engine_ca_cert:
                    self.environment[
                        oreportscons.ConfigEnv.APACHE_CA_CERTIFICATE
                    ] = engine_ca_cert
                else:
                    self.logger.error(
                        _(
                            'Failed to get CA Certificate from engine. '
                            'Please try again.'
                        )
                    )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: (
            self._enabled
        ),
        after=(
            oreportscons.Stages.CA_AVAILABLE,
            oreportscons.Stages.PKI_MISC,
        ),
    )
    def _misc_pki(self):
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].createGroup(
            group='ca_pki_reports',
            description='Reports PKI keys',
            optional=True,
        ).addFiles(
            group='ca_pki_reports',
            fileList=uninstall_files,
        )

        if self._need_key:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.FileLocations.
                    OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self._key,
                    modifiedList=uninstall_files,
                )
            )
            os.symlink(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            )

        if self._need_cert:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.FileLocations.
                    OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self.environment[
                        oreportscons.ConfigEnv.APACHE_CERTIFICATE
                    ],
                    modifiedList=uninstall_files,
                )
            )
            os.symlink(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )

        if self._need_ca_cert:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.FileLocations.
                    OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self.environment[
                        oreportscons.ConfigEnv.APACHE_CA_CERTIFICATE
                    ],
                    modifiedList=uninstall_files,
                )
            )
            os.symlink(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            )

    @plugin.event(
        stage=plugin.Stages.STAGE_CLEANUP,
    )
    def _cleanup(self):
        if self._csr_file is not None:
            try:
                os.unlink(self._csr_file.name)
            except OSError as e:
                self.logger.debug(
                    "Failed to delete '%s'",
                    self._csr_file.name,
                    exc_info=True,
                )


# vim: expandtab tabstop=4 shiftwidth=4

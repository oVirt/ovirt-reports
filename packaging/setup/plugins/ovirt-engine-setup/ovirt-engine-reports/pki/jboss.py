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


"""jboss PKI plugin."""


import os


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
from ovirt_engine_setup.reports import constants as oreportscons


@util.export
class Plugin(plugin.PluginBase):
    """jboss pki plugin."""

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
        return rsapem, req.as_pem()

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._enabled = False
        self._need_key = False
        self._need_cert = False
        self._on_separate_h = False

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.JBOSS_CERTIFICATE_CHAIN,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            oreportscons.Stages.CORE_ENABLE,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
        ),
        condition=lambda self: (
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] and
            # If on same host as engine, engine setup creates pki for us
            not self.environment[
                oreportscons.EngineCoreEnv.ENABLE
            ]
        ),
    )
    def _customization(self):
        self._enabled = True

        self._need_cert = not os.path.exists(
            oreportscons.FileLocations.
            OVIRT_ENGINE_PKI_REPORTS_JBOSS_CERT
        )

        self._need_key = not os.path.exists(
            oreportscons.FileLocations.
            OVIRT_ENGINE_PKI_REPORTS_JBOSS_KEY
        )

        if self._need_key:
            self._key, req = self._genReq()

        if (
            self._need_cert and
            self.environment[
                oreportscons.ConfigEnv.JBOSS_CERTIFICATE_CHAIN
            ] is None
        ):
            self.dialog.displayMultiString(
                name='REPORTS_JBOSS_CERTIFICATE_REQUEST',
                value=req.splitlines(),
                note=_(
                    '\n\nPlease issue Reports certificate based '
                    'on this certificate request\n\n'
                ),
            )

            self.dialog.note(
                text=_(
                    "Enroll SSL certificate for the Reports service.\n"
                    "It can be done using engine internal CA, if no 3rd "
                    "party CA is available, with this sequence:\n"

                    "1. Copy and save certificate request at\n"
                    "    /etc/pki/ovirt-engine/requests/{name}.req\n"
                    "on the engine server\n\n"
                    "2. execute, on the engine host, this command "
                    "to enroll the cert:\n"
                    " /usr/share/ovirt-engine/bin/pki-enroll-request.sh \\\n"
                    "     --name={name} \\\n"
                    "     --subject=\"/C=<country>/O=<organization>/"
                    "CN={fqdn}\"\n"
                    "Substitute <country>, <organization> to suite your "
                    "environment\n"
                    "(i.e. the values must match values in the "
                    "certificate authority of your engine)\n\n"

                    "3. Certificate will be available at\n"
                    "    /etc/pki/ovirt-engine/certs/{name}.cer\n"
                    "on the engine host, please copy that content here "
                    "when required\n"
                ).format(
                    fqdn=self.environment[osetupcons.ConfigEnv.FQDN],
                    name=oreportscons.Const.PKI_REPORTS_JBOSS_CERT_NAME,
                ),
            )

            self.environment[
                oreportscons.ConfigEnv.JBOSS_CERTIFICATE_CHAIN
            ] = self.dialog.queryMultiString(
                name='REPORTS_JBOSS_CERTIFICATE_CHAIN',
                note=_(
                    '\n\nPlease input Reports certificate chain that '
                    'matches certificate request, (issuer is not '
                    'mandatory, from intermediate and upper)\n\n'
                ),
            )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: (
            self._enabled
        ),
        after=(
            oreportscons.Stages.CA_AVAILABLE,
            oreportscons.Stages.PKI_MISC,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
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
                    OVIRT_ENGINE_PKI_REPORTS_JBOSS_KEY,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self._key,
                    modifiedList=uninstall_files,
                )
            )

        if self._need_cert:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.FileLocations.
                    OVIRT_ENGINE_PKI_REPORTS_JBOSS_CERT,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self.environment[
                        oreportscons.ConfigEnv.JBOSS_CERTIFICATE_CHAIN
                    ],
                    modifiedList=uninstall_files,
                )
            )


# vim: expandtab tabstop=4 shiftwidth=4
